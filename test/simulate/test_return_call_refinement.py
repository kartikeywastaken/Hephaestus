# -*- coding: utf-8 -*-
"""
Tests for Phase 5.4 Return and Call-Site Refinement.
"""

from __future__ import annotations

import os
import tempfile
import pytest
from src.ir.source.models import (
    ReconstructedFunction,
    SourceReconstructionArtifact,
    SCHEMA_VERSION,
)
from src.ir.source.return_recovery import analyze_return_sites
from src.ir.source.callsite_refinement import analyze_call_sites
from src.ir.source.c_emitter import emit_recovered_c
from src.ir.source.reconstructor import build_source_reconstruction


class TestReturnCallRefinement:

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

    # 1. Return register recovered
    def test_1_return_register_recovered(self):
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "tmp_w0 = tmp_w8;", "address": "0x1000"},
                {"kind": "return_comment", "text": "/* return via x0 */", "address": "0x1004", "source_instruction": {"mnemonic": "ret"}}
            ]
        }
        res = analyze_return_sites(lowered_blocks, return_type="i32", architecture="arm64")
        assert res["return_sites_total"] == 1
        assert res["return_sites_with_value"] == 1
        assert res["return_sites_unknown"] == 0
        assert res["return_registers_observed"] == ["w0"]
        assert res["return_expression_kind"] == "register"
        assert res["return_expression"] == "tmp_w0"
        site = res["sites"][0]
        assert site["register"] == "w0"
        assert site["expression_kind"] == "register"
        assert site["expression"] == "tmp_w0"
        assert site["replacement_text"] == "return tmp_w0; /* return value from w0 before ret */"

    # 2. Constant return recovered
    def test_2_constant_return_recovered(self):
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "tmp_w0 = 7;", "address": "0x1000"},
                {"kind": "return_comment", "text": "/* return via x0 */", "address": "0x1004", "source_instruction": {"mnemonic": "ret"}}
            ]
        }
        res = analyze_return_sites(lowered_blocks, return_type="i32", architecture="arm64")
        assert res["return_expression_kind"] == "constant"
        assert res["return_expression"] == "7"
        site = res["sites"][0]
        assert site["register"] == "w0"
        assert site["expression_kind"] == "constant"
        assert site["expression"] == "7"
        assert site["replacement_text"] == "return 7; /* return constant from w0 before ret */"

    # 3. Unknown return fallback
    def test_3_unknown_return_fallback(self):
        lowered_blocks = {
            "0x1000": [
                {"kind": "return_comment", "text": "/* return via x0 */", "address": "0x1004", "source_instruction": {"mnemonic": "ret"}}
            ]
        }
        res = analyze_return_sites(lowered_blocks, return_type="i32", architecture="arm64")
        assert res["return_sites_total"] == 1
        assert res["return_sites_with_value"] == 0
        assert res["return_sites_unknown"] == 1
        assert res["return_expression_kind"] == "unknown"
        assert res["return_expression"] is None

        # Verify C emission fallback return
        fn = ReconstructedFunction(
            name="test_func",
            canonical_name="test_func",
            c_name="test_func",
            return_type="i32",
            lowered_blocks=lowered_blocks,
            return_recovery=res,
            body_status="structured",
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        assert "/* return value unknown */" in c_code
        assert "return 0;" in c_code

    # 4. Multiple return sites disagree
    def test_4_multiple_return_sites_disagree(self):
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "tmp_w0 = 7;", "address": "0x1000"},
                {"kind": "return_comment", "text": "/* return via x0 */", "address": "0x1004", "source_instruction": {"mnemonic": "ret"}}
            ],
            "0x2000": [
                {"kind": "instruction", "text": "tmp_w0 = tmp_w8;", "address": "0x2000"},
                {"kind": "return_comment", "text": "/* return via x0 */", "address": "0x2004", "source_instruction": {"mnemonic": "ret"}}
            ]
        }
        res = analyze_return_sites(lowered_blocks, return_type="i32", architecture="arm64")
        assert res["return_sites_total"] == 2
        assert res["return_sites_with_value"] == 2
        # Function-level return expression is null/unknown when they disagree
        assert res["return_expression_kind"] == "unknown"
        assert res["return_expression"] is None

    # 5. Void return
    def test_5_void_return(self):
        lowered_blocks = {
            "0x1000": [
                {"kind": "return_comment", "text": "/* return via x0 */", "address": "0x1004", "source_instruction": {"mnemonic": "ret"}}
            ]
        }
        res = analyze_return_sites(lowered_blocks, return_type="void", architecture="arm64")
        assert res["return_sites_total"] == 1
        assert res["return_sites_with_value"] == 1
        assert res["return_expression_kind"] == "void"
        assert res["sites"][0]["replacement_text"] == "return; /* void return */"

    # 6. Direct call arguments preserved
    def test_6_direct_call_arguments_preserved(self):
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "tmp_x0 = 5;", "address": "0x1000"},
                {"kind": "instruction", "text": "tmp_x1 = tmp_x8;", "address": "0x1004"},
                {"kind": "call", "text": "call_0x2000(); /* bl 0x2000 */", "address": "0x1008"}
            ]
        }
        res = analyze_call_sites(lowered_blocks, architecture="arm64")
        assert res["call_sites_total"] == 1
        assert res["calls_with_arguments"] == 1
        site = res["sites"][0]
        assert site["refined_text"] == "call_0x2000(tmp_x0, tmp_x1); /* bl 0x2000; args refined from same-block evidence */"
        # Verify no fake source names are introduced
        assert "arg0" not in site["refined_text"]

    # 7. Unknown call args do not fabricate
    def test_7_unknown_call_args_do_not_fabricate(self):
        lowered_blocks = {
            "0x1000": [
                {"kind": "call", "text": "call_0x2000(); /* bl 0x2000 */", "address": "0x1008"}
            ]
        }
        res = analyze_call_sites(lowered_blocks, architecture="arm64")
        assert res["call_sites_total"] == 1
        assert res["calls_with_arguments"] == 0
        site = res["sites"][0]
        assert site["refined_text"] is None  # original is preserved

    # 8. Indirect call remains comment-only
    def test_8_indirect_call_remains_comment_only(self):
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "tmp_x0 = tmp_x8;", "address": "0x1000"},
                {"kind": "comment", "text": "/* indirect call via x9 */ /* blr x9 */", "address": "0x1004", "source_instruction": {"raw": "blr x9"}}
            ]
        }
        res = analyze_call_sites(lowered_blocks, architecture="arm64")
        assert res["call_sites_total"] == 1
        site = res["sites"][0]
        # Should stay as a comment-only replacement
        assert "blr x9" in site["refined_text"]
        assert "/*" in site["refined_text"]
        assert "*/" in site["refined_text"]
        assert "x9" in site["refined_text"]
        # Must NOT emit real C call syntax
        assert "x9(" not in site["refined_text"]

    # 9. Structured control flow preserved after Phase 5.4
    def test_9_structured_control_flow_preserved(self):
        fn = ReconstructedFunction(
            name="loop_func",
            canonical_name="loop_func",
            c_name="loop_func",
            return_type="void",
            structured_regions=[
                {
                    "type": "loop",
                    "kind": "while_like",
                    "header_block": "0x1000",
                    "body": {"type": "block", "id": "0x1004"},
                    "exit_blocks": []
                }
            ],
            lowered_blocks={
                "0x1000": [
                    {"kind": "instruction", "text": "tmp_w8 = 0;", "address": "0x1000"}
                ],
                "0x1004": [
                    {"kind": "instruction", "text": "tmp_w8 = tmp_w8 + 1;", "address": "0x1004"}
                ]
            },
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        assert "while (/* condition unknown: loop header 0x1000 */) {" in c_code
        assert "tmp_w8 = tmp_w8 + 1;" in c_code

    # 10. No fake conditions
    def test_10_no_fake_conditions(self):
        fn = ReconstructedFunction(
            name="cond_func",
            canonical_name="cond_func",
            c_name="cond_func",
            return_type="void",
            structured_regions=[
                {
                    "type": "if",
                    "condition_block": "0x1000",
                    "then_branch": {"type": "block", "id": "0x1004"},
                    "merge_block": "0x1008",
                }
            ],
            lowered_blocks={
                "0x1000": [],
                "0x1004": [],
                "0x1008": []
            },
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        # while and if must contain "condition unknown"
        for line in c_code.splitlines():
            s = line.strip()
            if s.startswith("if (") or s.startswith("while ("):
                assert "condition unknown" in s
                assert "tmp_" not in s

    # 11. No fake structs/fields
    def test_11_no_fake_structs_fields(self):
        # Scan emitted C to make sure no arrows -> or struct keyword or dots are fabricated
        fn = ReconstructedFunction(
            name="test_structs",
            canonical_name="test_structs",
            c_name="test_structs",
            return_type="void",
            lowered_blocks={
                "0x1000": [
                    {"kind": "instruction", "text": "tmp_x0 = 5;", "address": "0x1000"}
                ]
            },
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        assert "->" not in c_code
        assert "struct " not in c_code
        assert ".id" not in c_code
        assert ".ctx" not in c_code

    # 12. Schema and summary validation
    def test_12_schema_and_summary_validation(self):
        assert SCHEMA_VERSION == "5.5.0"
        artifact = SourceReconstructionArtifact()
        assert artifact.schema_version == "5.5.0"
        s = artifact.summary
        assert "return_sites_total" in s
        assert "return_sites_with_value" in s
        assert "return_sites_unknown" in s
        assert "functions_with_recovered_return_value" in s
        assert "call_sites_total" in s
        assert "direct_calls" in s
        assert "indirect_calls" in s
        assert "calls_with_arguments" in s
        assert "call_arguments_recovered" in s
        assert "call_arguments_unknown" in s

    # Test A: Call-site refined text exists in per-site metadata and recovered.c improves
    def test_A_call_site_refined_text_exists_and_recovered_c_improves(self):
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "tmp_x0 = 100;", "address": "0x1000"},
                {"kind": "call", "text": "call_0x2000(); /* bl 0x2000 */", "address": "0x1004"}
            ]
        }
        res_calls = analyze_call_sites(lowered_blocks, architecture="arm64")
        assert res_calls["sites"][0]["refined_text"] is not None

        fn = ReconstructedFunction(
            name="caller",
            canonical_name="caller",
            c_name="caller",
            return_type="void",
            lowered_blocks=lowered_blocks,
            callsite_refinement=res_calls,
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        assert "call_0x2000(tmp_x0);" in c_code

    # Test B: Call scan stops at previous call (stale registers not reused)
    def test_B_call_scan_stops_at_previous_call(self):
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "tmp_x0 = 42;", "address": "0x1000"},
                {"kind": "call", "text": "call_first(); /* bl first */", "address": "0x1004"},
                # x0 is NOT written here. Since a call clobbers registers, the second call cannot reuse x0 = 42.
                {"kind": "call", "text": "call_second(); /* bl second */", "address": "0x1008"}
            ]
        }
        res = analyze_call_sites(lowered_blocks, architecture="arm64")
        # first call should have arg x0
        assert res["sites"][0]["refined_text"] == "call_first(tmp_x0); /* bl first; args refined from same-block evidence */"
        # second call should NOT have arguments (or refined_text should be None)
        assert res["sites"][1]["refined_text"] is None

    # Test C: Return scan stops at previous call (return after intervening call -> unknown)
    def test_C_return_scan_stops_at_previous_call(self):
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "tmp_w0 = 5;", "address": "0x1000"},
                {"kind": "call", "text": "call_something(); /* bl something */", "address": "0x1004"},
                {"kind": "return_comment", "text": "/* return via x0 */", "address": "0x1008", "source_instruction": {"mnemonic": "ret"}}
            ]
        }
        res = analyze_return_sites(lowered_blocks, return_type="i32", architecture="arm64")
        assert res["sites"][0]["expression_kind"] == "unknown"

    # Test D: Per-site return replacement (only matching block_id + address is replaced)
    def test_D_per_site_return_replacement(self):
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "tmp_w0 = 123;", "address": "0x1000"},
                {"kind": "return_comment", "text": "/* return via x0 */", "address": "0x1004", "source_instruction": {"mnemonic": "ret"}}
            ],
            "0x2000": [
                # No tmp_w0 assignment in this block
                {"kind": "return_comment", "text": "/* return via x0 */", "address": "0x2004", "source_instruction": {"mnemonic": "ret"}}
            ]
        }
        res_ret = analyze_return_sites(lowered_blocks, return_type="i32", architecture="arm64")
        fn = ReconstructedFunction(
            name="multi_ret",
            canonical_name="multi_ret",
            c_name="multi_ret",
            return_type="i32",
            lowered_blocks=lowered_blocks,
            return_recovery=res_ret,
            body_status="structured",
            structured_regions=[
                {
                    "type": "sequence",
                    "children": [
                        {"type": "block", "id": "0x1000"},
                        {"type": "block", "id": "0x2000"}
                    ]
                }
            ]
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        # Verify block 0x1000 has the replaced return 123
        assert "return 123;" in c_code
        # Verify block 0x2000 has the fallback or unchanged comment
        # Note: in c_code, block 0x2000's return comment wasn't replaced since it was unknown
        # And the fallback return is emitted at the end of the function.
        assert "return 123;" in c_code
        # Check fallback return due to unreplaced return site in 0x2000
        assert "/* fallback return for paths without recovered return evidence */" in c_code

    # Test E: No expression folding
    def test_E_no_expression_folding(self):
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "tmp_w0 = tmp_w8 + 1;", "address": "0x1000"},
                {"kind": "return_comment", "text": "/* return via x0 */", "address": "0x1004", "source_instruction": {"mnemonic": "ret"}}
            ]
        }
        res = analyze_return_sites(lowered_blocks, return_type="i32", architecture="arm64")
        # Must return tmp_w0, not tmp_w8 + 1
        assert res["sites"][0]["replacement_text"] == "return tmp_w0; /* return value from w0 before ret */"

    # Test F: Indirect call comment-only
    def test_F_indirect_call_comment_only(self):
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "tmp_x0 = 10;", "address": "0x1000"},
                {"kind": "comment", "text": "/* indirect call via x9 */ /* blr x9 */", "address": "0x1004", "source_instruction": {"raw": "blr x9"}}
            ]
        }
        res = analyze_call_sites(lowered_blocks, architecture="arm64")
        site = res["sites"][0]
        # Should stay as a comment-only replacement
        assert "blr x9" in site["refined_text"]
        assert "/*" in site["refined_text"]
        assert "*/" in site["refined_text"]
        assert "tmp_x0" in site["refined_text"]
        assert "x9(" not in site["refined_text"]
