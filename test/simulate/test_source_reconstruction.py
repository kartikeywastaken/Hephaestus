# -*- coding: utf-8 -*-
"""
Tests for Phase 5.1 Source Reconstruction Foundation.

All tests use in-memory artifacts — no file I/O required.

Tests validate:
- ReconstructedFunction model
- SourceReconstructionArtifact model
- Reconstructor builder logic
- C identifier sanitization
- Body status determination
- Synthetic parameter generation from ABI bindings
- Unknown return type defaulting to u64
- No fabrication of structs, fields, or source expressions
- C emitter output structure
- Recursive region tree walking
"""

import json
import os
import tempfile

import pytest

from src.ir.source.models import (
    SCHEMA_VERSION,
    ReconstructedFunction,
    SourceReconstructionArtifact,
)
from src.ir.source.reconstructor import (
    build_source_reconstruction,
    sanitize_c_identifier,
    _determine_body_status,
    _extract_return_type,
    _extract_parameters,
)
from src.ir.source.emitter import write_source_reconstruction_artifact
from src.ir.source.c_emitter import emit_recovered_c


# ---------------------------------------------------------------------------
# Helpers — minimal artifact builders
# ---------------------------------------------------------------------------

def _make_ir(functions=None, symbol_aliases=None):
    """Build a minimal unified_ir.json dict."""
    data = {"functions": functions or []}
    if symbol_aliases is not None:
        data["symbol_aliases"] = symbol_aliases
    return {
        "schema_version": "2.0.0",
        "provenance": {"binary_path": "test.bin"},
        "data": data,
    }


def _make_ir_func(name="test_func", entry_point="0x1000", basic_blocks=None):
    """Build a minimal IR function dict."""
    return {
        "name": name,
        "entry_point": entry_point,
        "basic_blocks": basic_blocks or [],
    }


def _make_regions(entries=None):
    """Build a minimal structuring_regions.json list."""
    return entries or []


def _make_region_entry(func_name, body_dict):
    """Build a structuring region entry."""
    return {
        "function_name": func_name,
        "structured_body": body_dict,
    }


def _make_semantics(functions=None):
    """Build a minimal phase4_semantics.json dict."""
    return {
        "schema_version": "4D.1.0",
        "data": {
            "functions": functions or [],
            "summary": {},
        },
    }


def _make_sem_func(
    name="test_func",
    entry_point="0x1000",
    function_kind="user",
    recovered_signature=None,
    refined_signature=None,
    parameters=None,
    refined_parameters=None,
    variables=None,
    refined_variables=None,
    abi_argument_bindings=None,
    parameter_layout_evidence=None,
    layout_candidates=None,
):
    """Build a minimal Phase 4D function semantics dict."""
    return {
        "name": name,
        "entry_point": entry_point,
        "function_kind": function_kind,
        "recovered_signature": recovered_signature or {},
        "refined_signature": refined_signature or {},
        "parameters": parameters or [],
        "refined_parameters": refined_parameters or [],
        "variables": variables or [],
        "refined_variables": refined_variables or [],
        "abi_argument_bindings": abi_argument_bindings or [],
        "parameter_layout_evidence": parameter_layout_evidence or [],
        "layout_candidates": layout_candidates or [],
    }


# ---------------------------------------------------------------------------
# Test: Schema version
# ---------------------------------------------------------------------------

class TestSchemaVersion:
    def test_schema_version_is_5_7_0(self):
        assert SCHEMA_VERSION == "5.7.0"
 
    def test_artifact_schema_version(self):
        artifact = SourceReconstructionArtifact()
        assert artifact.schema_version == "5.7.0"
        d = artifact.to_dict()
        assert d["schema_version"] == "5.7.0"


# ---------------------------------------------------------------------------
# Test: C identifier sanitization
# ---------------------------------------------------------------------------

class TestSanitizeCIdentifier:
    def test_normal_name(self):
        assert sanitize_c_identifier("my_func") == "my_func"

    def test_digit_leading(self):
        result = sanitize_c_identifier("100_foo")
        assert result.startswith("fn_")
        assert "100" in result
        assert "foo" in result

    def test_special_chars(self):
        result = sanitize_c_identifier("sym._main")
        assert result == "sym_main"
        # Must be valid C identifier
        assert result.isidentifier()

    def test_fun_prefix(self):
        result = sanitize_c_identifier("FUN_100000460")
        assert result.isidentifier()

    def test_empty_string(self):
        assert sanitize_c_identifier("") == "fn_unknown"

    def test_whitespace_only(self):
        assert sanitize_c_identifier("   ") == "fn_unknown"

    def test_hex_address_only(self):
        result = sanitize_c_identifier("0x100000460")
        assert result.isidentifier()
        assert result.startswith("fn_")

    def test_preserves_semantic_content(self):
        result = sanitize_c_identifier("process_data_buffer")
        assert result == "process_data_buffer"

    def test_consecutive_special_chars(self):
        result = sanitize_c_identifier("a..b--c")
        # Should collapse underscores
        assert "__" not in result


# ---------------------------------------------------------------------------
# Test: Body status determination
# ---------------------------------------------------------------------------

class TestBodyStatus:
    def test_sequence_is_structured(self):
        region = {"structured_body": {"type": "sequence", "children": []}}
        assert _determine_body_status(region) == "structured"

    def test_if_is_structured(self):
        region = {"structured_body": {"type": "if", "condition_block": "b1"}}
        assert _determine_body_status(region) == "structured"

    def test_if_else_is_structured(self):
        region = {"structured_body": {"type": "if_else"}}
        assert _determine_body_status(region) == "structured"

    def test_loop_is_structured(self):
        region = {"structured_body": {"type": "loop"}}
        assert _determine_body_status(region) == "structured"

    def test_block_is_partial(self):
        region = {"structured_body": {"type": "block", "id": "b1"}}
        assert _determine_body_status(region) == "partially_structured"

    def test_unstructured_is_unstructured(self):
        region = {"structured_body": {"type": "unstructured"}}
        assert _determine_body_status(region) == "unstructured"

    def test_none_is_missing(self):
        assert _determine_body_status(None) == "missing"

    def test_empty_body_is_missing(self):
        region = {"structured_body": {}}
        assert _determine_body_status(region) == "missing"


# ---------------------------------------------------------------------------
# Test: Return type extraction
# ---------------------------------------------------------------------------

class TestReturnType:
    def test_known_return_type(self):
        sem = {
            "refined_signature": {
                "return_type": {"type": "int32"},
            },
        }
        warnings = []
        result = _extract_return_type(sem, warnings)
        assert result == "i32"
        assert "unknown_return_type_defaulted_to_u64" not in warnings

    def test_void_return(self):
        sem = {"refined_signature": {"return_type": {"type": "void"}}}
        warnings = []
        assert _extract_return_type(sem, warnings) == "void"

    def test_unknown_defaults_to_u64(self):
        sem = {"refined_signature": {"return_type": {"type": "unknown"}}}
        warnings = []
        result = _extract_return_type(sem, warnings)
        assert result == "u64"
        assert "unknown_return_type_defaulted_to_u64" in warnings

    def test_missing_semantics_defaults_to_u64(self):
        warnings = []
        result = _extract_return_type(None, warnings)
        assert result == "u64"
        assert "unknown_return_type_defaulted_to_u64" in warnings

    def test_fallback_to_recovered_signature(self):
        sem = {
            "refined_signature": {},
            "recovered_signature": {"return_type": {"type": "uint32"}},
        }
        warnings = []
        result = _extract_return_type(sem, warnings)
        assert result == "u32"


# ---------------------------------------------------------------------------
# Test: Parameter extraction with ABI synthetic fallback
# ---------------------------------------------------------------------------

class TestParameterExtraction:
    def test_phase4d_params_used(self):
        sem = {
            "refined_parameters": [
                {"name": "ptr", "type": "pointer"},
            ],
        }
        notes = []
        params = _extract_parameters(sem, [], notes)
        assert len(params) == 1
        assert params[0]["name"] == "ptr"

    def test_synthetic_from_abi_bindings(self):
        """When Phase 4D params empty, ABI bindings create synthetic params."""
        sem = {"refined_parameters": [], "parameters": []}
        abi = [
            {"argument_index": 0, "register": "x0"},
            {"argument_index": 2, "register": "x2"},
        ]
        notes = []
        params = _extract_parameters(sem, abi, notes)
        assert len(params) == 2
        assert params[0]["name"] == "arg0"
        assert params[0]["type"] == "u64"
        assert params[0]["source"] == "abi_synthetic"
        assert params[1]["name"] == "arg2"
        assert any("Synthetic" in n for n in notes)

    def test_no_synthetic_when_phase4d_has_params(self):
        """ABI bindings don't override Phase 4D params."""
        sem = {"refined_parameters": [{"name": "x", "type": "i32"}]}
        abi = [{"argument_index": 0, "register": "x0"}]
        notes = []
        params = _extract_parameters(sem, abi, notes)
        assert len(params) == 1
        assert params[0]["name"] == "x"

    def test_no_params_no_abi(self):
        sem = {"refined_parameters": [], "parameters": []}
        params = _extract_parameters(sem, [], [])
        assert params == []


# ---------------------------------------------------------------------------
# Test: Basic reconstruction
# ---------------------------------------------------------------------------

class TestBuildSourceReconstruction:
    def test_single_function(self):
        ir = _make_ir([_make_ir_func("my_func", "0x1000", [
            {"id": "b1", "instructions": [{"address": "0x1000", "mnemonic": "mov"}]},
        ])])
        regions = _make_regions([
            _make_region_entry("my_func", {"type": "block", "id": "b1"}),
        ])
        sem = _make_semantics([_make_sem_func(
            "my_func", "0x1000",
            refined_signature={"return_type": {"type": "int32"}},
            refined_parameters=[{"name": "x", "type": "int32"}],
        )])

        artifact = build_source_reconstruction(ir, regions, sem)
        assert artifact.schema_version == "5.7.0"
        assert len(artifact.functions) == 1

        fn = artifact.functions[0]
        assert fn.name == "my_func"
        assert fn.canonical_name == "my_func"
        assert fn.c_name == "my_func"
        assert fn.return_type == "i32"
        assert fn.body_status == "partially_structured"
        assert fn.instruction_count == 1
        assert fn.basic_block_count == 1

    def test_empty_function_warning(self):
        ir = _make_ir([_make_ir_func("empty_fn", "0x2000", [])])
        regions = _make_regions()
        sem = _make_semantics()

        artifact = build_source_reconstruction(ir, regions, sem)
        fn = artifact.functions[0]
        assert "empty_function" in fn.warnings
        assert fn.body_status == "missing"

    def test_structured_function(self):
        ir = _make_ir([_make_ir_func("loop_fn", "0x3000")])
        regions = _make_regions([
            _make_region_entry("loop_fn", {
                "type": "sequence",
                "children": [
                    {"type": "block", "id": "b1"},
                    {"type": "loop", "kind": "while", "header_block": "b2",
                     "body": {"type": "block", "id": "b3"},
                     "exit_blocks": ["b4"]},
                ],
            }),
        ])
        sem = _make_semantics()

        artifact = build_source_reconstruction(ir, regions, sem)
        fn = artifact.functions[0]
        assert fn.body_status == "structured"

    def test_unstructured_function(self):
        ir = _make_ir([_make_ir_func("messy_fn", "0x4000")])
        regions = _make_regions([
            _make_region_entry("messy_fn", {
                "type": "unstructured",
                "reason": "irreducible_cfg",
                "children": [],
            }),
        ])
        sem = _make_semantics()

        artifact = build_source_reconstruction(ir, regions, sem)
        fn = artifact.functions[0]
        assert fn.body_status == "unstructured"

    def test_multiple_functions_ordering(self):
        ir = _make_ir([
            _make_ir_func("fn_a", "0x1000"),
            _make_ir_func("fn_b", "0x2000"),
            _make_ir_func("fn_c", "0x3000"),
        ])
        regions = _make_regions()
        sem = _make_semantics()

        artifact = build_source_reconstruction(ir, regions, sem)
        assert len(artifact.functions) == 3
        names = [f.name for f in artifact.functions]
        assert names == ["fn_a", "fn_b", "fn_c"]

    def test_missing_phase4d_match_no_crash(self):
        """Function with no matching Phase 4D record should still work."""
        ir = _make_ir([_make_ir_func("orphan_fn", "0x9999")])
        regions = _make_regions()
        sem = _make_semantics([_make_sem_func("other_fn", "0x1111")])

        artifact = build_source_reconstruction(ir, regions, sem)
        fn = artifact.functions[0]
        assert fn.name == "orphan_fn"
        assert fn.return_type == "u64"
        assert "unknown_return_type_defaulted_to_u64" in fn.warnings

    def test_canonical_name_from_aliases(self):
        ir = _make_ir(
            [_make_ir_func("_main", "0x1000")],
            symbol_aliases=[{
                "entry_point": "0x1000",
                "canonical_name": "main",
                "aliases": ["_main", "main"],
            }],
        )
        regions = _make_regions()
        sem = _make_semantics()

        artifact = build_source_reconstruction(ir, regions, sem)
        fn = artifact.functions[0]
        assert fn.name == "_main"
        assert fn.canonical_name == "main"
        assert fn.c_name == "main"


# ---------------------------------------------------------------------------
# Test: Evidence preservation
# ---------------------------------------------------------------------------

class TestEvidencePreservation:
    def test_abi_bindings_preserved(self):
        abi = [{"register": "x0", "argument_index": 0, "binding_kind": "direct_abi_reg"}]
        ir = _make_ir([_make_ir_func("fn", "0x1000")])
        sem = _make_semantics([_make_sem_func("fn", "0x1000", abi_argument_bindings=abi)])

        artifact = build_source_reconstruction(ir, _make_regions(), sem)
        fn = artifact.functions[0]
        assert len(fn.abi_argument_bindings) == 1
        assert fn.abi_argument_bindings[0]["register"] == "x0"

    def test_parameter_layout_evidence_preserved(self):
        ple = [{
            "parameter_index": 0,
            "parameter_name": "arg0",
            "observed_offsets": [0, 8],
            "observed_sizes": [4, 4],
        }]
        ir = _make_ir([_make_ir_func("fn", "0x1000")])
        sem = _make_semantics([
            _make_sem_func("fn", "0x1000", parameter_layout_evidence=ple),
        ])

        artifact = build_source_reconstruction(ir, _make_regions(), sem)
        fn = artifact.functions[0]
        assert len(fn.parameter_layout_evidence) == 1

    def test_layout_candidates_preserved(self):
        lc = [{
            "base_id": "x0",
            "layout_kind": "struct_like",
            "observed_offsets": [0, 4, 8],
            "observed_sizes": [4, 4, 8],
        }]
        ir = _make_ir([_make_ir_func("fn", "0x1000")])
        sem = _make_semantics([
            _make_sem_func("fn", "0x1000", layout_candidates=lc),
        ])

        artifact = build_source_reconstruction(ir, _make_regions(), sem)
        fn = artifact.functions[0]
        assert len(fn.layout_candidates) == 1


# ---------------------------------------------------------------------------
# Test: Summary counters
# ---------------------------------------------------------------------------

class TestSummary:
    def test_summary_counts(self):
        ir = _make_ir([
            _make_ir_func("fn1", "0x1000", [
                {"id": "b1", "instructions": [{"mnemonic": "mov"}]},
            ]),
            _make_ir_func("fn2", "0x2000"),
        ])
        regions = _make_regions([
            _make_region_entry("fn1", {"type": "sequence", "children": []}),
        ])
        sem = _make_semantics([
            _make_sem_func("fn1", "0x1000",
                           refined_parameters=[{"name": "p", "type": "i32"}]),
        ])

        artifact = build_source_reconstruction(ir, regions, sem)
        s = artifact.summary
        assert s["functions_total"] == 2
        assert s["functions_structured"] == 1
        assert s["total_parameters"] >= 1
        assert s["total_instructions"] == 1


# ---------------------------------------------------------------------------
# Test: C emitter output
# ---------------------------------------------------------------------------

class TestCEmitter:
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

    def test_basic_c_output(self):
        fn = ReconstructedFunction(
            name="test_func",
            canonical_name="test_func",
            c_name="test_func",
            entry_point="0x1000",
            return_type="i32",
            parameters=[{"name": "x", "type": "i32"}],
            body_status="structured",
            basic_block_count=3,
            instruction_count=10,
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        output = self._emit_to_string(artifact)

        assert "#include <stdint.h>" in output
        assert "int32_t test_func(int32_t x)" in output
        assert "/* return value unknown */" in output
        assert "return 0;" in output
        assert "Body status: structured" in output

    def test_void_return(self):
        fn = ReconstructedFunction(
            name="void_fn", canonical_name="void_fn", c_name="void_fn",
            return_type="void",
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        output = self._emit_to_string(artifact)

        assert "void void_fn(void)" in output
        assert "return; /* void return */" in output

    def test_forward_declarations(self):
        fn = ReconstructedFunction(
            name="fn1", canonical_name="fn1", c_name="fn1",
            return_type="u64",
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        output = self._emit_to_string(artifact)

        assert "Forward Declarations" in output
        assert "uint64_t fn1(void);" in output

    def test_abi_binding_comments(self):
        fn = ReconstructedFunction(
            name="fn1", canonical_name="fn1", c_name="fn1",
            abi_argument_bindings=[
                {"register": "x0", "argument_index": 0, "binding_kind": "direct_abi_reg"},
            ],
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        output = self._emit_to_string(artifact)
        assert "x0 => param 0" in output

    def test_layout_evidence_comments(self):
        fn = ReconstructedFunction(
            name="fn1", canonical_name="fn1", c_name="fn1",
            parameter_layout_evidence=[{
                "parameter_index": 0,
                "parameter_name": "arg0",
                "observed_offsets": [0, 8],
                "observed_sizes": [4, 4],
            }],
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        output = self._emit_to_string(artifact)
        assert "param 0" in output
        assert "offsets=" in output

    def test_layout_candidate_comments(self):
        fn = ReconstructedFunction(
            name="fn1", canonical_name="fn1", c_name="fn1",
            layout_candidates=[{
                "base_id": "x0",
                "layout_kind": "struct_like",
                "observed_offsets": [0, 4],
                "observed_sizes": [4, 4],
            }],
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        output = self._emit_to_string(artifact)
        assert "base=x0" in output
        assert "kind=struct_like" in output

    def test_recursive_region_comments(self):
        """Verify that nested regions are recursively walked."""
        fn = ReconstructedFunction(
            name="fn1", canonical_name="fn1", c_name="fn1",
            structured_regions=[{
                "type": "sequence",
                "children": [
                    {"type": "block", "id": "b1"},
                    {
                        "type": "if_else",
                        "condition_block": "b2",
                        "then_branch": {"type": "block", "id": "b3"},
                        "else_branch": {
                            "type": "sequence",
                            "children": [
                                {"type": "block", "id": "b4"},
                                {"type": "block", "id": "b5"},
                            ],
                        },
                        "merge_block": "b6",
                    },
                ],
            }],
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        output = self._emit_to_string(artifact)

        # All blocks should appear in comments
        assert "block b1" in output
        assert 'if (HEPHAESTUS_UNKNOWN_COND("condition unknown: block b2"))' in output
        assert "block b3" in output
        assert "block b4" in output
        assert "block b5" in output

    def test_loop_region_comments(self):
        fn = ReconstructedFunction(
            name="fn1", canonical_name="fn1", c_name="fn1",
            structured_regions=[{
                "type": "loop",
                "kind": "while",
                "header_block": "b1",
                "body": {"type": "block", "id": "b2"},
                "exit_blocks": ["b3"],
            }],
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        output = self._emit_to_string(artifact)
        assert 'while (HEPHAESTUS_UNKNOWN_COND("condition unknown: loop header b1"))' in output
        assert "block b2" in output

    def test_unstructured_region_comments(self):
        fn = ReconstructedFunction(
            name="fn1", canonical_name="fn1", c_name="fn1",
            structured_regions=[{
                "type": "unstructured",
                "reason": "irreducible_cfg",
                "region_kind": "cyclic",
                "children": [
                    {"type": "block", "id": "b1"},
                    {"type": "block", "id": "b2"},
                ],
            }],
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        output = self._emit_to_string(artifact)
        assert "unstructured region" in output
        assert "irreducible_cfg" in output
        assert "block b1" in output
        assert "block b2" in output

    def test_warnings_in_output(self):
        fn = ReconstructedFunction(
            name="fn1", canonical_name="fn1", c_name="fn1",
            warnings=["empty_function", "unknown_return_type_defaulted_to_u64"],
        )
        artifact = SourceReconstructionArtifact(functions=[fn])
        output = self._emit_to_string(artifact)
        assert "WARNING: empty_function" in output
        assert "WARNING: unknown_return_type_defaulted_to_u64" in output


# ---------------------------------------------------------------------------
# Test: No fabrication
# ---------------------------------------------------------------------------

class TestNoFabrication:
    """
    Verify that Phase 5.1 does not invent struct definitions, field names,
    or ->field source expressions. These checks use content-aware patterns
    rather than naive substring matching.
    """

    def _build_c_output(self):
        """Build a complex artifact and emit C output."""
        ir = _make_ir([
            _make_ir_func("fn_a", "0x1000", [
                {"id": "b1", "instructions": [
                    {"address": "0x1000", "mnemonic": "mov"},
                    {"address": "0x1004", "mnemonic": "str"},
                ]},
            ]),
            _make_ir_func("fn_b", "0x2000", [
                {"id": "b2", "instructions": [
                    {"address": "0x2000", "mnemonic": "ldr"},
                ]},
            ]),
        ])
        regions = _make_regions([
            _make_region_entry("fn_a", {
                "type": "sequence",
                "children": [
                    {"type": "block", "id": "b1"},
                    {"type": "if", "condition_block": "b2",
                     "then_branch": {"type": "block", "id": "b3"},
                     "merge_block": "b4"},
                ],
            }),
        ])
        sem = _make_semantics([
            _make_sem_func("fn_a", "0x1000",
                           layout_candidates=[{
                               "base_id": "x0", "layout_kind": "struct_like",
                               "observed_offsets": [0, 4, 8],
                               "observed_sizes": [4, 4, 8],
                           }],
                           abi_argument_bindings=[{
                               "register": "x0", "argument_index": 0,
                               "binding_kind": "direct_abi_reg",
                           }],
                           parameter_layout_evidence=[{
                               "parameter_index": 0, "parameter_name": "arg0",
                               "observed_offsets": [0, 4], "observed_sizes": [4, 4],
                           }]),
        ])

        artifact = build_source_reconstruction(ir, regions, sem)

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

    def test_no_struct_definitions(self):
        """No 'struct ' followed by a name (struct definition/declaration)."""
        output = self._build_c_output()
        # Check for struct definitions: "struct Foo", "struct _data", etc.
        # Allow "struct_like" and "struct_candidate" as these are evidence labels
        lines = output.split("\n")
        for line in lines:
            # Skip lines that are comments with evidence labels
            stripped = line.strip()
            if stripped.startswith("/*") or stripped.startswith("*"):
                continue
            # No struct keyword in actual code lines
            assert "struct " not in stripped, (
                f"Found 'struct ' in non-comment line: {stripped!r}"
            )

    def test_no_arrow_operator(self):
        """No '->' field access expressions anywhere in the output."""
        output = self._build_c_output()
        assert "->" not in output, "Found '->' operator in output"

    def test_no_fake_field_names(self):
        """No invented field names like .id, .score, .name, .data, .next."""
        output = self._build_c_output()
        fake_fields = [".id", ".score", ".name", ".data", ".next",
                       ".value", ".key", ".count", ".size", ".ptr"]
        for field in fake_fields:
            # Only check in non-comment actual code lines
            for line in output.split("\n"):
                stripped = line.strip()
                if stripped.startswith("/*") or stripped.startswith("*"):
                    continue
                assert field not in stripped, (
                    f"Found fake field name '{field}' in code line: {stripped!r}"
                )

    def test_no_invented_conditions(self):
        """No invented if/while/for conditions in actual code."""
        output = self._build_c_output()
        for line in output.split("\n"):
            stripped = line.strip()
            if stripped.startswith("/*") or stripped.startswith("*"):
                continue
            if stripped.startswith("if (") or stripped.startswith("while (") or stripped.startswith("for ("):
                assert "condition unknown" in stripped, f"Found invented condition: {stripped!r}"
                assert "tmp_" not in stripped, f"Found variable in condition: {stripped!r}"
                assert "arg" not in stripped, f"Found variable in condition: {stripped!r}"
                assert "stack_" not in stripped, f"Found variable in condition: {stripped!r}"


# ---------------------------------------------------------------------------
# Test: JSON artifact emitter
# ---------------------------------------------------------------------------

class TestEmitter:
    def test_write_and_read(self):
        fn = ReconstructedFunction(
            name="fn1", canonical_name="fn1", c_name="fn1",
            entry_point="0x1000", return_type="u64",
        )
        artifact = SourceReconstructionArtifact(functions=[fn])

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            path = f.name
        try:
            write_source_reconstruction_artifact(artifact, path)
            with open(path, "r") as f:
                data = json.load(f)
            assert data["schema_version"] == "5.7.0"
            assert data["provenance"]["phase"] == "5.7"
            assert len(data["data"]["functions"]) == 1
            assert data["data"]["functions"][0]["name"] == "fn1"
            assert data["data"]["functions"][0]["canonical_name"] == "fn1"
            assert data["data"]["functions"][0]["c_name"] == "fn1"
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Test: ReconstructedFunction model
# ---------------------------------------------------------------------------

class TestReconstructedFunction:
    def test_to_dict_round_trip(self):
        fn = ReconstructedFunction(
            name="orig_name",
            canonical_name="canon_name",
            c_name="canon_name",
            entry_point="0x1000",
            function_kind="user",
            return_type="i32",
            body_status="structured",
            warnings=["empty_function"],
        )
        d = fn.to_dict()
        assert d["name"] == "orig_name"
        assert d["canonical_name"] == "canon_name"
        assert d["c_name"] == "canon_name"
        assert d["body_status"] == "structured"
        assert "empty_function" in d["warnings"]

    def test_defaults(self):
        fn = ReconstructedFunction()
        d = fn.to_dict()
        assert d["return_type"] == "u64"
        assert d["body_status"] == "missing"
        assert d["warnings"] == []
