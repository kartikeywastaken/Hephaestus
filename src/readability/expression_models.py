# -*- coding: utf-8 -*-
"""
Phase 7.3.1 Expression Simplification Data Models

Shared data structures used by expression_rules.py and
expression_simplification.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Per-rule result
# ---------------------------------------------------------------------------

@dataclass
class RuleResult:
    """
    Value returned by a single rule function.

    Attributes:
        new_expr:  The simplified expression (or statement fragment).
                   For statement-level rules (Category E/G) this is the full
                   replacement statement, including the trailing semicolon.
                   For expression-level rules (A/B/F) this is just the RHS.
        reason:    Short human-readable reason string for the evidence comment.
        category:  Category label used in reporting.
        evidence_preserved:  Always True for conservative rules.
        lines_consumed:  How many *additional* lines (beyond the current one)
                         were consumed by the rule.  Zero for single-line rules.
    """
    new_expr: str
    reason: str
    category: str
    evidence_preserved: bool = True
    lines_consumed: int = 0


# ---------------------------------------------------------------------------
# Per-site simplification record
# ---------------------------------------------------------------------------

@dataclass
class ExprSimplification:
    """One accepted simplification record."""
    site_id: str
    function: str
    line_number: int           # 1-indexed, relative to the whole file
    category: str              # identity_arithmetic | redundant_parentheses |
                               # assignment_rhs | copy_op_store | self_assignment |
                               # double_parentheses | temp_copy_roundtrip | mask_cast
    old_text: str              # original line text (stripped)
    new_text: str              # simplified line text (stripped), or "" for removed lines
    reason: str
    evidence_preserved: bool
    confidence: str = "static_safe"


# ---------------------------------------------------------------------------
# Aggregate statistics
# ---------------------------------------------------------------------------

@dataclass
class ExprSimplificationStats:
    """Aggregate statistics for expression simplification."""
    sites_total: int = 0
    simplified: int = 0
    skipped: int = 0
    # Single-line categories
    identity_arithmetic: int = 0
    redundant_parentheses: int = 0
    assignment_rhs: int = 0
    double_parentheses: int = 0
    self_assignment: int = 0
    mask_cast: int = 0
    # Multi-line categories
    copy_op_store: int = 0
    temp_copy_roundtrip: int = 0
