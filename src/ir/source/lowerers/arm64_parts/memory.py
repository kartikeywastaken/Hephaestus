# -*- coding: utf-8 -*-
"""
ARM64 Lowerer Memory Helpers
"""

from __future__ import annotations
import re
from typing import Any
from .registers import normalize_register, c_temp_for_register

def signed_offset_name(offset: int) -> str:
    """Format signed offset for stack variable names (e.g. stack_m20)."""
    if offset < 0:
        return f"m{-offset}"
    return f"{offset}"

def stack_slot_name(offset: int) -> str:
    """Format stack slot variable name."""
    return f"stack_{signed_offset_name(offset)}"

def format_memory_deref(base_expr: str, offset: int, size: int | None, is_signed: bool = False) -> str:
    """Emits *(ctype *)(base_expr + offset) memory dereference expression."""
    if is_signed and size == 4:
        ctype = "i32"
    else:
        size_map = {1: "u8", 2: "u16", 4: "u32", 8: "u64"}
        ctype = size_map.get(size, "u64")

    if offset == 0:
        expr = f"*({ctype} *)({base_expr})"
    elif offset < 0:
        expr = f"*({ctype} *)({base_expr} - {-offset})"
    else:
        expr = f"*({ctype} *)({base_expr} + {offset})"

    if is_signed and size == 4:
        return f"(i64){expr}"
    return expr

def memory_expr(
    base: str,
    offset: int,
    size: int | None,
    reg_to_arg: dict[str, str] | None = None,
    is_signed: bool = False,
) -> str:
    """Format memory access expression conservatively."""
    base_lower = base.lower().strip()
    norm_base = normalize_register(base_lower)

    if norm_base in {"sp", "x29"}:
        # Stack accesses use stack_N notation
        stack_var = stack_slot_name(offset)
        if is_signed and size == 4:
            return f"(i64)(i32){stack_var}"
        return stack_var
    else:
        base_expr = c_temp_for_register(base_lower, reg_to_arg)
        return format_memory_deref(base_expr, offset, size, is_signed)

def parse_raw_mem_operand(raw_str: str) -> tuple[str, int] | None:
    """Fallback parser for pre-indexed/writeback memory raw strings (e.g., [sp, #-0x20]!)."""
    cleaned = raw_str.strip()
    if not (cleaned.startswith("[") and (cleaned.endswith("]") or cleaned.endswith("]!"))):
        return None

    inside = cleaned.replace("[", "").replace("]", "").replace("!", "").strip()
    parts = [p.strip() for p in inside.split(",")]
    if not parts:
        return None

    base = parts[0]
    offset = 0
    if len(parts) > 1:
        off_str = parts[1].strip()
        if off_str.startswith("#"):
            off_str = off_str[1:].strip()

        try:
            if off_str.startswith("0x") or off_str.startswith("-0x"):
                sign = -1 if off_str.startswith("-") else 1
                val_str = off_str.replace("-", "").replace("0x", "")
                offset = sign * int(val_str, 16)
            else:
                offset = int(off_str)
        except ValueError:
            return None

    return base, offset

def parse_indexed_memory_enhanced(raw_str: str) -> tuple[str, str, str | None, int, list[str]] | None:
    """Enhanced parser for indexed memory operands, extracting base, index, extension and shift."""
    cleaned = raw_str.strip()
    if not (cleaned.startswith("[") and (cleaned.endswith("]") or cleaned.endswith("]!"))):
        return None
    
    inside = cleaned.replace("[", "").replace("]", "").replace("!", "").strip()
    parts = [p.strip() for p in inside.split(",") if p.strip()]
    if len(parts) < 2:
        return None
        
    sec_part = parts[1].strip()
    if sec_part.startswith("#") or sec_part.startswith("-") or sec_part.startswith("+") or (sec_part and sec_part[0].isdigit()):
        return None
        
    base = parts[0]
    index = ""
    ext = None
    shift = 0
    warnings = []
    
    # 3 parts (base, index, ext_shift)
    if len(parts) >= 3:
        index = parts[1]
        ext_shift = parts[2]
        subparts = ext_shift.split()
        if len(subparts) >= 1:
            ext = subparts[0].upper()
            if len(subparts) >= 2:
                shift_str = subparts[1].replace("#", "").strip()
                if not shift_str:
                    return None
                is_hex = shift_str.lower().startswith("0x")
                val_to_check = shift_str[2:] if is_hex else shift_str
                if not val_to_check or not all(c in "0123456789abcdefABCDEF" if is_hex else c in "0123456789" for c in val_to_check):
                    return None
                try:
                    if is_hex:
                        shift = int(shift_str, 16)
                    else:
                        shift = int(shift_str)
                except ValueError:
                    return None
            else:
                if ext in {"LSL", "SXTW", "UXTW", "SXTX", "UXTX"}:
                    warnings.append("indexed_shift_missing_defaulted_to_0")
                    shift = 0
    else:
        # 2 parts
        index_and_more = parts[1]
        subparts = index_and_more.split()
        if len(subparts) >= 1:
            index = subparts[0]
            if len(subparts) >= 2:
                ext = subparts[1].upper()
                if len(subparts) >= 3:
                    shift_str = subparts[2].replace("#", "").strip()
                    if not shift_str:
                        return None
                    is_hex = shift_str.lower().startswith("0x")
                    val_to_check = shift_str[2:] if is_hex else shift_str
                    if not val_to_check or not all(c in "0123456789abcdefABCDEF" if is_hex else c in "0123456789" for c in val_to_check):
                        return None
                    try:
                        if is_hex:
                            shift = int(shift_str, 16)
                        else:
                            shift = int(shift_str)
                    except ValueError:
                        return None
                else:
                    if ext in {"LSL", "SXTW", "UXTW", "SXTX", "UXTX"}:
                        warnings.append("indexed_shift_missing_defaulted_to_0")
                        shift = 0
            else:
                ext = None
                shift = 0
        else:
            return None
            
    return base, index, ext, shift, warnings

def parse_indexed_memory(raw_str: str) -> tuple[str, str, str | None, int, list[str]] | None:
    """Parse indexed memory, delegating to the enhanced implementation."""
    return parse_indexed_memory_enhanced(raw_str)

def format_indexed_address(
    base: str,
    index: str,
    ext: str | None,
    shift: int,
    reg_to_arg: dict[str, str] | None = None,
) -> str:
    """Format the index address calculation expression."""
    base_expr = c_temp_for_register(base, reg_to_arg)
    index_expr = c_temp_for_register(index, reg_to_arg)
    
    if ext == "SXTW":
        inner = f"((i64)(i32){index_expr})"
    elif ext == "UXTW":
        inner = f"((u64)(u32){index_expr})"
    elif ext == "SXTX":
        inner = f"((i64){index_expr})"
    elif ext == "UXTX":
        inner = f"((u64){index_expr})"
    else:
        inner = index_expr
        
    if shift > 0:
        return f"{base_expr} + ({inner} << {shift})"
    else:
        return f"{base_expr} + {inner}"

def indexed_memory_expr(
    base: str,
    index: str,
    shift: int,
    size: int | None,
    reg_to_arg: dict[str, str] | None = None,
    is_signed: bool = False,
) -> str:
    """Format structured indexed memory operand conservatively: *(ctype *)(tmp_base + (tmp_index << shift))"""
    base_lower = base.lower().strip()
    index_lower = index.lower().strip()

    # Size-to-ctype mapping
    if is_signed and size == 4:
        ctype = "i32"
    else:
        size_map = {1: "u8", 2: "u16", 4: "u32", 8: "u64"}
        ctype = size_map.get(size, "u64")

    base_expr = c_temp_for_register(base_lower, reg_to_arg)
    index_expr = c_temp_for_register(index_lower, reg_to_arg)

    if shift > 0:
        expr = f"*({ctype} *)({base_expr} + ({index_expr} << {shift}))"
    else:
        expr = f"*({ctype} *)({base_expr} + {index_expr})"

    if is_signed and size == 4:
        return f"(i64){expr}"
    return expr
