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

def _format_param(param: Dict[str, Any]) -> str:
    """Format a single parameter for a C function signature."""
    name = param.get("name", "arg")
    ptype = param.get("type", "u64")

    # Handle dict-style type
    if isinstance(ptype, dict):
        ptype = ptype.get("type", "unknown")

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
) -> None:
    """Emit a single function skeleton."""
    # Return type
    c_ret = _map_c_type(fn.return_type)

    # Parameter list
    if fn.parameters:
        param_strs = [_format_param(p) for p in fn.parameters]
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

    # Structured regions — recursive walk with replacements
    if fn.structured_regions:
        lines.append("    /* Control flow structure: */")
        from src.ir.source.control_emitter import emit_regions_to_c

        # We need to hook into the emission to apply replacements.
        # emit_regions_to_c returns lines with block statements.
        # We post-process those lines by matching block IDs and addresses.
        body_lines, _ = emit_regions_to_c(
            fn.structured_regions,
            fn.lowered_blocks,
            indent=1,
            seen_blocks=set(),
        )

        # Post-process emitted lines for return/call-site replacement
        processed_lines = _postprocess_body_lines(
            body_lines, fn, replacer
        )
        lines.extend(processed_lines)
        lines.append("")
    else:
        # Linear block sequence if no structuring region
        from src.ir.source.lowering import address_sort_key
        sorted_block_ids = sorted(fn.lowered_blocks.keys(), key=address_sort_key)
        if sorted_block_ids:
            lines.append("    /* Linear block sequence: */")
            for b_id in sorted_block_ids:
                lines.append(f"    /* block {b_id} */")
                stmts = fn.lowered_blocks.get(b_id, [])
                _emit_block_stmts_with_replacements(
                    stmts, b_id, replacer, "    ", lines
                )
            lines.append("")

    # Placeholder body
    if not fn.lowered_statements:
        lines.append("    /* TODO: body reconstruction pending */")
        lines.append("")

    # End-of-function return — Phase 5.4 strict placement rules
    _emit_fallback_return(fn, replacer, lines)

    lines.append("}")
    lines.append("")


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
    lines: List[str] = []

    # File header
    timestamp = datetime.now(tz=None).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines.append("/*")
    lines.append(" * recovered.c — Phase 5.4 Conservative Return and Call-Site Reconstruction")
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
    lines.append("typedef uint8_t u8;")
    lines.append("typedef uint16_t u16;")
    lines.append("typedef uint32_t u32;")
    lines.append("typedef uint64_t u64;")
    lines.append("typedef int8_t i8;")
    lines.append("typedef int16_t i16;")
    lines.append("typedef int32_t i32;")
    lines.append("typedef int64_t i64;")
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
            c_ret = _map_c_type(fn.return_type)
            if fn.parameters:
                param_strs = [_format_param(p) for p in fn.parameters]
                param_list = ", ".join(param_strs)
            else:
                param_list = "void"
            lines.append(f"{c_ret} {fn.c_name}({param_list});")
        lines.append("")

    # Function bodies
    if artifact.functions:
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
        for fn in artifact.functions:
            _emit_function(fn, lines)

    # Write to file
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
        if lines:
            fh.write("\n")
