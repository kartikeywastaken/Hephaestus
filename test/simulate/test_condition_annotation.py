# -*- coding: utf-8 -*-
"""
Tests for Phase 5.5 branch predicate annotations.
"""

from __future__ import annotations

import re
import os
import json
import tempfile
import pytest
from src.ir.source.models import (
    ReconstructedFunction,
    SourceReconstructionArtifact,
    SCHEMA_VERSION,
)
from src.ir.source.condition_recovery import analyze_condition_sites, get_entry_block
from src.ir.source.control_emitter import emit_regions_to_c
from src.ir.source.c_emitter import emit_recovered_c
from src.ir.source.reconstructor import build_source_reconstruction


def strip_c_comments(s: str) -> str:
    return re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)


class TestConditionAnnotation:

    def _emit_to_string(self, artifact):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".c", delete=False
        ) as f:
            path = f.name
        try:
            emit_recovered_c(artifact, path)
            with open(path, "r") as f:
                return f.read()
        finally:
            os.unlink(path)

    # Test 1 — Schema update
    def test_1_schema_update(self):
        assert SCHEMA_VERSION == "5.5.0"
        artifact = SourceReconstructionArtifact()
        assert artifact.schema_version == "5.5.0"

    # Test 2 — Condition expressions remain zero
    def test_2_condition_expressions_remain_zero(self):
        artifact = SourceReconstructionArtifact()
        assert artifact.summary["condition_expressions_recovered"] == 0

    # Test 3 — Loop condition annotation from branch evidence
    def test_3_loop_condition_annotation_from_branch_evidence(self):
        structured_regions = [
            {
                "type": "loop",
                "kind": "while_like",
                "header_block": "0x1000",
                "exit_blocks": ["0x1008"],
                "body": {"type": "block", "id": "0x1004"}
            }
        ]
        lowered_blocks = {
            "0x1000": [
                {
                    "kind": "instruction",
                    "text": "tmp_w8 = tmp_w8 + 1;",
                    "address": "0x1000",
                    "source_instruction": {"mnemonic": "subs", "raw": "subs w8, w8, #0xa"}
                },
                {
                    "kind": "branch_comment",
                    "text": "/* branch to exit */",
                    "address": "0x1004",
                    "source_instruction": {"mnemonic": "b.ge", "raw": "b.ge 0x1008"}
                }
            ],
            "0x1004": [],
            "0x1008": []
        }
        res = analyze_condition_sites(structured_regions, lowered_blocks, architecture="arm64")
        assert res["condition_sites_with_evidence"] == 1
        site = res["sites"][0]
        assert "b.ge at 0x1004" in site["annotation"]
        assert "after subs at 0x1000" in site["annotation"]
        assert "target 0x1008" in site["annotation"]
        assert "loop polarity inverted" in site["annotation"]

        # Emission check
        fn = ReconstructedFunction(
            name="loop_fn",
            canonical_name="loop_fn",
            c_name="loop_fn",
            return_type="void",
            structured_regions=structured_regions,
            lowered_blocks=lowered_blocks,
            condition_recovery=res,
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        
        # Must contain comment evidence
        assert "while (/* condition evidence: b.ge at 0x1004 after subs at 0x1000; target 0x1008; loop polarity inverted */)" in c_code
        
        # Executable check
        for line in c_code.splitlines():
            s = line.strip()
            if s.startswith("while ("):
                exec_part = strip_c_comments(s)
                assert "tmp_" not in exec_part
                assert "arg" not in exec_part

    # Test 4 — If condition annotation from cbz
    def test_4_if_condition_annotation_from_cbz(self):
        structured_regions = [
            {
                "type": "if",
                "condition_block": "0x1000",
                "then_branch": {"type": "block", "id": "0x1004"},
                "merge_block": "0x1008"
            }
        ]
        lowered_blocks = {
            "0x1000": [
                {
                    "kind": "branch_comment",
                    "text": "/* cbz w8 */",
                    "address": "0x1000",
                    "source_instruction": {"mnemonic": "cbz", "raw": "cbz w8, 0x1004"}
                }
            ],
            "0x1004": [],
            "0x1008": []
        }
        res = analyze_condition_sites(structured_regions, lowered_blocks, architecture="arm64")
        assert res["condition_sites_with_evidence"] == 1
        site = res["sites"][0]
        assert "cbz w8 at 0x1000 targeting 0x1004" in site["annotation"]
        assert "polarity direct" in site["annotation"]

        fn = ReconstructedFunction(
            name="if_fn",
            canonical_name="if_fn",
            c_name="if_fn",
            return_type="void",
            structured_regions=structured_regions,
            lowered_blocks=lowered_blocks,
            condition_recovery=res,
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        assert "if (/* condition evidence: cbz w8 at 0x1000 targeting 0x1004; polarity direct */)" in c_code

    # Test 5 — If-else polarity annotation
    def test_5_if_else_polarity_annotation(self):
        structured_regions = [
            {
                "type": "if_else",
                "condition_block": "0x1000",
                "then_branch": {"type": "block", "id": "0x1004"},
                "else_branch": {"type": "block", "id": "0x1008"},
                "merge_block": "0x100c"
            }
        ]
        # target matches else_branch entry -> inverted
        lowered_blocks = {
            "0x1000": [
                {
                    "kind": "branch_comment",
                    "text": "/* cbz w8 */",
                    "address": "0x1000",
                    "source_instruction": {"mnemonic": "cbz", "raw": "cbz w8, 0x1008"}
                }
            ],
            "0x1004": [],
            "0x1008": [],
            "0x100c": []
        }
        res = analyze_condition_sites(structured_regions, lowered_blocks, architecture="arm64")
        assert res["sites"][0]["polarity"] == "inverted"
        assert "polarity inverted" in res["sites"][0]["annotation"]

        fn = ReconstructedFunction(
            name="ifelse_fn",
            canonical_name="ifelse_fn",
            c_name="ifelse_fn",
            return_type="void",
            structured_regions=structured_regions,
            lowered_blocks=lowered_blocks,
            condition_recovery=res,
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        assert "if (/* condition evidence: cbz w8 at 0x1000 targeting 0x1008; polarity inverted */)" in c_code
        # Branches order remains direct
        then_idx = c_code.index("block 0x1004")
        else_idx = c_code.index("block 0x1008")
        assert then_idx < else_idx

    # Test 6 — Unknown condition fallback preserved
    def test_6_unknown_condition_fallback_preserved(self):
        structured_regions = [
            {
                "type": "if",
                "condition_block": "0x1000",
                "then_branch": {"type": "block", "id": "0x1004"},
                "merge_block": "0x1008"
            }
        ]
        lowered_blocks = {
            "0x1000": [],
            "0x1004": [],
            "0x1008": []
        }
        res = analyze_condition_sites(structured_regions, lowered_blocks, architecture="arm64")
        assert res["condition_sites_with_evidence"] == 0
        assert res["condition_sites_unknown"] == 1

        fn = ReconstructedFunction(
            name="fallback_fn",
            canonical_name="fallback_fn",
            c_name="fallback_fn",
            return_type="void",
            structured_regions=structured_regions,
            lowered_blocks=lowered_blocks,
            condition_recovery=res,
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        assert "if (/* condition unknown: block 0x1000 */)" in c_code

    # Test 7 — Unsupported architecture stays unknown
    def test_7_unsupported_architecture_stays_unknown(self):
        structured_regions = [
            {
                "type": "if",
                "condition_block": "0x1000",
                "then_branch": {"type": "block", "id": "0x1004"},
                "merge_block": "0x1008"
            }
        ]
        lowered_blocks = {
            "0x1000": [
                {
                    "kind": "branch_comment",
                    "text": "/* cbz w8 */",
                    "address": "0x1000",
                    "source_instruction": {"mnemonic": "cbz", "raw": "cbz w8, 0x1004"}
                }
            ],
            "0x1004": [],
            "0x1008": []
        }
        res = analyze_condition_sites(structured_regions, lowered_blocks, architecture="x86_64")
        assert res["condition_sites_total"] == 1
        assert res["condition_sites_with_evidence"] == 0
        assert res["condition_sites_unknown"] == 1

    # Test 8 — No cross-block condition recovery
    def test_8_no_cross_block_condition_recovery(self):
        structured_regions = [
            {
                "type": "if",
                "condition_block": "0x1004",
                "then_branch": {"type": "block", "id": "0x1008"},
                "merge_block": "0x100c"
            }
        ]
        # compare is in block 0x1000, branch is in block 0x1004
        lowered_blocks = {
            "0x1000": [
                {
                    "kind": "instruction",
                    "text": "cmp w8, #1",
                    "address": "0x1000",
                    "source_instruction": {"mnemonic": "cmp", "raw": "cmp w8, #1"}
                }
            ],
            "0x1004": [
                {
                    "kind": "branch_comment",
                    "text": "/* b.eq 0x1008 */",
                    "address": "0x1004",
                    "source_instruction": {"mnemonic": "b.eq", "raw": "b.eq 0x1008"}
                }
            ],
            "0x1008": [],
            "0x100c": []
        }
        res = analyze_condition_sites(structured_regions, lowered_blocks, architecture="arm64")
        site = res["sites"][0]
        # Should not associate compare from block 0x1000
        assert site["compare_address"] is None
        assert "compare/test producer unknown" in site["annotation"]

    # Test 9 — Stop at clobber boundary
    def test_9_stop_at_clobber_boundary(self):
        structured_regions = [
            {
                "type": "if",
                "condition_block": "0x1000",
                "then_branch": {"type": "block", "id": "0x1004"},
                "merge_block": "0x1008"
            }
        ]
        # call is a clobber boundary, compare is before it
        lowered_blocks = {
            "0x1000": [
                {
                    "kind": "instruction",
                    "text": "cmp w8, #1",
                    "address": "0x1000",
                    "source_instruction": {"mnemonic": "cmp", "raw": "cmp w8, #1"}
                },
                {
                    "kind": "call",
                    "text": "call_some();",
                    "address": "0x1004",
                    "source_instruction": {"mnemonic": "bl", "raw": "bl call_some"}
                },
                {
                    "kind": "branch_comment",
                    "text": "/* b.eq 0x1004 */",
                    "address": "0x1008",
                    "source_instruction": {"mnemonic": "b.eq", "raw": "b.eq 0x1004"}
                }
            ],
            "0x1004": [],
            "0x1008": []
        }
        res = analyze_condition_sites(structured_regions, lowered_blocks, architecture="arm64")
        assert res["sites"][0]["compare_address"] is None

    # Test 10 — Existing return/call refinement preserved
    def test_10_existing_return_call_refinement_preserved(self):
        # We need to verify that a reconstructed function contains Phase 5.4 refinements
        structured_regions = [
            {
                "type": "sequence",
                "children": [
                    {"type": "block", "id": "0x1000"},
                    {
                        "type": "if",
                        "condition_block": "0x1000",
                        "then_branch": {"type": "block", "id": "0x1004"},
                        "merge_block": "0x1008"
                    }
                ]
            }
        ]
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "tmp_x0 = 42;", "address": "0x1000"},
                {"kind": "call", "text": "call_0x2000(); /* bl 0x2000 */", "address": "0x1002"},
                {"kind": "branch_comment", "text": "/* b.eq 0x1004 */", "address": "0x1004", "source_instruction": {"mnemonic": "b.eq", "raw": "b.eq 0x1004"}},
            ],
            "0x1004": [
                {"kind": "instruction", "text": "tmp_w0 = 1;", "address": "0x1006"},
                {"kind": "return_comment", "text": "/* return via x0 */", "address": "0x1008", "source_instruction": {"mnemonic": "ret"}},
            ],
            "0x1008": []
        }
        
        # Simulate full reconstructor run
        # Direct call refinement should exist:
        from src.ir.source.callsite_refinement import analyze_call_sites
        res_calls = analyze_call_sites(lowered_blocks, architecture="arm64")
        assert res_calls["sites"][0]["refined_text"] is not None

        # Return recovery should exist:
        from src.ir.source.return_recovery import analyze_return_sites
        res_rets = analyze_return_sites(lowered_blocks, return_type="i32", architecture="arm64")
        assert res_rets["sites"][0]["replacement_text"] is not None

        # Condition recovery
        res_conds = analyze_condition_sites(structured_regions, lowered_blocks, architecture="arm64")

        fn = ReconstructedFunction(
            name="pres_fn",
            canonical_name="pres_fn",
            c_name="pres_fn",
            return_type="i32",
            structured_regions=structured_regions,
            lowered_blocks=lowered_blocks,
            callsite_refinement=res_calls,
            return_recovery=res_rets,
            condition_recovery=res_conds,
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)

        assert "call_0x2000(tmp_x0); /* bl 0x2000; args refined from same-block evidence */" in c_code
        assert "return 1; /* return constant from w0 before ret */" in c_code
        assert "if (/* condition evidence: b.eq at 0x1004" in c_code

    # Test 11 — No fake source variables
    def test_11_no_fake_source_variables(self):
        # We ensure no source variable names like i, n, acc exist in executable block
        artifact = SourceReconstructionArtifact()
        c_code = self._emit_to_string(artifact)
        executable = strip_c_comments(c_code)
        for keyword in ("acc", "values", "result", "ctx", "item"):
            assert keyword not in executable

    # Test 12 — No structs/fields/arrows
    def test_12_no_structs_fields_arrows(self):
        artifact = SourceReconstructionArtifact()
        c_code = self._emit_to_string(artifact)
        executable = strip_c_comments(c_code)
        assert "->" not in executable
        assert "struct " not in executable
        assert ".id" not in executable
        assert ".ctx" not in executable

    # Test 13 — No raw bracket syntax leak
    def test_13_no_raw_bracket_syntax_leak(self):
        artifact = SourceReconstructionArtifact()
        c_code = self._emit_to_string(artifact)
        for line in c_code.splitlines():
            assert not line.strip().startswith("[")

    # Test 14 — Summary metrics
    def test_14_summary_metrics(self):
        artifact = SourceReconstructionArtifact()
        s = artifact.summary
        assert "condition_sites_total" in s
        assert "condition_sites_with_evidence" in s
        assert "condition_sites_unknown" in s
        assert "condition_annotations_recovered" in s
        assert "conditions_inverted_for_structure" in s
        assert "ambiguous_condition_sites" in s

    # Test A — Annotation Values Are Comment Content Only
    def test_A_annotation_values_are_comment_content_only(self):
        structured_regions = [
            {
                "type": "if",
                "condition_block": "0x1000",
                "then_branch": {"type": "block", "id": "0x1004"},
                "merge_block": "0x1008"
            }
        ]
        lowered_blocks = {
            "0x1000": [
                {
                    "kind": "branch_comment",
                    "text": "/* cbz w8 */",
                    "address": "0x1000",
                    "source_instruction": {"mnemonic": "cbz", "raw": "cbz w8, 0x1004"}
                }
            ],
            "0x1004": [],
            "0x1008": []
        }
        res = analyze_condition_sites(structured_regions, lowered_blocks, architecture="arm64")
        for site in res["sites"]:
            annot = site["annotation"]
            assert "/*" not in annot
            assert "*/" not in annot

    # Test B — Same Block Can Produce Multiple Sites
    def test_B_same_block_can_produce_multiple_sites(self):
        structured_regions = [
            {
                "type": "loop",
                "kind": "while_like",
                "header_block": "0x1000",
                "body": {
                    "type": "if_else",
                    "condition_block": "0x1000",
                    "then_branch": {"type": "block", "id": "0x1004"},
                    "else_branch": {"type": "block", "id": "0x1008"},
                    "merge_block": "0x100c"
                }
            }
        ]
        lowered_blocks = {
            "0x1000": [
                {
                    "kind": "branch_comment",
                    "text": "/* cbz w8 */",
                    "address": "0x1000",
                    "source_instruction": {"mnemonic": "cbz", "raw": "cbz w8, 0x1008"}
                }
            ],
            "0x1004": [],
            "0x1008": [],
            "0x100c": []
        }
        res = analyze_condition_sites(structured_regions, lowered_blocks, architecture="arm64")
        # Same block 0x1000 acts as both loop header and if_else condition site. Total sites should be 2.
        assert res["condition_sites_total"] == 2

    # Test C — Earlier Branch Stops Compare Scan
    def test_C_earlier_branch_stops_compare_scan(self):
        structured_regions = [
            {
                "type": "if",
                "condition_block": "0x1000",
                "then_branch": {"type": "block", "id": "0x1004"},
                "merge_block": "0x1008"
            }
        ]
        lowered_blocks = {
            "0x1000": [
                {
                    "kind": "instruction",
                    "text": "subs w8, w8, #1",
                    "address": "0x1000",
                    "source_instruction": {"mnemonic": "subs", "raw": "subs w8, w8, #1"}
                },
                {
                    "kind": "branch_comment",
                    "text": "/* b.eq 0xAAA */",
                    "address": "0x1004",
                    "source_instruction": {"mnemonic": "b.eq", "raw": "b.eq 0xAAA"}
                },
                {
                    "kind": "instruction",
                    "text": "subs w9, w9, #2",
                    "address": "0x1008",
                    "source_instruction": {"mnemonic": "subs", "raw": "subs w9, w9, #2"}
                },
                {
                    "kind": "branch_comment",
                    "text": "/* b.ne 0xBBB */",
                    "address": "0x100c",
                    "source_instruction": {"mnemonic": "b.ne", "raw": "b.ne 0xBBB"}
                }
            ],
            "0x1004": [],
            "0x1008": []
        }
        res = analyze_condition_sites(structured_regions, lowered_blocks, architecture="arm64")
        site = res["sites"][0]
        # Should stop at b.eq on 0x1004 and associate with the second subs (0x1008)
        assert site["compare_address"] == "0x1008"
        assert site["compare_mnemonic"] == "subs"

    # Test D — Inverted Polarity Does Not Swap Branches
    def test_D_inverted_polarity_does_not_swap_branches(self):
        structured_regions = [
            {
                "type": "if_else",
                "condition_block": "0x1000",
                "then_branch": {"type": "block", "id": "0x1004"},
                "else_branch": {"type": "block", "id": "0x1008"},
                "merge_block": "0x100c"
            }
        ]
        # target matches else_branch entry -> inverted
        lowered_blocks = {
            "0x1000": [
                {
                    "kind": "branch_comment",
                    "text": "/* cbz w8 */",
                    "address": "0x1000",
                    "source_instruction": {"mnemonic": "cbz", "raw": "cbz w8, 0x1008"}
                }
            ],
            "0x1004": [
                {"kind": "instruction", "text": "tmp_w10 = 100;", "address": "0x1004"}
            ],
            "0x1008": [
                {"kind": "instruction", "text": "tmp_w10 = 200;", "address": "0x1008"}
            ],
            "0x100c": []
        }
        res = analyze_condition_sites(structured_regions, lowered_blocks, architecture="arm64")
        fn = ReconstructedFunction(
            name="ifelse_fn",
            canonical_name="ifelse_fn",
            c_name="ifelse_fn",
            return_type="void",
            structured_regions=structured_regions,
            lowered_blocks=lowered_blocks,
            condition_recovery=res,
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        assert "polarity inverted" in c_code
        # Verifying then-branch text (tmp_w10 = 100) is emitted before else-branch (tmp_w10 = 200)
        idx_100 = c_code.index("tmp_w10 = 100;")
        idx_200 = c_code.index("tmp_w10 = 200;")
        assert idx_100 < idx_200

    # Test E — Unsupported Architecture Counts Unknown Sites
    def test_E_unsupported_architecture_counts_unknown_sites(self):
        structured_regions = [
            {
                "type": "loop",
                "kind": "while_like",
                "header_block": "0x1000",
                "body": {"type": "block", "id": "0x1004"}
            }
        ]
        lowered_blocks = {
            "0x1000": [],
            "0x1004": []
        }
        res = analyze_condition_sites(structured_regions, lowered_blocks, architecture="x86_64")
        assert res["condition_sites_total"] == 1
        assert res["condition_sites_with_evidence"] == 0
        assert res["condition_sites_unknown"] == 1

    # Test F — Partial Branch Evidence
    def test_F_partial_branch_evidence(self):
        structured_regions = [
            {
                "type": "if",
                "condition_block": "0x1000",
                "then_branch": {"type": "block", "id": "0x1004"},
                "merge_block": "0x1008"
            }
        ]
        lowered_blocks = {
            "0x1000": [
                {
                    "kind": "branch_comment",
                    "text": "/* b.ne 0x1004 */",
                    "address": "0x1000",
                    "source_instruction": {"mnemonic": "b.ne", "raw": "b.ne 0x1004"}
                }
            ],
            "0x1004": [],
            "0x1008": []
        }
        res = analyze_condition_sites(structured_regions, lowered_blocks, architecture="arm64")
        site = res["sites"][0]
        assert site["compare_address"] is None
        assert "compare/test producer unknown" in site["annotation"]

    # Test G — No Nested Comment Markers
    def test_G_no_nested_comment_markers(self):
        structured_regions = [
            {
                "type": "if",
                "condition_block": "0x1000",
                "then_branch": {"type": "block", "id": "0x1004"},
                "merge_block": "0x1008"
            }
        ]
        lowered_blocks = {
            "0x1000": [
                {
                    "kind": "branch_comment",
                    "text": "/* b.ne 0x1004 */",
                    "address": "0x1000",
                    "source_instruction": {"mnemonic": "b.ne", "raw": "b.ne 0x1004"}
                }
            ],
            "0x1004": [],
            "0x1008": []
        }
        res = analyze_condition_sites(structured_regions, lowered_blocks, architecture="arm64")
        fn = ReconstructedFunction(
            name="test_nested",
            canonical_name="test_nested",
            c_name="test_nested",
            return_type="void",
            structured_regions=structured_regions,
            lowered_blocks=lowered_blocks,
            condition_recovery=res,
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        assert "/* /*" not in c_code
        assert "*/ */" not in c_code

    # Test H — Executable Condition Grep
    def test_H_executable_condition_grep(self):
        # Scan condition headers, strip comments, verify no register leaks
        structured_regions = [
            {
                "type": "if",
                "condition_block": "0x1000",
                "then_branch": {"type": "block", "id": "0x1004"},
                "merge_block": "0x1008"
            }
        ]
        lowered_blocks = {
            "0x1000": [
                {
                    "kind": "branch_comment",
                    "text": "/* b.ne 0x1004 */",
                    "address": "0x1000",
                    "source_instruction": {"mnemonic": "b.ne", "raw": "b.ne 0x1004"}
                }
            ],
            "0x1004": [],
            "0x1008": []
        }
        res = analyze_condition_sites(structured_regions, lowered_blocks, architecture="arm64")
        fn = ReconstructedFunction(
            name="test_exec",
            canonical_name="test_exec",
            c_name="test_exec",
            return_type="void",
            structured_regions=structured_regions,
            lowered_blocks=lowered_blocks,
            condition_recovery=res,
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)

        for line in c_code.splitlines():
            s = line.strip()
            if s.startswith("while (") or s.startswith("if ("):
                assert "condition unknown" in s or "condition evidence" in s
                exec_only = strip_c_comments(s)
                assert "tmp_" not in exec_only
                assert "arg" not in exec_only
                assert "stack_" not in exec_only
                assert "==" not in exec_only
                assert "!=" not in exec_only
                assert "<" not in exec_only
                assert ">" not in exec_only
                assert "&&" not in exec_only
                assert "||" not in exec_only
