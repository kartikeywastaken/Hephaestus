# -*- coding: utf-8 -*-
"""
Phase 5.1: Conservative C Skeleton Emitter

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
from typing import Any, Dict, List

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

def _emit_region_tree(
    region: Dict[str, Any],
    lines: List[str],
    indent: int,
) -> None:
    """
    Recursively walk a structuring region tree and emit structural comments.

    Each region type is emitted as a comment describing the control-flow
    structure observed by Phase 3. No conditions, loop bounds, or source
    expressions are invented.
    """
    prefix = "    " * indent
    region_type = region.get("type", "unknown")

    if region_type == "block":
        block_id = region.get("id", "?")
        lines.append(f"{prefix}/* block {block_id} */")

    elif region_type == "sequence":
        lines.append(f"{prefix}/* sequence begin */")
        for child in region.get("children", []):
            if isinstance(child, dict):
                _emit_region_tree(child, lines, indent + 1)
        lines.append(f"{prefix}/* sequence end */")

    elif region_type == "if":
        cond_block = region.get("condition_block", "?")
        merge_block = region.get("merge_block", "?")
        lines.append(
            f"{prefix}/* if (condition at block {cond_block}) "
            f"merge={merge_block} */"
        )
        lines.append(f"{prefix}/* then: */")
        then_branch = region.get("then_branch", {})
        if isinstance(then_branch, dict):
            _emit_region_tree(then_branch, lines, indent + 1)

    elif region_type == "if_else":
        cond_block = region.get("condition_block", "?")
        merge_block = region.get("merge_block", "?")
        lines.append(
            f"{prefix}/* if-else (condition at block {cond_block}) "
            f"merge={merge_block} */"
        )
        lines.append(f"{prefix}/* then: */")
        then_branch = region.get("then_branch", {})
        if isinstance(then_branch, dict):
            _emit_region_tree(then_branch, lines, indent + 1)
        lines.append(f"{prefix}/* else: */")
        else_branch = region.get("else_branch", {})
        if isinstance(else_branch, dict):
            _emit_region_tree(else_branch, lines, indent + 1)

    elif region_type == "loop":
        kind = region.get("kind", "unknown")
        header = region.get("header_block", "?")
        exits = region.get("exit_blocks", [])
        lines.append(
            f"{prefix}/* loop ({kind}) header={header} "
            f"exits={exits} */"
        )
        body = region.get("body", {})
        if isinstance(body, dict):
            _emit_region_tree(body, lines, indent + 1)

    elif region_type == "unstructured":
        reason = region.get("reason", "unknown")
        region_kind = region.get("region_kind", "unknown")
        lines.append(
            f"{prefix}/* unstructured region "
            f"(reason={reason}, kind={region_kind}) */"
        )
        for child in region.get("children", []):
            if isinstance(child, dict):
                _emit_region_tree(child, lines, indent + 1)

    else:
        lines.append(f"{prefix}/* region type={region_type} */")


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

    # Structured regions — recursive walk
    if fn.structured_regions:
        lines.append("    /* Control flow structure: */")
        for region in fn.structured_regions:
            if isinstance(region, dict):
                _emit_region_tree(region, lines, indent=1)
        lines.append("")

    # Placeholder body
    lines.append("    /* TODO: body reconstruction pending */")
    lines.append("")

    # Placeholder return
    if fn.return_type == "void":
        lines.append("    return; /* placeholder */")
    else:
        lines.append("    return 0; /* placeholder */")

    lines.append("}")
    lines.append("")


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
    lines.append(" * recovered.c — Phase 5.1 Source Reconstruction Skeleton")
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
