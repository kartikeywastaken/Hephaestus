# -*- coding: utf-8 -*-
"""
Phase 7.3 / 7.3.1 Static Expression Simplification

Orchestration layer.  Individual rule logic lives in expression_rules.py.
Data models live in expression_models.py.

This module is token-safe: it only touches identifiers and expressions that
appear in executable C code positions.  String literals, character literals,
line comments, and block comments are never modified.

Core rule:
    Missing evidence is acceptable.
    Fabricated evidence is not.

This module may SKIP a simplification freely; it must NEVER introduce
incorrect code or destroy evidence.

Pipeline position:
    After compile-shape hardening.
    Before the final compile-shape safety pass.
    Before clang -fsyntax-only gate.

Simplification categories:
    A — Identity arithmetic     (x + 0  ->  x,  x * 1  ->  x, etc.)
    B — Redundant parentheses   ((ident) -> ident)
    C — Assignment RHS gating   (restricts A/B/E/F/H to simple assignment RHS)
    D — Copy-op-store folding   (three consecutive lines, conservative)
    E — Self-assignment removal (x = x;  -> evidence comment)
    F — Double parentheses      (((ident)) -> ident)
    G — Temp copy roundtrip     (tmp = x; x = tmp; -> removed with evidence)
    H — Mask-cast               (disabled by default; --enable-mask-cast-simplification)
"""

from __future__ import annotations

import re
import logging
from typing import List, Dict, Tuple, Optional, Any

from src.ir.source.c_tokens import split_c_line

# Re-export models so existing imports from this module continue to work.
from src.readability.expression_models import (  # noqa: F401  (re-exported)
    RuleResult,
    ExprSimplification,
    ExprSimplificationStats,
)

from src.readability.expression_rules import (
    rule_identity_arithmetic,
    rule_redundant_parentheses,
    rule_self_assignment,
    rule_double_parentheses,
    rule_temp_copy_roundtrip,
    rule_mask_cast,
)

logger = logging.getLogger("readability.expression_simplification")


# ---------------------------------------------------------------------------
# Patterns used only by the orchestration layer
# ---------------------------------------------------------------------------

_IDENT = r"[a-zA-Z_][a-zA-Z0-9_]*"

# C type keywords (to detect cast context)
_C_TYPE_NAMES = frozenset({
    "u8", "u16", "u32", "u64", "i8", "i16", "i32", "i64",
    "uint8_t", "uint16_t", "uint32_t", "uint64_t",
    "int8_t", "int16_t", "int32_t", "int64_t",
    "char", "int", "float", "double", "long", "short",
    "void", "size_t", "uintptr_t", "intptr_t",
    "unsigned", "signed",
})

# For exact identity constant detection (used in _is_rhs_safe)
_ONE_CONSTANTS = {"1", "1u", "1U", "1ull", "1ULL", "1ll", "1LL"}

# Simple parenthesised expression: ( ident ) or ( int_lit )
_SIMPLE_PAREN_RE = re.compile(
    r"""^
    \(                              # opening paren
    \s*
    (?P<inner>[a-zA-Z_][a-zA-Z0-9_]*|0[xX][0-9a-fA-F]+|0[0-7]*|[1-9][0-9]*)(?:[uU]|[uU]ll|[uU]LL|[lL]l|[lL]L)?
    \s*
    \)                              # closing paren
    $""",
    re.VERBOSE,
)

# Assignment pattern:  <lhs_ident>  =  <rhs_expr> ;
_ASSIGN_RE = re.compile(
    r"""^
    (?P<lhs_ident>[a-zA-Z_][a-zA-Z0-9_]*)   # single identifier on LHS
    \s*=\s*
    (?P<rhs>.+?)
    ;
    $""",
    re.VERBOSE | re.DOTALL,
)

# Three-line copy-op-store patterns (Category D)
_COS_LINE1_RE = re.compile(
    r"""^
    (?P<tmp>[a-zA-Z_][a-zA-Z0-9_]*)
    \s*=\s*
    (?P<src>[a-zA-Z_][a-zA-Z0-9_]*)
    ;
    $""",
    re.VERBOSE,
)
_COS_LINE2_RE = re.compile(
    r"""^
    (?P<tmp>[a-zA-Z_][a-zA-Z0-9_]*)
    \s*=\s*
    (?P<tmp2>[a-zA-Z_][a-zA-Z0-9_]*)
    \s*
    (?P<op>[+\-|^&])
    \s*
    (?P<const>(?:0[xX][0-9a-fA-F]+|0[0-7]*|[1-9][0-9]*|\d+)(?:[uU]|[uU]ll|[uU]LL|[lL]l|[lL]L)?)
    ;
    $""",
    re.VERBOSE,
)
_COS_LINE3_RE = re.compile(
    r"""^
    (?P<dst>[a-zA-Z_][a-zA-Z0-9_]*)
    \s*=\s*
    (?P<tmp>[a-zA-Z_][a-zA-Z0-9_]*)
    ;
    $""",
    re.VERBOSE,
)

# Control flow boundary detector
_CONTROL_FLOW_BOUNDARY_RE = re.compile(
    r"""
    \b(if|else|while|for|do|switch|case|break|continue|goto|return)\b
    | /\*\s*(?:block|loop|branch|Entry|conditional|merge|if/else)\b
    | \b[a-zA-Z_]\w*\s*:                        # goto label
    """,
    re.VERBOSE,
)

# Simple operand pattern (identifier or integer literal with optional suffixes)
_SIMPLE_OPERAND_RE = re.compile(
    r"^(?:[a-zA-Z_][a-zA-Z0-9_]*|0[xX][0-9a-fA-F]+|0[0-7]*|[1-9][0-9]*)(?:[uU]|[uU]ll|[uU]LL|[lL]l|[lL]L)?$"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_code_text(line: str) -> Tuple[str, str, bool]:
    """
    Split a C source line into (code_text, trailing_comment, inside_block_comment).
    """
    chunks, still_in_bc = split_c_line(line, False)
    code_parts = []
    comment_parts = []
    for kind, text in chunks:
        if kind == "code":
            code_parts.append(text)
        elif kind == "comment":
            comment_parts.append(text)
    code_text = "".join(code_parts).strip()

    trailing = ""
    if comment_parts:
        trailing = "".join(comment_parts).strip()
        if trailing.startswith("//"):
            trailing = trailing[2:].strip()
        elif trailing.startswith("/*") and trailing.endswith("*/"):
            trailing = trailing[2:-2].strip()
    return code_text, trailing, still_in_bc


def _is_simple_operand(text: str) -> bool:
    return bool(_SIMPLE_OPERAND_RE.match(text.strip()))


def _is_boundary_line(line: str) -> bool:
    """Return True if line is a control-flow or comment barrier."""
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith("//") or stripped.startswith("/*"):
        return True
    if _CONTROL_FLOW_BOUNDARY_RE.search(line):
        return True
    return False


def _get_width_bits(name: str) -> Optional[int]:
    if re.search(r'\b(?:tmp|temp)_w\d+\b', name) or re.search(r'\b[wW]\d+\b', name):
        return 32
    if re.search(r'\b(?:tmp|temp)_x\d+\b', name) or re.search(r'\b[xX]\d+\b', name):
        return 64
    return None


def _rebuild_line_with_new_code(original_line: str, new_code: str, evidence: str) -> str:
    """Rebuild line with new code and trailing comment if any."""
    leading_ws = len(original_line) - len(original_line.lstrip())
    indent = original_line[:leading_ws]
    if evidence:
        return f"{indent}{new_code} /* {evidence} */\n"
    return f"{indent}{new_code}\n"


def _make_evidence_comment(original_comment: str, reason: str, old_rhs: str, new_rhs: str) -> str:
    """Build evidence comment placing original comment first."""
    desc = f"{reason}: {old_rhs} -> {new_rhs}"
    if original_comment:
        return f"{original_comment}; {desc}"
    return desc


# ---------------------------------------------------------------------------
# RHS Gating & Safety Checks (Category C gate)
# ---------------------------------------------------------------------------

def _is_rhs_safe(rhs: str) -> bool:
    """
    Perform strict safety checks to prevent rewriting inside casts, pointers,
    array indexing, function calls, macros, helpers, etc.
    """
    rhs_stripped = rhs.strip()

    if "->" in rhs_stripped:
        return False
    if "[" in rhs_stripped or "]" in rhs_stripped:
        return False
    if re.search(r'\b[a-zA-Z_]\w*\s*\(', rhs_stripped):
        return False

    # Check for pointer dereferences: * is ONLY allowed if it's a Category A
    # multiplication of 1.
    if "*" in rhs_stripped:
        m_mul = re.match(r"^(.+?)\s*\*\s*(.+)$", rhs_stripped)
        if not m_mul:
            return False
        lhs_part = m_mul.group(1).strip()
        rhs_part = m_mul.group(2).strip()
        is_valid_mul = (
            (lhs_part in _ONE_CONSTANTS and _is_simple_operand(rhs_part)) or
            (rhs_part in _ONE_CONSTANTS and _is_simple_operand(lhs_part))
        )
        if not is_valid_mul:
            return False

    # Check for parentheses: ONLY allowed if it's a simple paren or double paren match
    if "(" in rhs_stripped or ")" in rhs_stripped:
        # Allow single-level paren
        m_paren = _SIMPLE_PAREN_RE.match(rhs_stripped)
        if m_paren:
            inner = m_paren.group("inner").strip()
            if inner in _C_TYPE_NAMES or inner.endswith("_t"):
                return False
        else:
            # Allow double-level paren (Category F)
            from src.readability.expression_rules import _DOUBLE_PAREN_RE
            m_double = _DOUBLE_PAREN_RE.match(rhs_stripped)
            if m_double:
                inner = m_double.group("inner").strip()
                if inner in _C_TYPE_NAMES or inner.endswith("_t"):
                    return False
            else:
                # Allow mask-cast pattern: (type)(type)ident
                m_mask = re.match(
                    r'^\([a-zA-Z_][a-zA-Z0-9_]*\)\s*\([a-zA-Z_][a-zA-Z0-9_]*\)\s*[a-zA-Z_][a-zA-Z0-9_]*$',
                    rhs_stripped,
                )
                if not m_mask:
                    return False

    return True


# ---------------------------------------------------------------------------
# Category D — Three-Line Copy-Op-Store
# ---------------------------------------------------------------------------

def _try_copy_op_store(
    lines: List[str],
    start_idx: int,
) -> Optional[Tuple[int, str, str, str]]:
    """
    Strict detection and folding of consecutive three-line copy-op-store.
    """
    if start_idx + 2 >= len(lines):
        return None

    raw1 = lines[start_idx]
    raw2 = lines[start_idx + 1]
    raw3 = lines[start_idx + 2]

    if _is_boundary_line(raw1) or _is_boundary_line(raw2) or _is_boundary_line(raw3):
        return None

    c1, comment1, bc1 = _extract_code_text(raw1)
    c2, comment2, bc2 = _extract_code_text(raw2)
    c3, comment3, bc3 = _extract_code_text(raw3)

    if not (c1 and c2 and c3):
        return None
    if bc1 or bc2 or bc3:
        return None

    m1 = _COS_LINE1_RE.match(c1)
    m2 = _COS_LINE2_RE.match(c2)
    m3 = _COS_LINE3_RE.match(c3)

    if not (m1 and m2 and m3):
        return None

    tmp1 = m1.group("tmp")
    src = m1.group("src")
    tmp2 = m2.group("tmp")
    tmp2b = m2.group("tmp2")
    op = m2.group("op")
    const = m2.group("const")
    dst = m3.group("dst")
    tmp3 = m3.group("tmp")

    if not (tmp1 == tmp2 == tmp2b == tmp3):
        return None
    if src != dst:
        return None
    if tmp1 == src:
        return None

    w_tmp = _get_width_bits(tmp1)
    w_src = _get_width_bits(src)
    if w_tmp is not None and w_src is not None and w_tmp != w_src:
        return None

    # Region check: temp appears nowhere else in the 5 lines before or after
    window_start = max(0, start_idx - 5)
    window_end = min(len(lines), start_idx + 3 + 5)
    for idx in range(window_start, window_end):
        if start_idx <= idx <= start_idx + 2:
            continue
        line_code, _, _ = _extract_code_text(lines[idx])
        if not line_code:
            continue
        chunks, _ = split_c_line(lines[idx], False)
        for kind, text in chunks:
            if kind == "code":
                if re.search(r'\b' + re.escape(tmp1) + r'\b', text):
                    return None

    comments = [comment1, comment2, comment3]
    evidence_comments = [c.strip() for c in comments if c.strip()]
    combined_comment = "; ".join(evidence_comments) if evidence_comments else ""
    if len(combined_comment) > 120:
        return None

    new_stmt = f"{dst} = {dst} {op} {const};"
    reason = f"copy-op-store fold: {tmp1} = {src}; {tmp1} = {tmp1} {op} {const}; {dst} = {tmp1};"

    return start_idx + 2, new_stmt, reason, combined_comment


# ---------------------------------------------------------------------------
# Region checker helper (used by Category G via expression_rules)
# ---------------------------------------------------------------------------

def _make_region_checker(lines: List[str]):
    """
    Return a region-checker function compatible with rule_temp_copy_roundtrip.
    Returns True if tmp is NOT found in the surrounding 5-line window.
    """
    def _check(tmp: str, start: int, end: int) -> bool:
        window_start = max(0, start - 5)
        window_end = min(len(lines), end + 1 + 5)
        for idx in range(window_start, window_end):
            if start <= idx <= end:
                continue
            chunks, _ = split_c_line(lines[idx], False)
            for kind, text in chunks:
                if kind == "code":
                    if re.search(r'\b' + re.escape(tmp) + r'\b', text):
                        return False
        return True
    return _check


# ---------------------------------------------------------------------------
# Single-line Statement Simplification (Categories A, B, C, E, F, H)
# ---------------------------------------------------------------------------

def _simplify_statement(
    stmt_code: str,
    comment: str,
    enable_mask_cast: bool = False,
) -> Optional[Tuple[str, str, str, bool]]:
    """
    Try to simplify a single assignment statement.

    Returns (new_code, category, reason, evidence_preserved) or None.
    new_code == "" signals line removal (Category E self-assignment).
    """
    stmt = stmt_code.strip()
    if not stmt.endswith(";"):
        return None

    m = _ASSIGN_RE.match(stmt)
    if not m:
        return None

    lhs = m.group("lhs_ident")
    rhs = m.group("rhs").strip()

    # Category E: self-assignment (before RHS safety gate — it's always safe)
    e_result = rule_self_assignment(lhs, rhs)
    if e_result is not None:
        return "", e_result.category, e_result.reason, e_result.evidence_preserved

    # Gate RHS to make sure it contains no casts, pointers, array indexing, calls, etc.
    if not _is_rhs_safe(rhs):
        return None

    # Category A: identity arithmetic
    a_result = rule_identity_arithmetic(rhs)
    if a_result is not None:
        new_stmt = f"{lhs} = {a_result.new_expr};"
        return new_stmt, a_result.category, a_result.reason, a_result.evidence_preserved

    # Category B: redundant parentheses
    b_result = rule_redundant_parentheses(rhs)
    if b_result is not None:
        new_stmt = f"{lhs} = {b_result.new_expr};"
        return new_stmt, b_result.category, b_result.reason, b_result.evidence_preserved

    # Category F: double parentheses
    f_result = rule_double_parentheses(rhs)
    if f_result is not None:
        new_stmt = f"{lhs} = {f_result.new_expr};"
        return new_stmt, f_result.category, f_result.reason, f_result.evidence_preserved

    # Category H: mask-cast (flag-gated)
    h_result = rule_mask_cast(lhs, rhs, enabled=enable_mask_cast)
    if h_result is not None:
        new_stmt = f"{lhs} = {h_result.new_expr};"
        return new_stmt, h_result.category, h_result.reason, h_result.evidence_preserved

    return None


# ---------------------------------------------------------------------------
# Main Simplification Pass
# ---------------------------------------------------------------------------

def simplify_expressions(
    c_content: str,
    enable_copy_op_store: bool = True,
    enable_mask_cast: bool = False,
    _site_counter_start: int = 1,
) -> Tuple[str, List[ExprSimplification], List[Dict[str, Any]], ExprSimplificationStats]:
    """
    Simplify expressions in c_content (token-safely).

    Returns:
        (new_c_content, simplifications, skipped_list, stats)
    """
    from src.readability.symbol_promotion import parse_c_into_functions

    stats = ExprSimplificationStats()
    simplifications: List[ExprSimplification] = []
    skipped_list: List[Dict[str, Any]] = []

    site_counter = _site_counter_start

    def next_site_id() -> str:
        nonlocal site_counter
        sid = f"expr_{site_counter:06d}"
        site_counter += 1
        return sid

    blocks = parse_c_into_functions(c_content)
    output_blocks: List[str] = []

    for block in blocks:
        if block["type"] != "function":
            output_blocks.append("".join(block["lines"]))
            continue

        fn_name = block["name"]
        lines = block["lines"]
        new_lines: List[str] = []
        file_line_offset = block.get("start_line", 0)

        region_checker = _make_region_checker(lines)

        i = 0
        while i < len(lines):
            raw = lines[i]
            line_num = file_line_offset + i + 1

            code, comment, _ = _extract_code_text(raw)

            if not code:
                new_lines.append(raw)
                i += 1
                continue

            if _is_boundary_line(raw):
                new_lines.append(raw)
                i += 1
                continue

            # ----------------------------------------------------------------
            # Category D: three-line copy-op-store
            # ----------------------------------------------------------------
            if enable_copy_op_store:
                cos_res = _try_copy_op_store(lines, i)
                if cos_res is not None:
                    end_idx, new_stmt, reason, cos_comment = cos_res
                    stats.sites_total += 1

                    orig_texts = [lines[j].strip() for j in range(i, end_idx + 1)]

                    if cos_comment:
                        evidence_str = f"{cos_comment}; simplified copy-op-store"
                    else:
                        evidence_str = "simplified copy-op-store"

                    new_raw = _rebuild_line_with_new_code(raw, new_stmt, evidence_str)
                    sid = next_site_id()
                    simplifications.append(ExprSimplification(
                        site_id=sid,
                        function=fn_name,
                        line_number=line_num,
                        category="copy_op_store",
                        old_text=orig_texts[0],
                        new_text=new_stmt,
                        reason=reason,
                        evidence_preserved=True,
                    ))
                    stats.simplified += 1
                    stats.copy_op_store += 1

                    new_lines.append(new_raw)
                    i = end_idx + 1
                    continue

            # ----------------------------------------------------------------
            # Category G: two-line temp copy roundtrip
            # ----------------------------------------------------------------
            g_res = rule_temp_copy_roundtrip(
                lines, i,
                code_extractor=_extract_code_text,
                region_checker=region_checker,
                boundary_checker=_is_boundary_line,
            )
            if g_res is not None:
                stats.sites_total += 1
                sid = next_site_id()
                orig_text = lines[i].strip()

                # Build evidence comment line from the two removed lines
                evidence_parts = [g_res.new_expr] if g_res.new_expr else []
                evidence_parts.append(g_res.reason)
                evidence_str = "; ".join(p for p in evidence_parts if p)

                leading_ws = len(raw) - len(raw.lstrip())
                indent = raw[:leading_ws]
                evidence_line = f"{indent}/* {evidence_str} */\n"

                simplifications.append(ExprSimplification(
                    site_id=sid,
                    function=fn_name,
                    line_number=line_num,
                    category="temp_copy_roundtrip",
                    old_text=orig_text,
                    new_text="",   # both lines removed
                    reason=g_res.reason,
                    evidence_preserved=True,
                ))
                stats.simplified += 1
                stats.temp_copy_roundtrip += 1

                new_lines.append(evidence_line)
                i += 1 + g_res.lines_consumed  # skip both lines
                continue

            # ----------------------------------------------------------------
            # Categories A, B, C, E, F, H — single-line assignment
            # ----------------------------------------------------------------
            result = _simplify_statement(code, comment, enable_mask_cast=enable_mask_cast)
            if result is None:
                new_lines.append(raw)
                i += 1
                continue

            new_code, category, reason, evidence_preserved = result
            stats.sites_total += 1

            m_assign = _ASSIGN_RE.match(code.strip())
            old_rhs = m_assign.group("rhs").strip() if m_assign else code
            if new_code:
                m_new = _ASSIGN_RE.match(new_code.strip())
                new_rhs = m_new.group("rhs").strip() if m_new else new_code
            else:
                new_rhs = ""

            # Category E: self-assignment — replace with evidence comment line
            if category == "self_assignment":
                leading_ws = len(raw) - len(raw.lstrip())
                indent = raw[:leading_ws]
                ev = f"{comment}; {reason}" if comment else reason
                evidence_line = f"{indent}/* {ev} */\n"

                sid = next_site_id()
                simplifications.append(ExprSimplification(
                    site_id=sid,
                    function=fn_name,
                    line_number=line_num,
                    category=category,
                    old_text=code.strip(),
                    new_text="",
                    reason=reason,
                    evidence_preserved=evidence_preserved,
                ))
                stats.simplified += 1
                stats.self_assignment += 1
                new_lines.append(evidence_line)
                i += 1
                continue

            evidence_str = _make_evidence_comment(comment, reason, old_rhs, new_rhs)
            new_raw = _rebuild_line_with_new_code(raw, new_code, evidence_str)

            sid = next_site_id()
            simplifications.append(ExprSimplification(
                site_id=sid,
                function=fn_name,
                line_number=line_num,
                category=category,
                old_text=code.strip(),
                new_text=new_code.strip(),
                reason=reason,
                evidence_preserved=evidence_preserved,
            ))
            stats.simplified += 1
            if category == "identity_arithmetic":
                stats.identity_arithmetic += 1
                stats.assignment_rhs += 1
            elif category == "redundant_parentheses":
                stats.redundant_parentheses += 1
                stats.assignment_rhs += 1
            elif category == "double_parentheses":
                stats.double_parentheses += 1
                stats.assignment_rhs += 1
            elif category == "mask_cast":
                stats.mask_cast += 1
                stats.assignment_rhs += 1

            new_lines.append(new_raw)
            i += 1

        output_blocks.append("".join(new_lines))

    return "".join(output_blocks), simplifications, skipped_list, stats


def build_expression_simplification_report_data(
    simplifications: List[ExprSimplification],
    skipped_list: List[Dict[str, Any]],
    stats: ExprSimplificationStats,
    enabled: bool = True,
    status: str = "ok",
) -> Dict[str, Any]:
    """
    Build the expression_simplification section for the readability report.
    """
    return {
        "enabled": enabled,
        "status": status,
        "sites_total": stats.sites_total,
        "simplified": stats.simplified,
        "skipped": stats.skipped,
        "categories": {
            "identity_arithmetic": stats.identity_arithmetic,
            "redundant_parentheses": stats.redundant_parentheses,
            "assignment_rhs": stats.assignment_rhs,
            "copy_op_store": stats.copy_op_store,
            "self_assignment": stats.self_assignment,
            "double_parentheses": stats.double_parentheses,
            "temp_copy_roundtrip": stats.temp_copy_roundtrip,
            "mask_cast": stats.mask_cast,
        },
    }
