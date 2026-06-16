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

def normalize_register(reg: str | None) -> str | None:
    """Normalize ARM64 register to canonical form (lowercase, wX -> xX)."""
    if not reg:
        return None
    r = str(reg).lower().strip()
    if r == "fp":
        return "x29"
    if r == "lr":
        return "x30"
    if r.startswith("w") and r[1:].isdigit():
        return "x" + r[1:]
    return r


def c_temp_for_register(reg: str, reg_to_arg: dict[str, str] | None = None) -> str:
    """Format register as C temporary or map to ABI argument if verified."""
    r = str(reg).lower().strip()
    if r in {"xzr", "wzr"}:
        return "0"

    if reg_to_arg:
        norm = normalize_register(r)
        if norm in reg_to_arg:
            return reg_to_arg[norm]

    # Map x29/fp -> fp, x30/lr -> lr
    if r in {"x29", "fp"}:
        r = "fp"
    elif r in {"x30", "lr"}:
        r = "lr"

    # Sanitize register to valid C identifier characters
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", r)
    return f"tmp_{safe}"


def signed_offset_name(offset: int) -> str:
    """Format signed offset for stack variable names (e.g. stack_m20)."""
    if offset < 0:
        return f"m{-offset}"
    return f"{offset}"


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

    # Size-to-ctype mapping
    if is_signed and size == 4:
        ctype = "i32"
    else:
        size_map = {1: "u8", 2: "u16", 4: "u32", 8: "u64"}
        ctype = size_map.get(size, "u64")

    if norm_base in {"sp", "x29"}:
        # Stack accesses use stack_N notation
        stack_var = f"stack_{signed_offset_name(offset)}"
        if is_signed and size == 4:
            return f"(i64)(i32){stack_var}"
        return stack_var
    else:
        base_expr = c_temp_for_register(base_lower, reg_to_arg)
        if offset == 0:
            expr = f"*({ctype} *)({base_expr})"
        elif offset < 0:
            expr = f"*({ctype} *)({base_expr} - {-offset})"
        else:
            expr = f"*({ctype} *)({base_expr} + {offset})"

        if is_signed and size == 4:
            return f"(i64){expr}"
        return expr


def parse_shifted_extended_reg(op: dict[str, Any]) -> tuple[str, str | None, int] | None:
    """
    Parse a shifted or extended register operand.
    E.g. w9, SXTW #2 or x9, LSL #3 or w9, SXTW
    """
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


def parse_indexed_memory_enhanced(raw_str: str) -> tuple[str, str, str | None, int, list[str]] | None:
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


def format_indexed_address(
    base: str,
    index: str,
    ext: str | None,
    shift: int,
    reg_to_arg: dict[str, str] | None = None,
) -> str:
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


def parse_ldp_raw(raw: str) -> tuple[str, str, str, int, bool] | None:
    """
    Parses a raw ldp instruction string.
    Returns (reg1, reg2, base, offset, is_post_index) or None.
    """
    import re
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


# ---------------------------------------------------------------------------
# C sanitization helper (copied from reconstructor to avoid circular imports)
# ---------------------------------------------------------------------------

_C_IDENT_RE = re.compile(r"[^a-zA-Z0-9_]")

def sanitize_c_identifier(name: str) -> str:
    if not name or not name.strip():
        return "fn_unknown"
    sanitized = _C_IDENT_RE.sub("_", name.strip())
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")
    sanitized = sanitized.strip("_")
    if not sanitized:
        return "fn_unknown"
    if sanitized[0].isdigit():
        sanitized = f"fn_{sanitized}"
    return sanitized


# ---------------------------------------------------------------------------
# Operand filtering helper
# ---------------------------------------------------------------------------

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
            # Check if it represents a brackets memory operand or shifted/extended register
            if (raw.startswith("[") and "]" in raw) or parse_shifted_extended_reg(op) is not None or raw.lower() in cond_codes:
                clean.append(op)
    return clean


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

            elif mnemonic == "ldrsb" and len(ops) >= 2:
                dst, mem = ops[0], ops[1]
                dst_expr = operand_to_expr(dst, reg_to_arg, warnings=warnings)
                dst_val = str(dst.get("value") or "").lower()
                outer_cast = "(i64)" if dst_val.startswith("x") else "(i32)"
                
                mem_expr = operand_to_expr(mem, reg_to_arg, size_override=1, warnings=warnings)
                mem_expr_signed = mem_expr.replace("*(u8 *)", "*(i8 *)")
                
                lowered_text_list.append(f"{dst_expr} = {outer_cast}{mem_expr_signed};")
                stmt_kind = "load"
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

            elif mnemonic == "cset":
                dst_reg, cond_code = parse_cset_operands(ins)
                if dst_reg and cond_code:
                    dst_expr = c_temp_for_register(dst_reg, reg_to_arg)
                    escaped_cond = cond_code.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
                    
                    lowered_text_list.append(f"{dst_expr} = HEPHAESTUS_CSET(\"{escaped_cond}\"); /* cset {dst_reg},{cond_code}; flags not modeled */")
                    stmt_kind = "binary_op"
                    is_lowered = True
                    custom_comment = True

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

            elif mnemonic in {"cmp", "cmn", "tst"} and len(ops) >= 2:
                op1, op2 = ops[0], ops[1]
                op1_expr = operand_to_expr(op1, reg_to_arg, warnings=warnings)
                op2_expr = operand_to_expr(op2, reg_to_arg, warnings=warnings)
                lowered_text_list.append(f"/* compare: {op1_expr} vs {op2_expr} */")
                stmt_kind = "compare"
                is_lowered = True

            elif mnemonic == "bl" and len(ops) >= 1:
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

            elif mnemonic in {"b.eq", "b.ne", "b.ge", "b.gt", "b.le", "b.lt", "b.hi", "b.hs", "b.lo", "b.ls", "b.mi", "b.pl", "b.vs", "b.vc", "b.cs", "b.cc"} and len(ops) >= 1:
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

            elif mnemonic in {"stp", "ldp"}:
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
            # Fallback to unsupported instruction comment
            if ("[" in raw or "]" in raw) and (mnemonic in {"str", "stur", "strb", "strh"}):
                fallback_text = f"/* unsupported indexed memory store: {raw} */"
            elif ("[" in raw or "]" in raw) and (mnemonic in {"ldr", "ldur", "ldrb", "ldrh", "ldurb", "ldurh", "ldrsw", "ldursw"}):
                fallback_text = f"/* unsupported indexed memory load: {raw} */"
            elif mnemonic == "ldp":
                fallback_text = f"/* unsupported paired load: {raw} */"
            elif mnemonic == "cset":
                fallback_text = f"/* unsupported cset: {raw} */"
            else:
                fallback_text = f"/* {addr}: unsupported instruction: {raw} */"

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
