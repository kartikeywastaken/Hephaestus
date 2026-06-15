# -*- coding: utf-8 -*-
"""
Phase 5.2: Architecture-Dispatched Instruction Lowering Orchestrator
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from src.ir.source.statement_models import LoweredStatement
from src.ir.source.lowerers.arm64 import lower_arm64_instructions
from src.ir.source.lowerers.unsupported import lower_unsupported_instructions
from src.ir.utils.addressing import normalize_address


def address_sort_key(addr: Any) -> int:
    """Safely convert hex or decimal address into integer for sorting."""
    if not addr:
        return 0
    try:
        norm = normalize_address(str(addr))
        if norm.startswith("0x"):
            return int(norm, 16)
        return int(norm)
    except (ValueError, TypeError):
        return 0


def collect_function_instructions(ir_fn: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Flatten and sort blocks and instructions from an IR function."""
    blocks = ir_fn.get("basic_blocks", []) or []
    sorted_blocks = sorted(blocks, key=lambda b: address_sort_key(b.get("id")))
    out = []
    for block in sorted_blocks:
        instrs = block.get("instructions", []) or []
        sorted_instrs = sorted(instrs, key=lambda ins: address_sort_key(ins.get("address")))
        for ins in sorted_instrs:
            ins_copy = dict(ins)
            ins_copy["block_id"] = block.get("id")
            out.append((block.get("id"), ins_copy))
    return out


def detect_architecture(unified_ir: dict[str, Any] | None) -> str:
    """Detect architecture string from unified_ir provenance."""
    if not isinstance(unified_ir, dict):
        return "unknown"
    provenance = unified_ir.get("provenance", {})
    if not isinstance(provenance, dict):
        return "unknown"
    arch = provenance.get("architecture")
    if not arch:
        return "unknown"
    return str(arch).strip().lower()


def is_arm64(arch: str) -> bool:
    """Check if architecture maps to ARM64 lowerer."""
    a = arch.lower()
    return a == "arm64" or a.startswith("aarch64")


def lower_function_instructions(
    ir_function: dict[str, Any],
    semantic_function: dict[str, Any] | None = None,
    layout_candidates: list[dict[str, Any]] | None = None,
    unified_ir: dict[str, Any] | None = None,
    fn_param_counts: dict[str, int] | None = None,
) -> tuple[list[LoweredStatement], dict[str, Any]]:
    """
    Main lowering orchestrator. Sorts instructions, detects architecture, and dispatches.
    """
    # Flatten instructions in stable order
    instructions = collect_function_instructions(ir_function)

    # Detect architecture
    arch = detect_architecture(unified_ir)

    # Dispatch to appropriate lowerer
    if is_arm64(arch):
        return lower_arm64_instructions(
            ir_function,
            semantic_function,
            layout_candidates,
            instructions,
            fn_param_counts,
        )
    else:
        return lower_unsupported_instructions(ir_function, arch, instructions)
