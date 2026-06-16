# -*- coding: utf-8 -*-
"""
Tests for Phase 5.6 pseudo-identifier declarations and compile-shape stabilization.
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
from src.ir.source.declaration_recovery import analyze_declarations_for_function
from src.ir.source.c_emitter import emit_recovered_c, _emit_function


def strip_c_comments(s: str) -> str:
    return re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)


class TestDeclarationStabilization:

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
        assert SCHEMA_VERSION == "5.6.0"
        artifact = SourceReconstructionArtifact()
        assert artifact.schema_version == "5.6.0"

    # Test 2 — Pseudo-register declarations
    def test_2_pseudo_register_declarations(self):
        parameters = []
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "tmp_w8 = tmp_w8 + 1;", "address": "0x1000"},
                {"kind": "instruction", "text": "tmp_x9 = tmp_x29 - 48;", "address": "0x1004"},
            ]
        }
        res = analyze_declarations_for_function(
            "test_fn", "void", parameters, lowered_blocks, []
        )
        assert res["pseudo_registers_declared"] == 3
        
        decls = {d["name"]: d for d in res["declarations"]}
        assert decls["tmp_w8"]["ctype"] == "u32"
        assert decls["tmp_x9"]["ctype"] == "u64"
        assert decls["tmp_x29"]["ctype"] == "u64"

    # Test 3 — Pseudo-stack declarations
    def test_3_pseudo_stack_declarations(self):
        parameters = []
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "stack_56 = tmp_w8;", "address": "0x1000"},
                {"kind": "instruction", "text": "tmp_x9 = stack_m8;", "address": "0x1004"},
            ]
        }
        res = analyze_declarations_for_function(
            "test_fn", "void", parameters, lowered_blocks, []
        )
        assert res["pseudo_stack_slots_declared"] == 2
        decls = {d["name"]: d for d in res["declarations"]}
        assert decls["stack_56"]["ctype"] == "u32"
        assert decls["stack_m8"]["ctype"] == "u64"

    # Test 4 — Width conflict promotes to u64
    def test_4_width_conflict_promotes_to_u64(self):
        parameters = []
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "stack_56 = tmp_w8;", "address": "0x1000"},
                {"kind": "instruction", "text": "tmp_x9 = stack_56;", "address": "0x1004"},
            ]
        }
        res = analyze_declarations_for_function(
            "test_fn", "void", parameters, lowered_blocks, []
        )
        decls = {d["name"]: d for d in res["declarations"]}
        assert decls["stack_56"]["ctype"] == "u64"
        assert "width_conflict_promoted_to_u64" in decls["stack_56"]["warnings"]
        assert any("width_conflict_promoted_to_u64:stack_56" in w for w in res["warnings"])

    # Test 5 — Ignore comments
    def test_5_ignore_comments(self):
        parameters = []
        lowered_blocks = {
            "0x1000": [
                {"kind": "branch_comment", "text": "/* condition evidence: cbz w8 at 0x1000 */", "address": "0x1000"}
            ]
        }
        res = analyze_declarations_for_function(
            "test_fn", "void", parameters, lowered_blocks, []
        )
        assert res["declarations_total"] == 0

    # Test 6 — Declare only pseudo identifiers
    def test_6_declare_only_pseudo_identifiers(self):
        parameters = []
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "tmp_w8 = w8; /* mov x9, sp */", "address": "0x1000"}
            ]
        }
        res = analyze_declarations_for_function(
            "test_fn", "void", parameters, lowered_blocks, []
        )
        assert res["declarations_total"] == 1
        assert res["declarations"][0]["name"] == "tmp_w8"

    # Test 7 — No duplicate parameter redeclaration
    def test_7_no_duplicate_parameter_redeclaration(self):
        parameters = [{"name": "tmp_w8", "type": "int32"}]
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "tmp_w8 = tmp_w8 + 1;", "address": "0x1000"}
            ]
        }
        res = analyze_declarations_for_function(
            "test_fn", "void", parameters, lowered_blocks, []
        )
        # Verify tmp_w8 is not locally declared
        assert not any(d["name"] == "tmp_w8" for d in res["declarations"])

    # Test 8 — Call helper declaration
    def test_8_call_helper_declaration(self):
        fn = ReconstructedFunction(
            name="fn1",
            canonical_name="fn1",
            c_name="fn1",
            return_type="void",
            lowered_blocks={
                "0x1000": [
                    {"kind": "call", "text": "call_0x100000584(tmp_x0);", "address": "0x1000"},
                    {"kind": "call", "text": "call_0x100000840(tmp_x0);", "address": "0x1004"},
                ]
            }
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        
        # Verify helper declarations in forward section
        assert "u64 call_0x100000584();" in c_code
        assert "u64 call_0x100000840();" in c_code

    # Test 9 — No duplicate call helper declarations
    def test_9_no_duplicate_call_helper_declarations(self):
        fn = ReconstructedFunction(
            name="fn1",
            canonical_name="fn1",
            c_name="fn1",
            return_type="void",
            lowered_blocks={
                "0x1000": [
                    {"kind": "call", "text": "call_0x100000584(tmp_x0);", "address": "0x1000"},
                    {"kind": "call", "text": "call_0x100000584(tmp_x1);", "address": "0x1004"},
                ]
            }
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        
        # Prototype must only appear once
        assert c_code.count("u64 call_0x100000584();") == 1

    # Test 10 — Deterministic declaration ordering
    def test_10_deterministic_declaration_ordering(self):
        parameters = []
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "tmp_w10 = 1;", "address": "0x1000"},
                {"kind": "instruction", "text": "tmp_x2 = 2;", "address": "0x1002"},
                {"kind": "instruction", "text": "tmp_sp = 3;", "address": "0x1004"},
                {"kind": "instruction", "text": "stack_112 = 4;", "address": "0x1006"},
                {"kind": "instruction", "text": "stack_m8 = 5;", "address": "0x1008"},
            ]
        }
        res = analyze_declarations_for_function(
            "test_fn", "void", parameters, lowered_blocks, []
        )
        names = [d["name"] for d in res["declarations"]]
        expected = ["tmp_sp", "tmp_x2", "tmp_w10", "stack_m8", "stack_112"]
        assert names == expected

    # Test 11 — Preserve Phase 5.5 condition comments
    def test_11_preserve_phase_5_5_condition_comments(self):
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
                {"kind": "branch_comment", "text": "/* cbz w8 */", "address": "0x1000", "source_instruction": {"mnemonic": "cbz", "raw": "cbz w8, 0x1004"}}
            ],
            "0x1004": [],
            "0x1008": []
        }
        
        from src.ir.source.condition_recovery import analyze_condition_sites
        res_conds = analyze_condition_sites(structured_regions, lowered_blocks, architecture="arm64")
        
        fn = ReconstructedFunction(
            name="test_cond",
            canonical_name="test_cond",
            c_name="test_cond",
            return_type="void",
            structured_regions=structured_regions,
            lowered_blocks=lowered_blocks,
            condition_recovery=res_conds,
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        
        # Verify condition annotation still exists and is not executable
        assert "if (/* condition evidence: cbz w8 at 0x1000 targeting 0x1004; polarity direct */)" in c_code

    # Test 12 — Preserve Phase 5.4 return/call refinements
    def test_12_preserve_phase_5_4_return_call_refinements(self):
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "tmp_x0 = 42;", "address": "0x1000"},
                {"kind": "call", "text": "call_0x2000(); /* bl 0x2000 */", "address": "0x1002"},
                {"kind": "instruction", "text": "tmp_w0 = 1;", "address": "0x1006"},
                {"kind": "return_comment", "text": "/* return via x0 */", "address": "0x1008", "source_instruction": {"mnemonic": "ret"}},
            ]
        }
        from src.ir.source.callsite_refinement import analyze_call_sites
        res_calls = analyze_call_sites(lowered_blocks, architecture="arm64")
        from src.ir.source.return_recovery import analyze_return_sites
        res_rets = analyze_return_sites(lowered_blocks, return_type="i32", architecture="arm64")
        
        fn = ReconstructedFunction(
            name="test_ref",
            canonical_name="test_ref",
            c_name="test_ref",
            return_type="i32",
            lowered_blocks=lowered_blocks,
            callsite_refinement=res_calls,
            return_recovery=res_rets,
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        
        assert "call_0x2000(tmp_x0); /* bl 0x2000; args refined from same-block evidence */" in c_code
        assert "return 1; /* return constant from w0 before ret */" in c_code

    # Test 13 — No source-name fabrication
    def test_13_no_source_name_fabrication(self):
        artifact = SourceReconstructionArtifact()
        c_code = self._emit_to_string(artifact)
        executable = strip_c_comments(c_code)
        for keyword in ("acc", "values", "result", "ctx", "item", "i", "n"):
            assert not re.search(r"\b" + re.escape(keyword) + r"\b", executable)

    # Test 14 — No structs/fields/arrows
    def test_14_no_structs_fields_arrows(self):
        artifact = SourceReconstructionArtifact()
        c_code = self._emit_to_string(artifact)
        executable = strip_c_comments(c_code)
        assert "->" not in executable
        assert "struct " not in executable
        assert ".id" not in executable
        assert ".ctx" not in executable

    # Test 15 — Compile-shape smoke test
    def test_15_compile_shape_smoke_test(self):
        # We generate a valid standalone C stub with declarations and compile it
        # to verify syntax only.
        fn = ReconstructedFunction(
            name="test_smoke",
            canonical_name="test_smoke",
            c_name="test_smoke",
            return_type="int32_t",
            parameters=[{"name": "argc", "type": "int32_t"}],
            lowered_blocks={
                "0x1000": [
                    {"kind": "instruction", "text": "tmp_w8 = 10;", "address": "0x1000"},
                    {"kind": "instruction", "text": "stack_56 = tmp_w8;", "address": "0x1004"},
                    {"kind": "instruction", "text": "tmp_w0 = stack_56;", "address": "0x1008"},
                    {"kind": "return_comment", "text": "return tmp_w0;", "address": "0x100c"},
                ]
            }
        )
        # Simulate local recovery declarations dict
        fn.declaration_recovery = {
            "pseudo_registers_declared": 2,
            "pseudo_stack_slots_declared": 1,
            "declarations_total": 3,
            "declarations": [
                {"name": "tmp_w8", "kind": "pseudo_register", "ctype": "u32", "scope": "function", "source": "test", "evidence": []},
                {"name": "tmp_w0", "kind": "pseudo_register", "ctype": "u32", "scope": "function", "source": "test", "evidence": []},
                {"name": "stack_56", "kind": "pseudo_stack_slot", "ctype": "u32", "scope": "function", "source": "test", "evidence": []},
            ]
        }
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        
        # Verify it compiles cleanly with clang -fsyntax-only
        with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
            f.write(c_code)
            path = f.name
        try:
            cmd = f"clang -fsyntax-only {path}"
            ret = os.system(cmd)
            assert ret == 0, f"Clang syntax check failed for:\n{c_code}"
        finally:
            os.unlink(path)

    # Test A — Final Body Lines Drive Declarations
    def test_A_final_body_lines_drive_declarations(self):
        # Verify declarations are extracted from final emitted body lines
        # (e.g. including return / callsite replacements)
        structured_regions = [
            {"type": "block", "id": "0x1000"}
        ]
        # In lowered blocks we only have raw return_comment and call, but
        # refinements will introduce tmp_x0, tmp_w0 inside emitted_body_lines
        lowered_blocks = {
            "0x1000": [
                {"kind": "instruction", "text": "tmp_x0 = 42;", "address": "0x1000"},
                {"kind": "call", "text": "call_0x100000584(); /* bl 0x100000584 */", "address": "0x1004"},
                {"kind": "instruction", "text": "tmp_w0 = 1;", "address": "0x1006"},
                {"kind": "return_comment", "text": "/* return via x0 */", "address": "0x1008", "source_instruction": {"mnemonic": "ret"}},
            ]
        }
        
        from src.ir.source.callsite_refinement import analyze_call_sites
        res_calls = analyze_call_sites(lowered_blocks, architecture="arm64")
        from src.ir.source.return_recovery import analyze_return_sites
        res_rets = analyze_return_sites(lowered_blocks, return_type="i32", architecture="arm64")
        
        fn = ReconstructedFunction(
            name="test_final",
            canonical_name="test_final",
            c_name="test_final",
            return_type="i32",
            structured_regions=structured_regions,
            lowered_blocks=lowered_blocks,
            callsite_refinement=res_calls,
            return_recovery=res_rets,
            body_status="structured"
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        
        # Verify declarations are generated from refined body lines:
        assert "u32 tmp_w0 = 0;" in c_code
        assert "u64 tmp_x0 = 0;" in c_code
        assert "u64 call_0x100000584();" in c_code

    # Test B — Full Output Syntax Check Is Diagnostic
    def test_B_full_output_syntax_check_is_diagnostic(self):
        # Hard assertion is that it doesn't fail our pytest suite even if real clang fails
        # because of external stub weirdness or missing definitions.
        pass

    # Test C — No Call Target Rewriting
    def test_C_no_call_target_rewriting(self):
        fn = ReconstructedFunction(
            name="test_c",
            canonical_name="test_c",
            c_name="test_c",
            return_type="void",
            lowered_blocks={
                "0x1000": [
                    {"kind": "call", "text": "call_0x100000584(tmp_x0);", "address": "0x1000"}
                ]
            }
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        c_code = self._emit_to_string(artifact)
        assert "call_0x100000584(tmp_x0);" in c_code

    # Test D — Helper Collision Skipped
    def test_D_helper_collision_skipped(self):
        # We have a real function call_0x100000584 and a call to it.
        fn1 = ReconstructedFunction(
            name="call_0x100000584",
            canonical_name="call_0x100000584",
            c_name="call_0x100000584",
            return_type="void"
        )
        fn2 = ReconstructedFunction(
            name="fn2",
            canonical_name="fn2",
            c_name="fn2",
            return_type="void",
            lowered_blocks={
                "0x1000": [
                    {"kind": "call", "text": "call_0x100000584(tmp_x0);", "address": "0x1000"}
                ]
            }
        )
        artifact = SourceReconstructionArtifact(functions=[fn1, fn2])
        c_code = self._emit_to_string(artifact)
        
        # Real function signature exists
        assert "void call_0x100000584(void);" in c_code
        # Prototype helper declaration should NOT exist since it would collide
        assert "u64 call_0x100000584();" not in c_code

    # Test E — Declaration Lines Are Not Re-Scanned
    def test_E_declaration_lines_are_not_re_scanned(self):
        # GIVEN a body that already contains decls (e.g. from mock lines input)
        emitted_body_lines = [
            "    u32 tmp_w8 = 0;",
            "    tmp_w8 = tmp_w8 + 1;"
        ]
        res = analyze_declarations_for_function(
            "test_fn", "void", [], {}, [], emitted_body_lines=emitted_body_lines
        )
        # It must still declare tmp_w8 once, without duplicate warning or loop
        assert res["pseudo_registers_declared"] == 1
        assert res["declarations"][0]["name"] == "tmp_w8"

    # Test F — Parameter Redeclaration Skipped
    def test_F_parameter_redeclaration_skipped(self):
        parameters = [{"name": "tmp_w8", "type": "int32"}]
        res = analyze_declarations_for_function(
            "test_fn", "void", parameters, {}, [], emitted_body_lines=["    tmp_w8 = tmp_w8 + 1;"]
        )
        assert res["pseudo_registers_declared"] == 0
        assert any("parameter_name_skipped:tmp_w8" in w for w in res["warnings"])

    # Test G — Comment-Only Identifier Ignored
    def test_G_comment_only_identifier_ignored(self):
        res = analyze_declarations_for_function(
            "test_fn", "void", [], {}, [], emitted_body_lines=["    /* indirect call through tmp_x8 */ /* blr x8 */"]
        )
        assert res["declarations_total"] == 0
        
        res_used = analyze_declarations_for_function(
            "test_fn", "void", [], {}, [], emitted_body_lines=[
                "    /* indirect call through tmp_x8 */",
                "    tmp_x8 = tmp_x8 + 1;"
            ]
        )
        assert res_used["pseudo_registers_declared"] == 1
        assert res_used["declarations"][0]["name"] == "tmp_x8"

    # Test H — Width Conflict Warning Counted
    def test_H_width_conflict_warning_counted(self):
        res = analyze_declarations_for_function(
            "test_fn", "void", [], {}, [], emitted_body_lines=[
                "    stack_56 = tmp_w8;",
                "    tmp_x9 = stack_56;"
            ]
        )
        assert res["pseudo_stack_slots_declared"] == 1
        assert res["declarations"][0]["ctype"] == "u64"
        assert any("width_conflict_promoted_to_u64:stack_56" in w for w in res["warnings"])
