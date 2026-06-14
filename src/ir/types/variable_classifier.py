# -*- coding: utf-8 -*-
"""
Phase 4A: Variable Classifier

Converts raw variable records from the Unified IR into typed RecoveredVariable
instances using conservative, name-based heuristics.

Classification is purely name-driven in Phase 4A. No dataflow analysis is
performed. Unknown or ambiguous names always fall back to the `unknown_stack_slot`
category with type `unknown`.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.ir.types.models import (
    RecoveredVariable,
    RecoveredType,
    TYPE_INT32,
    TYPE_POINTER,
    TYPE_UNKNOWN,
    STORAGE_STACK,
    STORAGE_REGISTER,
    STORAGE_GLOBAL,
    STORAGE_UNKNOWN,
    CATEGORY_PARAMETER,
    CATEGORY_LOCAL,
    CATEGORY_UNKNOWN_STACK_SLOT,
)


# ---------------------------------------------------------------------------
# Helpers: raw variable field extraction with defensive parsing
# ---------------------------------------------------------------------------

def _get_name(raw_var: Dict[str, Any]) -> str:
    """Extract variable name from any of the commonly used field names."""
    for key in ("name", "variable_name", "var_name"):
        val = raw_var.get(key)
        if val and isinstance(val, str):
            return val.strip()
    return ""


def _get_offset(raw_var: Dict[str, Any]) -> Optional[int]:
    """Extract byte offset from any of the commonly used field names."""
    for key in ("offset_bytes", "offset", "stack_offset"):
        val = raw_var.get(key)
        if val is not None:
            try:
                return int(val)
            except (TypeError, ValueError):
                continue
    return None


def _get_size(raw_var: Dict[str, Any]) -> Optional[int]:
    """Extract size in bytes from any of the commonly used field names."""
    for key in ("size_bytes", "size"):
        val = raw_var.get(key)
        if val is not None:
            try:
                return int(val)
            except (TypeError, ValueError):
                continue
    return None


def _get_storage(raw_var: Dict[str, Any]) -> str:
    """Extract storage kind, defaulting to 'stack' if not specified."""
    for key in ("storage", "storage_kind"):
        val = raw_var.get(key)
        if val and isinstance(val, str):
            normalized = val.strip().lower()
            if normalized in (STORAGE_STACK, STORAGE_REGISTER, STORAGE_GLOBAL, STORAGE_UNKNOWN):
                return normalized
    return STORAGE_STACK  # Phase 4A default


def _get_source_provenance(raw_var: Dict[str, Any]) -> str:
    """Extract source provenance field."""
    for key in ("source", "provenance", "tool"):
        val = raw_var.get(key)
        if val and isinstance(val, str):
            return val.strip()
    return "unified_ir"


# ---------------------------------------------------------------------------
# Main classification entry point
# ---------------------------------------------------------------------------

def classify_variable(raw_var: Any) -> RecoveredVariable:
    """
    Classify a raw Unified IR variable record into a RecoveredVariable.

    Classification is name-based and conservative. The following priority
    order is used:

    1. Exact name ``argc``  → parameter, int32, confidence 0.9
    2. Exact name ``argv``  → parameter, pointer, confidence 0.85
    3. Prefix ``arg``       → parameter, unknown, confidence 0.45
    4. Prefix ``param``     → parameter, unknown, confidence 0.45
    5. Prefix ``local_``    → local, unknown, confidence 0.4
    6. Prefix ``var_``      → local, unknown, confidence 0.35
    7. Fallback             → unknown_stack_slot, unknown, confidence 0.2

    Parameters
    ----------
    raw_var : A variable dict from the Unified IR ``stack_variables`` or
              ``local_variables`` list.

    Returns
    -------
    RecoveredVariable
        Classified variable with type annotation, category, and evidence.
    """
    if not isinstance(raw_var, dict):
        name = str(raw_var) if raw_var is not None else ""
        raw_var = {"name": name}

    name = _get_name(raw_var)
    offset_bytes = _get_offset(raw_var)
    size_bytes = _get_size(raw_var)
    storage = _get_storage(raw_var)
    source_prov = _get_source_provenance(raw_var)

    # Use lowercase for all name comparisons
    name_lower = name.lower()

    # --- Rule 1: exact "argc" ---
    if name_lower == "argc":
        return RecoveredVariable(
            name=name,
            storage=storage,
            category=CATEGORY_PARAMETER,
            recovered_type=RecoveredType(
                type_name=TYPE_INT32,
                confidence=0.9,
                source="argc_name_heuristic",
                notes=[],
            ),
            offset_bytes=offset_bytes,
            size_bytes=size_bytes,
            source=source_prov or "unified_ir.stack_variables",
            confidence=0.9,
            notes=["classified via argc_name_heuristic"],
        )

    # --- Rule 2: exact "argv" ---
    if name_lower == "argv":
        return RecoveredVariable(
            name=name,
            storage=storage,
            category=CATEGORY_PARAMETER,
            recovered_type=RecoveredType(
                type_name=TYPE_POINTER,
                confidence=0.85,
                source="argv_name_heuristic",
                notes=[],
            ),
            offset_bytes=offset_bytes,
            size_bytes=size_bytes,
            source=source_prov or "unified_ir.stack_variables",
            confidence=0.85,
            notes=["classified via argv_name_heuristic"],
        )

    # --- Rule 3: prefix "arg" (but not "argv" / "argc" already caught above) ---
    if name_lower.startswith("arg"):
        return RecoveredVariable(
            name=name,
            storage=storage,
            category=CATEGORY_PARAMETER,
            recovered_type=RecoveredType(
                type_name=TYPE_UNKNOWN,
                confidence=0.45,
                source="argument_name_heuristic",
                notes=[],
            ),
            offset_bytes=offset_bytes,
            size_bytes=size_bytes,
            source=source_prov or "unified_ir.stack_variables",
            confidence=0.45,
            notes=["classified via argument_name_heuristic"],
        )

    # --- Rule 4: prefix "param" ---
    if name_lower.startswith("param"):
        return RecoveredVariable(
            name=name,
            storage=storage,
            category=CATEGORY_PARAMETER,
            recovered_type=RecoveredType(
                type_name=TYPE_UNKNOWN,
                confidence=0.45,
                source="parameter_name_heuristic",
                notes=[],
            ),
            offset_bytes=offset_bytes,
            size_bytes=size_bytes,
            source=source_prov or "unified_ir.stack_variables",
            confidence=0.45,
            notes=["classified via parameter_name_heuristic"],
        )

    # --- Rule 5: prefix "local_" ---
    if name_lower.startswith("local_"):
        return RecoveredVariable(
            name=name,
            storage=storage,
            category=CATEGORY_LOCAL,
            recovered_type=RecoveredType(
                type_name=TYPE_UNKNOWN,
                confidence=0.4,
                source="local_name_heuristic",
                notes=[],
            ),
            offset_bytes=offset_bytes,
            size_bytes=size_bytes,
            source=source_prov or "unified_ir.stack_variables",
            confidence=0.4,
            notes=["classified via local_name_heuristic"],
        )

    # --- Rule 6: prefix "var_" ---
    if name_lower.startswith("var_"):
        return RecoveredVariable(
            name=name,
            storage=storage,
            category=CATEGORY_LOCAL,
            recovered_type=RecoveredType(
                type_name=TYPE_UNKNOWN,
                confidence=0.35,
                source="var_name_heuristic",
                notes=[],
            ),
            offset_bytes=offset_bytes,
            size_bytes=size_bytes,
            source=source_prov or "unified_ir.stack_variables",
            confidence=0.35,
            notes=["classified via var_name_heuristic"],
        )

    # --- Rule 7: fallback ---
    fallback_name = name if name else "unknown"
    return RecoveredVariable(
        name=fallback_name,
        storage=storage,
        category=CATEGORY_UNKNOWN_STACK_SLOT,
        recovered_type=RecoveredType(
            type_name=TYPE_UNKNOWN,
            confidence=0.2,
            source="fallback",
            notes=[],
        ),
        offset_bytes=offset_bytes,
        size_bytes=size_bytes,
        source=source_prov or "unified_ir",
        confidence=0.2,
        notes=["no heuristic matched; classified as unknown_stack_slot"],
    )
