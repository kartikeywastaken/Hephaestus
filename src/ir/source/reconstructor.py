# -*- coding: utf-8 -*-
"""
Phase 5.1: Source Reconstruction Builder

Builds a SourceReconstructionArtifact from existing Phase 1–4D artifacts.

Core Rule: Missing evidence is acceptable. Fabricated evidence is not.

This module does NOT:
- Infer new types or struct definitions
- Invent field names, variable names, or expressions
- Compute confidence scores or similarity metrics
- Emit C source code (see c_emitter.py for that)
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from src.ir.source.models import (
    SCHEMA_VERSION,
    ReconstructedFunction,
    SourceReconstructionArtifact,
)
from src.ir.utils.addressing import normalize_address

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# C identifier sanitization
# ---------------------------------------------------------------------------

_C_IDENT_RE = re.compile(r"[^a-zA-Z0-9_]")


def sanitize_c_identifier(name: str) -> str:
    """
    Convert an arbitrary string into a valid C identifier.

    Rules:
    - Replace non-alphanumeric/underscore chars with '_'
    - Prefix with 'fn_' if starts with a digit
    - Ensure non-empty (fallback: 'fn_unknown')
    - Collapse consecutive underscores
    - Strip trailing underscores
    """
    if not name or not name.strip():
        return "fn_unknown"

    sanitized = _C_IDENT_RE.sub("_", name.strip())

    # Collapse consecutive underscores
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")

    # Strip leading/trailing underscores
    sanitized = sanitized.strip("_")

    if not sanitized:
        return "fn_unknown"

    # Prefix with 'fn_' if starts with digit
    if sanitized[0].isdigit():
        sanitized = f"fn_{sanitized}"

    return sanitized


# ---------------------------------------------------------------------------
# Safe dict extraction helpers
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


# ---------------------------------------------------------------------------
# Extract function lists from artifacts
# ---------------------------------------------------------------------------

def _extract_ir_functions(unified_ir: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract function list from unified_ir.json."""
    try:
        funcs = unified_ir["data"]["functions"]
    except (KeyError, TypeError):
        funcs = unified_ir.get("functions", [])
    return funcs if isinstance(funcs, list) else []


def _extract_semantics_functions(
    phase4_semantics: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Extract function list from phase4_semantics.json."""
    if not isinstance(phase4_semantics, dict):
        return []
    try:
        funcs = phase4_semantics["data"]["functions"]
    except (KeyError, TypeError):
        funcs = phase4_semantics.get("functions", [])
    return funcs if isinstance(funcs, list) else []


def _extract_structuring_regions(
    structuring_regions: Any,
) -> List[Dict[str, Any]]:
    """
    Extract structuring region list from structuring_regions.json.

    The artifact can be:
    - A list of {function_name, structured_body} dicts
    - A dict with a "data" key containing the list
    - A dict with region entries keyed by function name
    """
    if isinstance(structuring_regions, list):
        return structuring_regions
    if isinstance(structuring_regions, dict):
        # Try data.functions or data as list
        data = structuring_regions.get("data")
        if isinstance(data, list):
            return data
        # Try top-level list
        funcs = structuring_regions.get("functions")
        if isinstance(funcs, list):
            return funcs
        # Might be a list stored directly
        if not data:
            # Check if it's dict of function_name -> region
            result = []
            for key, val in structuring_regions.items():
                if isinstance(val, dict) and "structured_body" in val:
                    entry = dict(val)
                    entry.setdefault("function_name", key)
                    result.append(entry)
            if result:
                return result
    return []


def _extract_symbol_aliases(
    unified_ir: Dict[str, Any],
) -> Dict[str, str]:
    """
    Build entry_point → canonical_name mapping from unified_ir symbol_aliases.

    Returns {normalized_entry_point: canonical_name}.
    """
    mapping: Dict[str, str] = {}
    data = unified_ir.get("data", {}) if isinstance(unified_ir, dict) else {}
    aliases_list = data.get("symbol_aliases", [])
    if not isinstance(aliases_list, list):
        return mapping
    for group in aliases_list:
        if not isinstance(group, dict):
            continue
        ep = normalize_address(group.get("entry_point"))
        canonical = group.get("canonical_name", "")
        if ep and canonical:
            mapping[ep] = canonical
    return mapping


# ---------------------------------------------------------------------------
# Function index builders
# ---------------------------------------------------------------------------

def _build_semantics_index(
    functions: List[Dict[str, Any]],
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Build (by_entry_point, by_name) lookup indices for Phase 4D functions."""
    by_entry: Dict[str, Dict[str, Any]] = {}
    by_name: Dict[str, Dict[str, Any]] = {}
    for fn in functions:
        if not isinstance(fn, dict):
            continue
        ep = _safe_str(fn, "entry_point")
        name = _safe_str(fn, "name")
        ep_norm = normalize_address(ep) if ep else None
        if ep_norm and ep_norm != "unknown":
            by_entry[ep_norm] = fn
        if name and name != "unknown_function":
            by_name[name] = fn
    return by_entry, by_name


def _build_regions_index(
    regions: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Build function_name → region mapping from structuring_regions."""
    index: Dict[str, Dict[str, Any]] = {}
    for entry in regions:
        if not isinstance(entry, dict):
            continue
        fn_name = _safe_str(entry, "function_name")
        if fn_name:
            index[fn_name] = entry
    return index


def _match_semantics(
    entry_point: str,
    name: str,
    by_entry: Dict[str, Dict[str, Any]],
    by_name: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Match a function to its Phase 4D semantics record."""
    if entry_point and entry_point != "unknown":
        found = by_entry.get(entry_point)
        if found is not None:
            return found
    if name and name != "unknown_function":
        found = by_name.get(name)
        if found is not None:
            found_ep = normalize_address(_safe_str(found, "entry_point"))
            if (entry_point and entry_point != "unknown" and
                    found_ep and found_ep != "unknown" and
                    found_ep != entry_point):
                return None
            return found
    return None


# ---------------------------------------------------------------------------
# Body status determination
# ---------------------------------------------------------------------------

def _determine_body_status(region: Optional[Dict[str, Any]]) -> str:
    """
    Determine body_status from the structuring region.

    Returns one of: "structured", "partially_structured", "unstructured", "missing"
    """
    if region is None:
        return "missing"

    body = region.get("structured_body", {})
    if not isinstance(body, dict):
        return "missing"

    root_type = body.get("type", "")

    if root_type in ("sequence", "if", "if_else", "loop"):
        return "structured"
    elif root_type == "block":
        # Single block — partially structured
        return "partially_structured"
    elif root_type == "unstructured":
        return "unstructured"
    else:
        return "missing"


# ---------------------------------------------------------------------------
# Return type extraction
# ---------------------------------------------------------------------------

_TYPE_MAP = {
    "void": "void",
    "int32": "i32",
    "uint32": "u32",
    "int64": "i64",
    "uint64": "u64",
    "int8": "i8",
    "uint8": "u8",
    "int16": "i16",
    "uint16": "u16",
    "bool": "bool",
    "pointer": "void*",
    "function_pointer": "void*",
    "struct_candidate": "void*",
}


def _extract_return_type(
    semantics: Optional[Dict[str, Any]],
    warnings: List[str],
) -> str:
    """
    Extract return type from Phase 4D semantics.

    If unknown or missing, defaults to "u64" and adds a warning.
    """
    if semantics is None:
        warnings.append("unknown_return_type_defaulted_to_u64")
        return "u64"

    # Try refined_signature first, then recovered_signature
    for sig_key in ("refined_signature", "recovered_signature"):
        sig = _safe_dict(semantics, sig_key)
        if not sig:
            continue
        ret = sig.get("return_type", {})
        if isinstance(ret, dict):
            type_name = ret.get("type", "unknown")
        elif isinstance(ret, str):
            type_name = ret
        else:
            continue
        if type_name and type_name != "unknown":
            return _TYPE_MAP.get(type_name, type_name)

    warnings.append("unknown_return_type_defaulted_to_u64")
    return "u64"


# ---------------------------------------------------------------------------
# Parameter extraction with ABI synthetic fallback
# ---------------------------------------------------------------------------

def _extract_parameters(
    semantics: Optional[Dict[str, Any]],
    abi_bindings: List[Dict[str, Any]],
    evidence_notes: List[str],
) -> List[Dict[str, Any]]:
    """
    Extract parameters from Phase 4D semantics.

    If Phase 4D parameters are empty but ABI bindings contain argument_index
    values, emit conservative synthetic parameters: u64 arg0, u64 arg1, etc.
    Only observed indices are emitted.
    """
    params: List[Dict[str, Any]] = []

    if semantics is not None:
        # Try refined_parameters first, then parameters
        for key in ("refined_parameters", "parameters"):
            candidate = _safe_list(semantics, key)
            if candidate:
                params = list(candidate)
                break

    if params:
        return params

    # Synthetic fallback from ABI bindings
    observed_indices: Set[int] = set()
    for binding in abi_bindings:
        if not isinstance(binding, dict):
            continue
        idx = binding.get("argument_index")
        if idx is not None:
            try:
                observed_indices.add(int(idx))
            except (TypeError, ValueError):
                continue

    if observed_indices:
        evidence_notes.append(
            f"Synthetic parameters generated from ABI bindings for "
            f"argument indices: {sorted(observed_indices)}"
        )
        for idx in sorted(observed_indices):
            params.append({
                "name": f"arg{idx}",
                "type": "u64",
                "source": "abi_synthetic",
                "argument_index": idx,
            })

    return params


# ---------------------------------------------------------------------------
# Instruction/block counting from unified IR
# ---------------------------------------------------------------------------

def _count_instructions(ir_func: Dict[str, Any]) -> Tuple[int, int]:
    """Count (instruction_count, basic_block_count) from an IR function."""
    blocks = _safe_list(ir_func, "basic_blocks")
    block_count = len(blocks)
    instr_count = 0
    for bb in blocks:
        if isinstance(bb, dict):
            instrs = _safe_list(bb, "instructions")
            instr_count += len(instrs)
    return instr_count, block_count


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_source_reconstruction(
    unified_ir: Dict[str, Any],
    structuring_regions: Any,
    phase4_semantics: Dict[str, Any],
    layout_recovery: Optional[Dict[str, Any]] = None,
) -> SourceReconstructionArtifact:
    """
    Build a SourceReconstructionArtifact from existing Phase 1–4D artifacts.

    Parameters
    ----------
    unified_ir         : Parsed unified_ir.json.
    structuring_regions: Parsed structuring_regions.json.
    phase4_semantics   : Parsed phase4_semantics.json.
    layout_recovery    : Parsed layout_recovery.json (optional).

    Returns
    -------
    SourceReconstructionArtifact with all available evidence attached.
    """
    # Extract function lists
    ir_functions = _extract_ir_functions(unified_ir)
    sem_functions = _extract_semantics_functions(phase4_semantics)
    region_list = _extract_structuring_regions(structuring_regions)
    alias_map = _extract_symbol_aliases(unified_ir)

    # Build indices
    sem_by_entry, sem_by_name = _build_semantics_index(sem_functions)
    regions_index = _build_regions_index(region_list)

    # Counters for summary
    n_structured = 0
    n_partial = 0
    n_unstructured = 0
    n_missing = 0
    n_with_warnings = 0
    total_params = 0
    total_abi = 0
    total_ple = 0
    total_lc = 0
    total_instrs = 0

    reconstructed: List[ReconstructedFunction] = []

    for ir_func in ir_functions:
        if not isinstance(ir_func, dict):
            continue

        name = _safe_str(ir_func, "name", "unknown_function")
        ep_raw = _safe_str(ir_func, "entry_point", "unknown")
        ep_norm = normalize_address(ep_raw) or ep_raw

        # Canonical name from symbol aliases
        canonical_name = alias_map.get(ep_norm, name)

        # Sanitized C identifier
        c_name = sanitize_c_identifier(canonical_name)

        # Match Phase 4D semantics
        sem = _match_semantics(ep_norm, name, sem_by_entry, sem_by_name)

        # Match structuring region (by function name)
        region = regions_index.get(name)

        # Build warnings and evidence notes
        warnings: List[str] = []
        evidence_notes: List[str] = []

        # Function kind
        function_kind = "unknown"
        if sem is not None:
            function_kind = _safe_str(sem, "function_kind", "unknown")
        elif ir_func.get("function_kind"):
            function_kind = str(ir_func["function_kind"])

        # Return type
        return_type = _extract_return_type(sem, warnings)

        # ABI argument bindings
        abi_bindings = _safe_list(sem, "abi_argument_bindings") if sem else []

        # Parameters (with ABI synthetic fallback)
        parameters = _extract_parameters(sem, abi_bindings, evidence_notes)

        # Local variables
        local_variables: List[Dict[str, Any]] = []
        if sem is not None:
            for key in ("refined_variables", "variables"):
                candidate = _safe_list(sem, key)
                if candidate:
                    local_variables = list(candidate)
                    break

        # Body status
        body_status = _determine_body_status(region)

        # Structured regions
        structured_regions: List[Dict[str, Any]] = []
        if region is not None:
            body = region.get("structured_body")
            if isinstance(body, dict):
                structured_regions = [body]

        # Instruction and block counts
        instr_count, block_count = _count_instructions(ir_func)

        # Empty function warning
        if block_count == 0:
            warnings.append("empty_function")

        # Parameter-layout evidence
        param_layout = _safe_list(sem, "parameter_layout_evidence") if sem else []

        # Layout candidates
        layout_cands = _safe_list(sem, "layout_candidates") if sem else []

        # Build evidence notes
        if parameters:
            evidence_notes.append(f"{len(parameters)} parameter(s) recovered")
        if abi_bindings:
            evidence_notes.append(f"{len(abi_bindings)} ABI binding(s)")
        if param_layout:
            evidence_notes.append(
                f"{len(param_layout)} parameter-layout evidence item(s)"
            )
        if layout_cands:
            evidence_notes.append(f"{len(layout_cands)} layout candidate(s)")
        if local_variables:
            evidence_notes.append(f"{len(local_variables)} local variable(s)")

        rec = ReconstructedFunction(
            name=name,
            canonical_name=canonical_name,
            c_name=c_name,
            entry_point=ep_norm,
            function_kind=function_kind,
            return_type=return_type,
            parameters=parameters,
            local_variables=local_variables,
            body_status=body_status,
            structured_regions=structured_regions,
            abi_argument_bindings=abi_bindings,
            parameter_layout_evidence=param_layout,
            layout_candidates=layout_cands,
            instruction_count=instr_count,
            basic_block_count=block_count,
            warnings=warnings,
            evidence_notes=evidence_notes,
        )
        reconstructed.append(rec)

        # Update summary counters
        if body_status == "structured":
            n_structured += 1
        elif body_status == "partially_structured":
            n_partial += 1
        elif body_status == "unstructured":
            n_unstructured += 1
        else:
            n_missing += 1

        if warnings:
            n_with_warnings += 1

        total_params += len(parameters)
        total_abi += len(abi_bindings)
        total_ple += len(param_layout)
        total_lc += len(layout_cands)
        total_instrs += instr_count

    # Build summary
    summary = {
        "functions_total": len(reconstructed),
        "functions_structured": n_structured,
        "functions_partially_structured": n_partial,
        "functions_unstructured": n_unstructured,
        "functions_missing": n_missing,
        "functions_with_warnings": n_with_warnings,
        "total_parameters": total_params,
        "total_abi_bindings": total_abi,
        "total_parameter_layout_evidence": total_ple,
        "total_layout_candidates": total_lc,
        "total_instructions": total_instrs,
    }

    artifact = SourceReconstructionArtifact(
        schema_version=SCHEMA_VERSION,
        functions=reconstructed,
        summary=summary,
    )

    logger.info(
        "Built source reconstruction: %d functions "
        "(%d structured, %d partial, %d unstructured, %d missing)",
        len(reconstructed), n_structured, n_partial, n_unstructured, n_missing,
    )

    return artifact
