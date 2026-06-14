# -*- coding: utf-8 -*-
"""
Adversarial Constraint Propagation Unit Tests

Validates Phase 4B.1 type constraint propagation through register moves,
arithmetic clobbering, comparison opcodes, call boundaries, and malformed instructions.
"""

import unittest
from src.ir.types.bindings import BindingContext
from src.ir.types.constraints import ConstraintKind
from src.ir.types.propagation import collect_constraints
from src.ir.types.models import (
    RecoveredFunctionSemantics,
    RecoveredVariable,
    RecoveredSignature,
    RecoveredType,
    RecoveredParameter,
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
    return {"basic_blocks": blocks}


def _instr(address, opcode, operands, size_bytes=4, source="test"):
    return {
        "address": address,
        "opcode": opcode,
        "mnemonic": opcode,
        "operands": operands,
        "size_bytes": size_bytes,
        "raw": f"{opcode} at {address}",
        "source": source,
    }


def _reg(name):
    return {"kind": "register", "value": name}


def _mem(base, offset, size_bytes=4):
    return {"kind": "memory", "base": base, "offset": offset, "size_bytes": size_bytes}


def _sym(name):
    return {"kind": "symbol", "name": name}


def _imm(val):
    return {"kind": "immediate", "value": val}


def _var_op(name):
    return {"kind": "variable", "name": name}


class TestAdversarialConstraints(unittest.TestCase):

    # Test 1 — Bound register arithmetic emits constraint
    def test_bound_register_arithmetic_emits_constraint(self):
        record = _make_record(variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)])
        func_ir = _make_func_ir([{
            "id": "0x1000",
            "instructions": [
                _instr("0x1000", "ldr", [_reg("w8"), _mem("sp", 16, 4)]),
                _instr("0x1004", "add", [_reg("w8"), _reg("w8"), _imm(1)])
            ]
        }])
        cset = collect_constraints(func_ir, record)
        sign_constraints = [c for c in cset if c.lhs == "local_10" and c.kind == ConstraintKind.SIGN]
        self.assertEqual(len(sign_constraints), 1)

    # Test 2 — Unknown register arithmetic emits nothing
    def test_unknown_register_arithmetic_emits_nothing(self):
        record = _make_record(variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)])
        func_ir = _make_func_ir([{
            "id": "0x1000",
            "instructions": [
                _instr("0x1000", "add", [_reg("w8"), _reg("w8"), _imm(1)])
            ]
        }])
        cset = collect_constraints(func_ir, record)
        self.assertEqual(len(cset), 0)

    # Test 3 — Binding dies across basic block boundary
    def test_binding_dies_across_basic_block_boundary(self):
        record = _make_record(variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)])
        func_ir = _make_func_ir([
            {
                "id": "0x1000",
                "instructions": [
                    _instr("0x1000", "ldr", [_reg("w8"), _mem("sp", 16, 4)])
                ]
            },
            {
                "id": "0x1008",
                "instructions": [
                    _instr("0x1008", "add", [_reg("w8"), _reg("w8"), _imm(1)])
                ]
            }
        ])
        cset = collect_constraints(func_ir, record)
        # Only SIZE constraint from ldr in Block 1
        self.assertEqual(len(cset), 1)
        self.assertEqual(list(cset)[0].kind, ConstraintKind.SIZE)

    # Test 4 — Move propagates binding once
    def test_move_propagates_binding_once(self):
        record = _make_record(variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)])
        func_ir = _make_func_ir([{
            "id": "0x1000",
            "instructions": [
                _instr("0x1000", "ldr", [_reg("w8"), _mem("sp", 16, 4)]),
                _instr("0x1004", "mov", [_reg("w9"), _reg("w8")]),
                _instr("0x1008", "add", [_reg("w9"), _reg("w9"), _imm(1)])
            ]
        }])
        cset = collect_constraints(func_ir, record)
        sign_constraints = [c for c in cset if c.lhs == "local_10" and c.kind == ConstraintKind.SIGN]
        self.assertEqual(len(sign_constraints), 1)

    # Test 5 — Move from immediate clobbers destination
    def test_move_from_immediate_clobbers_destination(self):
        record = _make_record(variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)])
        func_ir = _make_func_ir([{
            "id": "0x1000",
            "instructions": [
                _instr("0x1000", "ldr", [_reg("w8"), _mem("sp", 16, 4)]),
                _instr("0x1004", "mov", [_reg("w8"), _imm(0)]),
                _instr("0x1008", "add", [_reg("w8"), _reg("w8"), _imm(1)])
            ]
        }])
        cset = collect_constraints(func_ir, record)
        sign_constraints = [c for c in cset if c.lhs == "local_10" and c.kind == ConstraintKind.SIGN]
        self.assertEqual(len(sign_constraints), 0)

    # Test 6 — Store emits memory constraint if register is bound
    def test_store_emits_memory_constraint_if_register_bound(self):
        record = _make_record(variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)])
        func_ir = _make_func_ir([{
            "id": "0x1000",
            "instructions": [
                _instr("0x1000", "ldr", [_reg("w8"), _mem("sp", 16, 4)]),
                _instr("0x1004", "str", [_reg("w8"), _mem("sp", 16, 4)])
            ]
        }])
        cset = collect_constraints(func_ir, record)
        # Should contain SIZE constraint (ldr & str both might emit it, deduped)
        size_constraints = [c for c in cset if c.lhs == "local_10" and c.kind == ConstraintKind.SIZE]
        self.assertEqual(len(size_constraints), 1)

    # Test 7 — Unknown call clears bindings
    def test_unknown_call_clears_bindings(self):
        record = _make_record(variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)])
        func_ir = _make_func_ir([{
            "id": "0x1000",
            "instructions": [
                _instr("0x1000", "ldr", [_reg("w8"), _mem("sp", 16, 4)]),
                _instr("0x1004", "bl", [_sym("_unknown")]),
                _instr("0x1008", "add", [_reg("w8"), _reg("w8"), _imm(1)])
            ]
        }])
        cset = collect_constraints(func_ir, record)
        sign_constraints = [c for c in cset if c.lhs == "local_10" and c.kind == ConstraintKind.SIGN]
        self.assertEqual(len(sign_constraints), 0)

    # Test 8 — printf only constrains first fixed arg
    def test_printf_only_constrains_first_fixed_arg(self):
        record = _make_record(variables=[
            _make_var("local_format", offset_bytes=16, size_bytes=8),
            _make_var("local_value", offset_bytes=24, size_bytes=4)
        ])
        func_ir = _make_func_ir([{
            "id": "0x1000",
            "instructions": [
                _instr("0x1000", "ldr", [_reg("x0"), _mem("sp", 16, 8)], size_bytes=8),
                _instr("0x1004", "ldr", [_reg("w1"), _mem("sp", 24, 4)], size_bytes=4),
                _instr("0x1008", "bl", [_sym("_printf")])
            ]
        }])
        cset = collect_constraints(func_ir, record)

        # local_format gets CALL_ARG
        format_constraints = [c for c in cset if c.lhs == "local_format" and c.kind == ConstraintKind.CALL_ARG]
        self.assertEqual(len(format_constraints), 1)

        # local_value does NOT get CALL_ARG (ignored as variadic)
        val_constraints = [c for c in cset if c.lhs == "local_value" and c.kind == ConstraintKind.CALL_ARG]
        self.assertEqual(len(val_constraints), 0)

    # Test 9 — Direct variable operand still works
    def test_direct_variable_operand_still_works(self):
        record = _make_record(variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)])
        func_ir = _make_func_ir([{
            "id": "0x1000",
            "instructions": [
                _instr("0x1000", "add", [_var_op("local_10"), _var_op("local_10"), _imm(1)])
            ]
        }])
        cset = collect_constraints(func_ir, record)
        sign_constraints = [c for c in cset if c.lhs == "local_10" and c.kind == ConstraintKind.SIGN]
        self.assertEqual(len(sign_constraints), 1)

    # Test 10 — Malformed instructions interleaved with valid ones
    def test_malformed_instructions_interleaved(self):
        record = _make_record(variables=[_make_var("local_10", offset_bytes=16, size_bytes=4)])
        func_ir = _make_func_ir([{
            "id": "0x1000",
            "instructions": [
                _instr("0x1000", "ldr", [_reg("w8"), _mem("sp", 16, 4)]),
                # Malformed missing opcode & mnemonic
                {"address": "0x1004", "operands": [], "source": "test"},
                _instr("0x1008", "add", [_reg("w8"), _reg("w8"), _imm(1)])
            ]
        }])
        cset = collect_constraints(func_ir, record)
        # Valid path should still propagate constraint
        sign_constraints = [c for c in cset if c.lhs == "local_10" and c.kind == ConstraintKind.SIGN]
        self.assertEqual(len(sign_constraints), 1)


if __name__ == "__main__":
    unittest.main()
