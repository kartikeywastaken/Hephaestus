# -*- coding: utf-8 -*-
"""
Phase 5.2: Unsupported Architecture Lowerer
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from src.ir.source.statement_models import LoweredStatement


def lower_unsupported_instructions(
    ir_function: dict[str, Any],
    arch_str: str,
    instructions: list[tuple[str, dict[str, Any]]],
) -> tuple[list[LoweredStatement], dict[str, Any]]:
    """
    Lower instructions for unsupported architectures safely by turning
    each instruction into a comment.
    """
    statements: list[LoweredStatement] = []
    total = len(instructions)

    for block_id, ins in instructions:
        addr = ins.get("address")
        raw = ins.get("raw") or f"{ins.get('mnemonic', '')} ..."
        comment_text = f"/* {addr}: unsupported instruction for architecture {arch_str}: {raw} */"

        stmt = LoweredStatement(
            address=addr,
            kind="comment",
            text=comment_text,
            source_instruction=ins,
            lowered=False,
        )
        statements.append(stmt)

    summary = {
        "instructions_total": total,
        "instructions_lowered": 0,
        "instructions_commented": total,
        "coverage_percent": 0.0,
    }
    return statements, summary
