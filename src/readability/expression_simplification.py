# -*- coding: utf-8 -*-
"""
Phase 7.3 Static Expression Simplification

Applies conservative, evidence-preserving simplifications to the code chunks
of recovered_readable.c.  This module is token-safe: it only touches
identifiers and expressions that appear in executable C code positions.
String literals, character literals, line comments, and block comments are
never modified.

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
    A — Identity arithmetic  (x + 0  ->  x,  x * 1  ->  x, etc.)
    B — Redundant parentheses on simple identifiers/literals
    C — Assignment RHS simplification  (x = x + 0;  ->  x = x;)
    D — Three-line copy-op-store folding  (conservative)
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any

from src.ir.source.c_tokens import split_c_line

logger = logging.getLogger("readability.expression_simplification")

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ExprSimplification:
    """One accepted simplification record."""
    site_id: str
    function: str
    line_number: int           # 1-indexed, relative to the whole file
    category: str              # identity_arithmetic | redundant_parentheses |
                               # assignment_rhs | copy_op_store
    old_text: str              # original line text (stripped)
    new_text: str              # simplified line text (stripped)
    reason: str
    evidence_preserved: bool
    confidence: str = "static_safe"


@dataclass
class ExprSimplificationStats:
    """Aggregate statistics for expression simplification."""
    sites_total: int = 0
    simplified: int = 0
    skipped: int = 0
    identity_arithmetic: int = 0
    redundant_parentheses: int = 0
    assignment_rhs: int = 0
    copy_op_store: int = 0


# ---------------------------------------------------------------------------
# Safe identifier / literal patterns
# ---------------------------------------------------------------------------

# A word-boundary identifier
_IDENT = r"[a-zA-Z_][a-zA-Z0-9_]*"

# A simple operand: identifier or integer literal with optional suffixes
_SIMPLE_OPERAND_RE = re.compile(
    r"^(?:[a-zA-Z_][a-zA-Z0-9_]*|0[xX][0-9a-fA-F]+|0[0-7]*|[1-9][0-9]*)(?:[uU]|[uU]ll|[uU]LL|[lL]l|[lL]L)?$"
)

# A "simple parenthesised expression": matches ( <identifier> ) or ( <int_lit> )
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

# C type keywords (to detect cast context and avoid mis-simplifying)
_C_TYPE_NAMES = frozenset({
    "u8", "u16", "u32", "u64", "i8", "i16", "i32", "i64",
    "uint8_t", "uint16_t", "uint32_t", "uint64_t",
    "int8_t", "int16_t", "int32_t", "int64_t",
    "char", "int", "float", "double", "long", "short",
    "void", "size_t", "uintptr_t", "intptr_t",
    "unsigned", "signed",
})

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

# Three-line copy-op-store patterns
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

# Control flow boundaries
_CONTROL_FLOW_BOUNDARY_RE = re.compile(
    r"""
    \b(if|else|while|for|do|switch|case|break|continue|goto|return)\b
    | /\*\s*(?:block|loop|branch|Entry|conditional|merge|if/else)\b
    | \b[a-zA-Z_]\w*\s*:                        # goto label
    """,
    re.VERBOSE,
)

# Exact identity constants lists
_ZERO_CONSTANTS = {"0", "0u", "0U", "0ull", "0ULL", "0ll", "0LL"}
_ONE_CONSTANTS = {"1", "1u", "1U", "1ull", "1ULL", "1ll", "1LL"}


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
    
    # Reconstruct the trailing comment (strip the /* */ markers for readability)
    trailing = ""
    if comment_parts:
        trailing = "".join(comment_parts).strip()
        if trailing.startswith("//"):
            trailing = trailing[2:].strip()
        elif trailing.startswith("/*") and trailing.endswith("*/"):
            trailing = trailing[2:-2].strip()
    return code_text, trailing, still_in_bc


def _is_simple_operand(text: str) -> bool:
    """Return True iff text is a bare identifier or bare integer literal (with suffixes)."""
    return bool(_SIMPLE_OPERAND_RE.match(text.strip()))


def _is_boundary_line(line: str) -> bool:
    """Return True if line is a control-flow or comment barrier."""
    stripped = line.strip()
    if not stripped:
        return True  # blank lines are boundaries
    if stripped.startswith("//") or stripped.startswith("/*"):
        return True
    if _CONTROL_FLOW_BOUNDARY_RE.search(line):
        return True
    return False


def _get_width_bits(name: str) -> Optional[int]:
    """Extract register width size (32 or 64) from variable name."""
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
    """
    Build evidence comment placing original comment first.
    """
    desc = f"{reason}: {old_rhs} -> {new_rhs}"
    if original_comment:
        return f"{original_comment}; {desc}"
    return desc


# ---------------------------------------------------------------------------
# RHS Gating & Safety Checks
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
        
    # Check for pointer dereferences: if '*' is present, it is ONLY allowed
    # if it's a Category A multiplication of 1.
    if "*" in rhs_stripped:
        # Check if it matches a valid multiplication of 1
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

    # Check for parentheses: ONLY allowed if it's a simple paren Category B match.
    if "(" in rhs_stripped or ")" in rhs_stripped:
        m_paren = _SIMPLE_PAREN_RE.match(rhs_stripped)
        if not m_paren:
            return False
        inner = m_paren.group("inner").strip()
        if inner in _C_TYPE_NAMES or inner.endswith("_t"):
            return False
            
    return True


# ---------------------------------------------------------------------------
# Category A — Identity Arithmetic
# ---------------------------------------------------------------------------

def _try_simplify_identity_arithmetic(expr: str) -> Optional[Tuple[str, str]]:
    """
    Simplify arithmetic expressions using exact identity constants.
    """
    expr = expr.strip()
    
    # Match binary expression
    m = re.match(r"^(.+?)\s*(<<|>>|[+\-*/|^])\s*(.+)$", expr)
    if not m:
        return None
    lhs = m.group(1).strip()
    op = m.group(2)
    rhs = m.group(3).strip()

    # Zero identity operators: +, -, |, ^, <<, >> (RHS is 0)
    if op in {"+", "-", "|", "^", "<<", ">>"}:
        if rhs in _ZERO_CONSTANTS and _is_simple_operand(lhs):
            return lhs, "simplified identity expression"
            
    # Commutative zero identity operators: +, |, ^ (LHS is 0)
    if op in {"+", "|", "^"}:
        if lhs in _ZERO_CONSTANTS and _is_simple_operand(rhs):
            return rhs, "simplified identity expression"

    # One identity operators: *, / (RHS is 1)
    if op in {"*", "/"}:
        if rhs in _ONE_CONSTANTS and _is_simple_operand(lhs):
            return lhs, "simplified identity expression"

    # Commutative one identity operator: * (LHS is 1)
    if op == "*":
        if lhs in _ONE_CONSTANTS and _is_simple_operand(rhs):
            return rhs, "simplified identity expression"

    return None


# ---------------------------------------------------------------------------
# Category B — Redundant Parentheses
# ---------------------------------------------------------------------------

def _try_simplify_parentheses(expr: str) -> Optional[Tuple[str, str]]:
    """
    Remove redundant parentheses around simple identifiers or literals.
    """
    expr = expr.strip()
    m = _SIMPLE_PAREN_RE.match(expr)
    if not m:
        return None
    inner = m.group("inner").strip()
    if inner in _C_TYPE_NAMES or inner.endswith("_t"):
        return None
    return inner, "simplified redundant parentheses"


# ---------------------------------------------------------------------------
# Single-line Statement Simplification
# ---------------------------------------------------------------------------

def _simplify_statement(
    stmt_code: str,
    comment: str,
) -> Optional[Tuple[str, str, str, bool]]:
    """
    Try to simplify a single assignment statement.
    """
    stmt = stmt_code.strip()
    if not stmt.endswith(";"):
        return None

    # We strictly enforce only simple assignment statements
    m = _ASSIGN_RE.match(stmt)
    if not m:
        return None

    lhs = m.group("lhs_ident")
    rhs = m.group("rhs").strip()

    # Gate RHS to make sure it contains no casts, pointers, array indexing, calls, etc.
    if not _is_rhs_safe(rhs):
        return None

    # Try Category A: identity arithmetic
    result = _try_simplify_identity_arithmetic(rhs)
    if result:
        new_rhs, reason = result
        new_stmt = f"{lhs} = {new_rhs};"
        return new_stmt, "identity_arithmetic", reason, True

    # Try Category B: redundant parentheses
    result = _try_simplify_parentheses(rhs)
    if result:
        new_rhs, reason = result
        new_stmt = f"{lhs} = {new_rhs};"
        return new_stmt, "redundant_parentheses", reason, True

    return None


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

    # No boundaries, comment lines, or blank lines inside/between
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

    # Width check
    w_tmp = _get_width_bits(tmp1)
    w_src = _get_width_bits(src)
    if w_tmp is not None and w_src is not None and w_tmp != w_src:
        return None

    # Region check: temp appears nowhere else in the 5 lines before or 5 lines after
    window_start = max(0, start_idx - 5)
    window_end = min(len(lines), start_idx + 3 + 5)
    for idx in range(window_start, window_end):
        if start_idx <= idx <= start_idx + 2:
            continue
        line_code, _, _ = _extract_code_text(lines[idx])
        if not line_code:
            continue
        # Token-safe word check
        chunks, _ = split_c_line(lines[idx], False)
        for kind, text in chunks:
            if kind == "code":
                if re.search(r'\b' + re.escape(tmp1) + r'\b', text):
                    return None

    # Clean trailing comments
    comments = [comment1, comment2, comment3]
    evidence_comments = [c.strip() for c in comments if c.strip()]
    combined_comment = "; ".join(evidence_comments) if evidence_comments else ""
    if len(combined_comment) > 120:
        return None

    new_stmt = f"{dst} = {dst} {op} {const};"
    reason = f"copy-op-store fold: {tmp1} = {src}; {tmp1} = {tmp1} {op} {const}; {dst} = {tmp1};"

    return start_idx + 2, new_stmt, reason, combined_comment


# ---------------------------------------------------------------------------
# Main Simplification Pass
# ---------------------------------------------------------------------------

def simplify_expressions(
    c_content: str,
    enable_copy_op_store: bool = True,
    _site_counter_start: int = 1,
) -> Tuple[str, List[ExprSimplification], List[Dict[str, Any]], ExprSimplificationStats]:
    """
    Simplify expressions in c_content (token-safely).
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

        i = 0
        while i < len(lines):
            raw = lines[i]
            line_num = file_line_offset + i + 1

            code, comment, _ = _extract_code_text(raw)

            if not code:
                new_lines.append(raw)
                i += 1
                continue

            # Skip lines with boundary elements
            if _is_boundary_line(raw):
                new_lines.append(raw)
                i += 1
                continue

            # Category D: copy-op-store
            if enable_copy_op_store:
                cos_res = _try_copy_op_store(lines, i)
                if cos_res is not None:
                    end_idx, new_stmt, reason, cos_comment = cos_res
                    stats.sites_total += 1
                    
                    orig_texts = [lines[j].strip() for j in range(i, end_idx + 1)]
                    
                    # Trailing comment formatting
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

            # Categories A, B, C (single assignment RHS)
            result = _simplify_statement(code, comment)
            if result is None:
                new_lines.append(raw)
                i += 1
                continue

            new_code, category, reason, evidence_preserved = result
            stats.sites_total += 1

            # Format evidence comment placing original comment first
            m = _ASSIGN_RE.match(code.strip())
            old_rhs = m.group("rhs").strip() if m else code
            m_new = _ASSIGN_RE.match(new_code.strip())
            new_rhs = m_new.group("rhs").strip() if m_new else new_code
            
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
        },
    }
