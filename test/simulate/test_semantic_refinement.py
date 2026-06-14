# -*- coding: utf-8 -*-
"""
Phase 4B: Semantic Refinement Unit Tests (10 tests)

Tests for:
1.  iter_instructions traverses basic_blocks[*].instructions
2.  Empty instruction arrays produce zero constraints
3.  Missing basic_blocks does not crash
4.  Malformed instruction (no opcode/mnemonic/raw) is skipped gracefully
5.  Resolver: no constraints → base type returned unchanged
6.  Resolver: CALL_ARG constraint raises confidence above Phase 4A baseline
7.  Resolver: never lowers confidence below base
8.  Resolver: highest-priority constraint wins
9.  End-to-end no-instruction fallback preserves Phase 4A types
10. Deterministic output — two runs produce identical JSON
"""

import json
import os
import tempfile
import unittest

from src.ir.types.constraints import (
    ConstraintKind,
    ConstraintSet,
    ConstraintSource,
    TypeConstraint,
)
from src.ir.types.models import (
    FUNCTION_KIND_USER,
    TYPE_INT32,
    TYPE_POINTER,
    TYPE_UNKNOWN,
    RecoveredFunctionSemantics,
    RecoveredParameter,
    RecoveredSignature,
    RecoveredType,
    RecoveredVariable,
    RefinedFunctionRecord,
    RefinedVariableRecord,
    STORAGE_STACK,
    CATEGORY_LOCAL,
)
from src.ir.types.propagation import iter_instructions, collect_constraints
from src.ir.types.resolver import resolve_constraints
from src.ir.types.refinement_engine import TypeRefinementEngine
from src.ir.types.semantic_emitter import (
    write_semantic_recovery_artifact,
    SCHEMA_VERSION,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_phase4a_record(
    name="test_func",
    entry_point="0x1000",
    variables=None,
    parameters=None,
):
    """Build a minimal RecoveredFunctionSemantics for testing."""
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
    """Wrap function dicts in the canonical type_recovery.json shape."""
    return {
        "schema_version": "4A.0.0",
        "provenance": {"phase": "4A"},
        "data": {
            "functions": [r.to_dict() for r in func_records],
        },
    }


def _make_unified_ir(func_list):
    """Wrap function dicts in the canonical Unified IR shape."""
    return {
        "schema_version": "2.0.0",
        "provenance": {"binary_path": "test.bin"},
        "data": {
            "functions": func_list,
            "call_graph": {"nodes": [], "edges": []},
        },
    }


def _unknown_var(name, offset=-4):
    return RecoveredVariable(
        name=name,
        storage=STORAGE_STACK,
        category=CATEGORY_LOCAL,
        recovered_type=RecoveredType(type_name=TYPE_UNKNOWN, confidence=0.2, source="test"),
        offset_bytes=offset,
        size_bytes=4,
        source="test",
        confidence=0.2,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPhase4BSemanticRefinement(unittest.TestCase):

    # ------------------------------------------------------------------
    # Test 1 — iter_instructions traverses basic_blocks[*].instructions
    # ------------------------------------------------------------------
    def test_iter_instructions_traverses_blocks(self):
        instr1 = {"address": "0x1000", "opcode": "add", "mnemonic": "add",
                  "operands": [], "size_bytes": 4, "raw": "add", "source": "test"}
        instr2 = {"address": "0x1004", "opcode": "sub", "mnemonic": "sub",
                  "operands": [], "size_bytes": 4, "raw": "sub", "source": "test"}
        func_ir = {
            "basic_blocks": [
                {"id": "0x1000", "instructions": [instr1]},
                {"id": "0x1004", "instructions": [instr2]},
            ]
        }
        instrs = list(iter_instructions(func_ir))
        self.assertEqual(len(instrs), 2)
        self.assertEqual(instrs[0]["opcode"], "add")
        self.assertEqual(instrs[1]["opcode"], "sub")

    # ------------------------------------------------------------------
    # Test 2 — Empty instruction arrays produce zero constraints
    # ------------------------------------------------------------------
    def test_empty_instructions_produce_zero_constraints(self):
        func_ir = {
            "basic_blocks": [
                {"id": "0x1000", "instructions": []},
            ]
        }
        record = _make_phase4a_record()
        cset = collect_constraints(func_ir, record)
        self.assertEqual(len(cset), 0)

    # ------------------------------------------------------------------
    # Test 3 — Missing basic_blocks does not crash
    # ------------------------------------------------------------------
    def test_missing_basic_blocks_does_not_crash(self):
        func_ir = {}
        record = _make_phase4a_record()
        cset = collect_constraints(func_ir, record)
        self.assertEqual(len(cset), 0)

    # ------------------------------------------------------------------
    # Test 4 — Malformed instruction (no opcode/mnemonic/raw) is skipped
    # ------------------------------------------------------------------
    def test_malformed_instruction_skipped(self):
        # An instruction with no identifying fields — should produce no constraints
        bad_instr = {"address": "0x1000", "operands": [], "source": "test"}
        func_ir = {"basic_blocks": [{"id": "0x1000", "instructions": [bad_instr]}]}
        record = _make_phase4a_record(variables=[_unknown_var("local_x")])
        cset = collect_constraints(func_ir, record)
        self.assertEqual(len(cset), 0)

    # ------------------------------------------------------------------
    # Test 5 — Resolver: no constraints → base type returned unchanged
    # ------------------------------------------------------------------
    def test_resolver_no_constraints_preserves_type(self):
        base = RecoveredType(type_name=TYPE_UNKNOWN, confidence=0.2, source="test")
        result = resolve_constraints(base, [])
        self.assertIs(result, base)  # same object

    # ------------------------------------------------------------------
    # Test 6 — Resolver: CALL_ARG raises confidence above Phase 4A baseline
    # ------------------------------------------------------------------
    def test_resolver_raises_confidence(self):
        base = RecoveredType(type_name=TYPE_UNKNOWN, confidence=0.2, source="test")
        constraint = TypeConstraint(
            kind=ConstraintKind.CALL_ARG,
            lhs="local_x",
            rhs=TYPE_POINTER,
            source_priority=ConstraintSource.IR_CALL_SITE,  # 80
            evidence_note="passed to printf",
        )
        result = resolve_constraints(base, [constraint])
        self.assertEqual(result.type_name, TYPE_POINTER)
        self.assertGreater(result.confidence, 0.2)
        self.assertLessEqual(result.confidence, 0.95)

    # ------------------------------------------------------------------
    # Test 7 — Resolver: never lowers confidence
    # ------------------------------------------------------------------
    def test_resolver_never_lowers_confidence(self):
        base = RecoveredType(type_name=TYPE_POINTER, confidence=1.0, source="known_db")
        # A weak constraint that would suggest int32
        constraint = TypeConstraint(
            kind=ConstraintKind.SIGN,
            lhs="x",
            rhs=TYPE_INT32,
            source_priority=ConstraintSource.IR_ARITHMETIC,  # 60
        )
        result = resolve_constraints(base, [constraint])
        # Confidence should NOT drop from 1.0
        self.assertGreaterEqual(result.confidence, 1.0)

    # ------------------------------------------------------------------
    # Test 8 — Resolver: highest-priority constraint wins
    # ------------------------------------------------------------------
    def test_resolver_known_signature_wins(self):
        base = RecoveredType(type_name=TYPE_UNKNOWN, confidence=0.2, source="test")
        # Lower-priority arithmetic constraint
        weak = TypeConstraint(
            kind=ConstraintKind.SIGN,
            lhs="x",
            rhs=TYPE_INT32,
            source_priority=ConstraintSource.IR_ARITHMETIC,  # 60
        )
        # Higher-priority call-arg constraint
        strong = TypeConstraint(
            kind=ConstraintKind.CALL_ARG,
            lhs="x",
            rhs=TYPE_POINTER,
            source_priority=ConstraintSource.KNOWN_SIGNATURE,  # 100
        )
        result = resolve_constraints(base, [weak, strong])
        self.assertEqual(result.type_name, TYPE_POINTER)
        # Confidence should reflect priority 100 → 0.95 (capped)
        self.assertAlmostEqual(result.confidence, 0.95, places=2)

    # ------------------------------------------------------------------
    # Test 9 — End-to-end no-instruction fallback preserves Phase 4A types
    # ------------------------------------------------------------------
    def test_end_to_end_no_instruction_fallback(self):
        var = _unknown_var("local_x")
        phase4a = _make_phase4a_record(variables=[var])
        type_recovery = _make_type_recovery_dict([phase4a])

        # Unified IR with empty instruction lists
        ir_func = {
            "name": "test_func",
            "entry_point": "0x1000",
            "basic_blocks": [{"id": "0x1000", "instructions": []}],
        }
        unified_ir = _make_unified_ir([ir_func])

        engine = TypeRefinementEngine()
        results = engine.refine(unified_ir, type_recovery)

        self.assertEqual(len(results), 1)
        r = results[0]
        self.assertEqual(r.total_constraints_applied, 0)
        # Phase 4A type preserved
        self.assertEqual(r.variables[0].refined_type.type_name, TYPE_UNKNOWN)
        self.assertEqual(r.variables[0].constraints_applied, 0)
        # Evidence note mentions no instruction evidence
        evidence_text = " ".join(r.evidence).lower()
        self.assertIn("phase 4a", evidence_text)

    # ------------------------------------------------------------------
    # Test 10 — Deterministic output: two runs produce identical JSON
    # ------------------------------------------------------------------
    def test_deterministic_output(self):
        var1 = _unknown_var("local_a", -4)
        var2 = _unknown_var("local_b", -8)
        phase4a = _make_phase4a_record(variables=[var1, var2])
        type_recovery = _make_type_recovery_dict([phase4a])

        ir_func = {
            "name": "test_func",
            "entry_point": "0x1000",
            "basic_blocks": [{"id": "0x1000", "instructions": []}],
        }
        unified_ir = _make_unified_ir([ir_func])

        engine = TypeRefinementEngine()

        run1 = engine.refine(unified_ir, type_recovery)
        run2 = engine.refine(unified_ir, type_recovery)

        with tempfile.TemporaryDirectory() as td:
            out1 = os.path.join(td, "run1.json")
            out2 = os.path.join(td, "run2.json")
            write_semantic_recovery_artifact(run1, out1)
            write_semantic_recovery_artifact(run2, out2)

            with open(out1) as f1, open(out2) as f2:
                j1 = json.load(f1)
                j2 = json.load(f2)

        self.assertEqual(j1, j2)

    # ------------------------------------------------------------------
    # Bonus: verify semantic_recovery.json schema
    # ------------------------------------------------------------------
    def test_semantic_emitter_schema(self):
        phase4a = _make_phase4a_record()
        type_recovery = _make_type_recovery_dict([phase4a])
        unified_ir = _make_unified_ir([])

        engine = TypeRefinementEngine()
        results = engine.refine(unified_ir, type_recovery)

        with tempfile.TemporaryDirectory() as td:
            out_path = os.path.join(td, "semantic_recovery.json")
            write_semantic_recovery_artifact(results, out_path)
            with open(out_path) as f:
                payload = json.load(f)

        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertEqual(payload["provenance"]["phase"], "4B")
        self.assertIn("functions", payload["data"])

    # ------------------------------------------------------------------
    # Bonus: constraint set deduplication
    # ------------------------------------------------------------------
    def test_constraint_deduplication(self):
        cset = ConstraintSet()
        c1 = TypeConstraint(
            kind=ConstraintKind.SIGN,
            lhs="x",
            rhs="int32",
            source_priority=60,
            evidence_note="first",
        )
        c2 = TypeConstraint(
            kind=ConstraintKind.SIGN,
            lhs="x",
            rhs="int32",
            source_priority=80,
            evidence_note="stronger",
        )
        cset.add(c1)
        cset.add(c2)
        # Should have only one entry, the stronger one
        self.assertEqual(len(cset), 1)
        entries = cset.all_for_lhs("x")
        self.assertEqual(entries[0].source_priority, 80)


if __name__ == "__main__":
    unittest.main()
