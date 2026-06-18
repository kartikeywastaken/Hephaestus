# -*- coding: utf-8 -*-
"""
Phase 5.2: ARM64 Conservative Instruction Lowerer
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple
from src.ir.source.statement_models import LoweredStatement
from src.ir.utils.addressing import normalize_address


# ---------------------------------------------------------------------------
# Helpers for register and memory formatting
# ---------------------------------------------------------------------------

from src.ir.source.lowerers.arm64_parts.registers import normalize_register, c_temp_for_register
from src.ir.source.lowerers.arm64_parts.operands import (
    filter_semantic_operands,
    parse_shifted_extended_reg,
    format_shifted_extended_expr,
    escape_c_string,
    operand_to_expr,
    assert_no_raw_bracket_memory_expr,
    format_comment_operand,
)
from src.ir.source.lowerers.arm64_parts.memory import memory_expr, parse_indexed_memory_enhanced, format_indexed_address, indexed_memory_expr, parse_raw_mem_operand


# (parse_shifted_extended_reg and format_shifted_extended_expr are now imported from src.ir.source.lowerers.arm64_parts.operands)


# (memory parsing and expression formatting are now imported from src.ir.source.lowerers.arm64_parts.memory)


from src.ir.source.lowerers.arm64_parts.conditions import (
    VALID_ARM64_CONDITIONS,
    parse_cset_operands,
    lower_cset,
)
from src.ir.source.lowerers.arm64_parts.arithmetic import lower_arithmetic
from src.ir.source.lowerers.arm64_parts.loads_stores import lower_loads_stores
from src.ir.source.lowerers.arm64_parts.paired import lower_paired
from src.ir.source.lowerers.arm64_parts.branches import lower_branches
from src.ir.source.lowerers.arm64_parts.calls import lower_calls
from src.ir.source.lowerers.arm64_parts.unsupported import unsupported_fallback_text


# ---------------------------------------------------------------------------
# Main lowering function for ARM64
# ---------------------------------------------------------------------------

def lower_arm64_instructions(
    ir_function: dict[str, Any],
    semantic_function: dict[str, Any] | None,
    layout_candidates: list[dict[str, Any]] | None,
    instructions: list[tuple[str, dict[str, Any]]],
    fn_param_counts: dict[str, int] | None = None,
) -> tuple[list[LoweredStatement], dict[str, Any]]:
    """
    Lower a flattened list of ARM64 instructions into pseudo-C statements.
    """
    # 1. Build ABI reg-to-arg mapping with conflict resolution
    reg_to_arg: dict[str, str] = {}
    bindings_warnings: list[str] = []
    
    if semantic_function:
        abi_bindings = semantic_function.get("abi_argument_bindings", []) or []
        from collections import defaultdict
        bindings_by_reg = defaultdict(set)
        
        for binding in abi_bindings:
            if not isinstance(binding, dict):
                continue
            idx = binding.get("argument_index")
            base = binding.get("base_register") or binding.get("register") or binding.get("current_register")
            if idx is not None and base:
                norm_base = normalize_register(str(base))
                if norm_base:
                    try:
                        bindings_by_reg[norm_base].add(int(idx))
                    except (ValueError, TypeError):
                        continue
        
        for reg, idxs in bindings_by_reg.items():
            if len(idxs) == 1:
                reg_to_arg[reg] = f"arg{list(idxs)[0]}"
            elif len(idxs) > 1:
                msg = f"Conflicting ABI bindings for {reg}: {sorted(idxs)}"
                bindings_warnings.append(msg)

    # 2. Main instruction lowering loop
    statements: list[LoweredStatement] = []
    instructions_lowered = 0
    instructions_commented = 0
    
    fn_param_counts = fn_param_counts or {}

    for block_id, ins in instructions:
        addr = ins.get("address")
        mnemonic = (ins.get("mnemonic") or "").lower().strip()
        raw = ins.get("raw") or f"{mnemonic} ..."
        ops = filter_semantic_operands(ins.get("operands"))

        lowered_text_list: list[str] = []
        stmt_kind = "unknown"
        is_lowered = False
        warnings: list[str] = []
        custom_comment = False

        try:
            # Check for supported instruction patterns
            res = lower_arithmetic(mnemonic, ops, reg_to_arg, warnings, raw, ins)
            if res:
                lowered_text_list, stmt_kind, is_lowered, custom_comment = res

            elif mnemonic == "cset":
                res = lower_cset(ins, reg_to_arg)
                if res:
                    text, stmt_kind, is_lowered, custom_comment = res
                    lowered_text_list.append(text)

            elif res := lower_loads_stores(mnemonic, ops, reg_to_arg, warnings):
                lowered_text_list, stmt_kind, is_lowered, custom_comment = res

            elif mnemonic in {"cmp", "cmn", "tst"} and len(ops) >= 2:
                op1, op2 = ops[0], ops[1]
                op1_expr = operand_to_expr(op1, reg_to_arg, warnings=warnings)
                op2_expr = operand_to_expr(op2, reg_to_arg, warnings=warnings)
                lowered_text_list.append(f"/* compare: {op1_expr} vs {op2_expr} */")
                stmt_kind = "compare"
                is_lowered = True

            elif res := lower_calls(mnemonic, ops, reg_to_arg, warnings, fn_param_counts):
                lowered_text_list, stmt_kind, is_lowered, custom_comment = res

            elif res := lower_branches(mnemonic, ops, reg_to_arg, warnings):
                lowered_text_list, stmt_kind, is_lowered, custom_comment = res

            elif res := lower_paired(mnemonic, ops, reg_to_arg, warnings, raw):
                lowered_text_list, stmt_kind, is_lowered, custom_comment = res

            elif mnemonic == "movk":
                # Explicitly comment out partial updates as unsupported bitfield operations
                lowered_text_list.append(f"/* partial immediate update unsupported: {raw} */")
                stmt_kind = "comment"
                is_lowered = False

        except Exception as ex:
            warnings.append(f"Error lowering instruction: {ex}")
            is_lowered = False

        # If lowering succeeded, validate and construct statements
        if is_lowered and lowered_text_list:
            try:
                for text in lowered_text_list:
                    assert_no_raw_bracket_memory_expr(text)
            except Exception as ex:
                warnings.append(f"Validation error: {ex}")
                is_lowered = False

        if is_lowered and lowered_text_list:
            for i, text in enumerate(lowered_text_list):
                if custom_comment:
                    comment_part = ""
                else:
                    comment_part = f" /* {raw} */" if i == 0 else ""
                stmt = LoweredStatement(
                    address=addr,
                    kind=stmt_kind,
                    text=f"{text}{comment_part}",
                    source_instruction=ins,
                    lowered=True,
                    warnings=warnings
                )
                statements.append(stmt)
            instructions_lowered += 1
        else:
            fallback_text = unsupported_fallback_text(mnemonic, raw, addr)

            stmt = LoweredStatement(
                address=addr,
                kind="comment" if mnemonic == "movk" else "unknown",
                text=fallback_text,
                source_instruction=ins,
                lowered=False,
                warnings=warnings
            )
            statements.append(stmt)
            instructions_commented += 1

    total = instructions_lowered + instructions_commented
    summary = {
        "instructions_total": total,
        "instructions_lowered": instructions_lowered,
        "instructions_commented": instructions_commented,
        "coverage_percent": round((instructions_lowered / total) * 100, 2) if total else 0.0
    }
    return statements, summary
