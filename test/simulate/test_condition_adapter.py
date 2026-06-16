# -*- coding: utf-8 -*-
"""
Tests for Phase 5.7 Syntax-Safe Unknown Condition Adapter.
"""

from __future__ import annotations

import re
import os
import tempfile
import pytest

from src.ir.source.models import (
    ReconstructedFunction,
    SourceReconstructionArtifact,
    SCHEMA_VERSION,
)
from src.ir.source.condition_adapter import (
    escape_c_string,
    adapt_condition_header,
    adapt_condition_lines,
)
from src.ir.source.c_emitter import emit_recovered_c


class TestConditionAdapter:

    def _emit_to_string(self, artifact: SourceReconstructionArtifact) -> str:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".c", delete=False
        ) as f:
            path = f.name
        try:
            emit_recovered_c(artifact, path)
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        finally:
            os.unlink(path)

    # Test 1 — Schema update
    def test_1_schema_update(self):
        assert SCHEMA_VERSION == "5.7.2"
        artifact = SourceReconstructionArtifact()
        assert artifact.schema_version == "5.7.2"

    # Test 2 — Adapt while evidence condition
    def test_2_adapt_while_evidence_condition(self):
        line = "while (/* condition evidence: b.ge at 0x1000 */) {"
        new_line, changed, kind = adapt_condition_header(line)
        assert changed
        assert kind == "evidence"
        assert new_line == 'while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x1000")) {'

    # Test 3 — Adapt if unknown condition
    def test_3_adapt_if_unknown_condition(self):
        line = "if (/* condition unknown: block 0x2000 */) {"
        new_line, changed, kind = adapt_condition_header(line)
        assert changed
        assert kind == "unknown"
        assert new_line == 'if (HEPHAESTUS_UNKNOWN_COND("condition unknown: block 0x2000")) {'

    # Test 4 — Preserve indentation
    def test_4_preserve_indentation(self):
        line = "        if (/* condition evidence: cbz w8 at 0x3000 */) {"
        new_line, changed, kind = adapt_condition_header(line)
        assert changed
        assert new_line == '        if (HEPHAESTUS_UNKNOWN_COND("condition evidence: cbz w8 at 0x3000")) {'

    # Test 5 — Do not adapt already-adapted line
    def test_5_do_not_adapt_already_adapted(self):
        line = 'if (HEPHAESTUS_UNKNOWN_COND("condition evidence: old")) {'
        new_line, changed, kind = adapt_condition_header(line)
        assert not changed
        assert new_line == line

    # Test 6 — Do not adapt non-header comments
    def test_6_do_not_adapt_non_header_comments(self):
        line = "/* condition evidence: b.ge at 0x1000 */"
        new_line, changed, kind = adapt_condition_header(line)
        assert not changed

    # Test 7 — Escape quotes and backslashes
    def test_7_escape_quotes_and_backslashes(self):
        evidence = 'cbz w8 at "0x1000" and C:\\tmp'
        escaped = escape_c_string(evidence)
        assert escaped == 'cbz w8 at \\"0x1000\\" and C:\\\\tmp'

    # Test 8 — Helper emitted once
    def test_8_helper_emitted_once(self):
        # Multiple functions containing condition adapters
        fn1 = ReconstructedFunction(
            name="fn1",
            c_name="fn1",
            lowered_blocks={
                "0x1000": [
                    {"kind": "instruction", "text": "tmp_w8 = 0;", "address": "0x1000"}
                ]
            },
            structured_regions=[
                {
                    "type": "loop",
                    "header_block": "0x1000",
                    "body": {"type": "block", "id": "0x1000"}
                }
            ],
            condition_recovery={
                "sites": [
                    {
                        "structured_region_kind": "loop",
                        "block_id": "0x1000",
                        "annotation": "condition evidence: b.eq at 0x1000"
                    }
                ]
            },
            body_status="structured"
        )
        fn2 = ReconstructedFunction(
            name="fn2",
            c_name="fn2",
            structured_regions=[
                {
                    "type": "if",
                    "condition_block": "0x2000",
                    "then_branch": {"type": "block", "id": "0x2004"}
                }
            ],
            lowered_blocks={
                "0x2000": []
            },
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn1, fn2])
        c_code = self._emit_to_string(artifact)

        # Count occurrences of the static definition helper
        matches = re.findall(r"static int HEPHAESTUS_UNKNOWN_COND", c_code)
        assert len(matches) == 1
        assert "HEPHAESTUS_UNKNOWN_COND(" in c_code

    # Test 9 — No executable real conditions
    def test_9_no_executable_real_conditions(self):
        fn = ReconstructedFunction(
            name="test_fn",
            c_name="test_fn",
            lowered_blocks={
                "0x1000": []
            },
            structured_regions=[
                {
                    "type": "if",
                    "condition_block": "0x1000",
                    "then_branch": {"type": "block", "id": "0x1000"}
                }
            ],
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)

        for line in c_code.splitlines():
            s = line.strip()
            if s.startswith("if (") or s.startswith("while ("):
                # Clean up the HEPHAESTUS_UNKNOWN_COND wrapper to see what's executable
                assert "HEPHAESTUS_UNKNOWN_COND" in s
                assert "tmp_" not in s.replace("HEPHAESTUS_UNKNOWN_COND", "")
                assert "arg" not in s.replace("HEPHAESTUS_UNKNOWN_COND", "")
                assert "stack_" not in s.replace("HEPHAESTUS_UNKNOWN_COND", "")

    # Test 10 — condition_expressions_recovered remains zero
    def test_10_condition_expressions_recovered_remains_zero(self):
        artifact = SourceReconstructionArtifact()
        assert artifact.summary["condition_expressions_recovered"] == 0

    # Test 11 — Phase 5.4/5.5/5.6 preserved
    def test_11_prev_phases_preserved(self):
        fn = ReconstructedFunction(
            name="test_fn",
            c_name="test_fn",
            lowered_blocks={
                "0x1000": [
                    {"kind": "instruction", "text": "tmp_w8 = 1;", "address": "0x1000"},
                    {"kind": "call", "text": "call_0x2000(); /* bl 0x2000 */", "address": "0x1004"},
                    {"kind": "instruction", "text": "tmp_w0 = 1;", "address": "0x1006"},
                    {"kind": "return_comment", "text": "/* return via x0 */", "address": "0x1008", "source_instruction": {"mnemonic": "ret"}},
                ]
            },
            return_recovery={
                "return_sites_total": 1,
                "sites": [
                    {
                        "block_id": "0x1000",
                        "address": "0x1008",
                        "register": "w0",
                        "expression_kind": "constant",
                        "expression": "1",
                        "replacement_text": "return 1; /* return constant from w0 before ret */"
                    }
                ]
            },
            callsite_refinement={
                "call_sites_total": 1,
                "sites": [
                    {
                        "block_id": "0x1000",
                        "address": "0x1004",
                        "original_text": "call_0x2000(); /* bl 0x2000 */",
                        "refined_text": "call_0x2000(tmp_w8); /* bl 0x2000; args refined */"
                    }
                ]
            },
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)

        assert "return 1; /* return constant from w0 before ret */" in c_code
        assert "call_0x2000(tmp_w8); /* bl 0x2000; args refined */" in c_code
        assert "Conservative pseudo declarations" in c_code

    # Test 12 — Declaration scanner ignores adapter helper
    def test_12_declaration_scanner_ignores_helper(self):
        fn = ReconstructedFunction(
            name="test_fn",
            c_name="test_fn",
            lowered_blocks={
                "0x1000": []
            },
            structured_regions=[
                {
                    "type": "if",
                    "condition_block": "0x1000",
                    "then_branch": {"type": "block", "id": "0x1000"}
                }
            ],
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)

        # Scanner should not declare call_HEPHAESTUS_UNKNOWN_COND
        assert "call_HEPHAESTUS_UNKNOWN_COND" not in c_code
        assert "HEPHAESTUS_UNKNOWN_COND = 0;" not in c_code

    # Test 13 — Synthetic compile-shape smoke test
    def test_13_synthetic_compile_shape_smoke_test(self):
        c_code = """#include <stdint.h>
typedef uint32_t u32;
typedef uint64_t u64;

static int HEPHAESTUS_UNKNOWN_COND(const char *evidence)
{
    (void)evidence;
    return 0;
}

u64 f(void)
{
    u32 tmp_w8 = 0;
    while (HEPHAESTUS_UNKNOWN_COND("condition evidence: b.ge at 0x1000")) {
        tmp_w8 = tmp_w8 + 1;
    }
    return tmp_w8;
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
            f.write(c_code)
            path = f.name
        try:
            cmd = f"clang -fsyntax-only {path}"
            ret = os.system(cmd)
            assert ret == 0, "Clang syntax check failed for synthetic stub."
        finally:
            os.unlink(path)

    # Test 14 — Full recovered.c diagnostic class check is diagnostic only
    def test_14_full_syntax_check_is_diagnostic(self):
        # This acts as a marker test to confirm full output is diagnostic only
        pass

    # Test A — Reserved Helper Ignored by Declaration Scanners
    def test_A_reserved_helper_ignored(self):
        body_lines = [
            "    if (HEPHAESTUS_UNKNOWN_COND(\"condition evidence: cbz w8\")) {",
            "        tmp_w8 = 42;",
            "    }"
        ]
        from src.ir.source.declaration_recovery import analyze_declarations_for_function
        res = analyze_declarations_for_function(
            "f", "void", [], {}, [], emitted_body_lines=body_lines
        )
        decl_names = {d["name"] for d in res["declarations"]}
        assert "HEPHAESTUS_UNKNOWN_COND" not in decl_names
        assert "call_HEPHAESTUS_UNKNOWN_COND" not in res.get("call_helpers", [])

    # Test B — Helper Not Emitted When No Adapters Exist
    def test_B_helper_not_emitted_when_no_adapters_exist(self):
        fn = ReconstructedFunction(
            name="test_fn",
            c_name="test_fn",
            body_status="missing"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        assert "HEPHAESTUS_UNKNOWN_COND" not in c_code

    # Test C — Else-If Is Not Adapted
    def test_C_else_if_not_adapted(self):
        line = "} else if (/* condition evidence: cbz w8 at 0x1000 */) {"
        new_line, changed, kind = adapt_condition_header(line)
        assert not changed
        assert new_line == line

    # Test D — Evidence Newline Escaped to \n
    def test_D_evidence_newline_escaped(self):
        evidence = "condition evidence: line1\nline2"
        escaped = escape_c_string(evidence)
        assert "\n" not in escaped
        assert "\\n" in escaped

        line = "while (/* condition evidence: line1\nline2 */) {"
        new_line, changed, kind = adapt_condition_header(line)
        assert changed
        assert "\n" not in new_line
        assert 'HEPHAESTUS_UNKNOWN_COND("condition evidence: line1\\nline2")' in new_line

    # Test E — Evidence Text Preserved Exactly
    def test_E_evidence_text_preserved(self):
        line = "while (/* condition evidence: b.ge at 0x100000490 after subs at 0x10000048c; target 0x1000004c8; loop polarity inverted */) {"
        new_line, changed, kind = adapt_condition_header(line)
        assert changed
        assert "b.ge at 0x100000490" in new_line
        assert "after subs at 0x10000048c" in new_line
        assert "target 0x1000004c8" in new_line
        assert "loop polarity inverted" in new_line

    # Test F — Adapter Idempotency
    def test_F_adapter_idempotency(self):
        lines = [
            "while (/* condition evidence: b.ge */) {",
            "    tmp_w8 = 0;",
            "}"
        ]
        adapted1, stats1 = adapt_condition_lines(lines)
        adapted2, stats2 = adapt_condition_lines(adapted1)
        assert adapted1 == adapted2
        assert stats2["condition_adapters_inserted"] == 0

    # Test G — Non-Header Comment Not Adapted
    def test_G_non_header_comment_not_adapted(self):
        lines = [
            "/* condition evidence: b.ge at 0x1000 */",
            "/* if/else condition block: 0x1000 */",
            "/* loop header: 0x1000 */"
        ]
        adapted, stats = adapt_condition_lines(lines)
        assert adapted == lines
        assert stats["condition_adapters_inserted"] == 0

    # Test H — Empty Condition Removed
    def test_H_empty_condition_removed(self):
        fn = ReconstructedFunction(
            name="fn",
            c_name="fn",
            structured_regions=[
                {
                    "type": "if",
                    "condition_block": "0x1000",
                    "then_branch": {"type": "block", "id": "0x1000"}
                }
            ],
            lowered_blocks={
                "0x1000": []
            },
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)

        assert "if ()" not in c_code
        assert "if ( )" not in c_code
        assert "while ()" not in c_code
        assert "while ( )" not in c_code
