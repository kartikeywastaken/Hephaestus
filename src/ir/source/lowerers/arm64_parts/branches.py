# -*- coding: utf-8 -*-
"""
ARM64 Lowerer Branch Instructions Helpers
"""

from __future__ import annotations
from typing import Any
from src.ir.utils.addressing import normalize_address
from .operands import operand_to_expr

def lower_branches(
    mnemonic: str,
    ops: list[dict[str, Any]],
    reg_to_arg: dict[str, str] | None,
    warnings: list[str]
) -> tuple[list[str], str, bool, bool] | None:
    """
    Handles lowering for cbz, cbnz, tbz, tbnz, b, br, ret, and conditional branches.
    
    Returns (lowered_text_list, stmt_kind, is_lowered, custom_comment) or None.
    """
    lowered_text_list: list[str] = []
    stmt_kind = "unknown"
    is_lowered = False
    custom_comment = False

    if mnemonic in {
        "b.eq", "b.ne", "b.ge", "b.gt", "b.le", "b.lt",
        "b.hi", "b.hs", "b.lo", "b.ls", "b.mi", "b.pl",
        "b.vs", "b.vc", "b.cs", "b.cc"
    } and len(ops) >= 1:
        target = ops[0]
        target_expr = operand_to_expr(target, reg_to_arg, warnings=warnings)
        norm_target = normalize_address(target_expr)
        lowered_text_list.append(f"/* conditional branch {mnemonic} -> {norm_target} */")
        stmt_kind = "conditional_branch_comment"
        is_lowered = True
        custom_comment = True

    elif mnemonic in {"cbz", "cbnz"} and len(ops) >= 2:
        reg, target = ops[0], ops[1]
        reg_expr = operand_to_expr(reg, reg_to_arg, warnings=warnings)
        target_expr = operand_to_expr(target, reg_to_arg, warnings=warnings)
        norm_target = normalize_address(target_expr)
        lowered_text_list.append(f"/* {mnemonic} {reg_expr} -> {norm_target} */")
        stmt_kind = "compare_branch_comment"
        is_lowered = True
        custom_comment = True

    elif mnemonic in {"tbz", "tbnz"} and len(ops) >= 3:
        reg, bit, target = ops[0], ops[1], ops[2]
        reg_expr = operand_to_expr(reg, reg_to_arg, warnings=warnings)
        bit_val = bit.get("value")
        if bit_val is not None:
            try:
                bit_str = str(int(bit_val))
            except (ValueError, TypeError):
                bit_str = str(bit_val).replace("#", "")
        else:
            bit_str = operand_to_expr(bit, reg_to_arg, warnings=warnings).replace("#", "")
        target_expr = operand_to_expr(target, reg_to_arg, warnings=warnings)
        norm_target = normalize_address(target_expr)
        lowered_text_list.append(f"/* {mnemonic} {reg_expr} bit {bit_str} -> {norm_target} */")
        stmt_kind = "test_branch_comment"
        is_lowered = True
        custom_comment = True

    elif mnemonic in {"b", "br"} and len(ops) >= 1:
        target = ops[0]
        target_expr = operand_to_expr(target, reg_to_arg, warnings=warnings)
        lowered_text_list.append(f"/* branch to {target_expr} */")
        stmt_kind = "branch_comment"
        is_lowered = True

    elif mnemonic == "ret":
        lowered_text_list.append("/* return via x0 */")
        stmt_kind = "return_comment"
        is_lowered = True

    if is_lowered:
        return lowered_text_list, stmt_kind, is_lowered, custom_comment
    return None
