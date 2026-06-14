# -*- coding: utf-8 -*-
"""
Phase 4B: Constraint Resolver

Given a Phase 4A base RecoveredType and a list of TypeConstraints gathered from
real instruction-level evidence, produce a refined RecoveredType.

Resolution rules
----------------
1. No constraints → return base_type unchanged (same object, no copy).
2. Select the highest source_priority constraint that maps to a concrete type.
3. If two constraints share the same priority and disagree on rhs, preserve
   the Phase 4A type and add an ambiguity note.
4. Never lower confidence below base_type.confidence.
5. Refined confidence = max(base_type.confidence, priority / 100.0), capped at 0.95.
6. Always return a NEW RecoveredType — never mutate the input.

This module does NOT emit C source, does NOT infer structs, and does NOT
fabricate types without constraint evidence.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from src.ir.types.constraints import ConstraintKind, ConstraintSource, TypeConstraint
from src.ir.types.models import (
    RecoveredType,
    TYPE_UNKNOWN,
    TYPE_INT8,
    TYPE_UINT8,
    TYPE_INT16,
    TYPE_INT32,
    TYPE_INT64,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Size → type name mapping for SIZE constraints
# ---------------------------------------------------------------------------

_SIZE_TO_INT_TYPE = {
    1: TYPE_INT8,
    2: TYPE_INT16,
    4: TYPE_INT32,
    8: TYPE_INT64,
}

# For unsigned load opcodes (ldrb / strb pattern)
_SIZE_TO_UINT_TYPE = {
    1: TYPE_UINT8,
}

# ---------------------------------------------------------------------------
# Max confidence ceiling
# ---------------------------------------------------------------------------

_MAX_CONFIDENCE = 0.95


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _priority_to_confidence(priority: int) -> float:
    """Convert a source priority integer to a confidence float (capped at 0.95)."""
    return min(priority / 100.0, _MAX_CONFIDENCE)


def _resolve_type_from_constraint(
    constraint: TypeConstraint,
    base_type: RecoveredType,
) -> Optional[str]:
    """
    Determine the concrete type string to apply for a given constraint.

    Returns None if the constraint does not produce a concrete type upgrade.
    """
    base_name = base_type.type_name

    if constraint.kind == ConstraintKind.CALL_ARG:
        # rhs is the known callee parameter type string
        rhs = constraint.rhs
        if rhs and rhs != TYPE_UNKNOWN:
            return rhs

    elif constraint.kind == ConstraintKind.SIGN:
        # Narrows unknown → int32 (signed integer evidence)
        if base_name == TYPE_UNKNOWN:
            return TYPE_INT32

    elif constraint.kind == ConstraintKind.SIZE:
        # rhs encodes size_bytes as a string (e.g. "4")
        if base_name == TYPE_UNKNOWN:
            try:
                size = int(constraint.rhs)
                return _SIZE_TO_INT_TYPE.get(size)
            except (ValueError, TypeError):
                pass

    elif constraint.kind == ConstraintKind.EQUALITY:
        rhs = constraint.rhs
        if rhs and rhs != TYPE_UNKNOWN:
            return rhs

    elif constraint.kind == ConstraintKind.SUBTYPE:
        # Weak narrowing hint — only apply if base is completely unknown
        if base_name == TYPE_UNKNOWN:
            rhs = constraint.rhs
            if rhs and rhs != TYPE_UNKNOWN:
                return rhs

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_constraints(
    base_type: RecoveredType,
    constraints: List[TypeConstraint],
) -> RecoveredType:
    """
    Resolve a list of TypeConstraints against a Phase 4A base type.

    Parameters
    ----------
    base_type   : The Phase 4A recovered type for this variable/parameter.
    constraints : All TypeConstraints for this variable (from ConstraintSet.all_for_lhs).

    Returns
    -------
    RecoveredType
        A new RecoveredType with potentially higher confidence and a more
        specific type name.  Returns ``base_type`` unchanged if no constraint
        improves it.
    """
    if not constraints:
        return base_type

    # Sort by priority descending so we examine the strongest evidence first
    sorted_constraints = sorted(
        constraints, key=lambda c: c.source_priority, reverse=True
    )

    # Find the highest priority with a concrete type result
    winning_priority: Optional[int] = None
    winning_type: Optional[str] = None
    winning_note: str = ""
    conflict = False

    for c in sorted_constraints:
        resolved = _resolve_type_from_constraint(c, base_type)
        if resolved is None:
            continue

        if winning_priority is None:
            # First concrete result at this priority level
            winning_priority = c.source_priority
            winning_type = resolved
            winning_note = c.evidence_note
        elif c.source_priority == winning_priority:
            # Same priority — check for conflict
            if resolved != winning_type:
                conflict = True
                logger.debug(
                    "Same-priority constraint conflict for type %r vs %r; "
                    "preserving Phase 4A type.",
                    winning_type,
                    resolved,
                )
        else:
            # Lower priority — stop (already have the best)
            break

    if winning_type is None or conflict:
        # No improvement or irresolvable conflict — return base unchanged
        if conflict:
            # Return base with an added ambiguity note
            new_notes = list(base_type.notes) + [
                "constraint conflict at same priority; Phase 4A type preserved"
            ]
            return RecoveredType(
                type_name=base_type.type_name,
                confidence=base_type.confidence,
                source=base_type.source,
                notes=new_notes,
            )
        return base_type

    # Build refined confidence
    new_confidence = max(
        base_type.confidence,
        _priority_to_confidence(winning_priority),
    )

    new_notes = list(base_type.notes) + [
        f"refined by constraint (priority={winning_priority}): {winning_note}"
        if winning_note
        else f"refined by constraint (priority={winning_priority})"
    ]

    return RecoveredType(
        type_name=winning_type,
        confidence=new_confidence,
        source=f"constraint_refinement(priority={winning_priority})",
        notes=new_notes,
    )
