# -*- coding: utf-8 -*-
"""
Tests for Phase 5.2 Instruction Lowering and Architecture Dispatching.
"""

from __future__ import annotations

import json
import os
import tempfile
import pytest

from src.ir.source.models import (
    ReconstructedFunction,
    SourceReconstructionArtifact,
    SCHEMA_VERSION,
)
from src.ir.source.lowering import lower_function_instructions
from src.ir.source.reconstructor import build_source_reconstruction
from src.ir.source.c_emitter import emit_recovered_c


# ---------------------------------------------------------------------------
# Helpers to build test instructions and operands
# ---------------------------------------------------------------------------

def _make_ir(functions=None, arch="arm64"):
    """Build a minimal unified_ir.json dict with custom architecture."""
    return {
        "schema_version": "2.0.0",
        "provenance": {"binary_path": "test.bin", "architecture": arch},
        "data": {"functions": functions or []},
    }


def _make_ir_func(name="test_func", entry_point="0x1000", basic_blocks=None):
    return {
        "name": name,
        "entry_point": entry_point,
        "basic_blocks": basic_blocks or [],
    }


def _make_bb(bb_id="0x1000", instructions=None):
    return {
        "id": bb_id,
        "instructions": instructions or [],
    }


def _make_ins(mnemonic, operands, raw=None, address="0x1000"):
    return {
        "address": address,
        "mnemonic": mnemonic,
        "operands": operands,
        "raw": raw or f"{mnemonic} ...",
    }


def _reg(val):
    return {"kind": "register", "value": val}


def _imm(val):
    return {"kind": "immediate", "value": val}


def _mem(base, offset=0, size_bytes=8):
    return {"kind": "memory", "base": base, "offset": offset, "size_bytes": size_bytes}


def _make_semantics(functions=None):
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
    abi_argument_bindings=None,
):
    return {
        "name": name,
        "entry_point": entry_point,
        "abi_argument_bindings": abi_argument_bindings or [],
    }


# ---------------------------------------------------------------------------
# Test Cases 1 - 12 (Instruction Lowering Rules)
# ---------------------------------------------------------------------------

class TestInstructionLoweringRules:
    
    def test_1_mov_register(self):
        # mov x8, x0 with ABI binding arg0
        ins = _make_ins("mov", [_reg("x8"), _reg("x0")], raw="mov x8, x0")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        sem_fn = _make_sem_func(abi_argument_bindings=[
            {"argument_index": 0, "register": "x0"}
        ])
        
        stmts, summary = lower_function_instructions(ir_fn, sem_fn, unified_ir=_make_ir(arch="arm64"))
        
        assert len(stmts) == 1
        assert "tmp_x8 = arg0;" in stmts[0].text
        assert stmts[0].kind == "assign"
        assert stmts[0].lowered is True

    def test_2_mov_immediate(self):
        ins = _make_ins("mov", [_reg("w9"), _imm(42)], raw="mov w9, #42")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        
        stmts, _ = lower_function_instructions(ir_fn, unified_ir=_make_ir(arch="arm64"))
        
        assert len(stmts) == 1
        assert "tmp_w9 = 42;" in stmts[0].text

    def test_3_add_immediate(self):
        # add x8, x0, #16
        ins = _make_ins("add", [_reg("x8"), _reg("x0"), _imm(16)], raw="add x8, x0, #16")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        sem_fn = _make_sem_func(abi_argument_bindings=[
            {"argument_index": 0, "register": "x0"}
        ])
        
        stmts, _ = lower_function_instructions(ir_fn, sem_fn, unified_ir=_make_ir(arch="arm64"))
        
        assert len(stmts) == 1
        assert "tmp_x8 = arg0 + 16;" in stmts[0].text
        assert stmts[0].kind == "binary_op"

    def test_4_ldr_parameter_derived_base(self):
        # ldr w9, [x8, #0]
        ins = _make_ins("ldr", [_reg("w9"), _mem("x8", 0, 4)], raw="ldr w9, [x8]")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        
        stmts, _ = lower_function_instructions(ir_fn, unified_ir=_make_ir(arch="arm64"))
        
        assert len(stmts) == 1
        assert "tmp_w9 = *(u32 *)(tmp_x8);" in stmts[0].text
        assert "->" not in stmts[0].text

    def test_5_str_parameter_derived_base(self):
        # str w9, [x8, #4]
        ins = _make_ins("str", [_reg("w9"), _mem("x8", 4, 4)], raw="str w9, [x8, #4]")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        
        stmts, _ = lower_function_instructions(ir_fn, unified_ir=_make_ir(arch="arm64"))
        
        assert len(stmts) == 1
        assert "*(u32 *)(tmp_x8 + 4) = tmp_w9;" in stmts[0].text
        assert "->" not in stmts[0].text

    def test_6_stack_store(self):
        # str x0, [sp, #24] with ABI binding arg0
        ins = _make_ins("str", [_reg("x0"), _mem("sp", 24, 8)], raw="str x0, [sp, #24]")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        sem_fn = _make_sem_func(abi_argument_bindings=[
            {"argument_index": 0, "register": "x0"}
        ])
        
        stmts, _ = lower_function_instructions(ir_fn, sem_fn, unified_ir=_make_ir(arch="arm64"))
        
        assert len(stmts) == 1
        assert "stack_24 = arg0;" in stmts[0].text
        assert stmts[0].kind == "store"

    def test_7_stack_restore(self):
        # ldr x8, [sp, #24]
        ins = _make_ins("ldr", [_reg("x8"), _mem("sp", 24, 8)], raw="ldr x8, [sp, #24]")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        
        stmts, _ = lower_function_instructions(ir_fn, unified_ir=_make_ir(arch="arm64"))
        
        assert len(stmts) == 1
        assert "tmp_x8 = stack_24;" in stmts[0].text
        assert stmts[0].kind == "load"

    def test_8_cmp_comment(self):
        # cmp w9, #0
        ins = _make_ins("cmp", [_reg("w9"), _imm(0)], raw="cmp w9, #0")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        
        stmts, _ = lower_function_instructions(ir_fn, unified_ir=_make_ir(arch="arm64"))
        
        assert len(stmts) == 1
        assert stmts[0].kind == "compare"
        assert "compare" in stmts[0].text or "cmp" in stmts[0].text

    def test_9_bl_call_placeholder(self):
        # bl 0x100002000
        ins = _make_ins("bl", [{"kind": "symbol", "name": "0x100002000"}], raw="bl 0x100002000")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        
        stmts, _ = lower_function_instructions(ir_fn, unified_ir=_make_ir(arch="arm64"))
        
        assert len(stmts) == 1
        assert "call_0x100002000" in stmts[0].text
        assert stmts[0].kind == "call"

    def test_10_blr_indirect_call_comment(self):
        # blr x16
        ins = _make_ins("blr", [_reg("x16")], raw="blr x16")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        
        stmts, _ = lower_function_instructions(ir_fn, unified_ir=_make_ir(arch="arm64"))
        
        assert len(stmts) == 1
        assert "indirect call" in stmts[0].text or "blr" in stmts[0].text
        assert stmts[0].kind == "comment"

    def test_11_movk_unsupported_comment(self):
        # movk w9, #0xa, LSL #16
        ins = _make_ins("movk", [_reg("w9"), _imm(10)], raw="movk w9, #0xa, LSL #16")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        
        stmts, _ = lower_function_instructions(ir_fn, unified_ir=_make_ir(arch="arm64"))
        
        assert len(stmts) == 1
        assert "unsupported" in stmts[0].text or "partial" in stmts[0].text
        assert stmts[0].lowered is False

    def test_12_stp_pair_store(self):
        # stp x29, x30, [sp, #16]
        ins = _make_ins("stp", [_reg("x29"), _reg("x30"), _mem("sp", 16, 8)], raw="stp x29, x30, [sp, #16]")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        
        stmts, _ = lower_function_instructions(ir_fn, unified_ir=_make_ir(arch="arm64"))
        
        assert len(stmts) == 2
        assert "stack_16 = tmp_x29;" in stmts[0].text
        assert "stack_24 = tmp_x30;" in stmts[1].text


# ---------------------------------------------------------------------------
# Test Cases 13 - 16 (Integration, Verification and Determinism)
# ---------------------------------------------------------------------------

class TestEmitterAndSummaryIntegration:

    def _emit_to_string(self, artifact):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
            path = f.name
        try:
            emit_recovered_c(artifact, path)
            with open(path, "r") as f:
                return f.read()
        finally:
            os.unlink(path)

    def test_13_recovered_c_includes_lowered_statements_inside_block(self):
        ir = _make_ir([
            _make_ir_func("foo", "0x1000", [
                _make_bb("0x1000", [
                    _make_ins("mov", [_reg("x8"), _reg("x0")], raw="mov x8, x0")
                ])
            ])
        ])
        regions = [{"function_name": "foo", "structured_body": {"type": "block", "id": "0x1000"}}]
        sem = _make_semantics([
            _make_sem_func("foo", "0x1000", abi_argument_bindings=[
                {"argument_index": 0, "register": "x0"}
            ])
        ])

        artifact = build_source_reconstruction(ir, regions, sem)
        output = self._emit_to_string(artifact)
        
        # Check basic block comment
        assert "block 0x1000" in output
        # Check statement is printed in block body
        assert "tmp_x8 = arg0;" in output

    def test_14_no_fake_fields(self):
        ir = _make_ir([
            _make_ir_func("foo", "0x1000", [
                _make_bb("0x1000", [
                    _make_ins("ldr", [_reg("w9"), _mem("x8", 4, 4)], raw="ldr w9, [x8, #4]")
                ])
            ])
        ])
        regions = []
        sem = _make_semantics([])

        artifact = build_source_reconstruction(ir, regions, sem)
        output = self._emit_to_string(artifact)

        # Split into lines
        for line in output.split("\n"):
            stripped = line.strip()
            # Ignore comments
            if stripped.startswith("/*") or stripped.startswith("*"):
                continue
            assert "->" not in stripped
            assert ".id" not in stripped
            assert ".score" not in stripped

    def test_15_lowering_summary(self):
        # 4 supported + 1 unsupported
        instrs = [
            _make_ins("mov", [_reg("x8"), _reg("x0")]),
            _make_ins("mov", [_reg("x9"), _reg("x1")]),
            _make_ins("add", [_reg("x8"), _reg("x8"), _imm(1)]),
            _make_ins("movk", [_reg("x9"), _imm(10)]), # unsupported
            _make_ins("ret", [])
        ]
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=instrs)])
        _, summary = lower_function_instructions(ir_fn, unified_ir=_make_ir(arch="arm64"))
        
        assert summary["instructions_total"] == 5
        assert summary["instructions_lowered"] == 4
        assert summary["instructions_commented"] == 1
        assert summary["coverage_percent"] == 80.0

    def test_16_deterministic_output(self):
        ins = _make_ins("mov", [_reg("x8"), _reg("x0")], raw="mov x8, x0")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        sem_fn = _make_sem_func(abi_argument_bindings=[
            {"argument_index": 0, "register": "x0"}
        ])

        stmts1, sum1 = lower_function_instructions(ir_fn, sem_fn, unified_ir=_make_ir(arch="arm64"))
        stmts2, sum2 = lower_function_instructions(ir_fn, sem_fn, unified_ir=_make_ir(arch="arm64"))

        assert sum1 == sum2
        assert [s.to_dict() for s in stmts1] == [s.to_dict() for s in stmts2]


# ---------------------------------------------------------------------------
# Test Cases 17 - 20 (Architecture Dispatch Requirements)
# ---------------------------------------------------------------------------

class TestArchitectureDispatch:

    def test_17_arm64_dispatch_lowers_supported_instructions(self):
        ins = _make_ins("mov", [_reg("x8"), _reg("x0")], raw="mov x8, x0")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        
        # Test mapping for multiple case variations of arm64 / aarch64
        for arch in ["arm64", "aarch64", "AARCH64:LE"]:
            stmts, summary = lower_function_instructions(ir_fn, unified_ir=_make_ir(arch=arch))
            assert summary["instructions_lowered"] == 1
            assert summary["instructions_commented"] == 0
            assert summary["coverage_percent"] == 100.0
            assert "tmp_x8" in stmts[0].text

    def test_18_x86_64_dispatch_emits_unsupported_comments_only(self):
        # x86_64 uses UnsupportedLowerer
        ins = _make_ins("mov", [_reg("rax"), _reg("rdi")], raw="mov rax, rdi")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        
        for arch in ["x86_64", "amd64", "x64", "x86", "i386", "i686"]:
            stmts, summary = lower_function_instructions(ir_fn, unified_ir=_make_ir(arch=arch))
            assert summary["instructions_lowered"] == 0
            assert summary["instructions_commented"] == 1
            assert summary["coverage_percent"] == 0.0
            assert stmts[0].lowered is False
            assert "unsupported instruction for architecture" in stmts[0].text
            assert arch in stmts[0].text

    def test_19_unknown_architecture_does_not_crash(self):
        # unknown arch doesn't crash, uses unsupported
        ins = _make_ins("mov", [_reg("r1"), _reg("r2")], raw="mov r1, r2")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        
        # Test missing / None / unknown / custom arch
        for arch in [None, "unknown", "mips", "riscv"]:
            ir = _make_ir(arch=arch)
            if arch is None:
                del ir["provenance"]["architecture"]
            
            stmts, summary = lower_function_instructions(ir_fn, unified_ir=ir)
            assert summary["instructions_lowered"] == 0
            assert summary["instructions_commented"] == 1
            assert stmts[0].lowered is False
            assert "unsupported instruction for architecture" in stmts[0].text

    def test_20_unsupported_output_contains_no_invented_x86_lowering(self):
        ins = _make_ins("mov", [_reg("rax"), _reg("rdi")], raw="mov rax, rdi")
        ir = _make_ir([_make_ir_func("foo", "0x1000", [_make_bb("0x1000", [ins])])], arch="x86_64")
        regions = []
        sem = _make_semantics([])

        artifact = build_source_reconstruction(ir, regions, sem)
        output = emit_recovered_c(artifact, tempfile.mktemp())
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
            path = f.name
        try:
            emit_recovered_c(artifact, path)
            with open(path, "r") as f:
                output = f.read()
            # Verify no pseudo-C assignment is invented
            for line in output.split("\n"):
                stripped = line.strip()
                if stripped.startswith("/*") or stripped.startswith("*") or not stripped:
                    continue
                # Make sure there is no code like tmp_rax = ... or rax = ...
                assert "rax" not in stripped
                assert "rdi" not in stripped
        finally:
            os.unlink(path)

    def test_21_indexed_memory_lowering(self):
        # str w8,[x9, x10, LSL #0x2]
        op_reg = _reg("w8")
        op_mem = {"kind": "unknown", "raw": "[x9, x10, LSL #0x2]"}
        ins_str = _make_ins("str", [op_reg, op_mem], raw="str w8,[x9, x10, LSL #0x2]")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins_str])])
        stmts, _ = lower_function_instructions(ir_fn, unified_ir=_make_ir(arch="arm64"))
        assert len(stmts) == 1
        assert stmts[0].lowered is True
        assert "*(u32 *)(tmp_x9 + (tmp_x10 << 2)) = tmp_w8;" in stmts[0].text
        
        # ldr w8,[x9, x10, LSL #0x2]
        ins_ldr = _make_ins("ldr", [op_reg, op_mem], raw="ldr w8,[x9, x10, LSL #0x2]")
        ir_fn_ldr = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins_ldr])])
        stmts_ldr, _ = lower_function_instructions(ir_fn_ldr, unified_ir=_make_ir(arch="arm64"))
        assert len(stmts_ldr) == 1
        assert stmts_ldr[0].lowered is True
        assert "tmp_w8 = *(u32 *)(tmp_x9 + (tmp_x10 << 2));" in stmts_ldr[0].text

    def test_22_malformed_indexed_memory_fallback(self):
        # malformed bracket memory operand
        op_mem = {"kind": "unknown", "raw": "[x9, x10, LSL #]"}
        ins_str = _make_ins("str", [_reg("w8"), op_mem], raw="str w8,[x9, x10, LSL #]")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins_str])])
        stmts, summary = lower_function_instructions(ir_fn, unified_ir=_make_ir(arch="arm64"))
        assert len(stmts) == 1
        assert stmts[0].lowered is False
        assert "unsupported indexed memory store" in stmts[0].text
        assert "str w8,[x9, x10, LSL #]" in stmts[0].text
        assert "[x9, x10, LSL #] =" not in stmts[0].text

    def test_23_ldrsw_ldursw_sign_extension(self):
        # Non-stack: ldrsw x10,[x8, #0x10]
        ins_ldrsw = _make_ins("ldrsw", [_reg("x10"), _mem("x8", 16, 4)], raw="ldrsw x10,[x8, #0x10]")
        ir_fn_ldrsw = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins_ldrsw])])
        stmts_ldrsw, _ = lower_function_instructions(ir_fn_ldrsw, unified_ir=_make_ir(arch="arm64"))
        assert len(stmts_ldrsw) == 1
        assert stmts_ldrsw[0].lowered is True
        assert "tmp_x10 = (i64)*(i32 *)(tmp_x8 + 16);" in stmts_ldrsw[0].text

        # Stack: ldursw x10,[x29, #-0x30]
        ins_ldursw = _make_ins("ldursw", [_reg("x10"), _mem("x29", -48, 4)], raw="ldursw x10,[x29, #-0x30]")
        ir_fn_ldursw = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins_ldursw])])
        stmts_ldursw, _ = lower_function_instructions(ir_fn_ldursw, unified_ir=_make_ir(arch="arm64"))
        assert len(stmts_ldursw) == 1
        assert stmts_ldursw[0].lowered is True
        assert "tmp_x10 = (i64)(i32)stack_m48;" in stmts_ldursw[0].text

    def test_24_no_lowered_statement_starts_with_raw_bracket(self):
        op_mem_bad = {"kind": "unknown", "raw": "[x9, x10, LSL #0x2]"}
        ins_str = _make_ins("str", [_reg("w8"), op_mem_bad], raw="str w8,[x9, x10, LSL #0x2]")
        ir = _make_ir([
            _make_ir_func("foo", "0x1000", [
                _make_bb("0x1000", [ins_str])
            ])
        ])
        regions = [{"function_name": "foo", "structured_body": {"type": "block", "id": "0x1000"}}]
        sem = _make_semantics([])

        artifact = build_source_reconstruction(ir, regions, sem)
        obj = artifact.to_dict()
        for fn in obj.get("data", {}).get("functions", []):
            for stmt in fn.get("lowered_statements", []):
                text = stmt.get("text", "")
                expr = text.split("/*", 1)[0].strip()
                assert not expr.startswith("[")
            for block_stmts in fn.get("lowered_blocks", {}).values():
                for stmt in block_stmts:
                    text = stmt.get("text", "")
                    expr = text.split("/*", 1)[0].strip()
                    assert not expr.startswith("[")

    def test_25_recovered_c_raw_bracket_safety(self):
        ins1 = _make_ins("str", [_reg("w8"), {"kind": "unknown", "raw": "[x9, x10, LSL #0x2]"}], raw="str w8,[x9, x10, LSL #0x2]")
        ins2 = _make_ins("str", [_reg("w8"), {"kind": "unknown", "raw": "[x9, x10, LSL #]"}], raw="str w8,[x9, x10, LSL #]")
        ir = _make_ir([
            _make_ir_func("foo", "0x1000", [
                _make_bb("0x1000", [ins1, ins2])
            ])
        ])
        regions = [{"function_name": "foo", "structured_body": {"type": "block", "id": "0x1000"}}]
        sem = _make_semantics([])

        artifact = build_source_reconstruction(ir, regions, sem)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
            path = f.name
        try:
            emit_recovered_c(artifact, path)
            with open(path, "r") as f:
                recovered_c = f.read()

            for line in recovered_c.splitlines():
                stripped = line.strip()
                expr = stripped.split("/*", 1)[0].strip()
                assert not expr.startswith("[")
        finally:
            os.unlink(path)

    def test_26_top_level_canonical_summary(self):
        ins = _make_ins("mov", [_reg("x8"), _reg("x0")], raw="mov x8, x0")
        ir = _make_ir([
            _make_ir_func("foo", "0x1000", [
                _make_bb("0x1000", [ins])
            ])
        ])
        regions = [{"function_name": "foo", "structured_body": {"type": "block", "id": "0x1000"}}]
        sem = _make_semantics([])

        artifact = build_source_reconstruction(ir, regions, sem)
        obj = artifact.to_dict()
        assert "summary" in obj
        if "summary" in obj.get("data", {}):
            assert obj["summary"] == obj["data"]["summary"]
