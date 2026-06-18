# -*- coding: utf-8 -*-
"""
ARM64 Lowerer Conditions Helpers
"""

from __future__ import annotations
from typing import Any
from .registers import c_temp_for_register
from .operands import escape_c_string

VALID_ARM64_CONDITIONS = {
    "eq", "ne",
    "cs", "hs",
    "cc", "lo",
    "mi", "pl",
    "vs", "vc",
    "hi", "ls",
    "ge", "lt",
    "gt", "le",
    "al", "nv",
}

def parse_condition_code(cond_code: str) -> str | None:
    """Normalize and check condition code."""
    c = cond_code.lower().strip()
    if c in VALID_ARM64_CONDITIONS:
        return c
    return None

def parse_cset_operands(instr: dict) -> tuple[str | None, str | None]:
    """
    Return (dst_register, condition_code).

    Accept structured operands first.
    Fallback to raw string parse:
      cset <dst>, <cond>
    Normalize condition to lowercase.
    Strip commas/spaces.
    Validate condition code against VALID_ARM64_CONDITIONS.
    """
    ops = instr.get("operands", [])
    if not ops:
        raw = instr.get("raw", "")
        if raw:
            import re
            m = re.match(r"^\s*cset\s+([a-zA-Z0-9_]+)\s*,\s*([a-zA-Z0-9_]+)\s*$", raw, re.IGNORECASE)
            if m:
                dst = m.group(1).strip()
                cond = m.group(2).lower().strip()
                if cond in VALID_ARM64_CONDITIONS:
                    return dst, cond
        return None, None
        
    dst = ops[0]
    dst_val = dst.get("value") or dst.get("raw") or dst.get("name")
    if not dst_val:
        return None, None
        
    # Join subsequent operands to handle split condition code tokens
    cond_parts = []
    for op in ops[1:]:
        val = op.get("value") or op.get("raw") or op.get("name")
        if val is not None:
            cond_parts.append(str(val).strip())
    cond_code = "".join(cond_parts).lower().strip()
    
    # If the joined cond_code is not in VALID_ARM64_CONDITIONS, try raw parsing
    if cond_code not in VALID_ARM64_CONDITIONS:
        raw = instr.get("raw", "")
        if raw:
            import re
            m = re.match(r"^\s*cset\s+([a-zA-Z0-9_]+)\s*,\s*([a-zA-Z0-9_]+)\s*$", raw, re.IGNORECASE)
            if m:
                dst_val = m.group(1).strip()
                cond_code = m.group(2).lower().strip()
                
    if cond_code in VALID_ARM64_CONDITIONS:
        return str(dst_val), cond_code
        
    return None, None

def lower_cset(ins: dict, reg_to_arg: dict[str, str] | None) -> tuple[str, str, bool, bool] | None:
    """
    Lower cset instruction.
    Returns (lowered_text, stmt_kind, is_lowered, custom_comment) or None.
    """
    dst_reg, cond_code = parse_cset_operands(ins)
    if dst_reg and cond_code:
        dst_expr = c_temp_for_register(dst_reg, reg_to_arg)
        escaped_cond = escape_c_string(cond_code)
        text = f"{dst_expr} = HEPHAESTUS_CSET(\"{escaped_cond}\"); /* cset {dst_reg},{cond_code}; flags not modeled */"
        return text, "binary_op", True, True
    return None
