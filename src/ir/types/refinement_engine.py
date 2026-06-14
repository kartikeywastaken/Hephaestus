# -*- coding: utf-8 -*-
"""
Phase 4B: Type Constraint Refinement Engine

Consumes Phase 4A output (type_recovery.json) and the Unified IR
(unified_ir.json) to produce conservative, constraint-backed refined type
records in semantic_recovery.json.

This module does NOT:
- Emit C source code
- Reconstruct expressions or statements
- Infer structs
- Fabricate type precision
- Break Phase 4A type records (confidence is never lowered)
"""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any, Dict, List, Optional

from src.ir.types.constraints import ConstraintSet
from src.ir.types.models import (
    FUNCTION_KIND_UNKNOWN,
    TYPE_UNKNOWN,
    RecoveredFunctionSemantics,
    RecoveredParameter,
    RecoveredSignature,
    RecoveredType,
    RecoveredVariable,
    RefinedFunctionRecord,
    RefinedVariableRecord,
)
from src.ir.types.propagation import collect_constraints
from src.ir.types.resolver import resolve_constraints

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers for loading Phase 4A records from type_recovery.json dicts
# ---------------------------------------------------------------------------

def _load_recovered_type(d: Dict[str, Any]) -> RecoveredType:
    """Reconstruct a RecoveredType from its to_dict() representation."""
    return RecoveredType(
        type_name=d.get("type", TYPE_UNKNOWN),
        confidence=float(d.get("confidence", 0.2)),
        source=d.get("source", "fallback"),
        notes=list(d.get("notes", [])),
    )


def _load_recovered_parameter(d: Dict[str, Any]) -> RecoveredParameter:
    return RecoveredParameter(
        name=d.get("name", "param"),
        index=int(d.get("index", 0)),
        recovered_type=_load_recovered_type(d.get("type", {})),
        source=d.get("source", "fallback"),
        confidence=float(d.get("confidence", 0.2)),
        notes=list(d.get("notes", [])),
    )


def _load_recovered_variable(d: Dict[str, Any]) -> RecoveredVariable:
    return RecoveredVariable(
        name=d.get("name", "unknown"),
        storage=d.get("storage", "stack"),
        category=d.get("category", "unknown_stack_slot"),
        recovered_type=_load_recovered_type(d.get("type", {})),
        offset_bytes=d.get("offset_bytes"),
        size_bytes=d.get("size_bytes"),
        source=d.get("source", "unified_ir"),
        confidence=float(d.get("confidence", 0.2)),
        notes=list(d.get("notes", [])),
    )


def _load_recovered_signature(d: Dict[str, Any]) -> RecoveredSignature:
    return RecoveredSignature(
        return_type=_load_recovered_type(d.get("return_type", {})),
        parameters=[_load_recovered_parameter(p) for p in d.get("parameters", [])],
        variadic=bool(d.get("variadic", False)),
        confidence=float(d.get("confidence", 0.2)),
        source=d.get("source", "fallback_unknown_signature"),
        notes=list(d.get("notes", [])),
    )


def _load_phase4a_record(func_dict: Dict[str, Any]) -> RecoveredFunctionSemantics:
    """Reconstruct a RecoveredFunctionSemantics from its serialized to_dict() form."""
    return RecoveredFunctionSemantics(
        name=func_dict.get("name", "unknown_function"),
        entry_point=func_dict.get("entry_point", "unknown"),
        function_kind=func_dict.get("function_kind", FUNCTION_KIND_UNKNOWN),
        signature=_load_recovered_signature(func_dict.get("signature", {})),
        variables=[_load_recovered_variable(v) for v in func_dict.get("variables", [])],
        evidence=list(func_dict.get("evidence", [])),
        confidence=float(func_dict.get("confidence", 0.2)),
    )


# ---------------------------------------------------------------------------
# Refinement Engine
# ---------------------------------------------------------------------------

class TypeRefinementEngine:
    """
    Phase 4B type-constraint refinement engine.

    Matches each Phase 4A function record against its Unified IR counterpart,
    collects real instruction-level constraints, and produces
    RefinedFunctionRecord objects with conservatively upgraded types.

    Usage
    -----
    engine = TypeRefinementEngine()
    results = engine.refine(unified_ir, type_recovery)
    """

    def refine(
        self,
        unified_ir: Dict[str, Any],
        type_recovery: Dict[str, Any],
        structuring_regions: Optional[Dict[str, Any]] = None,
    ) -> List[RefinedFunctionRecord]:
        """
        Run Phase 4B refinement.

        Parameters
        ----------
        unified_ir          : The Unified IR dict (Phase 2 output).
        type_recovery       : The Phase 4A type_recovery.json dict.
        structuring_regions : Optional Phase 3 dict (reserved; not used yet).

        Returns
        -------
        list[RefinedFunctionRecord]
            One refined record per Phase 4A function, sorted by
            (entry_point, name) for determinism.
        """
        # --- Validate inputs ---
        if not isinstance(type_recovery, dict):
            logger.warning(
                "Phase 4B: type_recovery is not a dict; returning empty result."
            )
            return []

        phase4a_functions = []
        try:
            phase4a_functions = type_recovery["data"]["functions"]
        except (KeyError, TypeError):
            try:
                phase4a_functions = type_recovery.get("functions", [])
            except AttributeError:
                pass

        if not isinstance(phase4a_functions, list):
            logger.warning(
                "Phase 4B: type_recovery 'functions' is not a list; returning empty."
            )
            return []

        # --- Build Unified IR function index ---
        ir_by_entry: Dict[str, Dict[str, Any]] = {}
        ir_by_name: Dict[str, Dict[str, Any]] = {}

        ir_functions = []
        if isinstance(unified_ir, dict):
            try:
                ir_functions = unified_ir["data"]["functions"]
            except (KeyError, TypeError):
                ir_functions = unified_ir.get("functions", [])

        if isinstance(ir_functions, list):
            for fn in ir_functions:
                if not isinstance(fn, dict):
                    continue
                ep = fn.get("entry_point", "")
                name = fn.get("name", "")
                if ep:
                    ir_by_entry[ep] = fn
                if name:
                    ir_by_name[name] = fn

        # --- Refine each Phase 4A function ---
        results: List[RefinedFunctionRecord] = []
        total_constraints_all = 0

        for func_dict in phase4a_functions:
            if not isinstance(func_dict, dict):
                continue
            try:
                record = self._refine_function(
                    func_dict, ir_by_entry, ir_by_name
                )
                total_constraints_all += record.total_constraints_applied
                results.append(record)
            except Exception as exc:
                name = func_dict.get("name", "unknown_function")
                logger.warning(
                    "Phase 4B: failed to refine function %s: %s", name, exc
                )
                # Fallback: preserve Phase 4A record as-is
                try:
                    phase4a = _load_phase4a_record(func_dict)
                    results.append(self._make_fallback_record(phase4a, reason=str(exc)))
                except Exception:
                    pass  # If even the fallback fails, skip this record

        # Sort deterministically
        results.sort(key=lambda r: (r.entry_point or "", r.name or ""))

        logger.info(
            "Phase 4B: refined %d function(s); %d total constraints applied.",
            len(results),
            total_constraints_all,
        )
        return results

    # ------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------

    def _refine_function(
        self,
        func_dict: Dict[str, Any],
        ir_by_entry: Dict[str, Dict[str, Any]],
        ir_by_name: Dict[str, Dict[str, Any]],
    ) -> RefinedFunctionRecord:
        """Refine a single Phase 4A function record."""
        phase4a = _load_phase4a_record(func_dict)

        # Locate the corresponding Unified IR function
        func_ir = (
            ir_by_entry.get(phase4a.entry_point)
            or ir_by_name.get(phase4a.name)
            or {}
        )

        # Collect constraints from real instruction evidence
        cset: ConstraintSet = collect_constraints(func_ir, phase4a)

        if len(cset) == 0:
            return self._make_fallback_record(phase4a)

        # Refine variables
        total_applied = 0
        refined_vars: List[RefinedVariableRecord] = []
        for var in phase4a.variables:
            constraints_for_var = cset.all_for_lhs(var.name)
            original_type_name = var.recovered_type.type_name
            refined_type = resolve_constraints(var.recovered_type, constraints_for_var)
            changed = int(refined_type.type_name != original_type_name)
            total_applied += changed
            refined_vars.append(RefinedVariableRecord(
                name=var.name,
                refined_type=refined_type,
                constraints_applied=changed,
                phase4a_type=original_type_name,
            ))

        # Refine signature parameters
        refined_params: List[RecoveredParameter] = []
        for param in phase4a.signature.parameters:
            constraints_for_param = cset.all_for_lhs(param.name)
            original_type_name = param.recovered_type.type_name
            refined_type = resolve_constraints(param.recovered_type, constraints_for_param)
            changed = int(refined_type.type_name != original_type_name)
            total_applied += changed
            refined_params.append(RecoveredParameter(
                name=param.name,
                index=param.index,
                recovered_type=refined_type,
                source=param.source,
                confidence=refined_type.confidence,
                notes=list(refined_type.notes),
            ))

        refined_signature = RecoveredSignature(
            return_type=phase4a.signature.return_type,
            parameters=refined_params,
            variadic=phase4a.signature.variadic,
            confidence=max(
                phase4a.signature.confidence,
                max((p.confidence for p in refined_params), default=phase4a.signature.confidence),
            ),
            source=phase4a.signature.source,
            notes=list(phase4a.signature.notes),
        )

        # Refined function-level confidence
        max_constraint_priority = max(
            (c.source_priority for c in cset), default=0
        )
        refined_confidence = max(
            phase4a.confidence,
            min(max_constraint_priority / 100.0, 0.95),
        )

        evidence = list(phase4a.evidence) + [
            f"{len(cset)} constraint(s) collected; {total_applied} applied"
        ]

        return RefinedFunctionRecord(
            name=phase4a.name,
            entry_point=phase4a.entry_point,
            function_kind=phase4a.function_kind,
            refined_signature=refined_signature,
            variables=refined_vars,
            total_constraints_applied=total_applied,
            confidence=refined_confidence,
            evidence=evidence,
        )

    def _make_fallback_record(
        self,
        phase4a: RecoveredFunctionSemantics,
        reason: str = "",
    ) -> RefinedFunctionRecord:
        """
        Produce a RefinedFunctionRecord that preserves Phase 4A types verbatim.

        Used when no instruction evidence is available or refinement fails.
        """
        note = (
            "No instruction-level evidence available; Phase 4A types preserved"
            if not reason
            else f"Refinement failed ({reason}); Phase 4A types preserved"
        )

        refined_vars = [
            RefinedVariableRecord(
                name=v.name,
                refined_type=v.recovered_type,
                constraints_applied=0,
                phase4a_type=v.recovered_type.type_name,
            )
            for v in phase4a.variables
        ]

        return RefinedFunctionRecord(
            name=phase4a.name,
            entry_point=phase4a.entry_point,
            function_kind=phase4a.function_kind,
            refined_signature=phase4a.signature,
            variables=refined_vars,
            total_constraints_applied=0,
            confidence=phase4a.confidence,
            evidence=list(phase4a.evidence) + [note],
        )
