# -*- coding: utf-8 -*-
"""
Tests for Phase 7.3 Conservative Expression Simplification
"""

import pytest
from src.readability.expression_simplification import (
    simplify_expressions,
    _is_rhs_safe,
    _try_simplify_identity_arithmetic,
    _try_simplify_parentheses
)
from src.readability.report import build_readability_report

def test_rhs_safety_checks():
    # Safe RHS cases
    assert _is_rhs_safe("tmp_w8 + 0") is True
    assert _is_rhs_safe("local_20 - 0") is True
    assert _is_rhs_safe("1 * tmp_w8") is True
    assert _is_rhs_safe("(tmp_w8)") is True
    
    # Unsafe RHS cases: pointers
    assert _is_rhs_safe("*ptr + 0") is False
    assert _is_rhs_safe("ptr->val + 0") is False
    
    # Unsafe RHS cases: array index
    assert _is_rhs_safe("arr[i] + 0") is False
    
    # Unsafe RHS cases: casts
    assert _is_rhs_safe("(u64)tmp_w8 + 0") is False
    assert _is_rhs_safe("((u64)tmp_w8)") is False
    
    # Unsafe RHS cases: calls & macros
    assert _is_rhs_safe("HEPHAESTUS_CSET(tmp_w8 + 0)") is False
    assert _is_rhs_safe("func(tmp_w8 + 0)") is False


def test_exact_numeric_constants():
    # Allowed zero constants
    for z in ["0", "0u", "0U", "0ull", "0ULL", "0ll", "0LL"]:
        assert _try_simplify_identity_arithmetic(f"tmp_w8 + {z}") == ("tmp_w8", "simplified identity expression")
        assert _try_simplify_identity_arithmetic(f"{z} + tmp_w8") == ("tmp_w8", "simplified identity expression")
        assert _try_simplify_identity_arithmetic(f"tmp_w8 | {z}") == ("tmp_w8", "simplified identity expression")
        assert _try_simplify_identity_arithmetic(f"tmp_w8 ^ {z}") == ("tmp_w8", "simplified identity expression")
        assert _try_simplify_identity_arithmetic(f"tmp_w8 << {z}") == ("tmp_w8", "simplified identity expression")
        assert _try_simplify_identity_arithmetic(f"tmp_w8 >> {z}") == ("tmp_w8", "simplified identity expression")
        
    # Allowed one constants
    for o in ["1", "1u", "1U", "1ull", "1ULL", "1ll", "1LL"]:
        assert _try_simplify_identity_arithmetic(f"tmp_w8 * {o}") == ("tmp_w8", "simplified identity expression")
        assert _try_simplify_identity_arithmetic(f"{o} * tmp_w8") == ("tmp_w8", "simplified identity expression")
        assert _try_simplify_identity_arithmetic(f"tmp_w8 / {o}") == ("tmp_w8", "simplified identity expression")

    # Disallowed constants
    for bad in ["0x10", "10", "01", "-0", "+0", "false", "NULL"]:
        assert _try_simplify_identity_arithmetic(f"tmp_w8 + {bad}") is None


def test_parentheses_simplification_narrow():
    # Allowed wrapping simple RHS
    assert _try_simplify_parentheses("(tmp_w8)") == ("tmp_w8", "simplified redundant parentheses")
    assert _try_simplify_parentheses("(42)") == ("42", "simplified redundant parentheses")
    
    # Cast contexts skipped
    assert _try_simplify_parentheses("(u64)") is None
    assert _try_simplify_parentheses("(uintptr_t)") is None
    
    # Complex paren expressions skipped
    assert _try_simplify_parentheses("(tmp_w8 + 1)") is None


def test_simplify_expressions_assignment_rhs():
    c_in = """
void func() {
    tmp_w8 = tmp_w8 + 0;
    local_20 = 0 + local_20; /* orig comment */
    tmp_x0 = tmp_x0 | 0U;
    tmp_w8 = (tmp_w9);
}
"""
    c_out, simplifications, skipped, stats = simplify_expressions(c_in)
    
    assert stats.sites_total == 4
    assert stats.simplified == 4
    assert stats.identity_arithmetic == 3
    assert stats.redundant_parentheses == 1
    
    # Verify line comments preserved
    assert "/* orig comment; simplified identity expression: 0 + local_20 -> local_20 */" in c_out
    assert "tmp_w8 = tmp_w9;" in c_out


def test_copy_op_store_strict():
    # Valid consecutive copy-op-store
    c_in = """
void func() {
    tmp_w8 = local_20;
    tmp_w8 = tmp_w8 + 1;
    local_20 = tmp_w8;
}
"""
    c_out, simplifications, skipped, stats = simplify_expressions(c_in, enable_copy_op_store=True)
    assert stats.copy_op_store == 1
    assert "local_20 = local_20 + 1;" in c_out
    assert "local_20++;" not in c_out
    
    # Unsafe due to comments in between
    c_comments = """
void func() {
    tmp_w8 = local_20;
    // some comment here
    tmp_w8 = tmp_w8 + 1;
    local_20 = tmp_w8;
}
"""
    _, _, _, stats_c = simplify_expressions(c_comments)
    assert stats_c.copy_op_store == 0

    # Unsafe due to width mismatch
    c_width = """
void func() {
    tmp_x8 = local_20;
    tmp_w8 = tmp_w8 + 1;
    local_20 = tmp_x8;
}
"""
    _, _, _, stats_w = simplify_expressions(c_width)
    assert stats_w.copy_op_store == 0

    # Unsafe due to temp used in region
    c_region = """
void func() {
    tmp_w8 = local_20;
    tmp_w8 = tmp_w8 + 1;
    local_20 = tmp_w8;
    tmp_w8 = 12;
}
"""
    _, _, _, stats_r = simplify_expressions(c_region)
    assert stats_r.copy_op_store == 0


def test_schema_version_and_phase_conditional():
    # Scenario A: Enabled and OK
    report_ok = build_readability_report(
        sites=[], skipped_sites=[], quality_gate_status="ok",
        safe_to_use_for_phase7=True, clang_syntax_status="ok",
        warnings=[], diagnostics=[], promote_symbols_enabled=True,
        compile_shape_enabled=True,
        expression_simplification_enabled=True,
        expression_simplification_data={"status": "ok", "simplified": 3}
    )
    assert report_ok["schema_version"] == "readability-1.3"
    assert report_ok["phase"] == "7.3"
    assert report_ok["mode"] == "static_predicate_symbol_promotion_compile_shape_expression_simplification"

    # Scenario B: Disabled
    report_disabled = build_readability_report(
        sites=[], skipped_sites=[], quality_gate_status="ok",
        safe_to_use_for_phase7=True, clang_syntax_status="ok",
        warnings=[], diagnostics=[], promote_symbols_enabled=True,
        compile_shape_enabled=True,
        expression_simplification_enabled=False
    )
    assert report_disabled["schema_version"] == "readability-1.2"
    assert report_disabled["phase"] == "7.2.1"
    
    # Scenario C: Rolled back
    report_rolled = build_readability_report(
        sites=[], skipped_sites=[], quality_gate_status="ok",
        safe_to_use_for_phase7=True, clang_syntax_status="ok",
        warnings=[], diagnostics=[], promote_symbols_enabled=True,
        compile_shape_enabled=True,
        expression_simplification_enabled=True,
        expression_simplification_data={"status": "rolled_back", "simplified": 0}
    )
    assert report_rolled["schema_version"] == "readability-1.2"
    assert report_rolled["phase"] == "7.2.1"
