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
from src.ir.source.names import sanitize_c_identifier, function_c_name
from src.ir.source.summary import default_source_summary, finalize_source_summary

logger = logging.getLogger(__name__)


# (sanitize_c_identifier is now imported from src.ir.source.names)


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

def _count_unstructured_regions(region: Any) -> int:
    """Recursively count unstructured region nodes in a region tree."""
    if not isinstance(region, dict):
        return 0
    rtype = region.get("type", "")
    count = 1 if rtype == "unstructured" else 0

    children = region.get("children", [])
    if isinstance(children, list):
        for child in children:
            count += _count_unstructured_regions(child)

    for branch_name in ("then_branch", "else_branch", "body"):
        branch = region.get(branch_name)
        if isinstance(branch, dict):
            count += _count_unstructured_regions(branch)

    return count


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
    from src.ir.source.lowering import lower_function_instructions
    from collections import defaultdict

    # Extract function lists
    ir_functions = _extract_ir_functions(unified_ir)
    sem_functions = _extract_semantics_functions(phase4_semantics)
    region_list = _extract_structuring_regions(structuring_regions)
    alias_map = _extract_symbol_aliases(unified_ir)

    # Build indices
    sem_by_entry, sem_by_name = _build_semantics_index(sem_functions)
    regions_index = _build_regions_index(region_list)

    # Pre-build parameter counts map for call signature formatting
    fn_param_counts: Dict[str, int] = {}
    for ir_func in ir_functions:
        if not isinstance(ir_func, dict):
            continue
        ep = normalize_address(ir_func.get("entry_point"))
        name = ir_func.get("name")
        sem = _match_semantics(ep, name, sem_by_entry, sem_by_name)
        
        num_params = 4  # default fallback
        if sem is not None:
            params = sem.get("refined_parameters") or sem.get("parameters") or []
            num_params = len(params)
        else:
            # Synthetic parameter count based on unique argument indices
            abi_bindings = ir_func.get("abi_argument_bindings") or []
            observed = set()
            for b in abi_bindings:
                if isinstance(b, dict) and b.get("argument_index") is not None:
                    try:
                        observed.add(int(b["argument_index"]))
                    except (ValueError, TypeError):
                        continue
            if observed:
                num_params = len(observed)
                
        if ep and ep != "unknown":
            fn_param_counts[ep] = num_params
        if name:
            fn_param_counts[name] = num_params
        canonical_name = alias_map.get(ep, name) if ep else name
        if canonical_name:
            fn_param_counts[canonical_name] = num_params

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

    # Phase 5.2 new summary counters
    n_with_structured_regions = 0
    n_with_semantic_evidence = 0
    n_with_layout_evidence = 0
    n_with_parameter_layout_evidence = 0
    unstructured_regions_total = 0
    total_lowered = 0
    total_commented = 0

    # Phase 5.3 control flow summary counters
    control_flow_regions_total = 0
    control_flow_constructs_emitted = 0
    loops_emitted = 0
    if_constructs_emitted = 0
    if_else_constructs_emitted = 0
    switch_constructs_emitted = 0
    fallback_regions = 0
    duplicate_blocks_skipped = 0
    condition_expressions_recovered = 0

    # Phase 5.4 return/call-site summary counters
    return_sites_total = 0
    return_sites_with_value = 0
    return_sites_unknown = 0
    functions_with_recovered_return_value = 0
    call_sites_total = 0
    summary_direct_calls = 0
    summary_indirect_calls = 0
    summary_calls_with_arguments = 0
    call_arguments_recovered = 0
    call_arguments_unknown = 0

    # Phase 5.5 condition predicate summary counters
    condition_sites_total = 0
    condition_sites_with_evidence = 0
    condition_sites_unknown = 0
    condition_annotations_recovered = 0
    conditions_inverted_for_structure = 0
    ambiguous_condition_sites = 0

    # Phase 5.6 declarations summary counters
    pseudo_registers_declared_total = 0
    pseudo_stack_slots_declared_total = 0
    call_helpers_declared_total = 0
    declarations_total = 0
    functions_with_declarations = 0
    compile_shape_warnings_total = 0
    global_call_helpers = set()
    existing_fn_names = set()
    for ir_f in ir_functions:
        if isinstance(ir_f, dict):
            fn_n = _safe_str(ir_f, "name", "unknown_function")
            ep_r = _safe_str(ir_f, "entry_point", "unknown")
            ep_n = normalize_address(ep_r) or ep_r
            canon_n = alias_map.get(ep_n, fn_n)
            existing_fn_names.add(fn_n)
            existing_fn_names.add(canon_n)
            existing_fn_names.add(sanitize_c_identifier(canon_n))
    existing_fn_names.update({"printf", "stack_chk_fail", "main"})

    # Detect real main entry point using priority rules
    real_main_ep = None
    main_candidates = []
    for ir_f in ir_functions:
        if not isinstance(ir_f, dict):
            continue
        ep_r = _safe_str(ir_f, "entry_point", "unknown")
        ep_n = normalize_address(ep_r) or ep_r
        fn_n = _safe_str(ir_f, "name", "unknown_function")
        canon_n = alias_map.get(ep_n, fn_n)
        
        sem_f = _match_semantics(ep_n, fn_n, sem_by_entry, sem_by_name)
        f_kind = "unknown"
        if sem_f is not None:
            f_kind = _safe_str(sem_f, "function_kind", "unknown")
        elif ir_f.get("function_kind"):
            f_kind = str(ir_f["function_kind"])
            
        c_n = function_c_name(canon_n, ep_n)
        is_prov = (fn_n in ("entry", "_main", "entry0") or 
                   canon_n in ("entry", "_main", "entry0"))
                   
        main_candidates.append({
            "ep": ep_n,
            "name": fn_n,
            "c_name": c_n,
            "function_kind": f_kind,
            "is_prov_entry": is_prov
        })
        
    p12_cands = [c for c in main_candidates if c["function_kind"] == "entrypoint" and c["is_prov_entry"]]
    if p12_cands:
        real_main_ep = p12_cands[0]["ep"]
    else:
        p3_cands = [c for c in main_candidates if c["function_kind"] == "entrypoint"]
        if p3_cands:
            p3_main_cands = [c for c in p3_cands if c["c_name"] == "main"]
            if p3_main_cands:
                p3_prov = [c for c in p3_main_cands if c["is_prov_entry"]]
                if p3_prov:
                    real_main_ep = p3_prov[0]["ep"]
                else:
                    real_main_ep = p3_main_cands[0]["ep"]
            else:
                real_main_ep = p3_cands[0]["ep"]
        else:
            p4_cands = [c for c in main_candidates if c["c_name"] == "main"]
            if p4_cands:
                real_main_ep = p4_cands[0]["ep"]

    duplicate_main_functions_renamed = 0

    # Detect architecture once for the whole IR
    from src.ir.source.lowering import detect_architecture
    arch = detect_architecture(unified_ir)

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
        c_name = function_c_name(canonical_name, ep_norm)
        if c_name == "main":
            if ep_norm != real_main_ep:
                c_name = f"main_{ep_norm}"
                duplicate_main_functions_renamed += 1

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

        # Lower instructions
        lowered_stmts, fn_lowering = lower_function_instructions(
            ir_func,
            semantic_function=sem,
            layout_candidates=layout_cands,
            unified_ir=unified_ir,
            fn_param_counts=fn_param_counts,
        )

        # Calculate unsupported instruction kinds
        unsupported_kinds = {}
        for stmt in lowered_stmts:
            if not stmt.lowered and stmt.kind == "unknown":
                mnem = "invalid"
                if stmt.source_instruction and stmt.source_instruction.get("mnemonic"):
                    mnem = str(stmt.source_instruction["mnemonic"]).strip().lower()
                if not mnem:
                    mnem = "invalid"
                unsupported_kinds[mnem] = unsupported_kinds.get(mnem, 0) + 1
        fn_lowering["unsupported_instruction_kinds"] = {k: v for k, v in sorted(unsupported_kinds.items())}

        # Group lowered statements by block ID
        lowered_blocks = defaultdict(list)
        for stmt in lowered_stmts:
            b_id = stmt.source_instruction.get("block_id") if stmt.source_instruction else None
            if b_id:
                lowered_blocks[b_id].append(stmt)

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

        # Phase 5.3 control-flow analysis
        from src.ir.source.control_emitter import analyze_control_flow_regions
        fn_control_flow = analyze_control_flow_regions(structured_regions)

        # Phase 5.4 return recovery
        from src.ir.source.return_recovery import analyze_return_sites
        fn_return_recovery = analyze_return_sites(
            dict(lowered_blocks), return_type, arch
        )

        # Phase 5.4 call-site refinement
        from src.ir.source.callsite_refinement import analyze_call_sites
        fn_callsite_refinement = analyze_call_sites(
            dict(lowered_blocks), arch
        )

        # Phase 5.5 branch predicate annotations
        from src.ir.source.condition_recovery import analyze_condition_sites
        fn_condition_recovery = analyze_condition_sites(
            structured_regions, dict(lowered_blocks), cfg_info=None, architecture=arch
        )

        # Phase 5.6 local pseudo declarations recovery (preliminary scan)
        from src.ir.source.declaration_recovery import analyze_declarations_for_function
        fn_declaration_recovery = analyze_declarations_for_function(
            name, return_type, parameters, dict(lowered_blocks), structured_regions, emitted_body_lines=None
        )

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
            lowered_statements=lowered_stmts,
            lowered_blocks=dict(lowered_blocks),
            lowering=fn_lowering,
            control_flow=fn_control_flow,
            return_recovery=fn_return_recovery,
            callsite_refinement=fn_callsite_refinement,
            condition_recovery=fn_condition_recovery,
            declaration_recovery=fn_declaration_recovery,
            abi_scratch_declarations=[],
        )
        reconstructed.append(rec)

        # Accumulate control-flow metrics
        control_flow_regions_total += fn_control_flow.get("regions_total", 0)
        control_flow_constructs_emitted += fn_control_flow.get("structured_constructs_emitted", 0)
        loops_emitted += fn_control_flow.get("loops_emitted", 0)
        if_constructs_emitted += fn_control_flow.get("if_constructs_emitted", 0)
        if_else_constructs_emitted += fn_control_flow.get("if_else_constructs_emitted", 0)
        switch_constructs_emitted += fn_control_flow.get("switch_constructs_emitted", 0)
        fallback_regions += fn_control_flow.get("fallback_regions", 0)
        duplicate_blocks_skipped += fn_control_flow.get("duplicate_blocks_skipped", 0)
        condition_expressions_recovered += fn_control_flow.get("condition_expressions_recovered", 0)

        # Accumulate Phase 5.4 return/call-site metrics
        return_sites_total += fn_return_recovery.get("return_sites_total", 0)
        return_sites_with_value += fn_return_recovery.get("return_sites_with_value", 0)
        return_sites_unknown += fn_return_recovery.get("return_sites_unknown", 0)
        if fn_return_recovery.get("return_sites_with_value", 0) > 0:
            functions_with_recovered_return_value += 1

        call_sites_total += fn_callsite_refinement.get("call_sites_total", 0)
        summary_direct_calls += fn_callsite_refinement.get("direct_calls", 0)
        summary_indirect_calls += fn_callsite_refinement.get("indirect_calls", 0)
        summary_calls_with_arguments += fn_callsite_refinement.get("calls_with_arguments", 0)
        call_arguments_recovered += fn_callsite_refinement.get("arguments_recovered", 0)
        call_arguments_unknown += fn_callsite_refinement.get("arguments_unknown", 0)

        # Accumulate Phase 5.5 condition metrics
        condition_sites_total += fn_condition_recovery.get("condition_sites_total", 0)
        condition_sites_with_evidence += fn_condition_recovery.get("condition_sites_with_evidence", 0)
        condition_sites_unknown += fn_condition_recovery.get("condition_sites_unknown", 0)
        condition_annotations_recovered += fn_condition_recovery.get("condition_annotations_recovered", 0)
        conditions_inverted_for_structure += fn_condition_recovery.get("conditions_inverted_for_structure", 0)
        ambiguous_condition_sites += fn_condition_recovery.get("ambiguous_condition_sites", 0)

        # Accumulate Phase 5.6 declaration metrics
        pseudo_registers_declared_total += fn_declaration_recovery.get("pseudo_registers_declared", 0)
        pseudo_stack_slots_declared_total += fn_declaration_recovery.get("pseudo_stack_slots_declared", 0)
        compile_shape_warnings_total += len(fn_declaration_recovery.get("warnings", []))
        if fn_declaration_recovery.get("declarations_total", 0) > 0:
            functions_with_declarations += 1
        for helper in fn_declaration_recovery.get("call_helpers", []):
            if helper not in existing_fn_names:
                global_call_helpers.add(helper)

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

        # Phase 5.2 new summary updates
        if structured_regions:
            n_with_structured_regions += 1
            for r in structured_regions:
                unstructured_regions_total += _count_unstructured_regions(r)
        
        # Semantic evidence present if sem matched or if ABI/params/local vars exist
        if sem is not None or parameters or abi_bindings or local_variables:
            n_with_semantic_evidence += 1

        if layout_cands:
            n_with_layout_evidence += 1

        if param_layout:
            n_with_parameter_layout_evidence += 1

        total_lowered += fn_lowering.get("instructions_lowered", 0)
        total_commented += fn_lowering.get("instructions_commented", 0)

    # Accumulate global unsupported instruction kinds
    global_unsupported_kinds = {}
    for fn in reconstructed:
        fn_unsupported = fn.lowering.get("unsupported_instruction_kinds", {})
        for mnem, count in fn_unsupported.items():
            global_unsupported_kinds[mnem] = global_unsupported_kinds.get(mnem, 0) + count

    # Build summary
    summary = default_source_summary()
    summary.update({
        "functions_total": len(reconstructed),
        "functions_emitted": len(reconstructed),
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
        # Phase 5.2 statistics
        "functions_with_structured_regions": n_with_structured_regions,
        "functions_with_semantic_evidence": n_with_semantic_evidence,
        "functions_with_layout_evidence": n_with_layout_evidence,
        "functions_with_parameter_layout_evidence": n_with_parameter_layout_evidence,
        "unstructured_regions_total": unstructured_regions_total,
        "instructions_total": total_instrs,
        "instructions_lowered": total_lowered,
        "instructions_commented": total_commented,
        # Phase 5.3 statistics
        "control_flow_regions_total": control_flow_regions_total,
        "control_flow_constructs_emitted": control_flow_constructs_emitted,
        "loops_emitted": loops_emitted,
        "if_constructs_emitted": if_constructs_emitted,
        "if_else_constructs_emitted": if_else_constructs_emitted,
        "switch_constructs_emitted": switch_constructs_emitted,
        "fallback_regions": fallback_regions,
        "duplicate_blocks_skipped": duplicate_blocks_skipped,
        "condition_expressions_recovered": condition_expressions_recovered,
        # Phase 5.4 return/call-site refinement
        "return_sites_total": return_sites_total,
        "return_sites_with_value": return_sites_with_value,
        "return_sites_unknown": return_sites_unknown,
        "functions_with_recovered_return_value": functions_with_recovered_return_value,
        "call_sites_total": call_sites_total,
        "direct_calls": summary_direct_calls,
        "indirect_calls": summary_indirect_calls,
        "calls_with_arguments": summary_calls_with_arguments,
        "call_arguments_recovered": call_arguments_recovered,
        "call_arguments_unknown": call_arguments_unknown,
        # Phase 5.5 condition predicate annotation
        "condition_sites_total": condition_sites_total,
        "condition_sites_with_evidence": condition_sites_with_evidence,
        "condition_sites_unknown": condition_sites_unknown,
        "condition_annotations_recovered": condition_annotations_recovered,
        "conditions_inverted_for_structure": conditions_inverted_for_structure,
        "ambiguous_condition_sites": ambiguous_condition_sites,
        # Phase 5.6 declarations
        "pseudo_registers_declared_total": pseudo_registers_declared_total,
        "pseudo_stack_slots_declared_total": pseudo_stack_slots_declared_total,
        "call_helpers_declared_total": len(global_call_helpers),
        "declarations_total": pseudo_registers_declared_total + pseudo_stack_slots_declared_total,
        "functions_with_declarations": functions_with_declarations,
        "compile_shape_warnings_total": compile_shape_warnings_total,
        # Phase 5.7 condition adapter
        "condition_adapters_inserted": 0,
        "condition_evidence_adapters": 0,
        "condition_unknown_adapters": 0,
        "unknown_condition_helpers_emitted": 0,
        # Phase 5.7.2 cset adapter
        "cset_adapters_inserted": 0,
        "cset_helper_emitted": 0,
        # Phase 5.7.3 ABI scratch declarations
        "abi_scratch_declarations_inserted": 0,
        "functions_with_abi_scratch_declarations": 0,
        # Phase 7.2.2 Compile-Shape normalization
        "main_compile_shape_normalized": True,
        "duplicate_main_functions_renamed": duplicate_main_functions_renamed,
        "main_abi_bridges_inserted": 0,
        # Phase 5.7.1 unsupported instruction kinds
        "unsupported_instruction_kinds": {k: v for k, v in sorted(global_unsupported_kinds.items())},
    })
    summary = finalize_source_summary(summary)

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
