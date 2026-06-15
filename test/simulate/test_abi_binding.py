# -*- coding: utf-8 -*-
"""
Tests for Phase 4B.2: ABI Argument Binding & Parameter-Layout Linking.

Tests the ABI register provenance tracker, pointer-base binding collection,
and parameter-layout evidence linking.
"""

import pytest

from src.ir.types.abi_binding import (
    AbiRegisterState,
    PointerBaseBinding,
    ParameterLayoutEvidence,
    collect_abi_bindings,
    link_parameter_layouts,
)


# ---------------------------------------------------------------------------
# Helpers to build instruction dicts
# ---------------------------------------------------------------------------

def _reg_op(name):
    """Make a register operand dict."""
    return {"kind": "register", "value": name}


def _mem_op(base, offset=None, size_bytes=None):
    """Make a memory operand dict."""
    op = {"kind": "memory", "base": base}
    if offset is not None:
        op["offset"] = offset
    if size_bytes is not None:
        op["size_bytes"] = size_bytes
    return op


def _imm_op(value):
    """Make an immediate operand dict."""
    return {"kind": "immediate", "value": value}


def _instr(opcode, operands, address="0x1000"):
    """Make a minimal instruction dict."""
    return {"opcode": opcode, "operands": operands, "address": address}


# ---------------------------------------------------------------------------
# AbiRegisterState — direct register access
# ---------------------------------------------------------------------------

class TestAbiRegisterState:
    """Tests for the basic register provenance tracker."""

    def test_init_abi_args(self):
        """After init, x0-x7 should have ABI provenance."""
        state = AbiRegisterState("0x1000")
        state.init_abi_args()
        for i in range(8):
            prov = state.get_provenance(f"x{i}")
            assert prov is not None, f"x{i} should have provenance"
            assert prov[0] == i  # argument_index

    def test_x8_has_no_provenance(self):
        """x8 is not an ABI argument register."""
        state = AbiRegisterState("0x1000")
        state.init_abi_args()
        assert state.get_provenance("x8") is None

    def test_mov_propagates_provenance(self):
        """mov x8, x0 should propagate x0's provenance to x8."""
        state = AbiRegisterState("0x1000")
        state.init_abi_args()
        state.process_instruction(
            _instr("mov", [_reg_op("x8"), _reg_op("x0")], "0x1004")
        )
        prov = state.get_provenance("x8")
        assert prov is not None
        assert prov[0] == 0  # argument 0

    def test_mov_chain(self):
        """mov x8, x0; mov x9, x8 → x9 has arg0 provenance."""
        state = AbiRegisterState("0x1000")
        state.init_abi_args()
        state.process_instruction(
            _instr("mov", [_reg_op("x8"), _reg_op("x0")], "0x1004")
        )
        state.process_instruction(
            _instr("mov", [_reg_op("x9"), _reg_op("x8")], "0x1008")
        )
        prov = state.get_provenance("x9")
        assert prov is not None
        assert prov[0] == 0

    def test_w0_normalized_to_x0(self):
        """w0 should be normalized to x0."""
        state = AbiRegisterState("0x1000")
        state.init_abi_args()
        prov = state.get_provenance("w0")
        assert prov is not None
        assert prov[0] == 0


class TestAbiRegisterStateStackSaveRestore:
    """Tests for stack save/restore provenance."""

    def test_stack_save_restore(self):
        """str x0, [sp, #32]; ldr x8, [sp, #32] → x8 has arg0 provenance."""
        state = AbiRegisterState("0x1000")
        state.init_abi_args()
        # Save x0 to stack
        state.process_instruction(
            _instr("str", [_reg_op("x0"), _mem_op("sp", 32)], "0x1004")
        )
        # Clear registers (simulate block boundary)
        state.clear_registers()
        # Re-init ABI args would normally happen, but we don't to test stack
        # Load from stack slot
        state.process_instruction(
            _instr("ldr", [_reg_op("x8"), _mem_op("sp", 32)], "0x1010")
        )
        prov = state.get_provenance("x8")
        assert prov is not None
        assert prov[0] == 0  # argument 0 restored from stack


class TestAbiRegisterStateOverwrite:
    """Tests for provenance invalidation."""

    def test_overwrite_clears_provenance(self):
        """Non-provenance write to register should clear it."""
        state = AbiRegisterState("0x1000")
        state.init_abi_args()
        state.process_instruction(
            _instr("mov", [_reg_op("x8"), _reg_op("x0")], "0x1004")
        )
        # Overwrite x8 with a non-ABI load
        state.process_instruction(
            _instr("ldr", [_reg_op("x8"), _mem_op("x9", 0)], "0x1008")
        )
        assert state.get_provenance("x8") is None

    def test_call_clobbers_caller_saved(self):
        """BL should clear x0-x18 provenance."""
        state = AbiRegisterState("0x1000")
        state.init_abi_args()
        state.process_instruction(
            _instr("mov", [_reg_op("x8"), _reg_op("x0")], "0x1004")
        )
        state.process_instruction(
            _instr("bl", [_reg_op("x20")], "0x1008")
        )
        assert state.get_provenance("x0") is None
        assert state.get_provenance("x8") is None

    def test_clear_registers_at_block_boundary(self):
        """clear_registers should remove all register provenance."""
        state = AbiRegisterState("0x1000")
        state.init_abi_args()
        state.clear_registers()
        assert state.get_provenance("x0") is None


class TestAbiRegisterStateMemoryBase:
    """Tests for memory base provenance detection."""

    def test_direct_x0_base(self):
        """ldr w9, [x0, #16] → binding for x0 at arg0."""
        state = AbiRegisterState("0x1000")
        state.init_abi_args()
        state.process_instruction(
            _instr("ldr", [_reg_op("w9"), _mem_op("x0", 16, 4)], "0x1004")
        )
        assert len(state.bindings) == 1
        b = state.bindings[0]
        assert b.argument_index == 0
        assert b.base_register == "x0"

    def test_mov_then_deref(self):
        """mov x8, x0; ldr w9, [x8, #16] → binding for x8 as arg0."""
        state = AbiRegisterState("0x1000")
        state.init_abi_args()
        state.process_instruction(
            _instr("mov", [_reg_op("x8"), _reg_op("x0")], "0x1004")
        )
        state.process_instruction(
            _instr("ldr", [_reg_op("w9"), _mem_op("x8", 16, 4)], "0x1008")
        )
        assert len(state.bindings) == 1
        assert state.bindings[0].argument_index == 0
        assert state.bindings[0].binding_kind == "mov_propagated"

    def test_sp_base_ignored(self):
        """Memory access via sp should NOT create a binding."""
        state = AbiRegisterState("0x1000")
        state.init_abi_args()
        state.process_instruction(
            _instr("ldr", [_reg_op("x8"), _mem_op("sp", 0)], "0x1004")
        )
        assert len(state.bindings) == 0

    def test_multi_argument_tracking(self):
        """x0 and x1 should both be tracked independently."""
        state = AbiRegisterState("0x1000")
        state.init_abi_args()
        state.process_instruction(
            _instr("ldr", [_reg_op("w9"), _mem_op("x0", 0, 4)], "0x1004")
        )
        state.process_instruction(
            _instr("ldr", [_reg_op("w10"), _mem_op("x1", 8, 4)], "0x1008")
        )
        assert len(state.bindings) == 2
        args = {b.argument_index for b in state.bindings}
        assert args == {0, 1}


# ---------------------------------------------------------------------------
# collect_abi_bindings
# ---------------------------------------------------------------------------

class TestCollectAbiBindings:
    """Tests for whole-IR ABI binding collection."""

    def test_arm64_collects(self):
        """arm64 functions should produce bindings."""
        ir = {
            "metadata": {"architecture": "arm64"},
            "data": {
                "functions": [{
                    "name": "test_func",
                    "entry_point": "0x1000",
                    "basic_blocks": [{
                        "id": "0x1000",
                        "instructions": [
                            _instr("ldr", [_reg_op("w9"), _mem_op("x0", 0, 4)], "0x1004"),
                        ],
                    }],
                }],
            },
        }
        result = collect_abi_bindings(ir)
        assert "0x1000" in result
        assert len(result["0x1000"]) == 1

    def test_non_arm64_skipped(self):
        """Non-arm64 architectures should produce no bindings."""
        ir = {
            "metadata": {"architecture": "x86_64"},
            "data": {
                "functions": [{
                    "name": "test_func",
                    "entry_point": "0x1000",
                    "basic_blocks": [{
                        "id": "0x1000",
                        "instructions": [
                            _instr("ldr", [_reg_op("w9"), _mem_op("x0", 0, 4)], "0x1004"),
                        ],
                    }],
                }],
            },
        }
        result = collect_abi_bindings(ir)
        assert result == {}

    def test_empty_ir(self):
        """Empty IR should produce no bindings."""
        assert collect_abi_bindings({}) == {}
        assert collect_abi_bindings(None) == {}

    def test_no_crash_on_malformed_instruction(self):
        """Should handle malformed instructions gracefully."""
        ir = {
            "metadata": {"architecture": "arm64"},
            "data": {
                "functions": [{
                    "name": "func",
                    "entry_point": "0x2000",
                    "basic_blocks": [{
                        "id": "0x2000",
                        "instructions": [
                            {"opcode": "???", "operands": []},
                            {"opcode": None},
                            {},
                            "not_a_dict",
                        ],
                    }],
                }],
            },
        }
        result = collect_abi_bindings(ir)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# link_parameter_layouts
# ---------------------------------------------------------------------------

class TestLinkParameterLayouts:
    """Tests for parameter-layout evidence linking."""

    def _make_bindings(self):
        """Create sample ABI bindings for testing."""
        return {
            "0x1000": [
                PointerBaseBinding(
                    function_entry="0x1000",
                    base_register="x8",
                    argument_index=0,
                    stack_slot=None,
                    source_instrs=("0x1004",),
                    binding_kind="mov_propagated",
                    evidence_notes=("mov x8, x0",),
                ),
            ],
        }

    def _make_layout_recovery(self, function_entry, base_id):
        """Create sample layout_recovery.json with one candidate."""
        return {
            "data": {
                "layout_candidates": [{
                    "function_entry": function_entry,
                    "function_name": "test_func",
                    "base_id": base_id,
                    "layout_kind": "record_like",
                    "observed_offsets": [0, 4, 8],
                    "observed_sizes": [4],
                    "source_instrs": ["0x1010"],
                }],
            },
        }

    def test_matching_entry_and_base(self):
        """Should link when both function_entry and base_id match."""
        bindings = self._make_bindings()
        layout = self._make_layout_recovery("0x1000", "x8")
        result = link_parameter_layouts(bindings, layout)
        assert "0x1000" in result
        assert len(result["0x1000"]) == 1
        ple = result["0x1000"][0]
        assert ple.parameter_index == 0
        assert ple.layout_kind == "record_like"

    def test_mismatched_entry(self):
        """Should NOT link when function_entry doesn't match."""
        bindings = self._make_bindings()
        layout = self._make_layout_recovery("0x2000", "x8")
        result = link_parameter_layouts(bindings, layout)
        assert result == {}

    def test_mismatched_base(self):
        """Should NOT link when base_id doesn't match."""
        bindings = self._make_bindings()
        layout = self._make_layout_recovery("0x1000", "x9")
        result = link_parameter_layouts(bindings, layout)
        assert result == {}

    def test_empty_bindings(self):
        """Empty bindings should produce no evidence."""
        layout = self._make_layout_recovery("0x1000", "x8")
        assert link_parameter_layouts({}, layout) == {}

    def test_no_layout_recovery(self):
        """None layout should produce no evidence."""
        bindings = self._make_bindings()
        assert link_parameter_layouts(bindings, None) == {}

    def test_evidence_serialization(self):
        """ParameterLayoutEvidence should serialize to dict cleanly."""
        bindings = self._make_bindings()
        layout = self._make_layout_recovery("0x1000", "x8")
        result = link_parameter_layouts(bindings, layout)
        ple = result["0x1000"][0]
        d = ple.to_dict()
        assert d["function_entry"] == "0x1000"
        assert d["parameter_index"] == 0
        assert isinstance(d["observed_offsets"], list)
        assert isinstance(d["evidence_notes"], list)

    def test_no_fabricated_evidence(self):
        """With no matching bindings, zero evidence should be produced."""
        bindings = {
            "0x3000": [
                PointerBaseBinding(
                    function_entry="0x3000",
                    base_register="x19",
                    argument_index=0,
                    stack_slot=None,
                    source_instrs=(),
                    binding_kind="direct_abi_reg",
                    evidence_notes=(),
                ),
            ],
        }
        layout = self._make_layout_recovery("0x1000", "x8")
        result = link_parameter_layouts(bindings, layout)
        assert result == {}
