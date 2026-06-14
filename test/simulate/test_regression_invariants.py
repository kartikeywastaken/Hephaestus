# -*- coding: utf-8 -*-
"""
Meta Regression Invariant Tests

Protects critical correctness invariants:
1. No fabricated placeholder strings in serialized outputs.
2. No C source code / AST emission during type recovery/refinement.
3. Confidence never decreases from Phase 4A baseline.
4. Deterministic sorting of output functions/instructions.
5. Preserving base types when evidence is unknown/missing.
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


class TestRegressionInvariants(unittest.TestCase):

    # 1. No fabricated strings anywhere
    def test_no_fabricated_strings_anywhere(self):
        # Setup pipeline with some fake inputs
        func_ir = {
            "name": "test_func",
            "entry_point": "0x1000",
            "basic_blocks": [
                {
                    "id": "0x1000",
                    "instructions": [
                        # An instruction trying to sneak in a fabricated placeholder
                        {"address": "0x1000", "opcode": "mov", "mnemonic": "mov", "raw": "mov eax, 0", "source": "test"},
                        {"address": "0x1004", "opcode": "ldr", "mnemonic": "ldr", "operands": [{"kind": "register", "value": "w8"}, {"kind": "symbol", "name": "kernel32.dll"}], "source": "test"}
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

        serialized = json.dumps([r.to_dict() for r in refined], indent=2)

        # Assert no forbidden fabricated strings appear anywhere in the output
        forbidden = [
            "LoadLibraryA",
            "GetProcAddress",
            "kernel32.dll",
            "0xDEADBEEF",
            "mov eax",
            "cmp eax",
            "je exit_block",
            "0x0045e0c0",
            "0x00401000"
        ]
        for term in forbidden:
            self.assertNotIn(term.lower(), serialized.lower())

    # 2. No C source emission before source reconstruction phase
    def test_no_c_source_emission_keys(self):
        phase4a = _make_record(
            variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)],
            entry_point="0x1000"
        )
        type_rec = _make_type_recovery_dict([phase4a])
        uni_ir = _make_unified_ir([])

        engine = TypeRefinementEngine()
        refined = engine.refine(uni_ir, type_rec)
        serialized = json.dumps([r.to_dict() for r in refined])

        c_source_keys = [
            "source_code",
            "c_source",
            "statements",
            "expressions",
            "ast",
            "structs",
            "fields"
        ]
        # Assert none of these keys appear in the serialized JSON (unless legally allowed)
        # Note: 'structs' is checked but only for actual C code representation.
        for key in c_source_keys:
            # We look for key: ... format to check for dictionary keys
            self.assertNotIn(f'"{key}"', serialized)

    # 3. Confidence never decreases
    def test_confidence_never_decreases(self):
        # We'll set a base confidence of 0.8 on Phase 4A variable type
        base_type = RecoveredType(type_name="int32", confidence=0.8, source="known_db")
        var = RecoveredVariable(
            name="local_10",
            storage=STORAGE_STACK,
            category=CATEGORY_LOCAL,
            recovered_type=base_type,
            offset_bytes=16,
            size_bytes=4,
            source="test",
            confidence=0.8
        )
        phase4a = _make_record(variables=[var], entry_point="0x1000")
        type_rec = _make_type_recovery_dict([phase4a])

        # Weak arithmetic instruction with constraint priority 60
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
        uni_ir = _make_unified_ir([func_ir])

        engine = TypeRefinementEngine()
        refined = engine.refine(uni_ir, type_rec)

        refined_var = refined[0].variables[0]
        # Confidence must remain >= 0.8
        self.assertGreaterEqual(refined_var.refined_type.confidence, 0.8)

    # 4. Deterministic ordering
    def test_deterministic_ordering(self):
        # 3 functions in random order
        phase4a_1 = _make_record(name="func_b", entry_point="0x2000")
        phase4a_2 = _make_record(name="func_a", entry_point="0x1000")
        phase4a_3 = _make_record(name="func_c", entry_point="0x1500")

        type_rec = _make_type_recovery_dict([phase4a_1, phase4a_2, phase4a_3])
        uni_ir = _make_unified_ir([])

        engine = TypeRefinementEngine()
        refined = engine.refine(uni_ir, type_rec)

        # Output must be sorted by entry_point (0x1000, 0x1500, 0x2000)
        self.assertEqual(refined[0].name, "func_a")
        self.assertEqual(refined[1].name, "func_c")
        self.assertEqual(refined[2].name, "func_b")

    # 5. Unknown evidence stays unknown
    def test_unknown_evidence_stays_unknown(self):
        # No instructions or operands binding to variable
        phase4a = _make_record(
            variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)],
            entry_point="0x1000"
        )
        type_rec = _make_type_recovery_dict([phase4a])
        # Empty instructions
        uni_ir = _make_unified_ir([{
            "name": "test_func",
            "entry_point": "0x1000",
            "basic_blocks": [{"id": "0x1000", "instructions": []}]
        }])

        engine = TypeRefinementEngine()
        refined = engine.refine(uni_ir, type_rec)

        self.assertEqual(refined[0].total_constraints_applied, 0)
        self.assertEqual(refined[0].variables[0].refined_type.type_name, TYPE_UNKNOWN)


if __name__ == "__main__":
    unittest.main()
