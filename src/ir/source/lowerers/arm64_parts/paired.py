# -*- coding: utf-8 -*-
"""
ARM64 Lowerer Paired Instruction (ldp/stp) Helpers
"""

from __future__ import annotations
import re
from typing import Any
from .registers import c_temp_for_register
from .operands import operand_to_expr
from .memory import memory_expr, parse_raw_mem_operand

def parse_ldp_raw(raw: str) -> tuple[str, str, str, int, bool] | None:
    """
    Parses a raw ldp instruction string.
    Returns (reg1, reg2, base, offset, is_post_index) or None.
    """
    raw = raw.strip()
    
    # Pattern 1: Normal offset / pre-index offset
    # Examples: ldp x29, x30, [sp, #0x60]
    #           ldp x8,x9,[x29,#-0x20]
    #           ldp x29,x30,[sp]
    m1 = re.match(r"^\s*ldp\s+([a-zA-Z0-9_]+)\s*,\s*([a-zA-Z0-9_]+)\s*,\s*\[\s*([a-zA-Z0-9_]+)\s*(?:,\s*#?(-?0x[0-9a-fA-F]+|-?[0-9]+))?\s*\]\s*!?\s*$", raw, re.IGNORECASE)
    if m1:
        reg1 = m1.group(1)
        reg2 = m1.group(2)
        base = m1.group(3)
        off_str = m1.group(4)
        offset = 0
        if off_str:
            try:
                if "0x" in off_str:
                    sign = -1 if off_str.startswith("-") else 1
                    val = int(off_str.replace("-", "").replace("0x", ""), 16)
                    offset = sign * val
                else:
                    offset = int(off_str)
            except ValueError:
                return None
        return reg1, reg2, base, offset, False

    # Pattern 2: Post-index offset
    # Examples: ldp x28,x27,[sp], #0x20
    #           ldp x28,x27,[sp],#0x20
    #           ldp x29,x30,[sp], #0x10
    m2 = re.match(r"^\s*ldp\s+([a-zA-Z0-9_]+)\s*,\s*([a-zA-Z0-9_]+)\s*,\s*\[\s*([a-zA-Z0-9_]+)\s*\]\s*,\s*#?(-?0x[0-9a-fA-F]+|-?[0-9]+)\s*$", raw, re.IGNORECASE)
    if m2:
        reg1 = m2.group(1)
        reg2 = m2.group(2)
        base = m2.group(3)
        off_str = m2.group(4)
        offset = 0
        if off_str:
            try:
                if "0x" in off_str:
                    sign = -1 if off_str.startswith("-") else 1
                    val = int(off_str.replace("-", "").replace("0x", ""), 16)
                    offset = sign * val
                else:
                    offset = int(off_str)
            except ValueError:
                return None
        return reg1, reg2, base, 0, True
        
    return None

def lower_paired(
    mnemonic: str,
    ops: list[dict[str, Any]],
    reg_to_arg: dict[str, str] | None,
    warnings: list[str],
    raw: str
) -> tuple[list[str], str, bool, bool] | None:
    """
    Handles lowering for ldp and stp.
    
    Returns (lowered_text_list, stmt_kind, is_lowered, custom_comment) or None.
    """
    lowered_text_list: list[str] = []
    stmt_kind = "unknown"
    is_lowered = False
    custom_comment = False

    if mnemonic in {"stp", "ldp"}:
        resolved = False
        # If it is ldp, try raw parsing first to ensure we get post-indexed and exact offsets
        if mnemonic == "ldp":
            parsed = parse_ldp_raw(raw)
            if parsed:
                reg1_name, reg2_name, base, offset, is_post_index = parsed
                reg1_expr = c_temp_for_register(reg1_name, reg_to_arg)
                reg2_expr = c_temp_for_register(reg2_name, reg_to_arg)
                reg1_val = reg1_name.lower().strip()
                resolved = True
        
        # Try standard structured parsing if not resolved yet
        if not resolved and len(ops) >= 3:
            reg1, reg2, mem = ops[0], ops[1], ops[2]
            try:
                reg1_expr = operand_to_expr(reg1, reg_to_arg, warnings=warnings)
                reg2_expr = operand_to_expr(reg2, reg_to_arg, warnings=warnings)
                if mem.get("kind") == "memory":
                    base = mem.get("base") or ""
                    raw_offset = mem.get("offset")
                    try:
                        offset = int(raw_offset) if raw_offset is not None else 0
                        resolved = True
                    except (ValueError, TypeError):
                        pass
                elif mem.get("kind") == "unknown":
                    parsed = parse_raw_mem_operand(mem.get("raw") or "")
                    if parsed:
                        base, offset = parsed
                        resolved = True
                is_post_index = False
                reg1_val = str(reg1.get("value") or "").lower()
            except Exception:
                pass

        if resolved:
            size = 4 if reg1_val.startswith("w") else 8
            
            if mnemonic == "stp":
                mem1 = memory_expr(base, offset, size, reg_to_arg)
                mem2 = memory_expr(base, offset + size, size, reg_to_arg)
                
                stmt1_text = f"{mem1} = {reg1_expr};"
                stmt2_text = f"{mem2} = {reg2_expr};"
                
                lowered_text_list.append(stmt1_text)
                lowered_text_list.append(f"{stmt2_text} /* paired store second register inferred offset +{size} */")
            else:  # ldp
                mem1 = memory_expr(base, offset, size, reg_to_arg)
                mem2 = memory_expr(base, offset + size, size, reg_to_arg)
                
                stmt1_text = f"{reg1_expr} = {mem1};"
                stmt2_text = f"{reg2_expr} = {mem2};"
                
                if is_post_index:
                    stmt1_text += f" /* {raw}; post-index writeback not modeled */"
                    stmt2_text += f" /* paired load second register inferred offset +{size} */"
                    custom_comment = True
                else:
                    stmt2_text += f" /* paired load second register inferred offset +{size} */"
                    
                lowered_text_list.append(stmt1_text)
                lowered_text_list.append(stmt2_text)
            stmt_kind = "store" if mnemonic == "stp" else "load"
            is_lowered = True

    if is_lowered:
        return lowered_text_list, stmt_kind, is_lowered, custom_comment
    return None
