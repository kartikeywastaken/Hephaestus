# -*- coding: utf-8 -*-
"""
Phase 7.3.1 Expression Simplification Rules

Each public function in this module implements exactly one simplification
category and returns Optional[RuleResult].  All rules must be:

  - Token-safe  : operate only on pre-extracted code text, never raw strings
                  that might contain comments or string literals.
  - Conservative: prefer returning None over guessing.
  - Evidence-preserving: never silently discard information.

Category summary:
    A — Identity arithmetic        (x + 0  ->  x,  x * 1  ->  x, etc.)
    B — Redundant parentheses      ((ident) -> ident)
    E — Self-assignment removal    (x = x;  ->  removed with evidence comment)
    F — Double parentheses         (((ident)) -> ident)
    G — Temp copy roundtrip        (tmp = x; x = tmp; -> removed with evidence)
    H — Mask-cast simplification   (disabled by default; flag-gated)
"""

from __future__ import annotations

import re
import logging
from typing import List, Optional, Tuple

from src.readability.expression_models import RuleResult

logger = logging.getLogger("readability.expression_rules")

# ---------------------------------------------------------------------------
# Shared constants and patterns (used across multiple rules)
# ---------------------------------------------------------------------------

_IDENT = r"[a-zA-Z_][a-zA-Z0-9_]*"

_SIMPLE_OPERAND_RE = re.compile(
    r"^(?:[a-zA-Z_][a-zA-Z0-9_]*|0[xX][0-9a-fA-F]+|0[0-7]*|[1-9][0-9]*)(?:[uU]|[uU]ll|[uU]LL|[lL]l|[lL]L)?$"
)

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

# Double-wrap: (( ident )) — exactly two paren levels, inner is simple operand
_DOUBLE_PAREN_RE = re.compile(
    r"""^
    \(\s*                           # outer opening
    \(\s*                           # inner opening
    (?P<inner>[a-zA-Z_][a-zA-Z0-9_]*|0[xX][0-9a-fA-F]+|0[0-7]*|[1-9][0-9]*)(?:[uU]|[uU]ll|[uU]LL|[lL]l|[lL]L)?
    \s*\)                           # inner closing
    \s*\)                           # outer closing
    $""",
    re.VERBOSE,
)

# C type keywords that may appear inside parentheses (cast context)
_C_TYPE_NAMES = frozenset({
    "u8", "u16", "u32", "u64", "i8", "i16", "i32", "i64",
    "uint8_t", "uint16_t", "uint32_t", "uint64_t",
    "int8_t", "int16_t", "int32_t", "int64_t",
    "char", "int", "float", "double", "long", "short",
    "void", "size_t", "uintptr_t", "intptr_t",
    "unsigned", "signed",
})

# Exact identity constants (case-sensitive, no others accepted)
_ZERO_CONSTANTS = {"0", "0u", "0U", "0ull", "0ULL", "0ll", "0LL"}
_ONE_CONSTANTS = {"1", "1u", "1U", "1ull", "1ULL", "1ll", "1LL"}

# Known safe mask-cast type names (width-preserving casts only)
_MASK_CAST_TYPES = frozenset({
    "u8", "u16", "u32", "u64",
    "uint8_t", "uint16_t", "uint32_t", "uint64_t",
})

_MASK_CAST_WIDTHS = {
    "u8": 8, "uint8_t": 8,
    "u16": 16, "uint16_t": 16,
    "u32": 32, "uint32_t": 32,
    "u64": 64, "uint64_t": 64,
}

# Two-line copy-op-store patterns (reused for Category G detection)
_COPY_LINE_RE = re.compile(
    r"""^
    (?P<dst>[a-zA-Z_][a-zA-Z0-9_]*)
    \s*=\s*
    (?P<src>[a-zA-Z_][a-zA-Z0-9_]*)
    ;
    $""",
    re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_simple_operand(text: str) -> bool:
    return bool(_SIMPLE_OPERAND_RE.match(text.strip()))


def _is_cast_type(name: str) -> bool:
    return name in _C_TYPE_NAMES or name.endswith("_t")


def _get_width_bits(name: str) -> Optional[int]:
    """Extract register width (32 or 64) from variable name suffix."""
    if re.search(r'\b(?:tmp|temp)_w\d+\b', name) or re.search(r'\b[wW]\d+\b', name):
        return 32
    if re.search(r'\b(?:tmp|temp)_x\d+\b', name) or re.search(r'\b[xX]\d+\b', name):
        return 64
    return None


# ---------------------------------------------------------------------------
# Category A — Identity Arithmetic
# ---------------------------------------------------------------------------

def rule_identity_arithmetic(expr: str) -> Optional[RuleResult]:
    """
    Simplify arithmetic expressions using exact identity constants.

    Supported:
        x + 0, x - 0, x | 0, x ^ 0, x << 0, x >> 0  ->  x
        0 + x, 0 | x, 0 ^ x                           ->  x
        x * 1, x / 1                                  ->  x
        1 * x                                          ->  x
    """
    expr = expr.strip()

    m = re.match(r"^(.+?)\s*(<<|>>|[+\-*/|^])\s*(.+)$", expr)
    if not m:
        return None
    lhs = m.group(1).strip()
    op = m.group(2)
    rhs = m.group(3).strip()

    # Zero identity: RHS is zero constant
    if op in {"+", "-", "|", "^", "<<", ">>"}:
        if rhs in _ZERO_CONSTANTS and _is_simple_operand(lhs):
            return RuleResult(
                new_expr=lhs,
                reason="simplified identity expression",
                category="identity_arithmetic",
            )

    # Commutative zero identity: LHS is zero constant
    if op in {"+", "|", "^"}:
        if lhs in _ZERO_CONSTANTS and _is_simple_operand(rhs):
            return RuleResult(
                new_expr=rhs,
                reason="simplified identity expression",
                category="identity_arithmetic",
            )

    # One identity: RHS is one constant
    if op in {"*", "/"}:
        if rhs in _ONE_CONSTANTS and _is_simple_operand(lhs):
            return RuleResult(
                new_expr=lhs,
                reason="simplified identity expression",
                category="identity_arithmetic",
            )

    # Commutative one identity: LHS is one constant
    if op == "*":
        if lhs in _ONE_CONSTANTS and _is_simple_operand(rhs):
            return RuleResult(
                new_expr=rhs,
                reason="simplified identity expression",
                category="identity_arithmetic",
            )

    return None


# ---------------------------------------------------------------------------
# Category B — Redundant Parentheses (single level)
# ---------------------------------------------------------------------------

def rule_redundant_parentheses(expr: str) -> Optional[RuleResult]:
    """
    Remove single-level redundant parentheses around a simple operand.

    (ident)  ->  ident
    (42)     ->  42

    Never removes if the inner token is a C type name (would be a cast).
    """
    expr = expr.strip()
    m = _SIMPLE_PAREN_RE.match(expr)
    if not m:
        return None
    inner = m.group("inner").strip()
    if _is_cast_type(inner):
        return None
    return RuleResult(
        new_expr=inner,
        reason="simplified redundant parentheses",
        category="redundant_parentheses",
    )


# ---------------------------------------------------------------------------
# Category E — Self-Assignment Removal
# ---------------------------------------------------------------------------

def rule_self_assignment(lhs: str, rhs: str) -> Optional[RuleResult]:
    """
    Detect and remove trivial self-assignments: x = x;

    Returns a RuleResult with new_expr="" to signal line removal.
    The orchestrator is responsible for replacing the line with an evidence comment.

    Gate:
      - Both sides must be exactly the same bare identifier.
      - We do not handle x = (x); or x = x + 0; (those are other rules).
    """
    lhs = lhs.strip()
    rhs = rhs.strip()

    if not _is_simple_operand(lhs):
        return None
    if lhs != rhs:
        return None

    return RuleResult(
        new_expr="",          # empty => remove line
        reason="self-assignment removed",
        category="self_assignment",
    )


# ---------------------------------------------------------------------------
# Category F — Double Parentheses Collapse
# ---------------------------------------------------------------------------

def rule_double_parentheses(expr: str) -> Optional[RuleResult]:
    """
    Collapse two levels of redundant parentheses around a simple operand.

    ((ident))  ->  ident
    ((42))     ->  42

    Requires exactly two wrapping levels and a simple inner operand.
    Never collapses if inner token is a type name.
    """
    expr = expr.strip()
    m = _DOUBLE_PAREN_RE.match(expr)
    if not m:
        return None
    inner = m.group("inner").strip()
    if _is_cast_type(inner):
        return None
    return RuleResult(
        new_expr=inner,
        reason="simplified double parentheses",
        category="double_parentheses",
    )


# ---------------------------------------------------------------------------
# Category G — Temp Copy Roundtrip (two consecutive lines)
# ---------------------------------------------------------------------------

def rule_temp_copy_roundtrip(
    lines: List[str],
    start_idx: int,
    code_extractor,       # callable(raw_line) -> (code_text, comment, in_block_comment)
    region_checker,       # callable(tmp_name, lines, start, end) -> bool  (True = safe)
    boundary_checker,     # callable(raw_line) -> bool  (True = is boundary)
) -> Optional[RuleResult]:
    """
    Detect and fold two-line temp copy roundtrip patterns:

        Line N:   tmp = src;
        Line N+1: src = tmp;

    Both lines are removed and replaced with an evidence comment on one line.

    Strict conditions:
      - Both lines must be consecutive with no boundaries between them.
      - tmp and src must be distinct bare identifiers.
      - Width prefixes must be compatible (both w, both x, or both unknown).
      - tmp must not appear in the 5 lines before or 5 lines after the window
        (region check using the caller-supplied checker).
    """
    if start_idx + 1 >= len(lines):
        return None

    raw1 = lines[start_idx]
    raw2 = lines[start_idx + 1]

    if boundary_checker(raw1) or boundary_checker(raw2):
        return None

    c1, comment1, bc1 = code_extractor(raw1)
    c2, comment2, bc2 = code_extractor(raw2)

    if not (c1 and c2):
        return None
    if bc1 or bc2:
        return None

    m1 = _COPY_LINE_RE.match(c1)
    m2 = _COPY_LINE_RE.match(c2)
    if not (m1 and m2):
        return None

    tmp = m1.group("dst")
    src = m1.group("src")

    # Line 2 must be: src = tmp;
    dst2 = m2.group("dst")
    src2 = m2.group("src")

    if dst2 != src or src2 != tmp:
        return None
    if tmp == src:
        return None

    # Width check
    w_tmp = _get_width_bits(tmp)
    w_src = _get_width_bits(src)
    if w_tmp is not None and w_src is not None and w_tmp != w_src:
        return None

    # Region check: tmp must not appear outside the two-line window
    if not region_checker(tmp, start_idx, start_idx + 1):
        return None

    # Combine evidence comments
    comments = [c for c in [comment1.strip(), comment2.strip()] if c]
    combined = "; ".join(comments) if comments else ""

    reason = f"temp copy roundtrip removed: {tmp} = {src}; {src} = {tmp};"

    return RuleResult(
        new_expr=combined,    # empty string or original comments — used in evidence
        reason=reason,
        category="temp_copy_roundtrip",
        lines_consumed=1,     # consumed one additional line (line N+1)
    )


# ---------------------------------------------------------------------------
# Category H — Mask-Cast Simplification (disabled by default)
# ---------------------------------------------------------------------------

def rule_mask_cast(lhs: str, rhs: str, enabled: bool = False) -> Optional[RuleResult]:
    """
    Simplify redundant mask-cast sequences of the form:

        x = (u32)(u64)x;    ->   x = x;   (if outer cast does not narrow beyond inner)

    Gate: Only active when ``enabled=True`` (requires --enable-mask-cast-simplification).

    Conservative rules:
      - Both type names must be from the known safe set (_MASK_CAST_TYPES).
      - The outer cast must have >= width of the variable's natural width (no narrowing).
      - LHS must be same identifier as the inner operand.
      - No other expressions in the RHS.
    """
    if not enabled:
        return None

    lhs = lhs.strip()
    rhs = rhs.strip()

    # Match pattern: (outer_type)(inner_type)ident
    m = re.match(
        r"""^\((?P<outer>[a-zA-Z_][a-zA-Z0-9_]*)\)\s*\((?P<inner>[a-zA-Z_][a-zA-Z0-9_]*)\)\s*(?P<operand>[a-zA-Z_][a-zA-Z0-9_]*)$""",
        rhs,
    )
    if not m:
        return None

    outer_type = m.group("outer")
    inner_type = m.group("inner")
    operand = m.group("operand")

    # Both types must be in the known safe mask-cast set
    if outer_type not in _MASK_CAST_TYPES or inner_type not in _MASK_CAST_TYPES:
        return None

    outer_width = _MASK_CAST_WIDTHS.get(outer_type)
    inner_width = _MASK_CAST_WIDTHS.get(inner_type)
    if outer_width is None or inner_width is None:
        return None

    # Outer cast must not narrow beyond inner (outer_width <= inner_width means
    # the outer is narrower, which is the actual mask; skip if outer >= inner to
    # be conservative — only simplify if the double cast is provably a no-op).
    #
    # A double cast (outer)(inner)x is a no-op only if outer_width >= inner_width
    # AND the variable is of width outer_width.  We cannot know the true type, so
    # we additionally require lhs == operand (identity) and outer == inner.
    if outer_type != inner_type:
        return None

    # LHS identifier must match the inner operand
    if operand != lhs:
        return None

    return RuleResult(
        new_expr=lhs,
        reason=f"mask-cast simplification: ({outer_type})({inner_type}){operand} -> {lhs}",
        category="mask_cast",
    )
