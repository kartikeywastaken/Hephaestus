# -*- coding: utf-8 -*-
"""
Symbol Alias Canonicalization

Groups function names sharing the same normalized entry point into alias
groups and selects a deterministic canonical name.

Core rules
----------
- Only functions with matching normalized entry points are grouped.
- Different entry points are NEVER merged, even if names look similar.
- Canonical name selection uses conservative deterministic rules.
- No evidence is lost; all aliases are preserved in metadata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from src.ir.utils.addressing import normalize_address


# ---------------------------------------------------------------------------
# Synthetic name patterns
# ---------------------------------------------------------------------------

_SYNTHETIC_RE = re.compile(
    r"^(?:FUN_|sub_|fcn\.|func\.|entry)[0-9a-fA-Fx]*$", re.IGNORECASE
)

_KNOWN_LIBRARY_NAMES = frozenset({
    "printf", "fprintf", "sprintf", "snprintf",
    "malloc", "calloc", "realloc", "free",
    "memcpy", "memmove", "memset", "memcmp",
    "strlen", "strcpy", "strncpy", "strcmp", "strncmp", "strcat",
    "exit", "_exit", "abort",
    "open", "close", "read", "write",
    "fopen", "fclose", "fread", "fwrite",
    "puts", "gets", "getchar", "putchar",
    "atoi", "atol", "atof", "strtol", "strtoul",
})


# ---------------------------------------------------------------------------
# FunctionAliasGroup
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FunctionAliasGroup:
    """
    A group of function names that share the same entry point.

    Attributes
    ----------
    canonical_name : The selected canonical name.
    entry_point    : Normalized entry point address.
    aliases        : All unique names seen (including canonical).
    sources        : Extractor sources that contributed names.
    evidence_notes : Human-readable notes explaining the grouping.
    """
    canonical_name: str
    entry_point: str
    aliases: tuple  # tuple[str, ...] for frozen
    sources: tuple  # tuple[str, ...] for frozen
    evidence_notes: tuple  # tuple[str, ...] for frozen

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_point": self.entry_point,
            "canonical_name": self.canonical_name,
            "aliases": list(self.aliases),
            "sources": list(self.sources),
            "evidence_notes": list(self.evidence_notes),
        }


# ---------------------------------------------------------------------------
# Canonical name selection
# ---------------------------------------------------------------------------

def _strip_leading_underscore(name: str) -> str:
    """Strip a single leading underscore (C linkage convention)."""
    if name.startswith("_") and len(name) > 1 and not name.startswith("__"):
        return name[1:]
    return name


def _clean_tool_prefix(name: str) -> str:
    """Remove common tool-specific prefixes."""
    if not name:
        return name
    for prefix in ("sym.imp.", "sym.fcn.", "sym.", "imp."):
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def _is_synthetic(name: str) -> bool:
    """Return True if the name is a synthetic/auto-generated name."""
    cleaned = _clean_tool_prefix(name)
    return bool(_SYNTHETIC_RE.match(cleaned))


def _name_quality_score(name: str) -> tuple:
    """
    Compute a quality tuple for canonical name selection.
    Higher is better. Returns a tuple for deterministic comparison.

    Rules (in priority order):
    1. Non-empty real names over synthetic names.
    2. Library-known names get highest priority.
    3. Non-FUN_*/sub_* names preferred.
    4. More semantic content (longer, non-generic).
    5. Stable lexical fallback.
    """
    if not name:
        return (0, 0, 0, 0, "")

    cleaned = _clean_tool_prefix(name)
    bare = _strip_leading_underscore(cleaned)

    # Score components
    is_real = 0 if _is_synthetic(name) else 1
    is_library = 1 if bare.lower() in _KNOWN_LIBRARY_NAMES else 0
    semantic_length = len(bare)

    return (is_real, is_library, semantic_length, len(cleaned), cleaned)


def choose_canonical_function_name(
    names: List[str],
    entry_point: str,
) -> str:
    """
    Select the canonical function name from a list of aliases.

    Parameters
    ----------
    names       : All names seen for this entry point.
    entry_point : Normalized entry point (for context, not used in scoring).

    Returns
    -------
    str
        The best canonical name, or 'unknown' if no valid names.
    """
    valid = sorted(set(n for n in names if n and n.strip()))
    if not valid:
        return "unknown"

    # Sort by quality score descending, then lexically for ties
    return max(valid, key=_name_quality_score)


# ---------------------------------------------------------------------------
# Build alias groups
# ---------------------------------------------------------------------------

def build_function_alias_groups(
    functions: List[Dict[str, Any]],
) -> Dict[str, FunctionAliasGroup]:
    """
    Group function records by normalized entry point and build alias groups.

    Parameters
    ----------
    functions : List of function dicts, each with 'name', 'entry_point',
                and optionally 'source_tool' or 'provenance'.

    Returns
    -------
    dict[str, FunctionAliasGroup]
        Mapping from normalized entry point to its alias group.
        Only entry points with at least one valid name are included.
    """
    # Group names and sources by normalized entry point
    names_by_entry: Dict[str, List[str]] = {}
    sources_by_entry: Dict[str, Set[str]] = {}

    for fn in functions:
        if not isinstance(fn, dict):
            continue
        raw_entry = fn.get("entry_point")
        entry = normalize_address(raw_entry)
        if not entry or entry == "unknown":
            continue

        name = fn.get("name", "")
        if name:
            names_by_entry.setdefault(entry, []).append(name)

        # Collect sources
        source = fn.get("source_tool", "")
        if source:
            sources_by_entry.setdefault(entry, set()).add(source)
        for prov in fn.get("provenance", []):
            if prov:
                sources_by_entry.setdefault(entry, set()).add(str(prov))

    # Build groups
    groups: Dict[str, FunctionAliasGroup] = {}
    for entry, raw_names in sorted(names_by_entry.items()):
        # Deduplicate and also include cleaned variants
        all_names: List[str] = []
        seen: Set[str] = set()
        for n in raw_names:
            if n not in seen:
                seen.add(n)
                all_names.append(n)
            cleaned = _clean_tool_prefix(n)
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                all_names.append(cleaned)

        if not all_names:
            continue

        canonical = choose_canonical_function_name(all_names, entry)
        sources = sorted(sources_by_entry.get(entry, set()))

        notes = ["aliases share normalized entry point"]
        if len(all_names) > 1:
            notes.append(
                f"{len(all_names)} name variants observed at {entry}"
            )

        groups[entry] = FunctionAliasGroup(
            canonical_name=canonical,
            entry_point=entry,
            aliases=tuple(sorted(set(all_names))),
            sources=tuple(sources),
            evidence_notes=tuple(notes),
        )

    return groups


# ---------------------------------------------------------------------------
# Apply to Unified IR
# ---------------------------------------------------------------------------

def apply_function_aliases_to_ir(
    unified_ir: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build alias groups from the Unified IR and attach them under
    ``data.symbol_aliases``.

    Does NOT remove or rename existing function records.

    Parameters
    ----------
    unified_ir : The Unified IR dict.

    Returns
    -------
    dict
        The same dict, mutated in-place with ``data.symbol_aliases`` added.
    """
    if not isinstance(unified_ir, dict):
        return unified_ir

    # Extract functions from the IR
    data = unified_ir.get("data", unified_ir)
    functions = data.get("functions", [])
    if not isinstance(functions, list):
        return unified_ir

    groups = build_function_alias_groups(functions)

    # Only include groups with more than one alias (interesting groups)
    alias_list = [
        g.to_dict() for g in sorted(groups.values(), key=lambda g: g.entry_point)
    ]

    # Place under data.symbol_aliases
    if "data" in unified_ir and isinstance(unified_ir["data"], dict):
        unified_ir["data"]["symbol_aliases"] = alias_list
    else:
        unified_ir["symbol_aliases"] = alias_list

    return unified_ir
