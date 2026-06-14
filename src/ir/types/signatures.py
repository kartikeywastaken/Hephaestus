# -*- coding: utf-8 -*-
"""
Phase 4A: Known Library Signature Database

A small built-in database of well-known C standard library function signatures.
These are used to emit high-confidence (1.0) signature records for library calls
without any inference needed.

Normalization rules:
- Leading underscores are stripped for lookup (e.g. `_printf` → `printf`)
- Names are lowercased for lookup
- Both the underscore-prefixed and plain variants resolve to the same entry
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.ir.types.models import (
    RecoveredType,
    RecoveredParameter,
    RecoveredSignature,
    TYPE_INT32,
    TYPE_UINT64,
    TYPE_POINTER,
    TYPE_VOID,
)


# ---------------------------------------------------------------------------
# KnownSignature dataclass
# ---------------------------------------------------------------------------

@dataclass
class KnownSignatureParam:
    """One parameter in a known library function signature."""
    name: str
    type_name: str


@dataclass
class KnownSignature:
    """
    A known library function signature entry.

    Attributes
    ----------
    canonical_name : Lowercase, no-underscore-prefix canonical name.
    return_type    : The exact return type string.
    params         : Ordered list of (name, type_name) parameter entries.
    variadic       : Whether the function is variadic.
    """
    canonical_name: str
    return_type: str
    params: List[KnownSignatureParam] = field(default_factory=list)
    variadic: bool = False

    def to_recovered_signature(self) -> RecoveredSignature:
        """Converts this database entry into a RecoveredSignature at confidence 1.0."""
        ret_type = RecoveredType(
            type_name=self.return_type,
            confidence=1.0,
            source="known_signature_database",
            notes=[],
        )
        parameters = []
        for idx, p in enumerate(self.params):
            parameters.append(RecoveredParameter(
                name=p.name,
                index=idx,
                recovered_type=RecoveredType(
                    type_name=p.type_name,
                    confidence=1.0,
                    source="known_signature_database",
                    notes=[],
                ),
                source="known_signature_database",
                confidence=1.0,
                notes=[],
            ))
        return RecoveredSignature(
            return_type=ret_type,
            parameters=parameters,
            variadic=self.variadic,
            confidence=1.0,
            source="known_signature_database",
            notes=[],
        )


# ---------------------------------------------------------------------------
# Built-in signature database
# ---------------------------------------------------------------------------

_KNOWN_SIGNATURES: Dict[str, KnownSignature] = {
    "printf": KnownSignature(
        canonical_name="printf",
        return_type=TYPE_INT32,
        params=[KnownSignatureParam(name="format", type_name=TYPE_POINTER)],
        variadic=True,
    ),
    "puts": KnownSignature(
        canonical_name="puts",
        return_type=TYPE_INT32,
        params=[KnownSignatureParam(name="s", type_name=TYPE_POINTER)],
        variadic=False,
    ),
    "atoi": KnownSignature(
        canonical_name="atoi",
        return_type=TYPE_INT32,
        params=[KnownSignatureParam(name="s", type_name=TYPE_POINTER)],
        variadic=False,
    ),
    "strlen": KnownSignature(
        canonical_name="strlen",
        return_type=TYPE_UINT64,
        params=[KnownSignatureParam(name="s", type_name=TYPE_POINTER)],
        variadic=False,
    ),
    "malloc": KnownSignature(
        canonical_name="malloc",
        return_type=TYPE_POINTER,
        params=[KnownSignatureParam(name="size", type_name=TYPE_UINT64)],
        variadic=False,
    ),
    "free": KnownSignature(
        canonical_name="free",
        return_type=TYPE_VOID,
        params=[KnownSignatureParam(name="p", type_name=TYPE_POINTER)],
        variadic=False,
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_symbol_name(name: str) -> str:
    """
    Normalize a function symbol name for database lookup.

    Normalization rules:
    - Strip leading underscores (e.g. ``_printf`` → ``printf``)
    - Lowercase the result

    Parameters
    ----------
    name : Raw function name string.

    Returns
    -------
    str
        Normalized name suitable for database lookup.
    """
    if not name:
        return ""
    normalized = name.lstrip("_").lower()
    return normalized


def get_known_signature(name: str) -> Optional[KnownSignature]:
    """
    Look up a known library function signature by name.

    Both ``printf`` and ``_printf`` resolve to the same entry.

    Parameters
    ----------
    name : Raw function name (may include leading underscores).

    Returns
    -------
    KnownSignature or None
        The matching entry if found, otherwise None.
    """
    normalized = normalize_symbol_name(name)
    return _KNOWN_SIGNATURES.get(normalized)


def is_known_library_function(name: str) -> bool:
    """Return True if the name matches a known library function."""
    return get_known_signature(name) is not None
