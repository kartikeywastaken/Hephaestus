# -*- coding: utf-8 -*-
"""
ARM64 Lowerer Call Instructions Helpers
"""

from __future__ import annotations
from typing import Any
from src.ir.utils.addressing import normalize_address
from src.ir.source.names import sanitize_c_identifier
from .registers import c_temp_for_register
from .operands import operand_to_expr

def lower_calls(
    mnemonic: str,
    ops: list[dict[str, Any]],
    reg_to_arg: dict[str, str] | None,
    warnings: list[str],
    fn_param_counts: dict[str, int]
) -> tuple[list[str], str, bool, bool] | None:
    """
    Handles lowering for bl and blr.
    
    Returns (lowered_text_list, stmt_kind, is_lowered, custom_comment) or None.
    """
    lowered_text_list: list[str] = []
    stmt_kind = "unknown"
    is_lowered = False
    custom_comment = False

    if mnemonic == "bl" and len(ops) >= 1:
        target = ops[0]
        target_name = ""
        if target.get("kind") == "symbol":
            target_name = target.get("name") or ""
        elif target.get("kind") == "immediate":
            val = target.get("value")
            target_name = hex(val) if isinstance(val, int) else str(val)
        else:
            target_name = str(target.get("value") or target.get("name") or "")

        if target_name.startswith("0x"):
            call_target = f"call_{target_name}"
            norm_target = normalize_address(target_name)
        else:
            call_target = f"call_{sanitize_c_identifier(target_name)}"
            norm_target = target_name

        # Look up target parameter count
        num_params = fn_param_counts.get(norm_target)
        if num_params is None:
            # Try fallback to lookup on non-normalized target_name
            num_params = fn_param_counts.get(target_name, 4)
        
        args = [c_temp_for_register(f"x{i}", reg_to_arg) for i in range(num_params)]
        args_str = ", ".join(args)
        lowered_text_list.append(f"{call_target}({args_str});")
        stmt_kind = "call"
        is_lowered = True

    elif mnemonic == "blr" and len(ops) >= 1:
        reg = ops[0]
        reg_expr = operand_to_expr(reg, reg_to_arg, warnings=warnings)
        lowered_text_list.append(f"/* indirect call via {reg_expr} */")
        stmt_kind = "comment"
        is_lowered = True

    if is_lowered:
        return lowered_text_list, stmt_kind, is_lowered, custom_comment
    return None
