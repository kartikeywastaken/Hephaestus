# -*- coding: utf-8 -*-
"""
Tests for Evidence Index Classifiers
"""

from __future__ import annotations
import pytest
from src.validation.evidence_index.classifiers import is_pure_comment, classify_line

def test_is_pure_comment():
    assert is_pure_comment("/* comment */") is True
    assert is_pure_comment("// line comment") is True
    assert is_pure_comment("  /* block comment */  ") is True
    assert is_pure_comment("int a = 0; // comment") is False
    assert is_pure_comment("   ") is False

def test_classify_helper():
    cat, sub = classify_line("static int HEPHAESTUS_UNKNOWN_COND(u64 val);", {})
    assert cat == "helper"
    assert sub == "helper_definition"

def test_classify_declaration():
    cat, sub = classify_line("typedef int my_int;", {})
    assert cat == "declaration"
    assert sub == "typedef"
    
    cat, sub = classify_line("void test_func(int a, float b);", {})
    assert cat == "declaration"
    assert sub == "prototype"

    # Local variable declarations
    cat, sub = classify_line("u64 tmp_sp = 0;", {})
    assert cat == "declaration"
    assert sub == "local_declaration"

def test_classify_empty_function_scaffold():
    cat, sub = classify_line("/* TODO: body reconstruction pending */", {})
    assert cat == "empty_function_scaffold"

def test_classify_syntax_adapter():
    cat, sub = classify_line("if (HEPHAESTUS_UNKNOWN_COND(0)) {", {})
    assert cat == "syntax_adapter"
    assert sub == "control_flow_condition"
    
    cat, sub = classify_line("u64 x = HEPHAESTUS_CSET(1);", {})
    assert cat == "syntax_adapter"
    assert sub == "cset"

def test_classify_true_unsupported_vs_comment_lowered():
    unsupported_kinds = {"invalid": 1, "udf": 1}
    
    # 1. Matches exact mnemonic in summary
    cat, sub = classify_line("/* unsupported instruction: udf */", unsupported_kinds)
    assert cat == "true_unsupported"
    assert sub == "udf"
    
    # 2. Text fallback search in summary keys
    cat, sub = classify_line("/* unsupported udf instruction at address 0x1000 */", unsupported_kinds)
    assert cat == "true_unsupported"
    assert sub == "udf"

    # 3. Not in summary -> comment_lowered fallback
    cat, sub = classify_line("/* unsupported instruction: nop */", unsupported_kinds)
    assert cat == "comment_lowered"
    assert sub == "unsupported_comment_fallback"

def test_classify_branch_evidence():
    cat, sub = classify_line("/* branch to 0x100000578 */", {})
    assert cat == "branch_evidence"
    
    cat, sub = classify_line("/* tbz tmp_w8 bit 0 -> 0x100 */", {})
    assert cat == "branch_evidence"

def test_classify_call():
    cat, sub = classify_line("call_0x10000();", {})
    assert cat == "call"
    assert sub == "direct_call"
    
    cat, sub = classify_line("/* indirect call */", {})
    assert cat == "call"
    assert sub == "indirect_call_comment"

def test_classify_return():
    cat, sub = classify_line("return 0;", {})
    assert cat == "return"
    assert sub == "return_statement"
    
    cat, sub = classify_line("/* return value */", {})
    assert cat == "return"
    assert sub == "return_comment"

def test_classify_control_flow_scaffold():
    assert classify_line("if (a == b) {", {})[0] == "control_flow_scaffold"
    assert classify_line("}", {})[0] == "control_flow_scaffold"

def test_classify_executable_lowered():
    assert classify_line("x = y + z;", {})[0] == "executable_lowered"
