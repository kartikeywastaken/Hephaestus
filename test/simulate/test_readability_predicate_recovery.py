# -*- coding: utf-8 -*-
"""
Tests for Readability Predicate Recovery
"""

from src.readability.predicate_recovery import recover_predicate, map_operand, parse_compare_instruction

def test_map_operand():
    assert map_operand("w8") == "tmp_w8"
    assert map_operand("x0") == "tmp_x0"
    assert map_operand("sp") == "tmp_sp"
    assert map_operand("x29") == "tmp_fp"
    assert map_operand("x30") == "tmp_lr"
    assert map_operand("wzr") == "0"
    assert map_operand("xzr") == "0"
    assert map_operand("#10") == "10"
    assert map_operand("0x12") == "18"
    assert map_operand("tmp_w8") == "tmp_w8"

def test_parse_compare_instruction():
    # cmp
    assert parse_compare_instruction({"mnemonic": "cmp", "raw": "cmp w8, #10"}) == ("w8", "10")
    assert parse_compare_instruction({"mnemonic": "cmp", "raw": "cmp w8, w9"}) == ("w8", "w9")
    
    # subs
    assert parse_compare_instruction({"mnemonic": "subs", "raw": "subs w8, w8, #0x12"}) == ("w8", "0x12")
    assert parse_compare_instruction({"mnemonic": "subs", "raw": "subs w8, w8, w9"}) == ("w8", "w9")
    
    # invalid
    assert parse_compare_instruction({"mnemonic": "add", "raw": "add w8, w8, #1"}) is None

def test_recover_cbz_cbnz():
    # cbz
    site = {"type": "cbz", "register": "w8", "polarity": "assumed_direct"}
    status, expr, reason, notes = recover_predicate(site, {})
    assert status == "recovered"
    assert expr == "tmp_w8 == 0"
    assert "polarity inferred" in notes[0]
    
    # cbz inverted
    site = {"type": "cbz", "register": "w8", "polarity": "inverted"}
    status, expr, reason, notes = recover_predicate(site, {})
    assert status == "recovered"
    assert expr == "tmp_w8 != 0"
    
    # cbnz
    site = {"type": "cbnz", "register": "x0", "polarity": "direct"}
    status, expr, reason, notes = recover_predicate(site, {})
    assert status == "recovered"
    assert expr == "tmp_x0 != 0"

def test_recover_tbz_tbnz():
    # tbz w-register
    site = {"type": "tbz", "register": "w8", "bit": 3, "polarity": "direct"}
    status, expr, reason, notes = recover_predicate(site, {})
    assert status == "recovered"
    assert expr == "(tmp_w8 & (1u << 3)) == 0"
    
    # tbz x-register
    site = {"type": "tbz", "register": "x8", "bit": 3, "polarity": "direct"}
    status, expr, reason, notes = recover_predicate(site, {})
    assert status == "recovered"
    assert expr == "(tmp_x8 & (1ull << 3)) == 0"
    
    # tbnz w-register inverted
    site = {"type": "tbnz", "register": "w8", "bit": 5, "polarity": "inverted"}
    status, expr, reason, notes = recover_predicate(site, {})
    assert status == "recovered"
    assert expr == "(tmp_w8 & (1u << 5)) == 0"

def test_recover_cmp_branch_direct():
    site = {
        "type": "cmp_branch_direct",
        "operand1": "w8",
        "operand2": "w9",
        "branch_cond": "b.lt",
        "polarity": "direct"
    }
    status, expr, reason, notes = recover_predicate(site, {})
    assert status == "recovered"
    assert expr == "tmp_w8 < tmp_w9"
    
    # immediate, inverted
    site = {
        "type": "cmp_branch_direct",
        "operand1": "w8",
        "operand2": "#10",
        "branch_cond": "b.ge",
        "polarity": "inverted"
    }
    status, expr, reason, notes = recover_predicate(site, {})
    assert status == "recovered"
    # ge negated is lt
    assert expr == "tmp_w8 < 10"

def test_recover_cmp_branch_indirect():
    inst_lookup = {
        "0x1000": {"mnemonic": "subs", "raw": "subs w8, w8, #0x12"}
    }
    site = {
        "type": "cmp_branch_indirect",
        "comp_address": "0x1000",
        "branch_cond": "b.ge",
        "polarity": "inverted"
    }
    status, expr, reason, notes = recover_predicate(site, inst_lookup)
    assert status == "recovered"
    assert expr == "tmp_w8 < 18"
    
    # missing cmp
    site = {
        "type": "cmp_branch_indirect",
        "comp_address": "0x2000",
        "branch_cond": "b.ge",
        "polarity": "inverted"
    }
    status, expr, reason, notes = recover_predicate(site, inst_lookup)
    assert status == "skipped"
    assert reason == "missing compare producer"

def test_unsigned_branch_note():
    site = {
        "type": "cmp_branch_direct",
        "operand1": "w8",
        "operand2": "w9",
        "branch_cond": "b.lo",
        "polarity": "direct"
    }
    status, expr, reason, notes = recover_predicate(site, {})
    assert status == "recovered"
    assert expr == "tmp_w8 < tmp_w9"
    assert any("unsigned branch condition" in n for n in notes)

def test_ambiguous_polarity_skips():
    site = {"type": "cbz", "register": "w8", "polarity": "unclear"}
    status, expr, reason, notes = recover_predicate(site, {})
    assert status == "skipped"
    assert reason == "ambiguous branch polarity"
