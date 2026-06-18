# -*- coding: utf-8 -*-
"""
Unit Tests for Phase 7.2.2 Hosted Main Signature and Duplicate Entry Function Fix
"""

import pytest
import re
from src.ir.source.models import ReconstructedFunction, SourceReconstructionArtifact
from src.ir.source.c_emitter import _emit_function, emit_recovered_c
from src.ir.source.declaration_recovery import analyze_declarations_for_function
from src.readability.compile_shape import (
    dedupe_and_resolve_forward_declarations,
    harden_compile_shape_functions
)

def test_main_signature_standardization():
    # Verify that the reconstructed main function signature forces hosted int32_t main(int32_t argc, char **argv)
    fn = ReconstructedFunction(
        name="_main",
        canonical_name="_main",
        c_name="main",
        entry_point="0x100000460",
        function_kind="entrypoint",
        return_type="i32",
        parameters=[
            {"name": "arg0", "type": "u64"},
            {"name": "arg1", "type": "u64"}
        ],
        local_variables=[],
        body_status="structured",
        structured_regions=[],
        abi_argument_bindings=[],
        parameter_layout_evidence=[],
        layout_candidates=[],
        instruction_count=10,
        basic_block_count=2,
        warnings=[],
        evidence_notes=[],
        lowered_statements=[],
        lowered_blocks={},
        lowering={}
    )
    
    lines = []
    _emit_function(fn, lines)
    
    # Signature line should be int32_t main(int32_t argc, char **argv)
    assert any("int32_t main(int32_t argc, char **argv)" in line for line in lines)
    # Stale/invalid parameters shouldn't exist in header definition
    assert not any("uint64_t arg0" in line for line in lines)

def test_main_bridge_locals_generation():
    # If main body uses arg0/arg1/param_0/param_1, bridge declarations should be injected
    fn = ReconstructedFunction(
        name="_main",
        canonical_name="_main",
        c_name="main",
        entry_point="0x100000460",
        function_kind="entrypoint",
        return_type="i32",
        parameters=[],
        local_variables=[],
        body_status="structured",
        structured_regions=[],
        abi_argument_bindings=[],
        parameter_layout_evidence=[],
        layout_candidates=[],
        instruction_count=10,
        basic_block_count=2,
        warnings=[],
        evidence_notes=[],
        lowered_statements=[],
        lowered_blocks={"0x100000460": [
            {"kind": "unknown", "text": "arg0 = 5;", "address": "0x100000460"},
            {"kind": "unknown", "text": "param_1 = 10;", "address": "0x100000464"}
        ]},
        lowering={}
    )
    
    lines = []
    _emit_function(fn, lines)
    
    # Verify bridge declarations exist
    assert any("u64 arg0 = (u64)argc;" in line for line in lines)
    assert any("u64 param_1 = (u64)(uintptr_t)argv;" in line for line in lines)
    # Since arg1/param_0 are NOT used, their bridges should NOT exist
    assert not any("arg1 =" in line for line in lines)
    assert not any("param_0 =" in line for line in lines)

def test_main_bridge_verification_rule():
    # Test that bridge identifiers count as declared only when the corresponding bridge is inserted
    
    # Scenario A: arg0 and arg1 are used, and bridges are inserted. They should not be declared as pseudo declarations.
    body_with_bridges = [
        "    u64 arg0 = (u64)argc;                  /* main ABI bridge: argc */",
        "    u64 arg1 = (u64)(uintptr_t)argv;       /* main ABI bridge: argv */",
        "    arg0 = 5;",
        "    arg1 = 10;"
    ]
    decls_data = analyze_declarations_for_function(
        function_name="main",
        return_type="i32",
        parameters=[],
        lowered_blocks={},
        structured_regions=[],
        emitted_body_lines=body_with_bridges
    )
    # arg0 and arg1 should be considered parameter/bridge declared and NOT put in declarations list
    declared_names = {d["name"] for d in decls_data["declarations"]}
    assert "arg0" not in declared_names
    assert "arg1" not in declared_names

    # Scenario B: arg0 is used, but the bridge was NOT inserted. Declaration recovery must declare it as = 0.
    body_without_bridge = [
        "    arg0 = 5;",
        "    arg1 = 10;" # no bridge lines
    ]
    # We pass it to compile-shape hardening to verify
    hardened, items, stats = harden_compile_shape_functions(
        c_content="""
int32_t main(int32_t argc, char **argv)
{
    arg0 = 5;
    arg1 = 10;
}
""",
        promote_temps_active=False,
        function_promotions={},
        original_types_by_func={},
        added_decls_from_predicates={}
    )
    # Checking if bridges were added during post-processing
    assert "u64 arg0 = (u64)argc; /* main ABI bridge: argc */" in hardened
    assert "u64 arg1 = (u64)(uintptr_t)argv; /* main ABI bridge: argv */" in hardened

def test_forward_declarations_normalization():
    # Bad prototypes:
    c_input = """
int32_t main(uint64_t arg0, uint64_t arg1);
int32_t main(uint64_t arg0);
int32_t main(void);
int32_t main(int32_t argc, char **argv);
int32_t main_0x100000548(uint64_t arg0);

int32_t main(int32_t argc, char **argv)
{
    return 0;
}
"""
    normalized, items, stats = dedupe_and_resolve_forward_declarations(c_input)
    
    # Should resolve to exactly 1 hosted main prototype and 1 duplicate prototype
    assert normalized.count("int32_t main(int32_t argc, char **argv);") == 1
    assert "int32_t main(int32_t argc, char **argv);" in normalized
    assert "int32_t main_0x100000548(uint64_t arg0);" in normalized
    # Stale main(void) / main(uint64_t...) must be cleaned up
    assert "main(uint64_t" not in normalized.split("int32_t main_")[0]
    assert "main(void)" not in normalized

def test_duplicate_definition_renaming():
    c_input = """
int32_t main(uint64_t arg0, uint64_t arg1)
{
    /* Entry: 0x100000460 */
    return 0;
}

int32_t main(uint64_t arg0)
{
    /* Entry: 0x100000548 */
    return 0;
}
"""
    # Second duplicate definition of main should be renamed to main_0x100000548
    normalized, items, stats = dedupe_and_resolve_forward_declarations(c_input)
    assert "int32_t main_0x100000548(uint64_t arg0)" in normalized
    assert stats["duplicate_main_definitions_renamed"] == 1
