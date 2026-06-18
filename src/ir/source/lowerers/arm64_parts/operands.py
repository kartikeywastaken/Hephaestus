# -*- coding: utf-8 -*-
"""
ARM64 Lowerer Operands Helpers
"""

from __future__ import annotations
import re
from typing import Any
from .registers import normalize_register, c_temp_for_register
from .memory import (
    memory_expr,
    indexed_memory_expr,
    parse_indexed_memory_enhanced,
    format_indexed_address,
    parse_raw_mem_operand,
)

def filter_semantic_operands(ops: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Filter out parser tokens (e.g. #, comma, shift tokens) from operands list."""
    if not isinstance(ops, list):
        return []
    clean = []
    cond_codes = {"eq", "ne", "cs", "hs", "cc", "lo", "mi", "pl", "vs", "vc", "hi", "ls", "ge", "lt", "gt", "le", "al", "nv"}
    for op in ops:
        if not isinstance(op, dict):
            continue
        kind = op.get("kind", "")
        if kind in {"register", "immediate", "memory", "symbol"}:
            clean.append(op)
        elif kind == "unknown":
            raw = str(op.get("raw") or "").strip()
            if (raw.startswith("[") and "]" in raw) or parse_shifted_extended_reg(op) is not None or raw.lower() in cond_codes:
                clean.append(op)
    return clean

def operand_register(op: dict[str, Any]) -> str | None:
    """Return register name if operand is a register."""
    if op.get("kind") == "register":
        return op.get("value")
    return None

def operand_immediate(op: dict[str, Any]) -> int | None:
    """Return immediate value if operand is an immediate."""
    if op.get("kind") == "immediate":
        return op.get("value")
    return None

def operand_raw(op: dict[str, Any]) -> str:
    """Return raw instruction string representation of operand."""
    return str(op.get("raw") or "")

def parse_int_literal(val_str: str) -> int | None:
    """Parse integer literal, supporting both decimal and hex formats."""
    try:
        val_str = val_str.strip()
        if val_str.lower().startswith("0x") or val_str.lower().startswith("-0x"):
            sign = -1 if val_str.startswith("-") else 1
            pure = val_str.replace("-", "").replace("0x", "")
            return sign * int(pure, 16)
        # Remove any '#' prefix
        if val_str.startswith("#"):
            val_str = val_str[1:].strip()
        return int(val_str)
    except ValueError:
        return None

def format_original_instruction(instr: dict[str, Any]) -> str:
    """Return raw assembly of original instruction."""
    return str(instr.get("raw") or "")

def escape_c_string(val: str) -> str:
    """Escape control characters and quotes for standard C comments/strings."""
    return val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")

def parse_shifted_extended_reg(op: dict[str, Any]) -> tuple[str, str | None, int] | None:
    """Parse a shifted or extended register operand. E.g. w9, SXTW #2"""
    if op.get("kind") != "unknown":
        return None
    raw = str(op.get("raw") or "").strip()
    match = re.match(
        r"^([a-zA-Z0-9_]+)\s*,\s*(LSL|lsl|LSR|lsr|ASR|asr|SXTW|sxtw|UXTW|uxtw|SXTX|sxtx|UXTX|uxtx)(?:\s*#?\s*(0x[0-9a-fA-F]+|[0-9]+))?$",
        raw
    )
    if not match:
        return None
    reg = match.group(1)
    shift_type = match.group(2).upper()
    shift_val_str = match.group(3)
    
    shift = 0
    if shift_val_str:
        try:
            if shift_val_str.lower().startswith("0x"):
                shift = int(shift_val_str, 16)
            else:
                shift = int(shift_val_str)
        except ValueError:
            pass
    return reg, shift_type, shift

def format_shifted_extended_expr(
    reg: str,
    shift_type: str | None,
    shift: int,
    reg_to_arg: dict[str, str] | None = None,
) -> str:
    """Format shifted or extended register operand as a C expression."""
    reg_expr = c_temp_for_register(reg, reg_to_arg)
    if not shift_type:
        return reg_expr
        
    if shift_type in {"LSL", "LSR", "ASR"}:
        op = "<<" if shift_type == "LSL" else ">>"
        return f"({reg_expr} {op} {shift})"
        
    if shift_type == "SXTW":
        inner = f"((i64)(i32){reg_expr})"
    elif shift_type == "UXTW":
        inner = f"((u64)(u32){reg_expr})"
    elif shift_type == "SXTX":
        inner = f"((i64){reg_expr})"
    elif shift_type == "UXTX":
        inner = f"((u64){reg_expr})"
    else:
        return reg_expr
        
    if shift > 0:
        return f"({inner} << {shift})"
    else:
        return inner

def assert_no_raw_bracket_memory_expr(expr: str) -> None:
    stripped = expr.strip()
    if stripped.startswith("[") or " = [" in stripped or " =  [" in stripped or "=[" in stripped:
        raise ValueError("raw ARM64 bracket memory expression leaked into generated C expression")

def operand_to_expr(
    op: dict[str, Any],
    reg_to_arg: dict[str, str] | None = None,
    size_override: int | None = None,
    is_signed_override: bool = False,
    warnings: list[str] | None = None,
) -> str:
    """Convert an operand dictionary into its C expression string."""
    kind = op.get("kind", "")
    if kind == "register":
        return c_temp_for_register(op.get("value", ""), reg_to_arg)
    elif kind == "immediate":
        val = op.get("value")
        if isinstance(val, int):
            # Hex format if val looks like an address or is large, else decimal
            if val > 0x10000 or val < -0x10000:
                return hex(val)
            return str(val)
        return str(val)
    elif kind == "memory":
        base = op.get("base", "")
        index = op.get("index")

        # Check if structured indexed memory operand
        if index:
            raw_shift = op.get("shift") or op.get("scale")
            try:
                shift = int(raw_shift) if raw_shift is not None else 0
            except (ValueError, TypeError):
                shift = 0
            size = size_override if size_override is not None else op.get("size_bytes")
            return indexed_memory_expr(base, index, shift, size, reg_to_arg, is_signed_override)

        # Standard base + offset
        raw_offset = op.get("offset")
        try:
            offset = int(raw_offset) if raw_offset is not None else 0
        except (ValueError, TypeError):
            offset = 0

        # Size mapping
        size = size_override if size_override is not None else op.get("size_bytes")
        return memory_expr(base, offset, size, reg_to_arg, is_signed_override)
    elif kind == "symbol":
        name = op.get("name", "")
        return name
    elif kind == "unknown":
        raw = op.get("raw", "")

        parsed_indexed = parse_indexed_memory_enhanced(raw)
        if parsed_indexed:
            base, index, ext, shift, warnings_list = parsed_indexed
            if warnings is not None:
                warnings.extend(warnings_list)
            addr_expr = format_indexed_address(base, index, ext, shift, reg_to_arg)
            size = size_override if size_override is not None else op.get("size_bytes")
            if is_signed_override and size == 4:
                ctype = "i32"
            else:
                size_map = {1: "u8", 2: "u16", 4: "u32", 8: "u64"}
                ctype = size_map.get(size, "u64")
            
            expr = f"*({ctype} *)({addr_expr})"
            if is_signed_override and size == 4:
                return f"(i64){expr}"
            return expr

        parsed_raw = parse_raw_mem_operand(raw)
        if parsed_raw:
            base, offset = parsed_raw
            return memory_expr(base, offset, size_override, reg_to_arg, is_signed_override)

        if "[" in raw or "]" in raw:
            raise ValueError(f"Could not safely parse raw bracket memory operand: {raw}")

        return raw
    return ""

def format_comment_operand(op: dict[str, Any], reg_to_arg: dict[str, str] | None) -> str:
    kind = op.get("kind", "")
    if kind == "register":
        val = str(op.get("value", "")).lower()
        if val in {"wzr", "xzr"}:
            return val
        return c_temp_for_register(val, reg_to_arg)
    elif kind == "immediate":
        val = op.get("value")
        if isinstance(val, int):
            if val >= 0:
                return f"#0x{val:x}"
            else:
                return f"#-0x{-val:x}"
        return f"#{val}"
    else:
        return operand_to_expr(op, reg_to_arg)
