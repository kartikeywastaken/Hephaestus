# -*- coding: utf-8 -*-
"""
Phase 5.4: Conservative C Skeleton Emitter

Emits a recovered.c file containing conservative function skeletons
based on the SourceReconstructionArtifact.

Core Rule: Missing evidence is acceptable. Fabricated evidence is not.

This module does NOT:
- Invent struct definitions
- Invent field names or ->field expressions
- Invent conditions, loop bounds, or array dimensions
- Emit real source expressions or algorithm names
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from src.ir.source.models import (
    SCHEMA_VERSION,
    ReconstructedFunction,
    SourceReconstructionArtifact,
)
from src.ir.source.c_helpers import (
    RESERVED_HELPERS,
    emit_typedefs,
    emit_unknown_cond_helper,
    emit_cset_helper,
)


# ---------------------------------------------------------------------------
# Type mapping for C emission
# ---------------------------------------------------------------------------

_C_TYPE_MAP = {
    "void": "void",
    "u64": "uint64_t",
    "i64": "int64_t",
    "u32": "uint32_t",
    "i32": "int32_t",
    "u16": "uint16_t",
    "i16": "int16_t",
    "u8": "uint8_t",
    "i8": "int8_t",
    "bool": "_Bool",
    "void*": "void *",
    "int32": "int32_t",
    "uint32": "uint32_t",
    "int64": "int64_t",
    "uint64": "uint64_t",
    "int8": "int8_t",
    "uint8": "uint8_t",
    "int16": "int16_t",
    "uint16": "uint16_t",
    "pointer": "void *",
    "function_pointer": "void *",
    "struct_candidate": "void *",
    "unknown": "uint64_t",
}


def _map_c_type(type_str: str) -> str:
    """Map an internal type string to a C type. Defaults to uint64_t."""
    return _C_TYPE_MAP.get(type_str, type_str)


# ---------------------------------------------------------------------------
# Recursive region tree walker
# ---------------------------------------------------------------------------

# Region tree C emission logic is delegated to control_emitter.py


# ---------------------------------------------------------------------------
# Parameter formatting
# ---------------------------------------------------------------------------

def _format_param(param: Dict[str, Any], is_main: bool = False) -> str:
    """Format a single parameter for a C function signature."""
    name = param.get("name", "arg")
    ptype = param.get("type", "u64")

    # Handle dict-style type
    if isinstance(ptype, dict):
        ptype = ptype.get("type", "unknown")

    if is_main and name == "argv":
        c_type = "char **"
    else:
        c_type = _map_c_type(str(ptype))
    return f"{c_type} {name}"


# ---------------------------------------------------------------------------
# Phase 5.4 Return/Call-Site Replacement Helpers
# ---------------------------------------------------------------------------

def _build_return_replacement_lookup(
    fn: ReconstructedFunction,
) -> Dict[Tuple[str, str], str]:
    """
    Build a lookup dict from return_recovery sites: (block_id, address) -> replacement_text.
    """
    lookup: Dict[Tuple[str, str], str] = {}
    rr = fn.return_recovery
    if not isinstance(rr, dict):
        return lookup
    sites = rr.get("sites", [])
    if not isinstance(sites, list):
        return lookup
    for site in sites:
        if not isinstance(site, dict):
            continue
        block_id = site.get("block_id")
        addr = site.get("address")
        replacement = site.get("replacement_text")
        if block_id and addr and replacement:
            lookup[(str(block_id), str(addr))] = replacement
    return lookup


def _build_callsite_replacement_lookup(
    fn: ReconstructedFunction,
) -> Dict[Tuple[str, str], str]:
    """
    Build a lookup dict from callsite_refinement sites: (block_id, address) -> refined_text.
    """
    lookup: Dict[Tuple[str, str], str] = {}
    cr = fn.callsite_refinement
    if not isinstance(cr, dict):
        return lookup
    sites = cr.get("sites", [])
    if not isinstance(sites, list):
        return lookup
    for site in sites:
        if not isinstance(site, dict):
            continue
        block_id = site.get("block_id")
        addr = site.get("address")
        refined = site.get("refined_text")
        if block_id and addr and refined:
            lookup[(str(block_id), str(addr))] = refined
    return lookup


def _apply_statement_replacements(
    text: str,
    stmt: Any,
    current_block_id: str,
    return_lookup: Dict[Tuple[str, str], str],
    callsite_lookup: Dict[Tuple[str, str], str],
    returns_emitted: Set[Tuple[str, str]],
) -> str:
    """
    Check if a statement should be replaced with a return or call-site refinement.
    Returns the (possibly replaced) text.
    """
    # Get statement metadata
    if isinstance(stmt, dict):
        kind = stmt.get("kind", "")
        addr = stmt.get("address", "")
    else:
        kind = getattr(stmt, "kind", "")
        addr = getattr(stmt, "address", "")

    addr_str = str(addr) if addr else ""
    key = (str(current_block_id), addr_str)

    # Return replacement
    if kind == "return_comment" and key in return_lookup:
        returns_emitted.add(key)
        return return_lookup[key]

    # Call-site replacement
    if kind == "call" and key in callsite_lookup:
        return callsite_lookup[key]

    return text


# ---------------------------------------------------------------------------
# Statement emission with replacements
# ---------------------------------------------------------------------------

class _StatementReplacer:
    """
    Wraps block statement emission with Phase 5.4 replacements.
    Tracks which return sites have been emitted inline.
    """

    def __init__(
        self,
        fn: ReconstructedFunction,
        return_lookup: Dict[Tuple[str, str], str],
        callsite_lookup: Dict[Tuple[str, str], str],
    ):
        self.fn = fn
        self.return_lookup = return_lookup
        self.callsite_lookup = callsite_lookup
        self.returns_emitted: Set[Tuple[str, str]] = set()

    def process_line(
        self,
        text: str,
        stmt: Any,
        block_id: str,
    ) -> str:
        return _apply_statement_replacements(
            text, stmt, block_id,
            self.return_lookup, self.callsite_lookup,
            self.returns_emitted,
        )


# ---------------------------------------------------------------------------
# Enhanced block statement emission
# ---------------------------------------------------------------------------

def _emit_block_stmts_with_replacements(
    stmts: list,
    block_id: str,
    replacer: _StatementReplacer,
    prefix: str,
    lines: List[str],
) -> None:
    """Emit statements for a block, applying return/call-site replacements."""
    for stmt in stmts:
        if isinstance(stmt, dict):
            text = stmt.get("text", "")
        else:
            text = getattr(stmt, "text", "")
        replaced = replacer.process_line(text, stmt, block_id)
        lines.append(f"{prefix}{replaced}")


# ---------------------------------------------------------------------------
# Function emission
# ---------------------------------------------------------------------------

def _emit_function(
    fn: ReconstructedFunction,
    lines: List[str],
    global_call_helpers: Set[str] | None = None,
) -> int:
    """Emit a single function skeleton."""
    # Return type and parameter list
    if fn.c_name == "main":
        c_ret = "int32_t"
        param_list = "int32_t argc, char **argv"
    else:
        c_ret = _map_c_type(fn.return_type)
        if fn.parameters:
            param_strs = [_format_param(p, is_main=False) for p in fn.parameters]
            param_list = ", ".join(param_strs)
        else:
            param_list = "void"

    # Signature
    lines.append(f"{c_ret} {fn.c_name}({param_list})")
    lines.append("{")

    # Entry point comment
    lines.append(f"    /* Entry: {fn.entry_point} */")

    # Names comment (if canonical differs)
    if fn.canonical_name != fn.name:
        lines.append(
            f"    /* Original: {fn.name}, Canonical: {fn.canonical_name} */"
        )

    # Body status comment
    lines.append(f"    /* Body status: {fn.body_status} */")

    # Block/instruction count
    lines.append(
        f"    /* {fn.basic_block_count} basic block(s), "
        f"{fn.instruction_count} instruction(s) */"
    )

    # Warnings
    for w in fn.warnings:
        lines.append(f"    /* WARNING: {w} */")

    lines.append("")

    # ABI argument bindings
    if fn.abi_argument_bindings:
        lines.append("    /* ABI argument bindings: */")
        for binding in fn.abi_argument_bindings:
            if isinstance(binding, dict):
                reg = binding.get("register", "?")
                idx = binding.get("argument_index", "?")
                kind = binding.get("binding_kind", "?")
                lines.append(
                    f"    /*   {reg} => param {idx} ({kind}) */"
                )
        lines.append("")

    # Parameter-layout evidence
    if fn.parameter_layout_evidence:
        lines.append("    /* Parameter-layout evidence: */")
        for ple in fn.parameter_layout_evidence:
            if isinstance(ple, dict):
                pidx = ple.get("parameter_index", "?")
                pname = ple.get("parameter_name", "?")
                offsets = ple.get("observed_offsets", [])
                sizes = ple.get("observed_sizes", [])
                lines.append(
                    f"    /*   param {pidx} ({pname}): "
                    f"offsets={offsets}, sizes={sizes} */"
                )
        lines.append("")

    # Layout candidates
    if fn.layout_candidates:
        lines.append("    /* Layout candidates: */")
        for lc in fn.layout_candidates:
            if isinstance(lc, dict):
                base_id = lc.get("base_id", "?")
                kind = lc.get("layout_kind", "?")
                offsets = lc.get("observed_offsets", [])
                sizes = lc.get("observed_sizes", [])
                lines.append(
                    f"    /*   base={base_id}, kind={kind}, "
                    f"offsets={offsets}, sizes={sizes} */"
                )
        lines.append("")

    # Build replacement lookups
    return_lookup = _build_return_replacement_lookup(fn)
    callsite_lookup = _build_callsite_replacement_lookup(fn)
    replacer = _StatementReplacer(fn, return_lookup, callsite_lookup)

    temp_body_lines = []

    # Structured regions — recursive walk with replacements
    if fn.structured_regions:
        temp_body_lines.append("    /* Control flow structure: */")
        from src.ir.source.control_emitter import emit_regions_to_c

        condition_annotations = {}
        cr = fn.condition_recovery
        if isinstance(cr, dict):
            for site in cr.get("sites", []):
                if isinstance(site, dict):
                    rk = site.get("structured_region_kind")
                    bid = site.get("block_id")
                    ba = site.get("branch_address")
                    annot = site.get("annotation")
                    if rk and bid and annot:
                        if ba:
                            condition_annotations[(str(rk), str(bid), str(ba))] = annot
                        condition_annotations[(str(rk), str(bid))] = annot

        body_lines, _ = emit_regions_to_c(
            fn.structured_regions,
            fn.lowered_blocks,
            indent=1,
            seen_blocks=set(),
            condition_annotations=condition_annotations,
        )

        # Post-process emitted lines for return/call-site replacement
        processed_lines = _postprocess_body_lines(
            body_lines, fn, replacer
        )
        temp_body_lines.extend(processed_lines)
        temp_body_lines.append("")
    else:
        # Linear block sequence if no structuring region
        from src.ir.source.lowering import address_sort_key
        sorted_block_ids = sorted(fn.lowered_blocks.keys(), key=address_sort_key)
        if sorted_block_ids:
            temp_body_lines.append("    /* Linear block sequence: */")
            for b_id in sorted_block_ids:
                temp_body_lines.append(f"    /* block {b_id} */")
                stmts = fn.lowered_blocks.get(b_id, [])
                _emit_block_stmts_with_replacements(
                    stmts, b_id, replacer, "    ", temp_body_lines
                )
            temp_body_lines.append("")

    # Placeholder body
    if not fn.lowered_statements:
        temp_body_lines.append("    /* TODO: body reconstruction pending */")
        temp_body_lines.append("")

    # End-of-function return — Phase 5.4 strict placement rules
    _emit_fallback_return(fn, replacer, temp_body_lines)

    # Phase 5.7: adapt condition lines
    from src.ir.source.condition_adapter import adapt_condition_lines
    adapted_body_lines, adapter_stats = adapt_condition_lines(temp_body_lines)
    fn.condition_adapter = adapter_stats

    # Phase 7.2.2 ABI bridge injection for main
    import re
    bridges_added_count = 0
    if fn.c_name == "main":
        body_text = "\n".join(adapted_body_lines)
        bridge_lines = []
        if re.search(r'\barg0\b', body_text):
            bridge_lines.append("    u64 arg0 = (u64)argc;                  /* main ABI bridge: argc */")
            bridges_added_count += 1
        if re.search(r'\barg1\b', body_text):
            bridge_lines.append("    u64 arg1 = (u64)(uintptr_t)argv;       /* main ABI bridge: argv */")
            bridges_added_count += 1
        if re.search(r'\bparam_0\b', body_text):
            bridge_lines.append("    u64 param_0 = (u64)argc;               /* main ABI bridge: argc */")
            bridges_added_count += 1
        if re.search(r'\bparam_1\b', body_text):
            bridge_lines.append("    u64 param_1 = (u64)(uintptr_t)argv;    /* main ABI bridge: argv */")
            bridges_added_count += 1
        if bridge_lines:
            adapted_body_lines = bridge_lines + [""] + adapted_body_lines

    # Phase 5.6: run declaration analysis on final emitted body lines
    from src.ir.source.declaration_recovery import analyze_declarations_for_function
    decls_data = analyze_declarations_for_function(
        fn.name, fn.return_type, fn.parameters, fn.lowered_blocks, fn.structured_regions, emitted_body_lines=adapted_body_lines
    )
    
    # Store global call helpers if collector is provided
    if global_call_helpers is not None:
        for helper in decls_data.get("call_helpers", []):
            global_call_helpers.add(helper)

    # Update function-level metadata declarations so serialized JSON is in sync
    fn.declaration_recovery = decls_data

    # Emit local declarations block
    if decls_data.get("declarations"):
        lines.append("    /* Conservative pseudo declarations: */")
        for decl in decls_data["declarations"]:
            name = decl["name"]
            ctype = decl["ctype"]
            lines.append(f"    {ctype} {name} = 0;")
        lines.append("")

    # Emit actual body lines
    lines.extend(adapted_body_lines)

    lines.append("}")
    lines.append("")
    return bridges_added_count


def _postprocess_body_lines(
    body_lines: List[str],
    fn: ReconstructedFunction,
    replacer: _StatementReplacer,
) -> List[str]:
    """
    Post-process emitted body lines from control_emitter to apply
    Phase 5.4 return and call-site replacements.

    Since control_emitter outputs pre-formatted text lines, we match
    against the original statement text to find replacement candidates.
    """
    processed: List[str] = []

    # Build reverse lookups: original text -> (block_id, address, replacement)
    return_text_lookup: Dict[str, Tuple[str, str, str]] = {}
    rr = fn.return_recovery
    if isinstance(rr, dict):
        for site in rr.get("sites", []):
            if not isinstance(site, dict):
                continue
            block_id = site.get("block_id", "")
            addr = site.get("address", "")
            replacement = site.get("replacement_text")
            if replacement:
                # The original text pattern for return comments
                return_text_lookup["/* return via x0 */"] = (block_id, addr, replacement)

    callsite_text_lookup: Dict[str, Tuple[str, str, str]] = {}
    cr = fn.callsite_refinement
    if isinstance(cr, dict):
        for site in cr.get("sites", []):
            if not isinstance(site, dict):
                continue
            original = site.get("original_text", "")
            block_id = site.get("block_id", "")
            addr = site.get("address", "")
            refined = site.get("refined_text")
            if original and refined:
                callsite_text_lookup[original] = (block_id, addr, refined)

    for line in body_lines:
        stripped = line.strip()
        replaced = False

        # Check for return comment replacement
        if "/* return via x0 */" in stripped:
            # Find the matching site by checking all return sites
            for site in (rr.get("sites", []) if isinstance(rr, dict) else []):
                if not isinstance(site, dict):
                    continue
                replacement = site.get("replacement_text")
                if replacement:
                    block_id = site.get("block_id", "")
                    addr = site.get("address", "")
                    key = (block_id, addr)
                    if key not in replacer.returns_emitted:
                        # Replace the return comment with the recovered return
                        indent = line[:len(line) - len(line.lstrip())]
                        processed.append(f"{indent}{replacement}")
                        replacer.returns_emitted.add(key)
                        replaced = True
                        break

        # Check for call-site replacement
        if not replaced:
            for original_text, (block_id, addr, refined) in callsite_text_lookup.items():
                if original_text in stripped:
                    indent = line[:len(line) - len(line.lstrip())]
                    processed.append(f"{indent}{refined}")
                    replaced = True
                    break

        if not replaced:
            processed.append(line)

    return processed


def _emit_fallback_return(
    fn: ReconstructedFunction,
    replacer: _StatementReplacer,
    lines: List[str],
) -> None:
    """
    Emit the end-of-function return statement based on Phase 5.4 rules.

    Rules:
    - If every ret site was emitted as real return: no fallback.
    - If no ret site was emitted: append unknown/void fallback.
    - If some ret sites emitted but not all: append fallback for uncovered paths.
    """
    rr = fn.return_recovery
    is_void = fn.return_type in ("void",)

    if not isinstance(rr, dict):
        # No return recovery data — use old behavior
        if is_void:
            lines.append("    return; /* void return */")
        else:
            lines.append("    /* return value unknown */")
            lines.append("    return 0;")
        return

    total_sites = rr.get("return_sites_total", 0)
    sites = rr.get("sites", [])
    sites_with_replacement = sum(
        1 for s in sites
        if isinstance(s, dict) and s.get("replacement_text")
    )

    if total_sites == 0:
        # No return sites found at all
        if is_void:
            lines.append("    return; /* void return */")
        else:
            lines.append("    /* return value unknown */")
            lines.append("    return 0;")
        return

    emitted_count = len(replacer.returns_emitted)

    if emitted_count >= sites_with_replacement and sites_with_replacement == total_sites:
        # Every ret site was emitted as a real return — no fallback needed
        pass
    elif emitted_count == 0:
        # No ret site was emitted as a real return
        if is_void:
            lines.append("    return; /* void return */")
        else:
            lines.append("    /* return value unknown */")
            lines.append("    return 0;")
    else:
        # Some ret sites emitted, but not all
        if is_void:
            lines.append("    return; /* void return */")
        else:
            lines.append("    /* fallback return for paths without recovered return evidence */")
            lines.append("    return 0;")


# ---------------------------------------------------------------------------
# Main C emitter
# ---------------------------------------------------------------------------

def emit_recovered_c(
    artifact: SourceReconstructionArtifact,
    output_path: str,
) -> None:
    """
    Emit a conservative recovered.c skeleton from a SourceReconstructionArtifact.

    Parameters
    ----------
    artifact    : The SourceReconstructionArtifact to emit.
    output_path : Path to write the recovered.c file.
    """
    # 1. Pre-generate function definition lines and collect call helpers/statistics
    function_definitions: List[Tuple[ReconstructedFunction, List[str]]] = []
    global_call_helpers: Set[str] = set()
    total_adapters_inserted = 0
    total_evidence_adapters = 0
    total_unknown_adapters = 0
    total_cset_adapters_inserted = 0

    total_bridges_added = 0
    for fn in artifact.functions:
        fn_lines = []
        bridges_count = _emit_function(fn, fn_lines, global_call_helpers)
        total_bridges_added += bridges_count
        stats = fn.condition_adapter
        if stats:
            total_adapters_inserted += stats.get("condition_adapters_inserted", 0)
            total_evidence_adapters += stats.get("condition_evidence_adapters", 0)
            total_unknown_adapters += stats.get("condition_unknown_adapters", 0)
        
        # Count HEPHAESTUS_CSET in fn_lines
        for line in fn_lines:
            if "HEPHAESTUS_CSET(" in line:
                total_cset_adapters_inserted += line.count("HEPHAESTUS_CSET(")
                
        function_definitions.append((fn, fn_lines))

    unknown_condition_helpers_emitted = 1 if total_adapters_inserted > 0 else 0
    cset_helper_emitted = 1 if total_cset_adapters_inserted > 0 else 0

    # Update artifact summary counts
    artifact.summary["condition_adapters_inserted"] = total_adapters_inserted
    artifact.summary["condition_evidence_adapters"] = total_evidence_adapters
    artifact.summary["condition_unknown_adapters"] = total_unknown_adapters
    artifact.summary["unknown_condition_helpers_emitted"] = unknown_condition_helpers_emitted
    artifact.summary["cset_adapters_inserted"] = total_cset_adapters_inserted
    artifact.summary["cset_helper_emitted"] = cset_helper_emitted
    artifact.summary["main_abi_bridges_inserted"] = total_bridges_added

    lines: List[str] = []

    # File header
    timestamp = datetime.now(tz=None).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines.append("/*")
    lines.append(" * recovered.c — Phase 5.7.2 Conservative ARM64 Coverage Cleanup")
    lines.append(f" * Schema version: {artifact.schema_version}")
    lines.append(f" * Generated: {timestamp}")
    lines.append(" *")
    lines.append(" * AUTO-GENERATED — DO NOT EDIT")
    lines.append(" *")
    lines.append(
        " * This file contains conservative function skeletons reconstructed"
    )
    lines.append(
        " * from binary analysis evidence. No source-level semantics are"
    )
    lines.append(
        " * invented. Missing evidence is acceptable; fabricated evidence"
    )
    lines.append(" * is not.")
    lines.append(" */")
    lines.append("")

    # Standard includes
    lines.append("#include <stdint.h>")
    lines.append("#include <stddef.h>")
    lines.append("")

    # Custom type definitions
    lines.extend(emit_typedefs())
    lines.append("")

    # Helper function / Macro Design
    if unknown_condition_helpers_emitted == 1:
        lines.extend(emit_unknown_cond_helper())
        lines.append("")

    if cset_helper_emitted == 1:
        lines.extend(emit_cset_helper())
        lines.append("")

    # Forward declarations
    if artifact.functions:
        lines.append(
            "/* ================================================== */"
        )
        lines.append(
            "/*                 Forward Declarations                */"
        )
        lines.append(
            "/* ================================================== */"
        )
        lines.append("")
        for fn in artifact.functions:
            if fn.c_name == "main":
                c_ret = "int32_t"
                param_list = "int32_t argc, char **argv"
            else:
                c_ret = _map_c_type(fn.return_type)
                if fn.parameters:
                    param_strs = [_format_param(p, is_main=False) for p in fn.parameters]
                    param_list = ", ".join(param_strs)
                else:
                    param_list = "void"
            lines.append(f"{c_ret} {fn.c_name}({param_list});")
        lines.append("")

    # 2. Emit global call helpers
    existing_fn_names = set()
    for fn in artifact.functions:
        existing_fn_names.add(fn.c_name)
        existing_fn_names.add(fn.name)
        existing_fn_names.add(fn.canonical_name)
    existing_fn_names.update({"printf", "stack_chk_fail", "main"})
    existing_fn_names.update(RESERVED_HELPERS)

    filtered_helpers = []
    for helper in global_call_helpers:
        if helper not in existing_fn_names:
            filtered_helpers.append(helper)

    def helper_sort_key(name: str) -> int:
        try:
            return int(name[7:], 16)
        except ValueError:
            return 0

    sorted_helpers = sorted(filtered_helpers, key=helper_sort_key)
    if sorted_helpers:
        lines.append("/* Conservative call target helpers */")
        for helper in sorted_helpers:
            lines.append(f"u64 {helper}();")
        lines.append("")

    # Function bodies
    if function_definitions:
        lines.append(
            "/* ================================================== */"
        )
        lines.append(
            "/*                 Function Definitions                */"
        )
        lines.append(
            "/* ================================================== */"
        )
        lines.append("")
        for fn, fn_lines in function_definitions:
            lines.extend(fn_lines)

    # Write to file
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
        if lines:
            fh.write("\n")
