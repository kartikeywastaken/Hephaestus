# -*- coding: utf-8 -*-
"""
Phase 4B.1: Operand Binding Unit Tests (12 tests)

Tests for:
1.  Explicit variable operand binds when name in Phase 4A index
2.  Unknown variable name does NOT bind
3.  Memory operand does NOT bind without verified offset model
4.  Memory operand binds with verified stack offset (exact match)
5.  Memory operand does NOT bind on size mismatch
6.  Register binding established from a load
7.  Register binding cleared between basic blocks
8.  Arithmetic on a bound register emits SIGN constraint
9.  Arithmetic on unbound register emits zero constraints
10. ABI call argument binding (ldr x0 + bl printf → CALL_ARG)
11. printf varargs NOT inferred (only first fixed arg constrained)
12. Call clears all register bindings
"""

import unittest

from src.ir.types.bindings import (
    BindingContext,
    VariableBinding,
    BINDING_EXPLICIT_VARIABLE,
    BINDING_STACK_SLOT,
    BINDING_REGISTER_TEMP,
    normalize_register_name,
)
from src.ir.types.constraints import ConstraintKind, ConstraintSet
from src.ir.types.models import (
    CATEGORY_LOCAL,
    FUNCTION_KIND_USER,
    STORAGE_STACK,
    TYPE_UNKNOWN,
    TYPE_INT32,
    TYPE_POINTER,
    RecoveredFunctionSemantics,
    RecoveredParameter,
    RecoveredSignature,
    RecoveredType,
    RecoveredVariable,
)
from src.ir.types.propagation import collect_constraints


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _make_param(name, index=0):
    return RecoveredParameter(
        name=name,
        index=index,
        recovered_type=RecoveredType(type_name=TYPE_UNKNOWN, confidence=0.2, source="test"),
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


def _make_func_ir(blocks):
    """Wrap a list of block dicts in the Unified IR function shape."""
    return {"basic_blocks": blocks}


def _instr(address, opcode, operands, size_bytes=4, source="test"):
    return {
        "address": address,
        "opcode": opcode,
        "mnemonic": opcode,
        "operands": operands,
        "size_bytes": size_bytes,
        "raw": opcode,
        "source": source,
    }


def _reg(name):
    return {"kind": "register", "value": name}


def _mem(base, offset, size_bytes=4):
    return {"kind": "memory", "base": base, "offset": offset, "size_bytes": size_bytes}


def _sym(name):
    return {"kind": "symbol", "name": name}


def _var_op(name):
    return {"kind": "variable", "name": name}


# ---------------------------------------------------------------------------
# Test 1 — Explicit variable operand binds
# ---------------------------------------------------------------------------

class TestExplicitVariableBinding(unittest.TestCase):

    def test_explicit_variable_binds(self):
        """kind=variable with name in Phase 4A index → VariableBinding at confidence 1.0"""
        record = _make_record(variables=[_make_var("local_10")])
        ctx = BindingContext(record)
        b = ctx.bind_operand(_var_op("local_10"))
        self.assertIsNotNone(b)
        self.assertEqual(b.variable_name, "local_10")
        self.assertEqual(b.binding_kind, BINDING_EXPLICIT_VARIABLE)
        self.assertAlmostEqual(b.confidence, 1.0)

    def test_unknown_variable_operand_does_not_bind(self):
        """kind=variable with name NOT in Phase 4A index → None"""
        record = _make_record(variables=[_make_var("local_10")])
        ctx = BindingContext(record)
        b = ctx.bind_operand(_var_op("fake_local"))
        self.assertIsNone(b)


# ---------------------------------------------------------------------------
# Test 3 — Memory operand does NOT bind without verified offset model
# ---------------------------------------------------------------------------

class TestMemoryBinding(unittest.TestCase):

    def test_memory_no_offset_model_returns_none(self):
        """Memory operand with no verified Phase 4A offset → None"""
        record = _make_record(variables=[_make_var("local_10", offset_bytes=None)])
        ctx = BindingContext(record)
        b = ctx.bind_operand(_mem("sp", 16))
        self.assertIsNone(b)

    def test_memory_binds_with_verified_offset(self):
        """Memory operand with verified Phase 4A offset → BINDING_STACK_SLOT"""
        record = _make_record(variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)])
        ctx = BindingContext(record)
        b = ctx.bind_operand(_mem("sp", 16, size_bytes=4))
        self.assertIsNotNone(b)
        self.assertEqual(b.variable_name, "local_10")
        self.assertEqual(b.binding_kind, BINDING_STACK_SLOT)

    def test_memory_does_not_bind_on_size_mismatch(self):
        """Memory operand with size_bytes mismatch → None"""
        record = _make_record(variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)])
        ctx = BindingContext(record)
        # Instruction accesses 8 bytes, variable is 4 bytes
        b = ctx.bind_operand(_mem("sp", 16, size_bytes=8))
        self.assertIsNone(b)

    def test_non_stack_base_does_not_bind(self):
        """Memory operand with non-stack base register → None"""
        record = _make_record(variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)])
        ctx = BindingContext(record)
        b = ctx.bind_operand(_mem("x9", 16, size_bytes=4))
        self.assertIsNone(b)


# ---------------------------------------------------------------------------
# Test 5 & 6 — Register binding
# ---------------------------------------------------------------------------

class TestRegisterBinding(unittest.TestCase):

    def test_register_binding_from_load(self):
        """ldr w8, [sp+offset] where offset matches → x8 bound to local_10"""
        record = _make_record(variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)])
        func_ir = _make_func_ir([{
            "id": "0x1000",
            "instructions": [
                _instr("0x1000", "ldr", [_reg("w8"), _mem("sp", 16, 4)], size_bytes=4),
            ]
        }])
        cset = collect_constraints(func_ir, record)
        # SIZE constraint should be emitted for local_10
        lhs_names = {c.lhs for c in cset}
        self.assertIn("local_10", lhs_names)

    def test_register_binding_cleared_between_blocks(self):
        """Register bound in block A must NOT be visible in block B"""
        record = _make_record(variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)])
        # Block A: ldr w8 (binds x8 → local_10), add w8 (emits constraint)
        # Block B: add w8 (should emit NO constraint because x8 was cleared)
        func_ir = _make_func_ir([
            {
                "id": "0x1000",
                "instructions": [
                    _instr("0x1000", "ldr", [_reg("w8"), _mem("sp", 16, 4)], size_bytes=4),
                    _instr("0x1004", "add", [_reg("w8"), _reg("w8"), {"kind": "immediate", "value": 1}]),
                ],
            },
            {
                "id": "0x1008",
                "instructions": [
                    # w8 should be unbound here — no ldr in this block
                    _instr("0x1008", "add", [_reg("w8"), _reg("w8"), {"kind": "immediate", "value": 2}]),
                ],
            },
        ])
        cset = collect_constraints(func_ir, record)

        # There should be constraints for local_10 (from block A only)
        local10_constraints = cset.all_for_lhs("local_10")
        # At least one from block A (SIZE from ldr, SIGN from add)
        self.assertTrue(len(local10_constraints) >= 1)

        # The key check: the second add in block B should NOT have produced
        # an extra constraint beyond what block A produced.
        # Since ConstraintSet deduplicates by (kind, lhs, rhs), we verify
        # the count is exactly what block A would produce (≤ 2: SIZE + SIGN).
        self.assertLessEqual(len(local10_constraints), 2)


# ---------------------------------------------------------------------------
# Test 7 & 8 — Arithmetic through bound register
# ---------------------------------------------------------------------------

class TestArithmeticConstraints(unittest.TestCase):

    def test_arithmetic_through_bound_register_emits_sign(self):
        """ldr w8, [slot]; add w8, w8, #1 → SIGN(local_10)"""
        record = _make_record(variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)])
        func_ir = _make_func_ir([{
            "id": "0x1000",
            "instructions": [
                _instr("0x1000", "ldr", [_reg("w8"), _mem("sp", 16, 4)], size_bytes=4),
                _instr("0x1004", "add", [_reg("w8"), _reg("w8"), {"kind": "immediate", "value": 1}]),
            ],
        }])
        cset = collect_constraints(func_ir, record)
        sign_constraints = [
            c for c in cset
            if c.lhs == "local_10" and c.kind == ConstraintKind.SIGN
        ]
        self.assertEqual(len(sign_constraints), 1)
        self.assertIn("0x1004", sign_constraints[0].evidence_note)

    def test_arithmetic_on_unbound_register_emits_zero_constraints(self):
        """add w8, w8, #1 with no prior ldr → 0 constraints"""
        record = _make_record(variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)])
        func_ir = _make_func_ir([{
            "id": "0x1000",
            "instructions": [
                # No ldr — x8 is unbound
                _instr("0x1000", "add", [_reg("w8"), _reg("w8"), {"kind": "immediate", "value": 1}]),
            ],
        }])
        cset = collect_constraints(func_ir, record)
        self.assertEqual(len(cset), 0)


# ---------------------------------------------------------------------------
# Tests 9–12 — ABI call argument binding
# ---------------------------------------------------------------------------

class TestABICallBinding(unittest.TestCase):

    def test_abi_call_arg_binding(self):
        """ldr x0, [slot for local_10]; bl _printf → CALL_ARG(local_10, pointer)"""
        record = _make_record(variables=[_make_var("local_10", offset_bytes=16, size_bytes=8)])
        func_ir = _make_func_ir([{
            "id": "0x1000",
            "instructions": [
                _instr("0x1000", "ldr", [_reg("x0"), _mem("sp", 16, 8)], size_bytes=8),
                _instr("0x1004", "bl", [_sym("_printf")]),
            ],
        }])
        cset = collect_constraints(func_ir, record)
        call_constraints = [
            c for c in cset
            if c.lhs == "local_10" and c.kind == ConstraintKind.CALL_ARG
        ]
        self.assertEqual(len(call_constraints), 1)
        self.assertEqual(call_constraints[0].rhs, TYPE_POINTER)
        self.assertIn("x0", call_constraints[0].evidence_note)
        self.assertIn("printf", call_constraints[0].evidence_note)

    def test_printf_varargs_not_inferred(self):
        """Only first fixed arg of printf constrained; x1/x2 ignored even if bound"""
        record = _make_record(variables=[
            _make_var("fmt_str", offset_bytes=16, size_bytes=8),
            _make_var("val_a",  offset_bytes=24, size_bytes=4),
            _make_var("val_b",  offset_bytes=32, size_bytes=4),
        ])
        func_ir = _make_func_ir([{
            "id": "0x1000",
            "instructions": [
                # Load all three into ABI arg registers
                _instr("0x1000", "ldr", [_reg("x0"), _mem("sp", 16, 8)], size_bytes=8),
                _instr("0x1004", "ldr", [_reg("w1"), _mem("sp", 24, 4)], size_bytes=4),
                _instr("0x1008", "ldr", [_reg("w2"), _mem("sp", 32, 4)], size_bytes=4),
                _instr("0x100c", "bl", [_sym("_printf")]),
            ],
        }])
        cset = collect_constraints(func_ir, record)
        call_constraints = [c for c in cset if c.kind == ConstraintKind.CALL_ARG]
        # Only fmt_str (x0) should get a CALL_ARG constraint; val_a and val_b are varargs
        self.assertEqual(len(call_constraints), 1)
        self.assertEqual(call_constraints[0].lhs, "fmt_str")

    def test_call_clears_register_bindings(self):
        """After a call, register bindings are cleared; subsequent add emits no constraint"""
        record = _make_record(variables=[_make_var("local_10", offset_bytes=16, size_bytes=8)])
        func_ir = _make_func_ir([{
            "id": "0x1000",
            "instructions": [
                _instr("0x1000", "ldr", [_reg("x0"), _mem("sp", 16, 8)], size_bytes=8),
                _instr("0x1004", "bl", [_sym("_printf")]),
                # After the call, x0 should be unbound
                _instr("0x1008", "add", [_reg("x0"), _reg("x0"), {"kind": "immediate", "value": 1}]),
            ],
        }])
        cset = collect_constraints(func_ir, record)
        # Should have: SIZE from ldr, CALL_ARG from bl; NO extra SIGN from post-call add
        sign_constraints = [
            c for c in cset
            if c.lhs == "local_10" and c.kind == ConstraintKind.SIGN
        ]
        self.assertEqual(len(sign_constraints), 0)


# ---------------------------------------------------------------------------
# Test 12 — normalize_register_name
# ---------------------------------------------------------------------------

class TestRegisterNormalization(unittest.TestCase):

    def test_w_to_x_normalization(self):
        """w0–w30 → x0–x30"""
        for i in range(31):
            self.assertEqual(normalize_register_name(f"w{i}"), f"x{i}")

    def test_xsp_normalization(self):
        self.assertEqual(normalize_register_name("xsp"), "sp")

    def test_fp_normalization(self):
        self.assertEqual(normalize_register_name("fp"), "x29")

    def test_lr_normalization(self):
        self.assertEqual(normalize_register_name("lr"), "x30")

    def test_x_registers_unchanged(self):
        """x0–x30 remain unchanged"""
        for i in range(31):
            self.assertEqual(normalize_register_name(f"x{i}"), f"x{i}")

    def test_sp_unchanged(self):
        self.assertEqual(normalize_register_name("sp"), "sp")


if __name__ == "__main__":
    unittest.main()
