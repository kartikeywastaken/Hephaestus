# -*- coding: utf-8 -*-
"""
ARM64 Lowerer Loads and Stores Helpers
"""

from __future__ import annotations
from typing import Any
from .operands import operand_to_expr

def lower_loads_stores(
    mnemonic: str,
    ops: list[dict[str, Any]],
    reg_to_arg: dict[str, str] | None,
    warnings: list[str]
) -> tuple[list[str], str, bool, bool] | None:
    """
    Handles lowering for ldrsb, ldr, ldur, ldrb, ldrh, ldurb, ldurh, ldrsw, ldursw,
    str, stur, strb, strh.
    
    Returns (lowered_text_list, stmt_kind, is_lowered, custom_comment) or None.
    """
    lowered_text_list: list[str] = []
    stmt_kind = "unknown"
    is_lowered = False
    custom_comment = False

    if mnemonic == "ldrsb" and len(ops) >= 2:
        dst, mem = ops[0], ops[1]
        dst_expr = operand_to_expr(dst, reg_to_arg, warnings=warnings)
        dst_val = str(dst.get("value") or "").lower()
        outer_cast = "(i64)" if dst_val.startswith("x") else "(i32)"
        
        mem_expr = operand_to_expr(mem, reg_to_arg, size_override=1, warnings=warnings)
        mem_expr_signed = mem_expr.replace("*(u8 *)", "*(i8 *)")
        
        lowered_text_list.append(f"{dst_expr} = {outer_cast}{mem_expr_signed};")
        stmt_kind = "load"
        is_lowered = True

    elif mnemonic in {"ldr", "ldur", "ldrb", "ldrh", "ldurb", "ldurh", "ldrsw", "ldursw"} and len(ops) >= 2:
        dst, mem = ops[0], ops[1]
        dst_expr = operand_to_expr(dst, reg_to_arg, warnings=warnings)
        
        # Determine access size
        if mnemonic in {"ldrb", "ldurb"}:
            size = 1
        elif mnemonic in {"ldrh", "ldurh"}:
            size = 2
        elif mnemonic in {"ldrsw", "ldursw"}:
            size = 4
        else:
            size = mem.get("size_bytes")
            if size is None:
                dst_val = str(dst.get("value") or "").lower()
                size = 4 if dst_val.startswith("w") else 8
        
        mem_expr = operand_to_expr(mem, reg_to_arg, size_override=size, is_signed_override=(mnemonic in {"ldrsw", "ldursw"}), warnings=warnings)
        lowered_text_list.append(f"{dst_expr} = {mem_expr};")
        stmt_kind = "load"
        is_lowered = True

    elif mnemonic in {"str", "stur", "strb", "strh"} and len(ops) >= 2:
        src, mem = ops[0], ops[1]
        src_expr = operand_to_expr(src, reg_to_arg, warnings=warnings)
        
        # Determine access size
        if mnemonic == "strb":
            size = 1
        elif mnemonic == "strh":
            size = 2
        else:
            size = mem.get("size_bytes")
            if size is None:
                src_val = str(src.get("value") or "").lower()
                size = 4 if src_val.startswith("w") else 8
        
        mem_expr = operand_to_expr(mem, reg_to_arg, size_override=size, warnings=warnings)
        lowered_text_list.append(f"{mem_expr} = {src_expr};")
        stmt_kind = "store"
        is_lowered = True

    if is_lowered:
        return lowered_text_list, stmt_kind, is_lowered, custom_comment
    return None
