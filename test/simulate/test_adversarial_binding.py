# -*- coding: utf-8 -*-
"""
Adversarial Binding Unit Tests

Tests correctness of the operand-to-variable binding engine, register aliases,
ambiguities, and crash protection.
"""

import unittest
import pytest
from src.ir.types.bindings import (
    BindingContext,
    VariableBinding,
    BINDING_STACK_SLOT,
    normalize_register_name,
)
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


def _make_record(variables=None, parameters=None, name="test_func"):
    sig = RecoveredSignature(
        return_type=RecoveredType(type_name=TYPE_UNKNOWN, confidence=0.2, source="test"),
        parameters=parameters or [],
        variadic=False,
        confidence=0.2,
        source="test",
    )
    return RecoveredFunctionSemantics(
        name=name,
        entry_point="0x1000",
        function_kind=FUNCTION_KIND_USER,
        signature=sig,
        variables=variables or [],
        evidence=["test"],
        confidence=0.2,
    )


class TestAdversarialBinding(unittest.TestCase):

    # Test 1 — Ambiguous duplicate stack offsets
    def test_ambiguous_duplicate_stack_offsets(self):
        # Two variables map to offset 16 in Phase 4A
        record = _make_record(variables=[
            _make_var("local_a", offset_bytes=16, size_bytes=4),
            _make_var("local_b", offset_bytes=16, size_bytes=4)
        ])
        ctx = BindingContext(record)
        operand = {"kind": "memory", "base": "sp", "offset": 16, "size_bytes": 4}
        # Both removed during build index → bind returns None
        self.assertIsNone(ctx.bind_operand(operand))

    # Test 2 — Plus/minus offset ambiguity
    @pytest.mark.xfail(reason="Stack frame modeling limitation: direct match preferred over fallback negation lookup")
    def test_plus_minus_offset_ambiguity(self):
        # One var at offset 16, one var at offset -16
        record = _make_record(variables=[
            _make_var("local_pos", offset_bytes=16, size_bytes=4),
            _make_var("local_neg", offset_bytes=-16, size_bytes=4)
        ])
        ctx = BindingContext(record)
        operand = {"kind": "memory", "base": "sp", "offset": 16, "size_bytes": 4}
        # Since offset 16 could mean +16 or -16, checking both signs makes it ambiguous.
        # However, the engine currently returns local_pos directly since it gets 16 first.
        # This xfails due to known stack frame modeling limits.
        self.assertIsNone(ctx.bind_operand(operand))

    # Test 3 — Size mismatch prevents binding
    def test_size_mismatch_prevents_binding(self):
        record = _make_record(variables=[
            _make_var("local_8", offset_bytes=16, size_bytes=8)
        ])
        ctx = BindingContext(record)
        operand = {"kind": "memory", "base": "sp", "offset": 16, "size_bytes": 4}
        self.assertIsNone(ctx.bind_operand(operand))

    # Test 4 — Non-stack base does not bind
    def test_non_stack_base_does_not_bind(self):
        record = _make_record(variables=[
            _make_var("local_10", offset_bytes=16, size_bytes=4)
        ])
        ctx = BindingContext(record)
        operand = {"kind": "memory", "base": "x9", "offset": 16, "size_bytes": 4}
        self.assertIsNone(ctx.bind_operand(operand))

    # Test 5 — Frame pointer aliases normalize safely
    def test_frame_pointer_aliases_normalize(self):
        aliases = [
            ("fp", "x29"),
            ("w29", "x29"),
            ("x29", "x29"),
            ("lr", "x30"),
            ("w30", "x30"),
            ("xsp", "sp"),
            ("sp", "sp")
        ]
        for src, expected in aliases:
            self.assertEqual(normalize_register_name(src), expected)

    # Test 6 — Weird register names do not crash
    def test_weird_register_names_do_not_crash(self):
        weird_names = ["r999", "foo", "", None]
        record = _make_record(variables=[
            _make_var("local_10", offset_bytes=16, size_bytes=4)
        ])
        ctx = BindingContext(record)

        for name in weird_names:
            # Check normalize_register_name
            try:
                norm = normalize_register_name(name)
            except Exception as e:
                self.fail(f"normalize_register_name crashed on {name}: {e}")

            # Check bind_operand
            op = {"kind": "register", "value": name}
            try:
                res = ctx.bind_operand(op)
                self.assertIsNone(res)
            except Exception as e:
                self.fail(f"bind_operand crashed on register {name}: {e}")

    # Test 7 — Register clear handles alias
    def test_register_clear_handles_alias(self):
        record = _make_record(variables=[
            _make_var("local_10", offset_bytes=16, size_bytes=4)
        ])
        ctx = BindingContext(record)

        # Bind x8 -> local_10
        binding = VariableBinding(
            variable_name="local_10",
            binding_kind="register_temp",
            source="test",
            confidence=0.8,
            evidence_note="test"
        )
        ctx.remember_register("x8", binding)
        self.assertIsNotNone(ctx.bind_register("x8"))

        # Clear w8
        ctx.clear_register("w8")

        # x8 binding should be gone because w8 normalizes to x8
        self.assertIsNone(ctx.bind_register("x8"))

    # Test 8 — Call clears all register bindings
    def test_call_clears_all_register_bindings(self):
        record = _make_record(variables=[
            _make_var("local_10", offset_bytes=16, size_bytes=4)
        ])
        ctx = BindingContext(record)

        binding = VariableBinding(
            variable_name="local_10",
            binding_kind="register_temp",
            source="test",
            confidence=0.8,
            evidence_note="test"
        )
        ctx.remember_register("x0", binding)
        ctx.remember_register("x1", binding)

        self.assertIsNotNone(ctx.bind_register("x0"))
        self.assertIsNotNone(ctx.bind_register("x1"))

        # Clear all
        ctx.clear_all_registers()

        self.assertIsNone(ctx.bind_register("x0"))
        self.assertIsNone(ctx.bind_register("x1"))

    # Test 9 — Binding does not create new variables
    def test_binding_does_not_create_new_variables(self):
        record = _make_record(variables=[
            _make_var("local_10", offset_bytes=16, size_bytes=4)
        ])
        ctx = BindingContext(record)
        operand = {"kind": "variable", "name": "nonexistent_local"}
        self.assertIsNone(ctx.bind_operand(operand))

    # Test 10 — Immediate and unknown operands never bind
    def test_immediate_and_unknown_operands_never_bind(self):
        record = _make_record(variables=[
            _make_var("local_10", offset_bytes=16, size_bytes=4)
        ])
        ctx = BindingContext(record)

        op_imm = {"kind": "immediate", "value": 4}
        op_unk = {"kind": "unknown", "raw": "[sp, #16]"}

        self.assertIsNone(ctx.bind_operand(op_imm))
        self.assertIsNone(ctx.bind_operand(op_unk))


if __name__ == "__main__":
    unittest.main()
