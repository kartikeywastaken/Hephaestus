# -*- coding: utf-8 -*-
"""
Unit Tests for Phase 5.7.3 ABI Scratch Identifier Declaration Completion
"""

import tempfile
import pytest
from pathlib import Path
from src.ir.source.models import ReconstructedFunction, SourceReconstructionArtifact
from src.ir.source.c_emitter import _emit_function, emit_recovered_c
from src.ir.source.declaration_recovery import (
    is_safe_abi_scratch_identifier,
    infer_abi_scratch_type,
    analyze_abi_scratch_declarations,
)
from src.readability.compile_shape import (
    get_completion_declaration,
    harden_compile_shape_functions,
)


def test_safe_abi_scratch_validation():
    # Test valid registers
    assert is_safe_abi_scratch_identifier("arg0") is True
    assert is_safe_abi_scratch_identifier("arg7") is True
    assert is_safe_abi_scratch_identifier("arg_0") is True
    assert is_safe_abi_scratch_identifier("arg_7") is True
    assert is_safe_abi_scratch_identifier("param_0") is True
    assert is_safe_abi_scratch_identifier("param_7") is True

    # Test stack parameter offsets in hex
    assert is_safe_abi_scratch_identifier("arg_10h") is True
    assert is_safe_abi_scratch_identifier("arg_30h") is True
    assert is_safe_abi_scratch_identifier("arg_60h") is True

    # Test invalid registers
    assert is_safe_abi_scratch_identifier("arg8") is False
    assert is_safe_abi_scratch_identifier("arg_8") is False
    assert is_safe_abi_scratch_identifier("param_8") is False
    assert is_safe_abi_scratch_identifier("arg_08h") is False
    assert is_safe_abi_scratch_identifier("arg_0fh") is False
    assert is_safe_abi_scratch_identifier("arg_68h") is False
    assert is_safe_abi_scratch_identifier("tmp_x0") is False
    assert is_safe_abi_scratch_identifier("something_else") is False


def test_abi_scratch_type_inference():
    assert infer_abi_scratch_type("arg0") == "u64"
    assert infer_abi_scratch_type("arg_30h") == "u64"


def test_non_main_function_abi_scratch_injection():
    # A non-main function using undeclared arg0/arg_30h should have declarations injected
    fn = ReconstructedFunction(
        name="test_func",
        canonical_name="test_func",
        c_name="test_func",
        entry_point="0x1000",
        function_kind="user",
        return_type="void",
        parameters=[
            {"name": "arg1", "type": "u64"}  # arg1 is declared as parameter
        ],
        local_variables=[],
        body_status="structured",
        structured_regions=[],
        lowered_blocks={
            "0x1000": [
                {"kind": "unknown", "text": "arg0 = arg1 + 5;", "address": "0x1000"},
                {"kind": "unknown", "text": "arg_30h = 10;", "address": "0x1004"},
            ]
        },
        lowered_statements=[],
        lowering={},
    )

    lines = []
    _emit_function(fn, lines)

    # Verify that only arg0 and arg_30h get declared as ABI scratch declarations
    assert any("u64 arg0 = 0; /* added for ABI scratch compile-shape */" in line for line in lines)
    assert any("u64 arg_30h = 0; /* added for ABI scratch compile-shape */" in line for line in lines)
    # arg1 should NOT get declared since it's already a parameter
    assert not any("u64 arg1 =" in line for line in lines)


def test_ignored_scanning_inside_comments_and_strings():
    # If a scratch variable name is only used in comments, string literals, or HEPHAESTUS_UNKNOWN_COND, it shouldn't be declared
    fn = ReconstructedFunction(
        name="test_func",
        canonical_name="test_func",
        c_name="test_func",
        entry_point="0x1000",
        function_kind="user",
        return_type="void",
        parameters=[],
        local_variables=[],
        body_status="structured",
        structured_regions=[],
        lowered_blocks={
            "0x1000": [
                {"kind": "unknown", "text": "/* This is a comment mentioning arg0 */", "address": "0x1000"},
                {"kind": "unknown", "text": 'const char* s = "arg1 in a string";', "address": "0x1004"},
                {"kind": "unknown", "text": "HEPHAESTUS_UNKNOWN_COND(\"arg2\");", "address": "0x1008"},
            ]
        },
        lowered_statements=[],
        lowering={},
    )

    lines = []
    _emit_function(fn, lines)

    # Verify that none of arg0, arg1, or arg2 are declared
    assert not any("u64 arg0" in line for line in lines)
    assert not any("u64 arg1" in line for line in lines)
    assert not any("u64 arg2" in line for line in lines)


def test_main_special_case_bridge_declaration():
    # In main, if bridge variables are missing but used, the bridges should be injected with correct initializers
    fn = ReconstructedFunction(
        name="main",
        canonical_name="main",
        c_name="main",
        entry_point="0x1000",
        function_kind="entrypoint",
        return_type="i32",
        parameters=[
            {"name": "argc", "type": "i32"},
            {"name": "argv", "type": "pointer"}
        ],
        local_variables=[],
        body_status="structured",
        structured_regions=[],
        lowered_blocks={
            "0x1000": [
                {"kind": "unknown", "text": "arg0 = 5;", "address": "0x1000"},
                {"kind": "unknown", "text": "param_1 = 10;", "address": "0x1004"},
            ]
        },
        lowered_statements=[],
        lowering={},
    )

    lines = []
    _emit_function(fn, lines)

    # Verify that bridges are injected with argc/argv instead of plain '= 0'
    assert any("u64 arg0 = (u64)argc;                  /* main ABI bridge: argc */" in line for line in lines)
    assert any("u64 param_1 = (u64)(uintptr_t)argv;    /* main ABI bridge: argv */" in line for line in lines)
    # Check that they do NOT get duplicated as '= 0'
    assert not any("u64 arg0 = 0;" in line for line in lines)
    assert not any("u64 param_1 = 0;" in line for line in lines)
