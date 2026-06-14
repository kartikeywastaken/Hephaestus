# -*- coding: utf-8 -*-
"""
Phase 4A: Type Recovery Engine

Implements the main Phase 4A semantic inference pipeline. Consumes a Unified IR
dict (and optionally a structuring_regions dict) and produces a list of
RecoveredFunctionSemantics objects.

Recovery priority order per function:
  1. Known signature database (library functions)
  2. Main/entrypoint heuristic (_main, main)
  3. User function: recover parameters from classified variables
  4. Fallback unknown signature

This module does NOT emit C source code, does NOT perform full type propagation,
and does NOT invent types without evidence.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from src.ir.types.models import (
    RecoveredFunctionSemantics,
    RecoveredParameter,
    RecoveredSignature,
    RecoveredType,
    RecoveredVariable,
    TYPE_INT32,
    TYPE_POINTER,
    TYPE_BOOL,
    TYPE_UNKNOWN,
    CATEGORY_PARAMETER,
    FUNCTION_KIND_LIBRARY,
    FUNCTION_KIND_ENTRYPOINT,
    FUNCTION_KIND_USER,
    FUNCTION_KIND_UNKNOWN,
)
from src.ir.types.signatures import (
    get_known_signature,
    is_known_library_function,
    normalize_symbol_name,
)
from src.ir.types.variable_classifier import classify_variable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers: defensive field extraction from the Unified IR function dict
# ---------------------------------------------------------------------------

def _get_function_name(func: Any) -> str:
    """Extract canonical function name from any of the commonly used field names."""
    if not isinstance(func, dict):
        return "unknown_function"
    for key in ("name", "canonical_name", "function_name"):
        val = func.get(key)
        if val and isinstance(val, str) and val.strip():
            return val.strip()
    return "unknown_function"


def _get_entry_point(func: Any) -> str:
    """Extract entry-point address string from a function record."""
    if not isinstance(func, dict):
        return "unknown"
    for key in ("entry_point", "entry", "address", "addr", "start_address"):
        val = func.get(key)
        if val is not None:
            return str(val).strip().lower()
    return "unknown"


def _get_provenance_sources(func: Any) -> List[str]:
    """
    Extract all provenance source strings from a function record.
    Handles list and string forms.
    """
    if not isinstance(func, dict):
        return []
    for key in ("provenance", "sources", "source", "tool"):
        val = func.get(key)
        if val is None:
            continue
        if isinstance(val, list):
            return [str(v).lower() for v in val]
        if isinstance(val, str) and val.strip():
            return [val.strip().lower()]
    return []


def _get_raw_variables(func: Any) -> List[Dict[str, Any]]:
    """
    Collect all raw variable dicts from the function, checking multiple field names.
    Handles both list-of-dicts and list-of-strings (from local_variables field).
    """
    raw: List[Dict[str, Any]] = []
    if not isinstance(func, dict):
        return raw

    for field_name in ("stack_variables", "variables", "locals", "local_variables",
                       "params", "parameters"):
        items = func.get(field_name, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                raw.append(item)
            elif isinstance(item, str) and item.strip():
                # local_variables may be a list of plain strings (from Phase 2 assembler)
                raw.append({"name": item})

    return raw


# ---------------------------------------------------------------------------
# Function kind classifier
# ---------------------------------------------------------------------------

def classify_function_kind(func: Dict[str, Any], name: str) -> str:
    """
    Classify a function as library, entrypoint, user, or unknown.

    Priority:
      1. known signature database → library
      2. name is main or _main   → entrypoint
      3. provenance has a tool name → user
      4. otherwise               → unknown
    """
    if is_known_library_function(name):
        return FUNCTION_KIND_LIBRARY

    normalized = normalize_symbol_name(name)
    if normalized in ("main",):
        return FUNCTION_KIND_ENTRYPOINT

    provenance = _get_provenance_sources(func)
    for src in provenance:
        if src in ("ghidra", "radare2", "r2", "ida"):
            return FUNCTION_KIND_USER

    return FUNCTION_KIND_UNKNOWN


# ---------------------------------------------------------------------------
# Signature recovery helpers
# ---------------------------------------------------------------------------

def _fallback_unknown_signature() -> RecoveredSignature:
    return RecoveredSignature(
        return_type=RecoveredType(
            type_name=TYPE_UNKNOWN,
            confidence=0.2,
            source="fallback_unknown_return",
            notes=[],
        ),
        parameters=[],
        variadic=False,
        confidence=0.2,
        source="fallback_unknown_signature",
        notes=[],
    )


def _recover_known_library_signature(name: str) -> RecoveredSignature:
    """Convert a known signature DB entry into a RecoveredSignature."""
    known = get_known_signature(name)
    if known is None:
        return _fallback_unknown_signature()
    return known.to_recovered_signature()


def _recover_main_signature(
    variables: List[RecoveredVariable],
) -> Tuple[RecoveredSignature, float]:
    """
    Apply the main/entrypoint heuristic.

    If argc and argv are both present in the classified variables, produce:
      int main(int argc, char **argv)  [confidence 0.9]
    Otherwise produce:
      int main(void)                   [confidence 0.8]

    Returns (RecoveredSignature, confidence).
    """
    var_names = {v.name.lower() for v in variables}
    has_argc = "argc" in var_names
    has_argv = "argv" in var_names

    if has_argc and has_argv:
        argc_param = RecoveredParameter(
            name="argc",
            index=0,
            recovered_type=RecoveredType(
                type_name=TYPE_INT32,
                confidence=0.9,
                source="main_argc_heuristic",
                notes=[],
            ),
            source="main_argc_heuristic",
            confidence=0.9,
            notes=[],
        )
        argv_param = RecoveredParameter(
            name="argv",
            index=1,
            recovered_type=RecoveredType(
                type_name=TYPE_POINTER,
                confidence=0.9,
                source="main_argv_heuristic",
                notes=[],
            ),
            source="main_argv_heuristic",
            confidence=0.9,
            notes=[],
        )
        sig = RecoveredSignature(
            return_type=RecoveredType(
                type_name=TYPE_INT32,
                confidence=0.9,
                source="main_function_heuristic",
                notes=[],
            ),
            parameters=[argc_param, argv_param],
            variadic=False,
            confidence=0.9,
            source="main_function_heuristic",
            notes=[],
        )
        return sig, 0.9

    # No argc/argv — emit int main(void)
    sig = RecoveredSignature(
        return_type=RecoveredType(
            type_name=TYPE_INT32,
            confidence=0.8,
            source="main_function_heuristic",
            notes=[],
        ),
        parameters=[],
        variadic=False,
        confidence=0.8,
        source="main_function_heuristic",
        notes=[],
    )
    return sig, 0.8


def _recover_user_signature(
    name: str,
    variables: List[RecoveredVariable],
) -> RecoveredSignature:
    """
    Recover a conservative signature for a user-defined function.

    Parameters are extracted from the classified variables categorized as
    `parameter`. Non-parameter variables are not used here.

    Return type is unknown by default (confidence 0.2).
    Optional: boolean_name_heuristic for is_*/has_*/check_* prefixes.
    """
    # --- Return type ---
    normalized = normalize_symbol_name(name)
    bool_prefixes = ("is_", "has_", "check_")
    if any(normalized.startswith(p) for p in bool_prefixes):
        ret_type = RecoveredType(
            type_name=TYPE_BOOL,
            confidence=0.35,
            source="boolean_name_heuristic",
            notes=["function name suggests boolean return"],
        )
    else:
        ret_type = RecoveredType(
            type_name=TYPE_UNKNOWN,
            confidence=0.2,
            source="fallback_unknown_return",
            notes=[],
        )

    # --- Parameters: only variables classified as parameter ---
    param_vars = [v for v in variables if v.category == CATEGORY_PARAMETER]

    # Deduplicate by (name, index); sort deterministically by offset then name
    seen_param_keys: Set[Tuple[str, Optional[int]]] = set()
    unique_param_vars: List[RecoveredVariable] = []
    for v in param_vars:
        key = (v.name, v.offset_bytes)
        if key not in seen_param_keys:
            seen_param_keys.add(key)
            unique_param_vars.append(v)

    # Sort parameters deterministically:
    # 1. offset (ascending, None treated as 999999)
    # 2. size (ascending, None treated as 0)
    # 3. name (lexicographically ascending)
    def param_sort_key(v: RecoveredVariable):
        offset = v.offset_bytes if v.offset_bytes is not None else 999999
        size = v.size_bytes if v.size_bytes is not None else 0
        name_val = v.name or ""
        return (offset, size, name_val)

    unique_param_vars.sort(key=param_sort_key)

    parameters = []
    for idx, v in enumerate(unique_param_vars):
        parameters.append(RecoveredParameter(
            name=v.name,
            index=idx,
            recovered_type=v.recovered_type,
            source=v.source,
            confidence=v.confidence,
            notes=list(v.notes),
        ))

    # Signature confidence: derived from the highest-confidence parameter evidence
    sig_confidence = 0.2
    if parameters:
        sig_confidence = max(p.confidence for p in parameters)
        # Cap to avoid over-confidence for name-only heuristics
        sig_confidence = min(sig_confidence, 0.6)

    return RecoveredSignature(
        return_type=ret_type,
        parameters=parameters,
        variadic=False,
        confidence=sig_confidence,
        source="user_function_parameter_recovery",
        notes=[],
    )


# ---------------------------------------------------------------------------
# Variable deduplication
# ---------------------------------------------------------------------------

def _deduplicate_variables(
    variables: List[RecoveredVariable],
) -> List[RecoveredVariable]:
    """
    Deduplicate variables by (name, offset_bytes, storage).
    Preserves deterministic ordering of first occurrence.
    """
    seen: Set[Tuple[str, Optional[int], str]] = set()
    result: List[RecoveredVariable] = []
    for v in variables:
        key = (v.name, v.offset_bytes, v.storage)
        if key not in seen:
            seen.add(key)
            result.append(v)
    return result


# ---------------------------------------------------------------------------
# Main recovery engine
# ---------------------------------------------------------------------------

class TypeRecoveryEngine:
    """
    Phase 4A type inference engine.

    Iterates over functions in the Unified IR and produces conservative
    RecoveredFunctionSemantics records.

    Usage
    -----
    engine = TypeRecoveryEngine()
    results = engine.recover(unified_ir, structuring_regions=None)
    """

    def recover(
        self,
        unified_ir: Dict[str, Any],
        structuring_regions: Optional[Dict[str, Any]] = None,
    ) -> List[RecoveredFunctionSemantics]:
        """
        Run Phase 4A recovery over all functions in the Unified IR.

        Parameters
        ----------
        unified_ir          : The canonical Unified IR dict (schema 2.0.0).
        structuring_regions : Optional Phase 3 structuring tree dict. Currently
                              reserved for future use in Phase 4B.

        Returns
        -------
        list[RecoveredFunctionSemantics]
            One record per function, in stable deterministic order.
        """
        # Defensively verify input is a dictionary
        if not isinstance(unified_ir, dict):
            logger.warning("Phase 4A: unified_ir is not a dict; returning empty result.")
            return []

        # Defensively locate the functions list
        functions: List[Dict[str, Any]] = []
        if "data" in unified_ir and "functions" in unified_ir["data"]:
            functions = unified_ir["data"]["functions"]
        elif "functions" in unified_ir:
            functions = unified_ir["functions"]

        if not isinstance(functions, list):
            logger.warning("Phase 4A: functions is not a list in Unified IR; returning empty result.")
            return []

        results: List[RecoveredFunctionSemantics] = []
        for func in functions:
            try:
                sem = self._recover_function(func)
                results.append(sem)
            except Exception as exc:
                fname = _get_function_name(func)
                logger.warning("Phase 4A: failed to recover function %s: %s", fname, exc)
                # Emit a minimal fallback record rather than crashing
                results.append(RecoveredFunctionSemantics(
                    name=fname,
                    entry_point=_get_entry_point(func),
                    function_kind=FUNCTION_KIND_UNKNOWN,
                    signature=_fallback_unknown_signature(),
                    variables=[],
                    evidence=["recovery failed; fallback record emitted"],
                    confidence=0.1,
                ))

        # Sort the functions list deterministically:
        # 1. entry_point (ascending address)
        # 2. name (lexicographical ascending)
        results.sort(key=lambda fn: (fn.entry_point or "", fn.name or ""))

        logger.info("Phase 4A: recovered semantics for %d function(s).", len(results))
        return results

    def _recover_function(self, func: Dict[str, Any]) -> RecoveredFunctionSemantics:
        """Recover semantics for a single function."""
        name = _get_function_name(func)
        entry_point = _get_entry_point(func)
        evidence: List[str] = ["function recovered from unified_ir"]

        # --- Step 1: classify raw variables ---
        raw_vars = _get_raw_variables(func)
        classified_vars = [classify_variable(rv) for rv in raw_vars]
        deduped_vars = _deduplicate_variables(classified_vars)

        # Sort variables deterministically according to the following priority:
        # 1. Category priority: parameter (0) < local (1) < unknown_stack_slot (2) < other (3)
        # 2. Storage priority: register (0) < stack (1) < global (2) < unknown (3) < other (4)
        # 3. Offset (ascending, None treated as 999999)
        # 4. Size (ascending, None treated as 0)
        # 5. Name (lexicographically ascending)
        def var_sort_key(v: RecoveredVariable):
            category_order = {
                "parameter": 0,
                "local": 1,
                "unknown_stack_slot": 2
            }
            cat_val = category_order.get(v.category, 3)

            storage_order = {
                "register": 0,
                "stack": 1,
                "global": 2,
                "unknown": 3
            }
            storage_val = storage_order.get(v.storage, 4)

            offset = v.offset_bytes if v.offset_bytes is not None else 999999
            size = v.size_bytes if v.size_bytes is not None else 0
            name_val = v.name or ""
            return (cat_val, storage_val, offset, size, name_val)

        deduped_vars.sort(key=var_sort_key)

        # --- Step 2: determine function kind ---
        func_kind = classify_function_kind(func, name)

        # --- Step 3: recover signature via priority chain ---
        normalized = normalize_symbol_name(name)
        signature: RecoveredSignature
        function_confidence: float

        if func_kind == FUNCTION_KIND_LIBRARY:
            # Priority 1: known signature database
            signature = _recover_known_library_signature(name)
            function_confidence = 1.0
            evidence.append("signature recovered from known signature database")

        elif normalized in ("main",) or func_kind == FUNCTION_KIND_ENTRYPOINT:
            # Priority 2: main/entrypoint heuristic
            func_kind = FUNCTION_KIND_ENTRYPOINT
            signature, function_confidence = _recover_main_signature(deduped_vars)
            evidence.append("signature inferred using main function heuristic")

        else:
            # Priority 3 / 4: user function parameter recovery (with fallback)
            if func_kind not in (FUNCTION_KIND_USER, FUNCTION_KIND_UNKNOWN):
                func_kind = FUNCTION_KIND_USER
            signature = _recover_user_signature(name, deduped_vars)
            function_confidence = signature.confidence
            if signature.parameters:
                evidence.append(
                    f"parameters recovered from {len(signature.parameters)} classified variable(s)"
                )
            else:
                evidence.append("no parameter variables found; fallback signature emitted")

        return RecoveredFunctionSemantics(
            name=name,
            entry_point=entry_point,
            function_kind=func_kind,
            signature=signature,
            variables=deduped_vars,
            evidence=evidence,
            confidence=function_confidence,
        )


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def recover_types(
    unified_ir: Dict[str, Any],
    structuring_regions: Optional[Dict[str, Any]] = None,
) -> List[RecoveredFunctionSemantics]:
    """
    Convenience wrapper around TypeRecoveryEngine.recover().

    Parameters
    ----------
    unified_ir          : Canonical Unified IR dict.
    structuring_regions : Optional Phase 3 structuring regions dict.

    Returns
    -------
    list[RecoveredFunctionSemantics]
    """
    engine = TypeRecoveryEngine()
    return engine.recover(unified_ir, structuring_regions)
