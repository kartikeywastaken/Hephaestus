# -*- coding: utf-8 -*-
"""
Unit Tests for Lightweight C Identifier Rewriter
"""

import pytest
from src.readability.symbol_promotion import split_c_line, rewrite_code_chunk

def test_split_c_line_basic():
    # Plain code
    chunks, inside = split_c_line("int a = 123;", False)
    assert chunks == [("code", "int a = 123;")]
    assert not inside

def test_split_c_line_double_quoted_strings():
    line = 'char *s = "hello /* world */ // test \\" escaped";'
    chunks, inside = split_c_line(line, False)
    assert chunks[0] == ("code", "char *s = ")
    assert chunks[1] == ("string", '"hello /* world */ // test \\" escaped"')
    assert chunks[2] == ("code", ";")
    assert not inside

def test_split_c_line_single_quoted_char_literals():
    line = "char c = '\\''; // char literal with escape"
    chunks, inside = split_c_line(line, False)
    assert chunks[0] == ("code", "char c = ")
    assert chunks[1] == ("string", "'\\''")
    assert chunks[2] == ("code", "; ")
    assert chunks[3] == ("comment", "// char literal with escape")
    assert not inside

def test_split_c_line_block_comments():
    line1 = "a = 1; /* block comment begin"
    chunks1, inside1 = split_c_line(line1, False)
    assert chunks1[0] == ("code", "a = 1; ")
    assert chunks1[1] == ("comment", "/*")
    assert chunks1[2] == ("comment", " block comment begin")
    assert inside1
    
    line2 = " still inside comment */ b = 2;"
    chunks2, inside2 = split_c_line(line2, True)
    assert chunks2[0] == ("comment", " still inside comment ")
    assert chunks2[1] == ("comment", "*/")
    assert chunks2[2] == ("code", " b = 2;")
    assert not inside2

def test_split_c_line_line_comments():
    line = "tmp_w8 = stack_36; // stack offset is evidence"
    chunks, inside = split_c_line(line, False)
    assert chunks[0] == ("code", "tmp_w8 = stack_36; ")
    assert chunks[1] == ("comment", "// stack offset is evidence")
    assert not inside

def test_rewrite_code_chunk_boundary():
    rename_map = {
        "stack_m16": "local_m16",
        "arg1": "param_1",
        "tmp_w8": "temp_w8"
    }
    
    # Identifier boundary respected
    assert rewrite_code_chunk("stack_m160 + stack_m16", rename_map) == "stack_m160 + local_m16"
    assert rewrite_code_chunk("arg10 + arg1", rename_map) == "arg10 + param_1"
    assert rewrite_code_chunk("tmp_w80 + tmp_w8", rename_map) == "tmp_w80 + temp_w8"
    
    # Exact replacement
    assert rewrite_code_chunk("u64 stack_m16 = 0;", rename_map) == "u64 local_m16 = 0;"
