# -*- coding: utf-8 -*-
"""
Phase 4D: Final Phase 4 Semantic Artifact Merger

Combines the three Phase 4 artifacts:
    type_recovery.json      (Phase 4A — required)
    semantic_recovery.json  (Phase 4B — optional)
    layout_recovery.json    (Phase 4C — optional)

into one clean handoff artifact:
    phase4_semantics.json

This module does NOT:
- Infer new types
- Emit structs or field names
- Compute confidence or similarity scores
- Emit C source code, expressions, or statements
- Modify the upstream Phase 4A/4B/4C artifacts

Core Rule: Missing evidence is acceptable. Fabricated evidence is not.
Phase 4D only summarizes and merges evidence that already exists.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "4D.0.0"


@dataclass
class Phase4FunctionSemantics:
    """
    Merged Phase 4 semantic record for a single function.

    Contains the union of Phase 4A, 4B, and 4C data, plus synthesized
    known_facts and uncertainties lists.
    """
    name: str = "unknown_function"
    entry_point: str = "unknown"
    function_kind: str = "unknown"

    # Phase 4A (type_recovery)
    recovered_signature: Dict[str, Any] = field(default_factory=dict)
    variables: List[Dict[str, Any]] = field(default_factory=list)
    parameters: List[Dict[str, Any]] = field(default_factory=list)

    # Phase 4B (semantic_recovery)
    refined_signature: Dict[str, Any] = field(default_factory=dict)
    refined_variables: List[Dict[str, Any]] = field(default_factory=list)
    refined_parameters: List[Dict[str, Any]] = field(default_factory=list)
    constraints_summary: Dict[str, Any] = field(default_factory=lambda: {
        "total_constraints_applied": 0,
        "variables_with_constraints": 0,
        "parameters_with_constraints": 0,
    })

    # Phase 4C (layout_recovery)
    layout_candidates: List[Dict[str, Any]] = field(default_factory=list)
    unbound_memory_accesses: List[Dict[str, Any]] = field(default_factory=list)

    # Synthesized facts and uncertainty
    known_facts: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "entry_point": self.entry_point,
            "function_kind": self.function_kind,
            "recovered_signature": dict(self.recovered_signature),
            "refined_signature": dict(self.refined_signature),
            "variables": list(self.variables),
            "parameters": list(self.parameters),
            "refined_variables": list(self.refined_variables),
            "refined_parameters": list(self.refined_parameters),
            "constraints_summary": dict(self.constraints_summary),
            "layout_candidates": list(self.layout_candidates),
            "unbound_memory_accesses": list(self.unbound_memory_accesses),
            "known_facts": list(self.known_facts),
            "uncertainties": list(self.uncertainties),
        }


@dataclass
class Phase4SemanticsArtifact:
    """
    The complete Phase 4D output artifact.
    """
    schema_version: str = SCHEMA_VERSION
    provenance: Dict[str, Any] = field(default_factory=dict)
    functions: List[Phase4FunctionSemantics] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=lambda: {
        "functions_total": 0,
        "functions_with_refinement": 0,
        "functions_with_layout_candidates": 0,
        "total_layout_candidates": 0,
        "total_unbound_memory_accesses": 0,
        "total_constraints_applied": 0,
    })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "provenance": dict(self.provenance),
            "data": {
                "functions": [f.to_dict() for f in self.functions],
                "summary": dict(self.summary),
            },
        }


# ---------------------------------------------------------------------------
# Helpers — safe extraction from dicts
# ---------------------------------------------------------------------------

def _safe_list(d: Any, key: str) -> list:
    """Return d[key] if it's a list, else []."""
    if not isinstance(d, dict):
        return []
    val = d.get(key)
    return val if isinstance(val, list) else []


def _safe_dict(d: Any, key: str) -> dict:
    """Return d[key] if it's a dict, else {}."""
    if not isinstance(d, dict):
        return {}
    val = d.get(key)
    return val if isinstance(val, dict) else {}


def _safe_str(d: Any, key: str, default: str = "") -> str:
    if not isinstance(d, dict):
        return default
    val = d.get(key)
    return str(val) if val is not None else default


def _safe_int(d: Any, key: str, default: int = 0) -> int:
    if not isinstance(d, dict):
        return default
    val = d.get(key)
    if val is None:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Extract function lists from each artifact
# ---------------------------------------------------------------------------

def _extract_type_recovery_functions(
    type_recovery: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Extract the function list from type_recovery.json."""
    try:
        funcs = type_recovery["data"]["functions"]
    except (KeyError, TypeError):
        funcs = type_recovery.get("functions", [])
    return funcs if isinstance(funcs, list) else []


def _extract_semantic_recovery_functions(
    semantic_recovery: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Extract the function list from semantic_recovery.json."""
    if semantic_recovery is None or not isinstance(semantic_recovery, dict):
        return []
    try:
        funcs = semantic_recovery["data"]["functions"]
    except (KeyError, TypeError):
        funcs = semantic_recovery.get("functions", [])
    return funcs if isinstance(funcs, list) else []


def _extract_layout_candidates(
    layout_recovery: Optional[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Extract (layout_candidates, unbound_memory_accesses) from layout_recovery.json."""
    if layout_recovery is None:
        return [], []
    try:
        data = layout_recovery["data"]
    except (KeyError, TypeError):
        data = layout_recovery
    if not isinstance(data, dict):
        return [], []
    candidates = data.get("layout_candidates", [])
    unbound = data.get("unbound_memory_accesses", [])
    return (
        candidates if isinstance(candidates, list) else [],
        unbound if isinstance(unbound, list) else [],
    )


# ---------------------------------------------------------------------------
# Function matching
# ---------------------------------------------------------------------------

def _build_function_index(
    functions: List[Dict[str, Any]],
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Build lookup indices for a function list.

    Returns (by_entry_point, by_name) dicts.
    Skips non-dict entries.
    """
    by_entry: Dict[str, Dict[str, Any]] = {}
    by_name: Dict[str, Dict[str, Any]] = {}
    for fn in functions:
        if not isinstance(fn, dict):
            continue
        ep = _safe_str(fn, "entry_point")
        name = _safe_str(fn, "name")
        if ep and ep != "unknown":
            by_entry[ep] = fn
        if name and name != "unknown_function":
            by_name[name] = fn
    return by_entry, by_name


def _match_function(
    entry_point: str,
    name: str,
    by_entry: Dict[str, Dict[str, Any]],
    by_name: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Match a function by entry_point (preferred) then name (fallback).

    Never merges two functions with conflicting entry points just because
    names are similar.
    """
    # Prefer entry_point exact match
    if entry_point and entry_point != "unknown":
        found = by_entry.get(entry_point)
        if found is not None:
            return found

    # Name fallback — only if entry_point didn't match
    if name and name != "unknown_function":
        found = by_name.get(name)
        if found is not None:
            # Safety check: if the found record has a different entry_point,
            # and we also have a non-trivial entry_point, don't merge
            found_ep = _safe_str(found, "entry_point")
            if (entry_point and entry_point != "unknown" and
                    found_ep and found_ep != "unknown" and
                    found_ep != entry_point):
                return None  # conflicting entry points — refuse merge
            return found

    return None


# ---------------------------------------------------------------------------
# Layout attachment
# ---------------------------------------------------------------------------

def _attach_layouts(
    fn_entry: str,
    fn_name: str,
    all_candidates: List[Dict[str, Any]],
    all_unbound: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Find layout candidates and unbound accesses for a specific function.

    Match by function_entry (preferred), then function_name (fallback).
    """
    matched_candidates: List[Dict[str, Any]] = []
    matched_unbound: List[Dict[str, Any]] = []

    for c in all_candidates:
        if not isinstance(c, dict):
            continue
        c_entry = _safe_str(c, "function_entry")
        c_name = _safe_str(c, "function_name")
        if (c_entry and c_entry == fn_entry) or (c_name and c_name == fn_name):
            matched_candidates.append(c)

    for u in all_unbound:
        if not isinstance(u, dict):
            continue
        u_entry = _safe_str(u, "function_entry")
        u_name = _safe_str(u, "function_name")
        if (u_entry and u_entry == fn_entry) or (u_name and u_name == fn_name):
            matched_unbound.append(u)

    # Sort deterministically
    matched_candidates.sort(
        key=lambda c: (
            _safe_str(c, "function_entry"),
            _safe_str(c, "base_id"),
            _safe_str(c, "layout_kind"),
        )
    )
    matched_unbound.sort(
        key=lambda u: (
            _safe_str(u, "function_entry"),
            _safe_str(u, "base_id"),
            _safe_str(u, "instr_address", _safe_str(u, "instruction_address")),
        )
    )

    return matched_candidates, matched_unbound


# ---------------------------------------------------------------------------
# Variable deduplication
# ---------------------------------------------------------------------------

def _dedup_by_name(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate a list of dicts by the 'name' key, keeping first occurrence."""
    seen: set = set()
    result: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "")
        if name and name in seen:
            continue
        if name:
            seen.add(name)
        result.append(item)
    return sorted(result, key=lambda x: x.get("name", ""))


# ---------------------------------------------------------------------------
# Known facts & uncertainties generation
# ---------------------------------------------------------------------------

def _generate_known_facts(fn: Phase4FunctionSemantics) -> List[str]:
    """Generate known_facts from actual counts. Only include true facts."""
    facts: List[str] = []

    n_vars = len(fn.variables)
    if n_vars > 0:
        facts.append(f"Function has {n_vars} recovered variable(s).")

    n_params = len(fn.parameters)
    if n_params > 0:
        facts.append(f"Function has {n_params} recovered parameter(s).")

    n_refined = fn.constraints_summary.get("variables_with_constraints", 0)
    if n_refined > 0:
        facts.append(
            f"{n_refined} variable(s) received instruction-backed refinement."
        )

    n_constraints = fn.constraints_summary.get("total_constraints_applied", 0)
    if n_constraints > 0:
        facts.append(f"{n_constraints} type constraint(s) were applied.")

    n_ref_params = fn.constraints_summary.get("parameters_with_constraints", 0)
    if n_ref_params > 0:
        facts.append(
            f"{n_ref_params} parameter(s) received instruction-backed refinement."
        )

    n_layouts = len(fn.layout_candidates)
    if n_layouts > 0:
        facts.append(f"{n_layouts} layout candidate(s) were observed.")

    n_unbound = len(fn.unbound_memory_accesses)
    if n_unbound > 0:
        facts.append(f"{n_unbound} unbound memory access(es) were preserved.")

    return facts


def _generate_uncertainties(
    fn: Phase4FunctionSemantics,
    has_semantic: bool,
    has_layout: bool,
) -> List[str]:
    """Generate uncertainties for missing or incomplete evidence."""
    uncertainties: List[str] = []

    if not has_semantic:
        uncertainties.append("No semantic refinement artifact was available.")

    if not has_layout:
        uncertainties.append("No layout recovery artifact was available.")

    n_constraints = fn.constraints_summary.get("total_constraints_applied", 0)
    if has_semantic and n_constraints == 0:
        uncertainties.append("No instruction-backed constraints were applied.")

    # Count unknown variables
    n_unknown = 0
    for v in fn.variables:
        if isinstance(v, dict):
            vtype = v.get("type", {})
            if isinstance(vtype, dict) and vtype.get("type", "unknown") == "unknown":
                n_unknown += 1
    # Also check refined_variables
    for rv in fn.refined_variables:
        if isinstance(rv, dict):
            rt = rv.get("refined_type", {})
            if isinstance(rt, dict) and rt.get("type", "unknown") == "unknown":
                n_unknown += 1

    if n_unknown > 0:
        uncertainties.append(
            f"{n_unknown} variable(s) remain unknown after refinement."
        )

    n_unbound = len(fn.unbound_memory_accesses)
    if n_unbound > 0:
        uncertainties.append(
            f"{n_unbound} memory access(es) could not be bound to a layout candidate."
        )

    if len(fn.layout_candidates) > 0:
        uncertainties.append(
            "Layout candidates are evidence-only and are not final structs."
        )

    return uncertainties


# ---------------------------------------------------------------------------
# Main merger
# ---------------------------------------------------------------------------

def build_phase4_semantics(
    type_recovery: Dict[str, Any],
    semantic_recovery: Optional[Dict[str, Any]] = None,
    layout_recovery: Optional[Dict[str, Any]] = None,
    source_type_recovery: Optional[str] = None,
    source_semantic_recovery: Optional[str] = None,
    source_layout_recovery: Optional[str] = None,
) -> Phase4SemanticsArtifact:
    """
    Build the final Phase 4 semantics artifact by merging Phase 4A/4B/4C data.

    Parameters
    ----------
    type_recovery       : Parsed type_recovery.json dict (required).
    semantic_recovery   : Parsed semantic_recovery.json dict (optional).
    layout_recovery     : Parsed layout_recovery.json dict (optional).
    source_*            : Provenance path strings for the artifact.

    Returns
    -------
    Phase4SemanticsArtifact
        The merged artifact ready for serialization.

    Raises
    ------
    ValueError
        If type_recovery is None or not a dict.
    """
    if not isinstance(type_recovery, dict):
        raise ValueError(
            "Phase 4D: type_recovery.json is required and must be a dict."
        )

    has_semantic = (
        isinstance(semantic_recovery, dict) and
        bool(_extract_semantic_recovery_functions(semantic_recovery))
    )
    has_layout = isinstance(layout_recovery, dict)

    # --- Extract raw data ---
    tr_functions = _extract_type_recovery_functions(type_recovery)
    sr_functions = _extract_semantic_recovery_functions(semantic_recovery)
    layout_candidates, layout_unbound = _extract_layout_candidates(layout_recovery)

    # --- Build indices for semantic recovery ---
    sr_by_entry, sr_by_name = _build_function_index(sr_functions)

    # --- Track which semantic functions were consumed ---
    consumed_sr_entries: set = set()
    consumed_sr_names: set = set()

    # --- Process each Phase 4A function ---
    merged_functions: List[Phase4FunctionSemantics] = []

    for tr_fn in tr_functions:
        if not isinstance(tr_fn, dict):
            continue

        fn_name = _safe_str(tr_fn, "name", "unknown_function")
        fn_entry = _safe_str(tr_fn, "entry_point", "unknown")
        fn_kind = _safe_str(tr_fn, "function_kind", "unknown")

        # --- Phase 4A data ---
        recovered_signature = _safe_dict(tr_fn, "signature")
        raw_variables = _safe_list(tr_fn, "variables")
        raw_parameters = _safe_list(
            _safe_dict(tr_fn, "signature"), "parameters"
        )

        # Dedup
        variables = _dedup_by_name(raw_variables)
        parameters = _dedup_by_name(raw_parameters)

        # --- Phase 4B data ---
        sr_fn = _match_function(fn_entry, fn_name, sr_by_entry, sr_by_name)
        refined_signature: Dict[str, Any] = {}
        refined_variables: List[Dict[str, Any]] = []
        refined_parameters: List[Dict[str, Any]] = []
        total_constraints = 0
        vars_with_constraints = 0
        params_with_constraints = 0

        if sr_fn is not None:
            # Mark as consumed
            sr_ep = _safe_str(sr_fn, "entry_point")
            sr_nm = _safe_str(sr_fn, "name")
            if sr_ep:
                consumed_sr_entries.add(sr_ep)
            if sr_nm:
                consumed_sr_names.add(sr_nm)

            refined_signature = _safe_dict(sr_fn, "refined_signature")
            raw_refined_vars = _safe_list(sr_fn, "variables")
            refined_variables = _dedup_by_name(raw_refined_vars)

            # Extract refined parameters from refined_signature
            raw_refined_params = _safe_list(refined_signature, "parameters")
            refined_parameters = _dedup_by_name(raw_refined_params)

            total_constraints = _safe_int(sr_fn, "total_constraints_applied")

            # Count variables with constraints > 0
            for rv in refined_variables:
                if isinstance(rv, dict) and _safe_int(rv, "constraints_applied") > 0:
                    vars_with_constraints += 1

            # Count parameters with changed type (by comparing)
            for rp in refined_parameters:
                if isinstance(rp, dict):
                    # A parameter has constraints if its confidence changed
                    # or if it appears in the refined list with altered type
                    rp_type = _safe_dict(rp, "type")
                    if rp_type.get("source", "fallback") != "fallback":
                        params_with_constraints += 1

        constraints_summary = {
            "total_constraints_applied": total_constraints,
            "variables_with_constraints": vars_with_constraints,
            "parameters_with_constraints": params_with_constraints,
        }

        # --- Phase 4C data ---
        fn_layout_candidates, fn_unbound = _attach_layouts(
            fn_entry, fn_name, layout_candidates, layout_unbound
        )

        # --- Build merged record ---
        fn_record = Phase4FunctionSemantics(
            name=fn_name,
            entry_point=fn_entry,
            function_kind=fn_kind,
            recovered_signature=recovered_signature,
            refined_signature=refined_signature,
            variables=variables,
            parameters=parameters,
            refined_variables=refined_variables,
            refined_parameters=refined_parameters,
            constraints_summary=constraints_summary,
            layout_candidates=fn_layout_candidates,
            unbound_memory_accesses=fn_unbound,
        )

        # Generate facts and uncertainties
        fn_record.known_facts = _generate_known_facts(fn_record)
        fn_record.uncertainties = _generate_uncertainties(
            fn_record, has_semantic, has_layout
        )

        merged_functions.append(fn_record)

    # --- Handle unmatched semantic functions ---
    for sr_fn in sr_functions:
        if not isinstance(sr_fn, dict):
            continue
        sr_ep = _safe_str(sr_fn, "entry_point")
        sr_nm = _safe_str(sr_fn, "name")

        # Skip if already consumed
        if sr_ep and sr_ep in consumed_sr_entries:
            continue
        if sr_nm and sr_nm in consumed_sr_names:
            continue

        # Only include if function identity is clear
        if not sr_nm or sr_nm == "unknown_function":
            if not sr_ep or sr_ep == "unknown":
                continue  # Identity not clear — skip

        fn_record = Phase4FunctionSemantics(
            name=sr_nm or "unknown_function",
            entry_point=sr_ep or "unknown",
            function_kind=_safe_str(sr_fn, "function_kind", "unknown"),
            refined_signature=_safe_dict(sr_fn, "refined_signature"),
            refined_variables=_dedup_by_name(_safe_list(sr_fn, "variables")),
        )

        total_constraints = _safe_int(sr_fn, "total_constraints_applied")
        fn_record.constraints_summary = {
            "total_constraints_applied": total_constraints,
            "variables_with_constraints": 0,
            "parameters_with_constraints": 0,
        }

        fn_record.known_facts = _generate_known_facts(fn_record)
        fn_record.uncertainties = [
            "Function found in semantic recovery but not in type recovery.",
        ] + _generate_uncertainties(fn_record, has_semantic, has_layout)

        merged_functions.append(fn_record)

    # --- Sort deterministically ---
    merged_functions.sort(key=lambda f: (f.entry_point or "", f.name or ""))

    # --- Compute summary ---
    functions_with_refinement = sum(
        1 for f in merged_functions
        if f.constraints_summary.get("total_constraints_applied", 0) > 0
    )
    functions_with_layouts = sum(
        1 for f in merged_functions if len(f.layout_candidates) > 0
    )
    total_layout_candidates = sum(
        len(f.layout_candidates) for f in merged_functions
    )
    total_unbound = sum(
        len(f.unbound_memory_accesses) for f in merged_functions
    )
    total_constraints = sum(
        f.constraints_summary.get("total_constraints_applied", 0)
        for f in merged_functions
    )

    summary = {
        "functions_total": len(merged_functions),
        "functions_with_refinement": functions_with_refinement,
        "functions_with_layout_candidates": functions_with_layouts,
        "total_layout_candidates": total_layout_candidates,
        "total_unbound_memory_accesses": total_unbound,
        "total_constraints_applied": total_constraints,
    }

    provenance = {
        "phase": "4D",
        "description": "Final Phase 4 semantic artifact merger",
        "source_type_recovery": source_type_recovery or "type_recovery.json",
        "source_semantic_recovery": source_semantic_recovery or "semantic_recovery.json",
        "source_layout_recovery": source_layout_recovery or "layout_recovery.json",
    }

    artifact = Phase4SemanticsArtifact(
        schema_version=SCHEMA_VERSION,
        provenance=provenance,
        functions=merged_functions,
        summary=summary,
    )

    logger.info(
        "Phase 4D: merged %d function(s); %d with refinement, %d with layouts.",
        len(merged_functions), functions_with_refinement, functions_with_layouts,
    )
    return artifact
