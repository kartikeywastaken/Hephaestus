# -*- coding: utf-8 -*-
"""
Tests for Readability Predicate Parser
"""

from src.readability.predicate_parser import parse_adapter_string, unescape_c_string, parse_adapter_polarity

def test_unescape_c_string():
    assert unescape_c_string("hello\\nworld") == "hello\nworld"
    assert unescape_c_string("test\\\"string\\\"") == 'test"string"'
    assert unescape_c_string("path\\\\to\\\\file") == "path\\to\\file"

def test_parse_polarity():
    assert parse_adapter_polarity("cbz w8; loop polarity inverted") == "inverted"
    assert parse_adapter_polarity("cbnz x0; branch polarity inverted") == "inverted"
    assert parse_adapter_polarity("tbz w8, #3; condition polarity inverted") == "inverted"
    assert parse_adapter_polarity("cmp w8, w9; polarity inverted") == "inverted"
    assert parse_adapter_polarity("cmp w8, w9; inverted") == "inverted"
    
    assert parse_adapter_polarity("cbz w8; polarity direct") == "direct"
    assert parse_adapter_polarity("cbnz x0; direct") == "direct"
    
    assert parse_adapter_polarity("cmp w8, w9; polarity unknown") == "unclear"
    
    assert parse_adapter_polarity("cbz w8") == "assumed_direct"

def test_parse_adapter_cbz_cbnz():
    p1 = parse_adapter_string("condition evidence: cbz w8 at 0x1000 targeting 0x1004")
    assert p1 is not None
    assert p1["type"] == "cbz"
    assert p1["register"] == "w8"
    assert p1["polarity"] == "assumed_direct"
    
    p2 = parse_adapter_string("condition evidence: cbnz x0; loop polarity inverted")
    assert p2 is not None
    assert p2["type"] == "cbnz"
    assert p2["register"] == "x0"
    assert p2["polarity"] == "inverted"

def test_parse_adapter_tbz_tbnz():
    p1 = parse_adapter_string("condition evidence: tbz w8,#3 at 0x1000")
    assert p1 is not None
    assert p1["type"] == "tbz"
    assert p1["register"] == "w8"
    assert p1["bit"] == 3
    
    p2 = parse_adapter_string("condition evidence: tbnz x8, #7; polarity direct")
    assert p2 is not None
    assert p2["type"] == "tbnz"
    assert p2["register"] == "x8"
    assert p2["bit"] == 7
    assert p2["polarity"] == "direct"

def test_parse_adapter_cmp_branch_direct():
    p1 = parse_adapter_string("condition evidence: cmp w8, w9; b.lt -> 0x1000")
    assert p1 is not None
    assert p1["type"] == "cmp_branch_direct"
    assert p1["operand1"] == "w8"
    assert p1["operand2"] == "w9"
    assert p1["branch_cond"] == "b.lt"
    
    p2 = parse_adapter_string("condition evidence: cmp x0,#0 + b.ne")
    assert p2 is not None
    assert p2["type"] == "cmp_branch_direct"
    assert p2["operand1"] == "x0"
    assert p2["operand2"] == "#0"
    assert p2["branch_cond"] == "b.ne"

def test_parse_adapter_cmp_branch_indirect():
    p1 = parse_adapter_string("condition evidence: b.ge at 0x1004 after subs at 0x1000; target 0x1008; loop polarity inverted")
    assert p1 is not None
    assert p1["type"] == "cmp_branch_indirect"
    assert p1["comp_mnemonic"] == "subs"
    assert p1["comp_address"] == "0x1000"
    assert p1["branch_cond"] == "b.ge"
    assert p1["polarity"] == "inverted"

def test_parse_unsupported_garbage():
    assert parse_adapter_string("condition unknown: loop header 0x1000") is None
    assert parse_adapter_string("some random string") is None
