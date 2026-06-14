# -*- coding: utf-8 -*-
"""
Adversarial Full Pipeline End-to-End Stress Tests

Tests the end-to-end type refinement engine under missing evidence, conflicting
constraints, missing functions, malformed schemas, and verifies determinism.
"""

import json
import unittest
from src.ir.types.refinement_engine import TypeRefinementEngine
from src.ir.types.models import (
    RecoveredFunctionSemantics,
    RecoveredVariable,
    RecoveredSignature,
    RecoveredType,
    STORAGE_STACK,
    CATEGORY_LOCAL,
    TYPE_UNKNOWN,
    FUNCTION_KIND_USER,
)


def _make_var(name, offset_bytes=None, size_bytes=4):
    return RecoveredVariable(
        name=name,
        storage=STORAGE_STACK,
        category=CATEGORY_LOCAL,
        recovered_type=RecoveredType(type_name=TYPE_UNKNOWN, confidence=0.2, source="test"),
        offset_bytes=offset_bytes,
        size_bytes=size_bytes,
        source="test",
        confidence=0.2,
    )


def _make_record(variables=None, parameters=None, name="test_func", entry_point="0x1000"):
    sig = RecoveredSignature(
        return_type=RecoveredType(type_name=TYPE_UNKNOWN, confidence=0.2, source="test"),
        parameters=parameters or [],
        variadic=False,
        confidence=0.2,
        source="test",
    )
    return RecoveredFunctionSemantics(
        name=name,
        entry_point=entry_point,
        function_kind=FUNCTION_KIND_USER,
        signature=sig,
        variables=variables or [],
        evidence=["test"],
        confidence=0.2,
    )


def _make_type_recovery_dict(func_records):
    return {
        "schema_version": "4A.0.0",
        "provenance": {"phase": "4A"},
        "data": {
            "functions": [r.to_dict() for r in func_records],
        },
    }


def _make_unified_ir(func_list):
    return {
        "schema_version": "2.0.0",
        "provenance": {"binary_path": "test.bin"},
        "data": {
            "functions": func_list,
            "call_graph": {"nodes": [], "edges": []},
        },
    }


class TestAdversarialFullPipeline(unittest.TestCase):

    # Test 1 — Stack arithmetic refinement
    def test_stack_arithmetic_refinement(self):
        # ldr w8, [sp, #16]; add w8, w8, #1; str w8, [sp, #16]
        func_ir = {
            "name": "test_func",
            "entry_point": "0x1000",
            "basic_blocks": [
                {
                    "id": "0x1000",
                    "instructions": [
                        {"address": "0x1000", "opcode": "ldr", "mnemonic": "ldr", "operands": [{"kind": "register", "value": "w8"}, {"kind": "memory", "base": "sp", "offset": 16, "size_bytes": 4}], "size_bytes": 4, "source": "test"},
                        {"address": "0x1004", "opcode": "add", "mnemonic": "add", "operands": [{"kind": "register", "value": "w8"}, {"kind": "register", "value": "w8"}, {"kind": "immediate", "value": 1}], "source": "test"},
                        {"address": "0x1008", "opcode": "str", "mnemonic": "str", "operands": [{"kind": "register", "value": "w8"}, {"kind": "memory", "base": "sp", "offset": 16, "size_bytes": 4}], "size_bytes": 4, "source": "test"}
                    ]
                }
            ]
        }
        phase4a = _make_record(
            variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)],
            entry_point="0x1000"
        )
        type_rec = _make_type_recovery_dict([phase4a])
        uni_ir = _make_unified_ir([func_ir])

        engine = TypeRefinementEngine()
        refined = engine.refine(uni_ir, type_rec)

        self.assertEqual(len(refined), 1)
        ref_func = refined[0]
        self.assertGreaterEqual(ref_func.total_constraints_applied, 1)

        # Check local_10 has refined_type changed or confidence increased
        local_10_record = next(v for v in ref_func.variables if v.name == "local_10")
        self.assertGreater(local_10_record.refined_type.confidence, 0.2)

    # Test 2 — No binding means no refinement
    def test_no_binding_means_no_refinement(self):
        func_ir = {
            "name": "test_func",
            "entry_point": "0x1000",
            "basic_blocks": [
                {
                    "id": "0x1000",
                    "instructions": [
                        {"address": "0x1000", "opcode": "add", "mnemonic": "add", "operands": [{"kind": "register", "value": "w8"}, {"kind": "register", "value": "w8"}, {"kind": "immediate", "value": 1}], "source": "test"}
                    ]
                }
            ]
        }
        # local_10 offset is 16, but instruction does not bind SP or offset 16.
        phase4a = _make_record(
            variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)],
            entry_point="0x1000"
        )
        type_rec = _make_type_recovery_dict([phase4a])
        uni_ir = _make_unified_ir([func_ir])

        engine = TypeRefinementEngine()
        refined = engine.refine(uni_ir, type_rec)

        self.assertEqual(len(refined), 1)
        ref_func = refined[0]
        self.assertEqual(ref_func.total_constraints_applied, 0)
        local_10_record = next(v for v in ref_func.variables if v.name == "local_10")
        self.assertEqual(local_10_record.refined_type.type_name, TYPE_UNKNOWN)

    # Test 3 — ABI call argument refinement
    def test_abi_call_argument_refinement(self):
        func_ir = {
            "name": "test_func",
            "entry_point": "0x1000",
            "basic_blocks": [
                {
                    "id": "0x1000",
                    "instructions": [
                        {"address": "0x1000", "opcode": "ldr", "mnemonic": "ldr", "operands": [{"kind": "register", "value": "x0"}, {"kind": "memory", "base": "sp", "offset": 16, "size_bytes": 8}], "size_bytes": 8, "source": "test"},
                        {"address": "0x1004", "opcode": "bl", "mnemonic": "bl", "operands": [{"kind": "symbol", "name": "_printf"}], "source": "test"}
                    ]
                }
            ]
        }
        phase4a = _make_record(
            variables=[_make_var("local_fmt", offset_bytes=16, size_bytes=8)],
            entry_point="0x1000"
        )
        type_rec = _make_type_recovery_dict([phase4a])
        uni_ir = _make_unified_ir([func_ir])

        engine = TypeRefinementEngine()
        refined = engine.refine(uni_ir, type_rec)

        self.assertEqual(len(refined), 1)
        ref_func = refined[0]
        self.assertGreaterEqual(ref_func.total_constraints_applied, 1)

        # fmt var should have a CALL_ARG constraint and confidence > 0.2
        local_fmt_record = next(v for v in ref_func.variables if v.name == "local_fmt")
        self.assertGreater(local_fmt_record.refined_type.confidence, 0.2)

    # Test 4 — Conflict keeps base
    def test_conflict_keeps_base(self):
        from src.ir.types.resolver import resolve_constraints
        from src.ir.types.constraints import TypeConstraint, ConstraintSource, ConstraintKind

        # Same priority (e.g. 60) conflicting constraints
        c1 = TypeConstraint(ConstraintKind.SIZE, "x", "int32", ConstraintSource.IR_MEMORY, "note1")
        c2 = TypeConstraint(ConstraintKind.SIZE, "x", "int16", ConstraintSource.IR_MEMORY, "note2")

        base = RecoveredType("unknown", 0.2, "test")
        resolved = resolve_constraints(base, [c1, c2])

        # Conflicting same priority keeps base type_name
        self.assertEqual(resolved.type_name, "unknown")

    # Test 5 — Function missing from Unified IR
    def test_function_missing_from_unified_ir(self):
        # type_rec has test_func at 0x1000, but Unified IR is empty
        phase4a = _make_record(
            variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)],
            entry_point="0x1000",
            name="test_func"
        )
        type_rec = _make_type_recovery_dict([phase4a])
        uni_ir = _make_unified_ir([])  # Empty IR

        engine = TypeRefinementEngine()
        refined = engine.refine(uni_ir, type_rec)

        # Refinement should still run and preserve phase 4a types
        self.assertEqual(len(refined), 1)
        self.assertEqual(refined[0].name, "test_func")
        self.assertEqual(refined[0].total_constraints_applied, 0)
        self.assertEqual(refined[0].variables[0].refined_type.type_name, TYPE_UNKNOWN)

    # Test 6 — Malformed type recovery function
    def test_malformed_type_recovery_function(self):
        # Recovery record missing signature, variables, etc.
        malformed_phase4a = {
            "name": "malformed_func",
            "entry_point": "0x1000"
            # missing signature, variables
        }
        type_rec = {
            "schema_version": "4A.0.0",
            "provenance": {"phase": "4A"},
            "data": {
                "functions": [malformed_phase4a]
            }
        }
        uni_ir = _make_unified_ir([])

        engine = TypeRefinementEngine()
        # Should handle gracefully, not crash (either skipping or returning empty)
        try:
            refined = engine.refine(uni_ir, type_rec)
            # Safe return is acceptable
            self.assertIsInstance(refined, list)
        except Exception as e:
            self.fail(f"Refinement engine crashed on malformed type recovery function: {e}")

    # Test 7 — Repeated run deterministic
    def test_repeated_run_deterministic(self):
        func_ir = {
            "name": "test_func",
            "entry_point": "0x1000",
            "basic_blocks": [
                {
                    "id": "0x1000",
                    "instructions": [
                        {"address": "0x1000", "opcode": "ldr", "mnemonic": "ldr", "operands": [{"kind": "register", "value": "w8"}, {"kind": "memory", "base": "sp", "offset": 16, "size_bytes": 4}], "size_bytes": 4, "source": "test"},
                        {"address": "0x1004", "opcode": "add", "mnemonic": "add", "operands": [{"kind": "register", "value": "w8"}, {"kind": "register", "value": "w8"}, {"kind": "immediate", "value": 1}], "source": "test"}
                    ]
                }
            ]
        }
        phase4a = _make_record(
            variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)],
            entry_point="0x1000"
        )
        type_rec = _make_type_recovery_dict([phase4a])
        uni_ir = _make_unified_ir([func_ir])

        engine = TypeRefinementEngine()
        refined1 = engine.refine(uni_ir, type_rec)
        refined2 = engine.refine(uni_ir, type_rec)

        dict1 = [r.to_dict() for r in refined1]
        dict2 = [r.to_dict() for r in refined2]

        self.assertEqual(
            json.dumps(dict1, sort_keys=True),
            json.dumps(dict2, sort_keys=True)
        )


if __name__ == "__main__":
    unittest.main()
