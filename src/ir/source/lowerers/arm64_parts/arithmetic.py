# -*- coding: utf-8 -*-
"""
ARM64 Lowerer Arithmetic, Shifts, Logical, and Division Helpers
"""

from __future__ import annotations
import re
from typing import Any
from .registers import normalize_register, c_temp_for_register
from .operands import (
    operand_to_expr,
    parse_shifted_extended_reg,
    format_shifted_extended_expr,
    format_comment_operand,
)

def lower_arithmetic(
    mnemonic: str,
    ops: list[dict[str, Any]],
    reg_to_arg: dict[str, str] | None,
    warnings: list[str],
    raw: str,
    ins: dict[str, Any]
) -> tuple[list[str], str, bool, bool] | None:
    """
    Handles lowering for mov, movz, adrp, adds, subs, add, sub, and, orr, eor,
    mul, lsl, lsr, asr, udiv, sdiv, sxtw.
    
    Returns (lowered_text_list, stmt_kind, is_lowered, custom_comment) or None.
    """
    lowered_text_list: list[str] = []
    stmt_kind = "unknown"
    is_lowered = False
    custom_comment = False

    if mnemonic in {"mov", "movz"} and len(ops) >= 2:
        dst, src = ops[0], ops[1]
        dst_expr = operand_to_expr(dst, reg_to_arg, warnings=warnings)
        src_expr = operand_to_expr(src, reg_to_arg, warnings=warnings)
        lowered_text_list.append(f"{dst_expr} = {src_expr};")
        stmt_kind = "assign"
        is_lowered = True

    elif mnemonic == "adrp" and len(ops) >= 2:
        dst, imm = ops[0], ops[1]
        dst_expr = operand_to_expr(dst, reg_to_arg, warnings=warnings)
        val = imm.get("value")
        imm_expr = hex(val) if isinstance(val, int) else operand_to_expr(imm, reg_to_arg, warnings=warnings)
        lowered_text_list.append(f"{dst_expr} = {imm_expr};")
        stmt_kind = "assign"
        is_lowered = True

    elif mnemonic in {"subs", "adds"}:
        if len(ops) >= 2:
            if len(ops) >= 3:
                dst, src1, src2 = ops[0], ops[1], ops[2]
            else:
                dst, src1, src2 = ops[0], ops[0], ops[1]
            
            dst_val = str(dst.get("value") or "").lower()
            is_zero = dst_val in {"wzr", "xzr"}
            op_sym = "+" if mnemonic == "adds" else "-"
            
            src1_expr = operand_to_expr(src1, reg_to_arg, warnings=warnings)
            src2_expr = operand_to_expr(src2, reg_to_arg, warnings=warnings)
            
            if is_zero:
                # Zero register target: comparison comment only
                src1_comment = format_comment_operand(src1, reg_to_arg)
                src2_comment = format_comment_operand(src2, reg_to_arg)
                comment_text = f"/* {mnemonic} {dst_val},{src1_comment},{src2_comment}; flags updated, result discarded */"
                lowered_text_list.append(comment_text)
                stmt_kind = "compare"
                is_lowered = True
                custom_comment = True
            else:
                dst_expr = operand_to_expr(dst, reg_to_arg, warnings=warnings)
                stmt_text = f"{dst_expr} = {src1_expr} {op_sym} {src2_expr};"
                lowered_text_list.append(f"{stmt_text} /* {raw}; flags updated */")
                stmt_kind = "binary_op"
                is_lowered = True
                custom_comment = True

    elif mnemonic in {"add", "sub", "and", "orr", "eor"}:
        if len(ops) >= 2:
            if len(ops) >= 3:
                dst, src1, src2 = ops[0], ops[1], ops[2]
            else:
                dst, src1, src2 = ops[0], ops[0], ops[1]
            
            dst_expr = operand_to_expr(dst, reg_to_arg, warnings=warnings)
            src1_expr = operand_to_expr(src1, reg_to_arg, warnings=warnings)
            
            # 1. Try parsing shift/extend from raw text
            shift_type = None
            shift_val = 0
            raw_clean = raw.strip()
            shift_match = re.search(
                r",\s*(LSL|lsl|LSR|lsr|ASR|asr|SXTW|sxtw|UXTW|uxtw|SXTX|sxtx|UXTX|uxtx)(?:\s*#?\s*(0x[0-9a-fA-F]+|[0-9]+))?\s*$",
                raw_clean
            )
            if shift_match:
                shift_type = shift_match.group(1).upper()
                shift_val_str = shift_match.group(2)
                if shift_val_str:
                    try:
                        if shift_val_str.lower().startswith("0x"):
                            shift_val = int(shift_val_str, 16)
                        else:
                            shift_val = int(shift_val)
                    except ValueError:
                        pass
                        
            # 2. Try parsing from src2 if it's unknown kind
            src2_expr = None
            if src2.get("kind") == "unknown":
                parsed = parse_shifted_extended_reg(src2)
                if parsed:
                    reg, s_type, s_val = parsed
                    src2_expr = format_shifted_extended_expr(reg, s_type, s_val, reg_to_arg)
                    
            if not src2_expr:
                if shift_type:
                    src2_expr = format_shifted_extended_expr(src2.get("value", ""), shift_type, shift_val, reg_to_arg)
                else:
                    src2_expr = operand_to_expr(src2, reg_to_arg, warnings=warnings)
                    
            # Construct expression based on mnemonic
            if mnemonic == "add":
                op_sym = "+"
            elif mnemonic == "sub":
                op_sym = "-"
            elif mnemonic == "and":
                op_sym = "&"
            elif mnemonic == "orr":
                op_sym = "|"
            elif mnemonic == "eor":
                op_sym = "^"
                
            if mnemonic == "orr" and src1_expr == "0":
                lowered_text_list.append(f"{dst_expr} = {src2_expr};")
            elif mnemonic == "orr" and src2_expr == "0":
                lowered_text_list.append(f"{dst_expr} = {src1_expr};")
            else:
                lowered_text_list.append(f"{dst_expr} = {src1_expr} {op_sym} {src2_expr};")
            
            dst_norm = normalize_register(dst.get("value"))
            if dst_norm == "sp":
                stmt_kind = "stack_adjust"
            else:
                stmt_kind = "binary_op"
            is_lowered = True

    elif mnemonic == "mul":
        if len(ops) >= 3:
            dst, src1, src2 = ops[0], ops[1], ops[2]
            dst_expr = operand_to_expr(dst, reg_to_arg, warnings=warnings)
            src1_expr = operand_to_expr(src1, reg_to_arg, warnings=warnings)
            src2_expr = operand_to_expr(src2, reg_to_arg, warnings=warnings)
            lowered_text_list.append(f"{dst_expr} = {src1_expr} * {src2_expr};")
            is_lowered = True
        elif len(ops) == 2:
            dst, src = ops[0], ops[1]
            dst_expr = operand_to_expr(dst, reg_to_arg, warnings=warnings)
            src_expr = operand_to_expr(src, reg_to_arg, warnings=warnings)
            lowered_text_list.append(f"{dst_expr} = {dst_expr} * {src_expr};")
            is_lowered = True
        stmt_kind = "binary_op"

    elif mnemonic in {"lsl", "lsr", "asr"}:
        op_sym = "<<" if mnemonic == "lsl" else ">>"
        extra = " /* arithmetic shift */" if mnemonic == "asr" else ""
        if len(ops) >= 3:
            dst, src, shift = ops[0], ops[1], ops[2]
            dst_expr = operand_to_expr(dst, reg_to_arg, warnings=warnings)
            src_expr = operand_to_expr(src, reg_to_arg, warnings=warnings)
            shift_expr = operand_to_expr(shift, reg_to_arg, warnings=warnings)
            lowered_text_list.append(f"{dst_expr} = {src_expr} {op_sym} {shift_expr};{extra}")
            is_lowered = True
        elif len(ops) == 2:
            dst, shift = ops[0], ops[1]
            dst_expr = operand_to_expr(dst, reg_to_arg, warnings=warnings)
            shift_expr = operand_to_expr(shift, reg_to_arg, warnings=warnings)
            lowered_text_list.append(f"{dst_expr} = {dst_expr} {op_sym} {shift_expr};{extra}")
            is_lowered = True
        stmt_kind = "binary_op"

    elif mnemonic in {"udiv", "sdiv"} and len(ops) >= 3:
        dst, src1, src2 = ops[0], ops[1], ops[2]
        dst_val = str(dst.get("value") or "").lower()
        is_zero = dst_val in {"wzr", "xzr"}
        
        src1_expr = operand_to_expr(src1, reg_to_arg, warnings=warnings)
        src2_expr = operand_to_expr(src2, reg_to_arg, warnings=warnings)
        
        if mnemonic == "udiv":
            if is_zero:
                comment_text = f"/* udiv {dst_val},{c_temp_for_register(src1.get('value', ''), reg_to_arg)},{c_temp_for_register(src2.get('value', ''), reg_to_arg)}; result discarded */"
                lowered_text_list.append(comment_text)
                stmt_kind = "compare"
                is_lowered = True
                custom_comment = True
            else:
                dst_expr = operand_to_expr(dst, reg_to_arg, warnings=warnings)
                lowered_text_list.append(f"{dst_expr} = {src1_expr} / {src2_expr};")
                stmt_kind = "binary_op"
                is_lowered = True
        else:  # sdiv
            # Determine cast type
            cast_type = "i64" if dst_val.startswith("x") or dst_val == "xzr" else "i32"
            if is_zero:
                comment_text = f"/* sdiv {dst_val},(({cast_type}){c_temp_for_register(src1.get('value', ''), reg_to_arg)}),(({cast_type}){c_temp_for_register(src2.get('value', ''), reg_to_arg)}); result discarded */"
                lowered_text_list.append(comment_text)
                stmt_kind = "compare"
                is_lowered = True
                custom_comment = True
            else:
                dst_expr = operand_to_expr(dst, reg_to_arg, warnings=warnings)
                lowered_text_list.append(f"{dst_expr} = (({cast_type}){src1_expr}) / (({cast_type}){src2_expr});")
                stmt_kind = "binary_op"
                is_lowered = True

    elif mnemonic == "sxtw" and len(ops) >= 2:
        dst, src = ops[0], ops[1]
        dst_expr = operand_to_expr(dst, reg_to_arg, warnings=warnings)
        src_expr = operand_to_expr(src, reg_to_arg, warnings=warnings)
        dst_val = str(dst.get("value") or "").lower()
        
        if dst_val.startswith("x"):
            lowered_text_list.append(f"{dst_expr} = (i64)(i32){src_expr};")
        else:
            lowered_text_list.append(f"{dst_expr} = {src_expr}; /* sxtw {dst_val},{src.get('value', '')}; width already 32-bit */")
            custom_comment = True
        stmt_kind = "binary_op"
        is_lowered = True

    if is_lowered:
        return lowered_text_list, stmt_kind, is_lowered, custom_comment
    return None
