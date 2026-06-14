# -*- coding: utf-8 -*-
"""
Phase 4B: Type Constraint System

Defines the constraint kinds, source priority constants, TypeConstraint dataclass,
and ConstraintSet container used by the Phase 4B refinement engine.

Constraints represent evidence assertions about a named variable or slot.
They are gathered from real instruction-level evidence only — no fabrication.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Iterator, List, Tuple


# ---------------------------------------------------------------------------
# Constraint kinds
# ---------------------------------------------------------------------------

class ConstraintKind(Enum):
    """The semantic type of a constraint assertion."""
    EQUALITY       = auto()  # lhs has exactly type rhs
    SUBTYPE        = auto()  # lhs is a subtype of rhs (weak narrowing)
    SIZE           = auto()  # lhs has size_bytes equal to rhs (encoded as str)
    SIGN           = auto()  # lhs is a signed integer type
    POINTER_TARGET = auto()  # lhs is a pointer to rhs
    RETURN_USE     = auto()  # lhs is used as a return value of type rhs
    CALL_ARG       = auto()  # lhs is passed as argument of type rhs


# ---------------------------------------------------------------------------
# Source priority constants
# ---------------------------------------------------------------------------

class ConstraintSource:
    """
    Integer priority constants for constraint sources.

    Higher value = stronger evidence.  The resolver always selects the
    highest-priority compatible constraint for a given variable.
    """
    KNOWN_SIGNATURE = 100  # entry from the built-in known signature database
    IR_CALL_SITE    = 80   # inferred from a call-site in the instruction stream
    IR_ARITHMETIC   = 60   # inferred from arithmetic opcode evidence
    IR_MEMORY       = 60   # inferred from memory load/store size evidence
    IR_COMPARISON   = 50   # inferred from comparison/branch opcode evidence
    NAME_HEURISTIC  = 20   # weakest: derived from variable name pattern only


# ---------------------------------------------------------------------------
# TypeConstraint
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TypeConstraint:
    """
    A single type constraint assertion backed by instruction-level evidence.

    Attributes
    ----------
    kind            : Semantic category of the constraint.
    lhs             : Name of the variable or parameter this constraint applies to.
    rhs             : Target type string (e.g. "int32") or referenced slot name.
    source_priority : Integer from ConstraintSource indicating evidence strength.
    evidence_note   : Free-form human-readable description of why this constraint
                      was emitted.
    """
    kind: ConstraintKind
    lhs: str
    rhs: str
    source_priority: int
    evidence_note: str = ""

    def dedup_key(self) -> Tuple[ConstraintKind, str, str]:
        """Deduplication key — ignores evidence_note and priority."""
        return (self.kind, self.lhs, self.rhs)


# ---------------------------------------------------------------------------
# ConstraintSet
# ---------------------------------------------------------------------------

class ConstraintSet:
    """
    A deduplicated, ordered collection of TypeConstraints for a single function.

    Deduplication key: (kind, lhs, rhs).
    When a duplicate is added, the version with the higher source_priority wins.
    Insertion order of first-seen keys is preserved.
    """

    def __init__(self) -> None:
        # Maps dedup_key → TypeConstraint (the highest-priority one seen so far)
        self._by_key: Dict[Tuple[ConstraintKind, str, str], TypeConstraint] = {}
        # Ordered list of dedup keys (insertion order of first occurrence)
        self._order: List[Tuple[ConstraintKind, str, str]] = []

    def add(self, constraint: TypeConstraint) -> None:
        """
        Add a constraint.

        If a constraint with the same (kind, lhs, rhs) already exists, keep the
        one with the higher source_priority.
        """
        key = constraint.dedup_key()
        existing = self._by_key.get(key)
        if existing is None:
            self._by_key[key] = constraint
            self._order.append(key)
        elif constraint.source_priority > existing.source_priority:
            # Replace with stronger evidence
            self._by_key[key] = constraint

    def all_for_lhs(self, name: str) -> List[TypeConstraint]:
        """Return all constraints whose lhs matches ``name``, in insertion order."""
        return [
            self._by_key[k]
            for k in self._order
            if k[1] == name
        ]

    def __len__(self) -> int:
        return len(self._by_key)

    def __iter__(self) -> Iterator[TypeConstraint]:
        for key in self._order:
            yield self._by_key[key]

    def __repr__(self) -> str:
        return f"ConstraintSet({len(self)} constraints)"
