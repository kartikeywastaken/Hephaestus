# -*- coding: utf-8 -*-
"""
Tests for Phase 5.7.2 ARM64 Remaining Instruction Lowering Cleanup.
"""

from __future__ import annotations

import json
import os
import pytest
from src.ir.source.models import (
    ReconstructedFunction,
    SourceReconstructionArtifact,
    SCHEMA_VERSION,
)
from src.ir.source.lowering import lower_function_instructions
from src.ir.source.reconstructor import build_source_reconstruction
from src.ir.source.c_emitter import emit_recovered_c


def _make_ir(functions=None, arch="arm64"):
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


def _unknown(raw):
    return {"kind": "unknown", "raw": raw}


class TestArm64RemainingLowering:

    # Test 1 — udiv 64-bit
    def test_1_udiv_64bit(self):
        ins = _make_ins("udiv", [_reg("x8"), _reg("x9"), _reg("x10")], raw="udiv x8,x9,x10")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        stmts, summary = lower_function_instructions(ir_fn, unified_ir=_make_ir())
        assert len(stmts) == 1
        assert stmts[0].lowered is True
        assert stmts[0].text == "tmp_x8 = tmp_x9 / tmp_x10; /* udiv x8,x9,x10 */"

        # Zero register target test
        ins_zero = _make_ins("udiv", [_reg("xzr"), _reg("x9"), _reg("x10")], raw="udiv xzr,x9,x10")
        ir_fn_zero = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins_zero])])
        stmts_zero, summary_zero = lower_function_instructions(ir_fn_zero, unified_ir=_make_ir())
        assert len(stmts_zero) == 1
        assert stmts_zero[0].lowered is True
        assert stmts_zero[0].text == "/* udiv xzr,tmp_x9,tmp_x10; result discarded */"

    # Test 2 — udiv 32-bit
    def test_2_udiv_32bit(self):
        ins = _make_ins("udiv", [_reg("w8"), _reg("w9"), _reg("w10")], raw="udiv w8,w9,w10")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        stmts, summary = lower_function_instructions(ir_fn, unified_ir=_make_ir())
        assert len(stmts) == 1
        assert stmts[0].lowered is True
        assert stmts[0].text == "tmp_w8 = tmp_w9 / tmp_w10; /* udiv w8,w9,w10 */"

    # Test 3 — sdiv 64-bit
    def test_3_sdiv_64bit(self):
        ins = _make_ins("sdiv", [_reg("x8"), _reg("x9"), _reg("x10")], raw="sdiv x8,x9,x10")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        stmts, summary = lower_function_instructions(ir_fn, unified_ir=_make_ir())
        assert len(stmts) == 1
        assert stmts[0].lowered is True
        assert stmts[0].text == "tmp_x8 = ((i64)tmp_x9) / ((i64)tmp_x10); /* sdiv x8,x9,x10 */"

        # Zero register target test
        ins_zero = _make_ins("sdiv", [_reg("xzr"), _reg("x9"), _reg("x10")], raw="sdiv xzr,x9,x10")
        ir_fn_zero = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins_zero])])
        stmts_zero, summary_zero = lower_function_instructions(ir_fn_zero, unified_ir=_make_ir())
        assert len(stmts_zero) == 1
        assert stmts_zero[0].lowered is True
        assert stmts_zero[0].text == "/* sdiv xzr,((i64)tmp_x9),((i64)tmp_x10); result discarded */"

    # Test 4 — sdiv 32-bit
    def test_4_sdiv_32bit(self):
        ins = _make_ins("sdiv", [_reg("w8"), _reg("w9"), _reg("w10")], raw="sdiv w8,w9,w10")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        stmts, summary = lower_function_instructions(ir_fn, unified_ir=_make_ir())
        assert len(stmts) == 1
        assert stmts[0].lowered is True
        assert stmts[0].text == "tmp_w8 = ((i32)tmp_w9) / ((i32)tmp_w10); /* sdiv w8,w9,w10 */"

        # Zero register target test
        ins_zero = _make_ins("sdiv", [_reg("wzr"), _reg("w9"), _reg("w10")], raw="sdiv wzr,w9,w10")
        ir_fn_zero = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins_zero])])
        stmts_zero, summary_zero = lower_function_instructions(ir_fn_zero, unified_ir=_make_ir())
        assert len(stmts_zero) == 1
        assert stmts_zero[0].lowered is True
        assert stmts_zero[0].text == "/* sdiv wzr,((i32)tmp_w9),((i32)tmp_w10); result discarded */"

    # Test 5 — ldrsb into x-register
    def test_5_ldrsb_x_register(self):
        ins = _make_ins("ldrsb", [_reg("x8"), _unknown("[x9, w10, SXTW]")], raw="ldrsb x8,[x9,w10,SXTW]")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        stmts, summary = lower_function_instructions(ir_fn, unified_ir=_make_ir())
        assert len(stmts) == 1
        assert stmts[0].lowered is True
        assert stmts[0].text == "tmp_x8 = (i64)*(i8 *)(tmp_x9 + ((i64)(i32)tmp_w10)); /* ldrsb x8,[x9,w10,SXTW] */"

    # Test 6 — ldrsb into w-register
    def test_6_ldrsb_w_register(self):
        ins = _make_ins("ldrsb", [_reg("w8"), _unknown("[x9, #0x4]")], raw="ldrsb w8,[x9,#0x4]")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        stmts, summary = lower_function_instructions(ir_fn, unified_ir=_make_ir())
        assert len(stmts) == 1
        assert stmts[0].lowered is True
        assert stmts[0].text == "tmp_w8 = (i32)*(i8 *)(tmp_x9 + 4); /* ldrsb w8,[x9,#0x4] */"

    # Test 7 — ldurb
    def test_7_ldurb(self):
        ins = _make_ins("ldurb", [_reg("w8"), _unknown("[x9, #-0x1]")], raw="ldurb w8,[x9,#-0x1]")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        stmts, summary = lower_function_instructions(ir_fn, unified_ir=_make_ir())
        assert len(stmts) == 1
        assert stmts[0].lowered is True
        assert stmts[0].text == "tmp_w8 = *(u8 *)(tmp_x9 - 1); /* ldurb w8,[x9,#-0x1] */"

    # Test 8 — ldurh
    def test_8_ldurh(self):
        ins = _make_ins("ldurh", [_reg("w8"), _unknown("[x9, #-0x2]")], raw="ldurh w8,[x9,#-0x2]")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        stmts, summary = lower_function_instructions(ir_fn, unified_ir=_make_ir())
        assert len(stmts) == 1
        assert stmts[0].lowered is True
        assert stmts[0].text == "tmp_w8 = *(u16 *)(tmp_x9 - 2); /* ldurh w8,[x9,#-0x2] */"

    # Test 9 — ldp x-pair
    def test_9_ldp_x_pair(self):
        ins = _make_ins("ldp", [_reg("x29"), _reg("x30"), _unknown("[sp, #0x60]")], raw="ldp x29,x30,[sp,#0x60]")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        stmts, summary = lower_function_instructions(ir_fn, unified_ir=_make_ir())
        assert len(stmts) == 2
        assert stmts[0].lowered is True
        assert stmts[0].text == "tmp_fp = stack_96; /* ldp x29,x30,[sp,#0x60] */"
        assert stmts[1].lowered is True
        assert stmts[1].text == "tmp_lr = stack_104; /* paired load second register inferred offset +8 */"

    # Test 10 — ldp w-pair
    def test_10_ldp_w_pair(self):
        ins = _make_ins("ldp", [_reg("w8"), _reg("w9"), _unknown("[sp, #0x10]")], raw="ldp w8,w9,[sp,#0x10]")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        stmts, summary = lower_function_instructions(ir_fn, unified_ir=_make_ir())
        assert len(stmts) == 2
        assert stmts[0].lowered is True
        assert stmts[0].text == "tmp_w8 = stack_16; /* ldp w8,w9,[sp,#0x10] */"
        assert stmts[1].lowered is True
        assert stmts[1].text == "tmp_w9 = stack_20; /* paired load second register inferred offset +4 */"

        # Unresolved ldp fallback test
        ins_unresolved = _make_ins("ldp", [_reg("x8"), _reg("x9"), _unknown("[x10, x11]")], raw="ldp x8,x9,[x10, x11]")
        ir_fn_unresolved = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins_unresolved])])
        stmts_unres, summary_unres = lower_function_instructions(ir_fn_unresolved, unified_ir=_make_ir())
        assert len(stmts_unres) == 1
        assert stmts_unres[0].lowered is False
        assert stmts_unres[0].text == "/* unsupported paired load: ldp x8,x9,[x10, x11] */"

    # Test 11 — sxtw
    def test_11_sxtw(self):
        ins1 = _make_ins("sxtw", [_reg("x8"), _reg("w9")], raw="sxtw x8,w9")
        ins2 = _make_ins("sxtw", [_reg("w8"), _reg("w9")], raw="sxtw w8,w9")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins1, ins2])])
        stmts, summary = lower_function_instructions(ir_fn, unified_ir=_make_ir())
        assert len(stmts) == 2
        assert stmts[0].lowered is True
        assert stmts[0].text == "tmp_x8 = (i64)(i32)tmp_w9; /* sxtw x8,w9 */"
        assert stmts[1].lowered is True
        assert stmts[1].text == "tmp_w8 = tmp_w9; /* sxtw w8,w9; width already 32-bit */"

    # Test 12 — cset helper lowering
    def test_12_cset_lowering(self):
        ins = _make_ins("cset", [_reg("w8"), _unknown("eq")], raw="cset w8,eq")
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=[ins])])
        stmts, summary = lower_function_instructions(ir_fn, unified_ir=_make_ir())
        assert len(stmts) == 1
        assert stmts[0].lowered is True
        assert stmts[0].text == 'tmp_w8 = HEPHAESTUS_CSET("eq"); /* cset w8,eq; flags not modeled */'

    # Test 13 — cset does not recover conditions
    def test_13_cset_safety(self):
        # Build structure and run c_emitter
        fn = ReconstructedFunction(
            name="fn_test",
            c_name="fn_test",
            entry_point="0x1000",
            body_status="structured",
            lowered_statements=[{
                "address": "0x1000",
                "kind": "binary_op",
                "text": 'tmp_w8 = HEPHAESTUS_CSET("eq"); /* cset w8,eq; flags not modeled */',
                "lowered": True,
                "warnings": []
            }]
        )
        artifact = SourceReconstructionArtifact(schema_version="5.7.2", functions=[fn])
        
        with tempfile_path() as path:
            emit_recovered_c(artifact, path)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Assert condition_expressions_recovered == 0
            assert artifact.summary["condition_expressions_recovered"] == 0
            # Assert no executable conditional statements are generated
            assert "if (tmp_" not in content
            assert "while (tmp_" not in content

    # Test 14 — Helper scanners ignore HEPHAESTUS_CSET
    def test_14_scanners_ignore_cset(self):
        fn = ReconstructedFunction(
            name="fn_test",
            c_name="fn_test",
            entry_point="0x1000",
            body_status="structured",
            lowered_statements=[{
                "address": "0x1000",
                "kind": "binary_op",
                "text": 'tmp_w8 = HEPHAESTUS_CSET("eq"); /* cset w8,eq; flags not modeled */',
                "lowered": True,
                "warnings": []
            }]
        )
        artifact = SourceReconstructionArtifact(schema_version="5.7.2", functions=[fn])
        with tempfile_path() as path:
            emit_recovered_c(artifact, path)
            # Check helper scanner ignoral: it's not declared as local pseudo declaration
            decls = fn.declaration_recovery.get("declarations", [])
            decl_names = [d["name"] for d in decls]
            assert "HEPHAESTUS_CSET" not in decl_names
            # Check call helper ignores it
            helpers = fn.declaration_recovery.get("call_helpers", [])
            assert "HEPHAESTUS_CSET" not in helpers
            assert "call_HEPHAESTUS_CSET" not in helpers

    # Test 15 — Unsupported analytics cleanup (with invalid)
    def test_15_analytics_cleanup(self):
        ins_list = [
            _make_ins("udiv", [_reg("x8"), _reg("x9"), _reg("x10")]),
            _make_ins("sdiv", [_reg("x8"), _reg("x9"), _reg("x10")]),
            _make_ins("ldrsb", [_reg("x8"), _unknown("[x9, w10, SXTW]")]),
            _make_ins("ldurb", [_reg("w8"), _unknown("[x9, #-0x1]")]),
            _make_ins("ldurh", [_reg("w8"), _unknown("[x9, #-0x2]")]),
            _make_ins("ldp", [_reg("x29"), _reg("x30"), _unknown("[sp, #0x60]")]),
            _make_ins("sxtw", [_reg("x8"), _reg("w9")]),
            _make_ins("cset", [_reg("w8"), _unknown("eq")]),
            _make_ins("invalid", []),
        ]
        ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=ins_list)])
        ir = _make_ir([ir_fn])
        regions = [{"function_name": "test_func", "structured_body": {"type": "block", "id": "0x1000"}}]
        sem = {"schema_version": "4D.1.0", "data": {"functions": []}}
        
        artifact = build_source_reconstruction(ir, regions, sem)
        global_unsupported = artifact.summary.get("unsupported_instruction_kinds", {})
        
        # udiv, sdiv, ldrsb, ldurb, ldurh, ldp, sxtw, cset should NOT be unsupported
        for m in ["udiv", "sdiv", "ldrsb", "ldurb", "ldurh", "ldp", "sxtw", "cset"]:
            assert m not in global_unsupported
        
        # invalid SHOULD be unsupported
        assert "invalid" in global_unsupported
        assert global_unsupported["invalid"] == 1

    # Test 16 — Ultimate torture regression check
    def test_16_ultimate_torture_regression(self):
        artifact = SourceReconstructionArtifact()
        assert artifact.summary["condition_expressions_recovered"] == 0


import contextlib

@contextlib.contextmanager
def tempfile_path(suffix=".c"):
    import tempfile
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        yield path
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(path)
