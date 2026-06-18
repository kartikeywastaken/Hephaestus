# -*- coding: utf-8 -*-
"""
ARM64 instruction lowering behavior regression tests.
"""

from __future__ import annotations
import pytest
from src.ir.source.lowering import lower_function_instructions

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

def _mem(base, offset=0, size_bytes=8):
    return {"kind": "memory", "base": base, "offset": offset, "size_bytes": size_bytes}

def _unk(raw, size_bytes=8):
    return {"kind": "unknown", "raw": raw, "size_bytes": size_bytes}

def _make_sem_func(name="test_func", entry_point="0x1000", abi_bindings=None):
    return {
        "name": name,
        "entry_point": entry_point,
        "abi_argument_bindings": abi_bindings or [],
    }

def test_regression_arm64_lowering():
    # 1. mov
    mov_ins = _make_ins("mov", [_reg("x8"), _reg("x0")], raw="mov x8, x0", address="0x1000")
    # 2. add/sub
    add_ins = _make_ins("add", [_reg("x9"), _reg("x10"), _imm(16)], raw="add x9, x10, #16", address="0x1004")
    sub_ins = _make_ins("sub", [_reg("x11"), _reg("x12"), _imm(8)], raw="sub x11, x12, #8", address="0x1008")
    # 3. mul
    mul_ins = _make_ins("mul", [_reg("x13"), _reg("x14"), _reg("x15")], raw="mul x13, x14, x15", address="0x100c")
    # 4. udiv
    udiv_ins = _make_ins("udiv", [_reg("x16"), _reg("x17"), _reg("x18")], raw="udiv x16, x17, x18", address="0x1010")
    # 5. sdiv (fully parenthesized cast)
    sdiv_ins = _make_ins("sdiv", [_reg("x19"), _reg("x20"), _reg("x21")], raw="sdiv x19, x20, x21", address="0x1014")
    # 6. ldrsb
    ldrsb_ins = _make_ins("ldrsb", [_reg("x22"), _mem("x23", 0, 1)], raw="ldrsb x22, [x23]", address="0x1018")
    # 7. ldurb
    ldurb_ins = _make_ins("ldurb", [_reg("w24"), _mem("x25", -4, 1)], raw="ldurb w24, [x25, #-4]", address="0x101c")
    # 8. ldurh
    ldurh_ins = _make_ins("ldurh", [_reg("w26"), _mem("x27", -8, 2)], raw="ldurh w26, [x27, #-8]", address="0x1020")
    # 9. ldrsw/ldursw
    ldrsw_ins = _make_ins("ldrsw", [_reg("x28"), _mem("x2", 0, 4)], raw="ldrsw x28, [x2]", address="0x1024")
    # 10. ldr/ldur
    ldr_ins = _make_ins("ldr", [_reg("x0"), _mem("x1", 0, 8)], raw="ldr x0, [x1]", address="0x1028")
    ldur_ins = _make_ins("ldur", [_reg("x2"), _mem("x3", -16, 8)], raw="ldur x2, [x3, #-16]", address="0x102c")
    # 11. str/stur
    str_ins = _make_ins("str", [_reg("x4"), _mem("x5", 0, 8)], raw="str x4, [x5]", address="0x1030")
    stur_ins = _make_ins("stur", [_reg("x6"), _mem("x7", -24, 8)], raw="stur x6, [x7, #-24]", address="0x1034")
    # 12. stp
    stp_ins = _make_ins("stp", [_reg("x29"), _reg("x30"), _mem("sp", 16, 8)], raw="stp x29, x30, [sp, #16]", address="0x1038")
    # 13. ldp
    ldp_ins = _make_ins("ldp", [_reg("x29"), _reg("x30"), _mem("sp", 16, 8)], raw="ldp x29, x30, [sp, #16]", address="0x103c")
    # 14. sxtw
    sxtw_ins = _make_ins("sxtw", [_reg("x8"), _reg("w9")], raw="sxtw x8, w9", address="0x1040")
    # 15. cset
    cset_ins = _make_ins("cset", [_reg("w8"), _reg("eq")], raw="cset w8, eq", address="0x1044")
    # 16. cbz/cbnz
    cbz_ins = _make_ins("cbz", [_reg("x8"), _imm(0x1000)], raw="cbz x8, 0x1000", address="0x1048")
    cbnz_ins = _make_ins("cbnz", [_reg("x9"), _imm(0x1008)], raw="cbnz x9, 0x1008", address="0x104c")
    # 17. tbz/tbnz
    tbz_ins = _make_ins("tbz", [_reg("x10"), _imm(0), _imm(0x1010)], raw="tbz x10, #0, 0x1010", address="0x1050")
    tbnz_ins = _make_ins("tbnz", [_reg("x11"), _imm(1), _imm(0x1018)], raw="tbnz x11, #1, 0x1018", address="0x1054")
    # 18. conditional branch comments
    beq_ins = _make_ins("b.eq", [_imm(0x1020)], raw="b.eq 0x1020", address="0x1058")
    # 19. ret comments
    ret_ins = _make_ins("ret", [], raw="ret", address="0x105c")
    # 20. invalid unsupported
    inv_ins = _make_ins("invalid_op", [_reg("x8")], raw="invalid_op x8", address="0x1060")
    # 21. indexed memory
    idx_mem_ins = _make_ins("ldr", [_reg("x8"), _mem("x9", 0, 8)], raw="ldr x8, [x9, x10, LSL #3]", address="0x1064")
    # 22. shifted/extended register arithmetic
    add_shift_ins = _make_ins("add", [_reg("x8"), _reg("x9"), _unk("x10, LSL #3")], raw="add x8, x9, x10, LSL #3", address="0x1068")
    # 23. zero-register destination behavior (adds xzr)
    adds_xzr_ins = _make_ins("adds", [_reg("xzr"), _reg("x8"), _reg("x9")], raw="adds xzr, x8, x9", address="0x106c")

    ins_list = [
        mov_ins, add_ins, sub_ins, mul_ins, udiv_ins, sdiv_ins, ldrsb_ins, ldurb_ins, ldurh_ins,
        ldrsw_ins, ldr_ins, ldur_ins, str_ins, stur_ins, stp_ins, ldp_ins, sxtw_ins, cset_ins,
        cbz_ins, cbnz_ins, tbz_ins, tbnz_ins, beq_ins, ret_ins, inv_ins, idx_mem_ins, add_shift_ins,
        adds_xzr_ins
    ]

    ir_fn = _make_ir_func(basic_blocks=[_make_bb(instructions=ins_list)])
    sem_fn = _make_sem_func(abi_bindings=[{"argument_index": 0, "register": "x0"}])
    
    stmts, summary = lower_function_instructions(ir_fn, sem_fn, unified_ir=_make_ir(arch="arm64"))
    
    # Map statements by address to verify unique ones
    from collections import defaultdict
    addr_map = defaultdict(list)
    for stmt in stmts:
        addr_map[stmt.address].append(stmt.text)
    
    # Assert lowered output expectations
    assert "tmp_x8 = arg0;" in addr_map["0x1000"][0]
    assert "tmp_x9 = tmp_x10 + 16;" in addr_map["0x1004"][0]
    assert "tmp_x11 = tmp_x12 - 8;" in addr_map["0x1008"][0]
    assert "tmp_x13 = tmp_x14 * tmp_x15;" in addr_map["0x100c"][0]
    assert "tmp_x16 = tmp_x17 / tmp_x18;" in addr_map["0x1010"][0]
    assert "tmp_x19 = ((i64)tmp_x20) / ((i64)tmp_x21);" in addr_map["0x1014"][0]
    assert "tmp_x22 = (i64)*(i8 *)(tmp_x23);" in addr_map["0x1018"][0]
    assert "tmp_w24 = *(u8 *)(tmp_x25 - 4);" in addr_map["0x101c"][0]
    assert "tmp_w26 = *(u16 *)(tmp_x27 - 8);" in addr_map["0x1020"][0]
    assert "tmp_x28 = (i64)*(i32 *)(tmp_x2);" in addr_map["0x1024"][0]
    assert "arg0 = *(u64 *)(tmp_x1);" in addr_map["0x1028"][0]
    assert "tmp_x2 = *(u64 *)(tmp_x3 - 16);" in addr_map["0x102c"][0]
    assert "*(u64 *)(tmp_x5) = tmp_x4;" in addr_map["0x1030"][0]
    assert "*(u64 *)(tmp_x7 - 24) = tmp_x6;" in addr_map["0x1034"][0]
    
    # stp
    assert "stack_16 = tmp_fp;" in addr_map["0x1038"][0]
    
    # ldp
    ldp_texts = addr_map["0x103c"]
    assert any("tmp_fp = stack_16;" in s for s in ldp_texts)
    assert any("tmp_lr = stack_24;" in s for s in ldp_texts)
    
    assert "tmp_x8 = (i64)(i32)tmp_w9;" in addr_map["0x1040"][0]
    assert 'tmp_w8 = HEPHAESTUS_CSET("eq");' in addr_map["0x1044"][0]
    assert "/* cbz tmp_x8 -> 0x1000 */" in addr_map["0x1048"][0]
    assert "/* cbnz tmp_x9 -> 0x1008 */" in addr_map["0x104c"][0]
    assert "/* tbz tmp_x10 bit 0 -> 0x1010 */" in addr_map["0x1050"][0]
    assert "/* tbnz tmp_x11 bit 1 -> 0x1018 */" in addr_map["0x1054"][0]
    assert "/* conditional branch b.eq -> 0x1020 */" in addr_map["0x1058"][0]
    assert "/* return via x0 */" in addr_map["0x105c"][0]
    assert "unsupported instruction: invalid_op" in addr_map["0x1060"][0]
    
    # shifted/extended register arithmetic
    assert "tmp_x8 = tmp_x9 + (tmp_x10 << 3);" in addr_map["0x1068"][0]
    
    # zero-register adds update flags, result discarded comment only
    assert "/* adds xzr,tmp_x8,tmp_x9; flags updated, result discarded */" in addr_map["0x106c"][0]
