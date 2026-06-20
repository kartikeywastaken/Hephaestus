# -*- coding: utf-8 -*-
"""
Tests for Phase 7.3 Conservative Expression Simplification
"""

import pytest
from src.readability.expression_simplification import (
    simplify_expressions,
    _is_rhs_safe,
    # Phase 7.3.1 re-exports
    ExprSimplification,
    ExprSimplificationStats,
)
from src.readability.expression_rules import (
    rule_identity_arithmetic,
    rule_redundant_parentheses,
    rule_self_assignment,
    rule_double_parentheses,
    rule_mask_cast,
)
from src.readability.expression_models import RuleResult
from src.readability.report import build_readability_report

# Backward-compat aliases (the old private functions now live in expression_rules)
def _try_simplify_identity_arithmetic(expr):
    result = rule_identity_arithmetic(expr)
    if result is None:
        return None
    return (result.new_expr, result.reason)

def _try_simplify_parentheses(expr):
    result = rule_redundant_parentheses(expr)
    if result is None:
        return None
    return (result.new_expr, result.reason)


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


# ---------------------------------------------------------------------------
# Phase 7.3.1 — New category tests
# ---------------------------------------------------------------------------

def test_import_continuity():
    """Ensure Phase 7.3 public symbols are still importable (backward compat)."""
    # Data models re-exported from expression_simplification
    assert ExprSimplification is not None
    assert ExprSimplificationStats is not None
    # Rule functions importable from expression_rules
    assert rule_identity_arithmetic is not None
    assert rule_redundant_parentheses is not None
    assert rule_self_assignment is not None
    assert rule_double_parentheses is not None
    assert rule_mask_cast is not None
    assert RuleResult is not None


def test_category_e_self_assignment():
    """Category E: self-assignment lines are removed and replaced with evidence comment."""
    c_in = """\
void func() {
    tmp_w8 = tmp_w8;
    local_20 = local_20; /* orig */
    tmp_x0 = tmp_x0;
}
"""
    c_out, simplifications, _, stats = simplify_expressions(c_in)

    assert stats.self_assignment == 3
    assert stats.simplified == 3
    # Original assignment lines should be gone, replaced by evidence comments
    assert "tmp_w8 = tmp_w8;" not in c_out
    assert "local_20 = local_20;" not in c_out
    assert "tmp_x0 = tmp_x0;" not in c_out
    # Evidence comments should be present
    assert "self-assignment removed" in c_out

    # rule_self_assignment directly
    result = rule_self_assignment("tmp_w8", "tmp_w8")
    assert result is not None
    assert result.category == "self_assignment"
    assert result.new_expr == ""

    # Distinct LHS/RHS should not match
    assert rule_self_assignment("tmp_w8", "tmp_w9") is None
    # Non-simple operand LHS should not match
    assert rule_self_assignment("arr[0]", "arr[0]") is None


def test_category_f_double_parentheses():
    """Category F: double-wrapped parentheses around a simple operand are collapsed."""
    c_in = """\
void func() {
    tmp_w8 = ((tmp_w9));
    local_20 = ((42));
}
"""
    c_out, simplifications, _, stats = simplify_expressions(c_in)

    assert stats.double_parentheses == 2
    assert stats.simplified == 2
    assert "tmp_w8 = tmp_w9;" in c_out
    assert "local_20 = 42;" in c_out

    # rule_double_parentheses directly
    result = rule_double_parentheses("((tmp_w8))")
    assert result is not None
    assert result.new_expr == "tmp_w8"
    assert result.category == "double_parentheses"

    # Single-wrap: should not match (that's Category B)
    assert rule_double_parentheses("(tmp_w8)") is None

    # Type name inside: should be skipped
    assert rule_double_parentheses("((u64))") is None

    # More than two levels: should not match
    assert rule_double_parentheses("(((tmp_w8)))") is None


def test_category_g_temp_copy_roundtrip():
    """Category G: tmp = src; src = tmp; is folded into an evidence comment."""
    c_in = """\
void func() {
    tmp_w8 = local_20;
    local_20 = tmp_w8;
}
"""
    c_out, simplifications, _, stats = simplify_expressions(c_in)

    assert stats.temp_copy_roundtrip == 1
    assert stats.simplified == 1
    # The original lines must NOT appear as standalone code (they may appear inside comments)
    for line in c_out.splitlines():
        stripped = line.strip()
        if stripped.startswith("/*") or stripped.startswith("//"):
            continue  # evidence comment line, ok
        assert "tmp_w8 = local_20;" not in stripped, f"Unexpected code line: {stripped!r}"
        assert "local_20 = tmp_w8;" not in stripped, f"Unexpected code line: {stripped!r}"
    # Evidence comment should be present
    assert "temp copy roundtrip removed" in c_out

    # Unsafe: tmp used in surrounding region
    c_region = """\
void func() {
    tmp_w8 = local_20;
    local_20 = tmp_w8;
    tmp_w8 = 42;
}
"""
    _, _, _, stats_r = simplify_expressions(c_region)
    assert stats_r.temp_copy_roundtrip == 0

    # Unsafe: width mismatch
    c_width = """\
void func() {
    tmp_x8 = local_20;
    local_20 = tmp_w8;
}
"""
    _, _, _, stats_w = simplify_expressions(c_width)
    assert stats_w.temp_copy_roundtrip == 0

    # Unsafe: identical var on both sides
    c_same = """\
void func() {
    local_20 = local_20;
    local_20 = local_20;
}
"""
    # Both lines are self-assignments (Category E), not roundtrips
    _, _, _, stats_s = simplify_expressions(c_same)
    assert stats_s.temp_copy_roundtrip == 0

    # Unsafe: boundary line in between
    c_boundary = """\
void func() {
    tmp_w8 = local_20;
    if (cond) {}
    local_20 = tmp_w8;
}
"""
    _, _, _, stats_b = simplify_expressions(c_boundary)
    assert stats_b.temp_copy_roundtrip == 0


def test_category_h_mask_cast_disabled_by_default():
    """Category H: mask-cast is disabled by default; not applied unless enabled."""
    c_in = """\
void func() {
    tmp_w8 = (u32)(u32)tmp_w8;
}
"""
    # Default: disabled
    c_out_default, _, _, stats_default = simplify_expressions(c_in, enable_mask_cast=False)
    assert stats_default.mask_cast == 0
    assert "(u32)(u32)tmp_w8" in c_out_default

    # Enabled: simplifies x = (T)(T)x; -> x = x;
    c_out_enabled, _, _, stats_enabled = simplify_expressions(c_in, enable_mask_cast=True)
    assert stats_enabled.mask_cast == 1
    assert "tmp_w8 = tmp_w8;" in c_out_enabled

    # rule_mask_cast directly: disabled
    assert rule_mask_cast("tmp_w8", "(u32)(u32)tmp_w8", enabled=False) is None

    # rule_mask_cast directly: enabled, same type double-cast
    result = rule_mask_cast("tmp_w8", "(u32)(u32)tmp_w8", enabled=True)
    assert result is not None
    assert result.new_expr == "tmp_w8"
    assert result.category == "mask_cast"

    # rule_mask_cast: different types should NOT simplify (outer != inner)
    assert rule_mask_cast("tmp_w8", "(u32)(u64)tmp_w8", enabled=True) is None

    # rule_mask_cast: LHS does not match inner operand
    assert rule_mask_cast("tmp_w9", "(u32)(u32)tmp_w8", enabled=True) is None

    # rule_mask_cast: unknown type not in safe set
    assert rule_mask_cast("tmp_w8", "(my_type)(my_type)tmp_w8", enabled=True) is None


def test_category_e_rhs_safety_gate():
    """Category E respects the safety gate: x = x is fine but complex forms are not."""
    # Self-assignment of simple identifier → should be removed (Category E)
    c_simple = """\
void func() {
    tmp_w8 = tmp_w8;
}
"""
    _, _, _, stats = simplify_expressions(c_simple)
    assert stats.self_assignment == 1

    # Non-simple RHS form should NOT trigger Category E (e.g., tmp = tmp + 0 goes to Category A)
    c_arithmetic = """\
void func() {
    tmp_w8 = tmp_w8 + 0;
}
"""
    _, _, _, stats2 = simplify_expressions(c_arithmetic)
    assert stats2.self_assignment == 0
    assert stats2.identity_arithmetic == 1
