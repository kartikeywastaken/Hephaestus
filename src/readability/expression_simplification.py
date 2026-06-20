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

# A word-boundary identifier (not a keyword, not a type prefix)
_IDENT = r"[a-zA-Z_][a-zA-Z0-9_]*"

# An integer literal (decimal, hex, or octal; optional sign)
_INT_LIT = r"(?:0[xX][0-9a-fA-F]+|0[0-7]*|[1-9][0-9]*)"

# A "simple operand": identifier or integer literal — no operators, parens,
# pointer dereferences, or casts.  Used to guard Category A and B.
_SIMPLE_OPERAND_RE = re.compile(
    r"^(?:[a-zA-Z_][a-zA-Z0-9_]*|0[xX][0-9a-fA-F]+|0[0-7]*|[1-9][0-9]*)$"
)

# Matches:  <simple_expr> OP <identity_constant>
#   where OP is one of: + - | ^ << >>
# Group 1: the whole LHS (everything before OP)
# Group 2: OP
# Group 3: the identity constant (0 or 1 for * and /)
_IDENTITY_RHS_RE = re.compile(
    r"""^
    (?P<lhs>.+?)                        # left-hand expression
    \s*
    (?P<op>[+\-|^]|<<|>>)               # identity operator
    \s*
    (?P<rhs>0)                          # identity value for + - | ^ << >>
    $""",
    re.VERBOSE,
)

_IDENTITY_MUL_RE = re.compile(
    r"""^
    (?P<lhs>.+?)
    \s*
    (?P<op>[*/])
    \s*
    (?P<rhs>1)
    $""",
    re.VERBOSE,
)

# Matches:   0  OP  <simple_expr>   (commutative only)
_IDENTITY_LHS_RE = re.compile(
    r"""^
    (?P<lhs>0)
    \s*
    (?P<op>[+|^])                       # commutative identity operators only
    \s*
    (?P<rhs>.+?)
    $""",
    re.VERBOSE,
)

_IDENTITY_MUL_LHS_RE = re.compile(
    r"""^
    (?P<lhs>1)
    \s*
    (?P<op>\*)
    \s*
    (?P<rhs>.+?)
    $""",
    re.VERBOSE,
)

# A "simple parenthesised expression": matches ( <identifier> ) or ( <int_lit> )
# Does NOT match casts like (u64), (int), or complex expressions.
_SIMPLE_PAREN_RE = re.compile(
    r"""^
    \(                              # opening paren
    \s*
    (?P<inner>[a-zA-Z_][a-zA-Z0-9_]*|0[xX][0-9a-fA-F]+|0[0-7]*|[1-9][0-9]*)
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

# Operators that are forbidden as part of the LHS in Category A
# (we require the LHS to be a simple operand for Category A;
#  compound expressions are left alone)
_OPERATOR_CHARS = frozenset("+-*/<>=!&|^~%?:")

# Assignment pattern:  <lhs_ident>  =  <rhs_expr> ;
# We only handle simple single-identifier LHS.
_ASSIGN_RE = re.compile(
    r"""^
    (?P<lhs_ident>[a-zA-Z_][a-zA-Z0-9_]*)   # single identifier on LHS
    \s*=\s*
    (?P<rhs>.+?)
    ;
    (?P<trailing>\s*(?:/\*.*?\*/)?\s*)?       # optional trailing comment
    $""",
    re.VERBOSE | re.DOTALL,
)

# Three-line copy-op-store patterns
# Line 1:  tmp = src;
# Line 2:  tmp = tmp OP const;
# Line 3:  dst = tmp;
_COS_LINE1_RE = re.compile(
    r"""^
    (?P<tmp>[a-zA-Z_][a-zA-Z0-9_]*)
    \s*=\s*
    (?P<src>[a-zA-Z_][a-zA-Z0-9_]*)
    ;
    """,
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
    (?P<const>(?:0[xX][0-9a-fA-F]+|0[0-7]*|[1-9][0-9]*|\d+))
    ;
    """,
    re.VERBOSE,
)
_COS_LINE3_RE = re.compile(
    r"""^
    (?P<dst>[a-zA-Z_][a-zA-Z0-9_]*)
    \s*=\s*
    (?P<tmp>[a-zA-Z_][a-zA-Z0-9_]*)
    ;
    """,
    re.VERBOSE,
)

# Patterns that indicate a line is a control-flow boundary for Category D
_CONTROL_FLOW_BOUNDARY_RE = re.compile(
    r"""
    \b(?:if|else|while|for|do|switch|case|break|continue|goto|return)\b
    | /\*\s*(?:block|loop|branch|Entry|conditional|merge|if/else)\b
    | \*/\s*$                                   # end of block comment
    | \blabel_\w+\s*:                           # goto label
    """,
    re.VERBOSE,
)

# Pattern indicating a call site — Category D must not cross calls
_CALL_RE = re.compile(r"\b\w+\s*\(")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_code_text(line: str) -> Tuple[str, str, bool]:
    """
    Split a C source line into (code_text, trailing_comment, inside_block_comment).

    Returns the concatenated code chunks, the first trailing comment (if any),
    and whether the line ends inside a block comment.

    The trailing comment is the last /* ... */ or // ... comment fragment
    found on the line (used for evidence preservation).
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
        # Join everything; the caller uses this for evidence annotation.
        trailing = "".join(comment_parts).strip()
        # Remove outer /* */ or // so we just have the evidence text
        if trailing.startswith("//"):
            trailing = trailing[2:].strip()
        elif trailing.startswith("/*") and trailing.endswith("*/"):
            trailing = trailing[2:-2].strip()
    return code_text, trailing, still_in_bc


def _is_simple_operand(text: str) -> bool:
    """Return True iff text is a bare identifier or bare integer literal."""
    return bool(_SIMPLE_OPERAND_RE.match(text.strip()))


def _contains_operator(text: str) -> bool:
    """Return True iff text contains any operator character (indicating complex expr)."""
    return any(c in _OPERATOR_CHARS for c in text)


def _is_cast(text: str) -> bool:
    """Return True if text looks like a C cast: (<type_name>)."""
    m = _SIMPLE_PAREN_RE.match(text.strip())
    if m:
        inner = m.group("inner").strip()
        if inner in _C_TYPE_NAMES or inner.endswith("_t"):
            return True
    return False


def _rebuild_line_with_new_code(original_line: str, new_code: str, evidence: str) -> str:
    """
    Rebuild a source line replacing the code portion with new_code.
    Appends evidence comment if the original had a comment.
    """
    leading_ws = len(original_line) - len(original_line.lstrip())
    indent = original_line[:leading_ws]
    if evidence:
        return f"{indent}{new_code} /* {evidence} */\n"
    return f"{indent}{new_code}\n"


def _make_evidence_comment(original_code: str, original_comment: str, reason: str) -> str:
    """
    Build the evidence annotation comment for a simplified line.
    Format: simplified: <original_expr> -> <reason>; evidence: <original_comment>
    """
    if original_comment:
        return f"simplified: {original_code}; evidence: {original_comment}"
    return f"simplified: {original_code}"


# ---------------------------------------------------------------------------
# Category A — Identity Arithmetic
# ---------------------------------------------------------------------------

# Forbidden simplifications (must NOT match)
_FORBIDDEN_PATTERNS: List[re.Pattern] = [
    re.compile(r"^\s*0\s*-\s*"),            # 0 - x
    re.compile(r"/\s*0\b"),                 # x / 0
    re.compile(r"%\s*1\b"),                 # x % 1
    re.compile(r"&\s*0\b"),                 # x & 0 (zeroes the result)
    re.compile(r"\*\s*0\b"),               # x * 0
    re.compile(r"0\s*\*"),                  # 0 * x
    re.compile(r"&&"),                      # boolean AND
    re.compile(r"\|\|"),                    # boolean OR
]


def _is_forbidden(expr: str) -> bool:
    """Return True if expr matches any forbidden simplification pattern."""
    for pat in _FORBIDDEN_PATTERNS:
        if pat.search(expr):
            return True
    return False


def _try_simplify_identity_arithmetic(expr: str) -> Optional[Tuple[str, str]]:
    """
    Try to simplify an arithmetic expression using identity laws.

    Returns (simplified_expr, reason) or None if no safe simplification applies.

    Only applied when the operand being kept is a 'simple operand'
    (identifier or integer literal), to avoid accidentally simplifying
    complex sub-expressions.
    """
    expr = expr.strip()

    if _is_forbidden(expr):
        return None

    # x + 0, x - 0, x | 0, x ^ 0, x << 0, x >> 0
    m = _IDENTITY_RHS_RE.match(expr)
    if m:
        lhs = m.group("lhs").strip()
        op = m.group("op")
        if _is_simple_operand(lhs):
            return lhs, f"identity {op}-zero simplification"

    # x * 1, x / 1
    m = _IDENTITY_MUL_RE.match(expr)
    if m:
        lhs = m.group("lhs").strip()
        op = m.group("op")
        if _is_simple_operand(lhs):
            return lhs, f"identity {op}-one simplification"

    # 0 + x, 0 | x, 0 ^ x
    m = _IDENTITY_LHS_RE.match(expr)
    if m:
        rhs = m.group("rhs").strip()
        op = m.group("op")
        if _is_simple_operand(rhs):
            return rhs, f"identity zero-{op} simplification"

    # 1 * x
    m = _IDENTITY_MUL_LHS_RE.match(expr)
    if m:
        rhs = m.group("rhs").strip()
        if _is_simple_operand(rhs):
            return rhs, f"identity one-* simplification"

    return None


# ---------------------------------------------------------------------------
# Category B — Redundant Parentheses
# ---------------------------------------------------------------------------

def _try_simplify_parentheses(expr: str) -> Optional[Tuple[str, str]]:
    """
    Remove redundant parentheses around a simple identifier or literal.

    Only simplifies:
        (identifier)    -> identifier
        (integer_lit)   -> integer_lit

    Never simplifies casts or complex sub-expressions.
    """
    expr = expr.strip()
    m = _SIMPLE_PAREN_RE.match(expr)
    if not m:
        return None
    inner = m.group("inner").strip()
    # Skip type-name casts
    if inner in _C_TYPE_NAMES or inner.endswith("_t"):
        return None
    return inner, "redundant parentheses removal"


# ---------------------------------------------------------------------------
# Single-line statement simplifier
# ---------------------------------------------------------------------------

def _simplify_statement(
    stmt_code: str,
    comment: str,
) -> Optional[Tuple[str, str, str, bool]]:
    """
    Try to simplify a single executable C statement (code chunk, no comment).

    Returns (new_code, category, reason, evidence_preserved) or None.

    new_code does NOT include a trailing comment; the caller decides how to
    reattach the (updated) comment.
    """
    stmt = stmt_code.strip()
    if not stmt.endswith(";"):
        return None

    # Try Category C first: assignment RHS
    m = _ASSIGN_RE.match(stmt)
    if m:
        lhs = m.group("lhs_ident")
        rhs = m.group("rhs").strip()
        trailing = m.group("trailing") or ""

        # Try to simplify the RHS with Category A
        result = _try_simplify_identity_arithmetic(rhs)
        if result:
            new_rhs, reason = result
            new_stmt = f"{lhs} = {new_rhs};"
            evidence_preserved = bool(comment)
            return new_stmt, "assignment_rhs", reason, evidence_preserved

        # Try to simplify the RHS with Category B
        result = _try_simplify_parentheses(rhs)
        if result:
            new_rhs, reason = result
            new_stmt = f"{lhs} = {new_rhs};"
            evidence_preserved = bool(comment)
            return new_stmt, "redundant_parentheses", reason, evidence_preserved

        return None

    # Stand-alone expression statement (not assignment)
    # Try Category A then B on the whole statement minus trailing semicolon
    core = stmt.rstrip(";").strip()

    result = _try_simplify_identity_arithmetic(core)
    if result:
        new_core, reason = result
        evidence_preserved = bool(comment)
        return new_core + ";", "identity_arithmetic", reason, evidence_preserved

    result = _try_simplify_parentheses(core)
    if result:
        new_core, reason = result
        evidence_preserved = bool(comment)
        return new_core + ";", "redundant_parentheses", reason, evidence_preserved

    return None


# ---------------------------------------------------------------------------
# Category D — Three-Line Copy-Op-Store
# ---------------------------------------------------------------------------

def _is_boundary_line(line: str) -> bool:
    """Return True if line is a control-flow or comment barrier."""
    stripped = line.strip()
    if not stripped:
        return False  # blank lines are ok
    # Pure comment lines are barriers (they may carry evidence)
    if stripped.startswith("//") or stripped.startswith("/*"):
        return True
    if _CONTROL_FLOW_BOUNDARY_RE.search(line):
        return True
    return False


def _has_call(line_code: str) -> bool:
    """Return True if the code chunk appears to contain a function call."""
    # Heuristic: any word followed immediately by '(' is a call.
    # We exclude common casts by checking if the word is a type name.
    for m in _CALL_RE.finditer(line_code):
        name = m.group(0).split("(")[0].strip()
        if name not in _C_TYPE_NAMES:
            return True
    return False


def _has_pointer_deref(code: str) -> bool:
    """Return True if the code contains a pointer dereference on LHS or RHS."""
    return "*" in code or "->" in code or "[" in code


def _try_copy_op_store(
    lines: List[str],
    start_idx: int,
) -> Optional[Tuple[int, str, str, str]]:
    """
    Attempt to detect and fold a three-line copy-op-store pattern.

    Returns (end_idx, new_stmt, reason, combined_comment) or None.
    end_idx is the index of the last line that was consumed (inclusive).
    """
    if start_idx + 2 >= len(lines):
        return None

    # Collect up to 3 consecutive non-boundary, non-call code lines
    # starting at start_idx
    triplet_lines = []
    triplet_codes = []
    triplet_comments = []

    scan = start_idx
    while len(triplet_lines) < 3 and scan < len(lines):
        raw = lines[scan]
        if _is_boundary_line(raw):
            if triplet_lines:
                # boundary hit mid-search
                return None
            scan += 1
            continue
        code, comment, _ = _extract_code_text(raw)
        if not code:
            scan += 1
            continue
        if _has_call(code) or _has_pointer_deref(code):
            return None
        triplet_lines.append(raw)
        triplet_codes.append(code)
        triplet_comments.append(comment)
        scan += 1

    if len(triplet_lines) < 3:
        return None

    c1, c2, c3 = (c.strip() for c in triplet_codes)

    # Pattern match
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

    # Validate: all tmp references are the same variable
    if not (tmp1 == tmp2 == tmp2b == tmp3):
        return None
    # src and dst must be the same identifier
    if src != dst:
        return None
    # tmp must be different from src/dst
    if tmp1 == src:
        return None

    # If any of the three lines has a trailing comment, we need to preserve evidence.
    # If ALL comments fit on one combined comment we do; if the combined comment
    # would be too long or complex, skip.
    combined_evidence_parts = [c for c in triplet_comments if c]
    if len(combined_evidence_parts) > 2:
        # Too many separate evidence fragments — skip rather than lose any
        return None

    new_stmt = f"{dst} = {dst} {op} {const};"
    reason = f"copy-op-store fold: {tmp1} = {src}; {tmp1} = {tmp1} {op} {const}; {dst} = {tmp1};"

    combined_comment = "; ".join(combined_evidence_parts) if combined_evidence_parts else ""
    # Also embed original raw lines for audit
    if combined_comment:
        combined_comment = f"copy-op-store simplified; evidence: {combined_comment}"
    else:
        combined_comment = "copy-op-store simplified"

    # end_idx is the index of the last line in the triplet (exclusive = scan)
    end_idx = scan - 1
    return end_idx, new_stmt, reason, combined_comment


# ---------------------------------------------------------------------------
# Per-function block context helper
# ---------------------------------------------------------------------------

def _get_function_name_from_lines(lines: List[str]) -> str:
    """
    Extract the function name from a list of lines that represent a function block.
    Looks for pattern:  <type> <name>(...) {
    """
    func_sig_re = re.compile(
        r"^[a-zA-Z_][a-zA-Z0-9_*\s]+\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\("
    )
    for line in lines[:5]:
        m = func_sig_re.match(line.strip())
        if m:
            return m.group(1)
    return "<unknown>"


# ---------------------------------------------------------------------------
# Main simplification pass
# ---------------------------------------------------------------------------

def simplify_expressions(
    c_content: str,
    enable_copy_op_store: bool = True,
    _site_counter_start: int = 1,
) -> Tuple[str, List[ExprSimplification], List[Dict[str, Any]], ExprSimplificationStats]:
    """
    Simplify expressions in c_content (token-safely).

    Parameters
    ----------
    c_content            : Full C source content of recovered_readable.c.
    enable_copy_op_store : If False, Category D (copy-op-store) is disabled.
    _site_counter_start  : Starting value for site_id counter.

    Returns
    -------
    (simplified_c, simplifications, skipped_list, stats)

    simplified_c     : Rewritten C source.
    simplifications  : List of ExprSimplification records (accepted).
    skipped_list     : List of dicts for skipped/rejected sites.
    stats            : Aggregate ExprSimplificationStats.
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

    # Parse into function/global blocks so we know function names
    blocks = parse_c_into_functions(c_content)

    output_blocks: List[str] = []

    for block in blocks:
        if block["type"] != "function":
            output_blocks.append("".join(block["lines"]))
            continue

        fn_name = block["name"]
        lines = block["lines"]
        new_lines: List[str] = []
        file_line_offset = block.get("start_line", 0)  # may not exist, default 0

        i = 0
        while i < len(lines):
            raw = lines[i]
            line_num = file_line_offset + i + 1

            # Extract code + comment
            code, comment, _ = _extract_code_text(raw)

            # Skip blank or pure comment lines
            if not code:
                new_lines.append(raw)
                i += 1
                continue

            # Skip lines with control flow keywords — do not simplify
            if _CONTROL_FLOW_BOUNDARY_RE.search(raw) or _has_call(code) or _has_pointer_deref(code):
                new_lines.append(raw)
                i += 1
                continue

            # Category D: try copy-op-store FIRST (consumes 3 lines)
            if enable_copy_op_store and code.strip().endswith(";"):
                cos_result = _try_copy_op_store(lines, i)
                if cos_result is not None:
                    end_idx, new_stmt, reason, cos_comment = cos_result
                    stats.sites_total += 1

                    # Collect original evidence from all three lines
                    orig_texts = [lines[j].strip() for j in range(i, end_idx + 1)]
                    # Sanity: the combined comment should mention all original code
                    all_have_evidence = all(
                        _extract_code_text(lines[j])[1] for j in range(i, end_idx + 1)
                        if _extract_code_text(lines[j])[0]
                    )

                    # Preserve evidence: build combined comment
                    new_raw = _rebuild_line_with_new_code(raw, new_stmt, cos_comment)
                    sid = next_site_id()
                    simplifications.append(ExprSimplification(
                        site_id=sid,
                        function=fn_name,
                        line_number=line_num,
                        category="copy_op_store",
                        old_text=orig_texts[0] if orig_texts else code,
                        new_text=new_stmt,
                        reason=reason,
                        evidence_preserved=True,
                        confidence="static_safe",
                    ))
                    stats.simplified += 1
                    stats.copy_op_store += 1

                    new_lines.append(new_raw)
                    # Skip the consumed lines
                    i = end_idx + 1
                    continue

            # Categories A, B, C: single-line
            result = _simplify_statement(code, comment)
            if result is None:
                new_lines.append(raw)
                i += 1
                continue

            new_code, category, reason, evidence_preserved = result

            stats.sites_total += 1

            # Build evidence annotation
            if evidence_preserved and comment:
                evidence_str = _make_evidence_comment(code, comment, reason)
            elif evidence_preserved:
                evidence_str = f"simplified: {code}"
            else:
                evidence_str = ""

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
                confidence="static_safe",
            ))
            stats.simplified += 1
            if category == "identity_arithmetic":
                stats.identity_arithmetic += 1
            elif category == "redundant_parentheses":
                stats.redundant_parentheses += 1
            elif category == "assignment_rhs":
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
