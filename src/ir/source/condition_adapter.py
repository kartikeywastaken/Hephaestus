# -*- coding: utf-8 -*-
"""
Phase 5.7: Syntax-Safe Unknown Condition Adapter Engine

Converts comment-only condition headers into syntax-safe HEPHAESTUS_UNKNOWN_COND(...) calls
without recovering or fabricating executable conditions.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple, Optional

# Match lines starting with optional whitespace, followed directly by while/if
# and containing a comment-only condition evidence or condition unknown comment.
# Group 1: Indentation
# Group 2: Keyword (while or if)
# Group 3: The evidence or unknown prefix and details (e.g. "condition evidence: ...")
# Group 4: Anything after the closing parenthesis (e.g. " {")
ADAPT_RE = re.compile(
    r"^(\s*)(while|if)\s*\(\s*/\*\s*((?:condition evidence:|condition unknown:).*?)\s*\*/\s*\)(.*)$",
    flags=re.DOTALL
)


def escape_c_string(value: str) -> str:
    """
    Escape a string so it can safely appear inside a C string literal.
    Must escape backslash, quote, newline, carriage return, and tab.
    """
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace('"', '\\"')
    escaped = escaped.replace("\n", "\\n")
    escaped = escaped.replace("\r", "\\r")
    escaped = escaped.replace("\t", "\\t")
    return escaped


def adapt_condition_header(line: str) -> tuple[str, bool, str | None]:
    """
    Convert comment-only condition headers into syntax-safe helper calls.
    Returns (adapted_line, changed, kind).
    """
    match = ADAPT_RE.match(line)
    if not match:
        return line, False, None

    indent, keyword, evidence, tail = match.groups()
    evidence_clean = evidence.strip()

    kind = None
    if evidence_clean.startswith("condition evidence:"):
        kind = "evidence"
    elif evidence_clean.startswith("condition unknown:"):
        kind = "unknown"

    escaped = escape_c_string(evidence_clean)
    new_line = f'{indent}{keyword} (HEPHAESTUS_UNKNOWN_COND("{escaped}")){tail}'
    return new_line, True, kind


def adapt_condition_lines(lines: list[str]) -> tuple[list[str], dict]:
    """
    Apply adapt_condition_header to all body lines.
    Return adapted_lines, stats.
    """
    stats = {
        "condition_adapters_inserted": 0,
        "condition_evidence_adapters": 0,
        "condition_unknown_adapters": 0,
        "warnings": [],
    }
    adapted: list[str] = []

    for line in lines:
        new_line, changed, kind = adapt_condition_header(line)
        if changed:
            stats["condition_adapters_inserted"] += 1
            if kind == "evidence":
                stats["condition_evidence_adapters"] += 1
            elif kind == "unknown":
                stats["condition_unknown_adapters"] += 1
        adapted.append(new_line)

    return adapted, stats
