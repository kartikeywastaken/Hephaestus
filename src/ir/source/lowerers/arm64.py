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


def parse_indexed_memory(raw_str: str) -> tuple[str, str, int] | None:
    """
    Parse a raw string representing an indexed memory operand.
    Format: [base, index, LSL #shift] or [base, index]
    E.g. [x9, x10, LSL #0x2] -> ("x9", "x10", 2)
         [x9, x10]           -> ("x9", "x10", 0)
    """
    cleaned = raw_str.strip()
    match = re.match(
        r"^\[\s*([a-zA-Z0-9_]+)\s*,\s*([a-zA-Z0-9_]+)(?:\s*,\s*(?:LSL|lsl)\s*#\s*(0x[0-9a-fA-F]+|[0-9]+))?\s*\]!?$",
        cleaned
    )
    if not match:
        return None
    base = match.group(1)
    index = match.group(2)
    shift_val_str = match.group(3)

    shift = 0
    if shift_val_str:
        try:
            if shift_val_str.lower().startswith("0x"):
                shift = int(shift_val_str, 16)
            else:
                shift = int(shift_val_str)
        except ValueError:
            return None

    return base, index, shift


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


def assert_no_raw_bracket_memory_expr(expr: str) -> None:
    stripped = expr.strip()
    if stripped.startswith("[") or " = [" in stripped or " =  [" in stripped or "=[" in stripped:
        raise ValueError("raw ARM64 bracket memory expression leaked into generated C expression")


def operand_to_expr(
    op: dict[str, Any],
    reg_to_arg: dict[str, str] | None = None,
    size_override: int | None = None,
    is_signed_override: bool = False,
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

        parsed_indexed = parse_indexed_memory(raw)
        if parsed_indexed:
            base, index, shift = parsed_indexed
            size = size_override if size_override is not None else op.get("size_bytes")
            return indexed_memory_expr(base, index, shift, size, reg_to_arg, is_signed_override)

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
    for op in ops:
        if not isinstance(op, dict):
            continue
        kind = op.get("kind", "")
        if kind in {"register", "immediate", "memory", "symbol"}:
            clean.append(op)
        elif kind == "unknown":
            raw = str(op.get("raw") or "").strip()
            # Check if it represents a brackets memory operand
            if raw.startswith("[") and "]" in raw:
                clean.append(op)
    return clean


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

        try:
            # Check for supported instruction patterns
            if mnemonic in {"mov", "movz"} and len(ops) >= 2:
                dst, src = ops[0], ops[1]
                dst_expr = operand_to_expr(dst, reg_to_arg)
                src_expr = operand_to_expr(src, reg_to_arg)
                lowered_text_list.append(f"{dst_expr} = {src_expr};")
                stmt_kind = "assign"
                is_lowered = True

            elif mnemonic == "adrp" and len(ops) >= 2:
                dst, imm = ops[0], ops[1]
                dst_expr = operand_to_expr(dst, reg_to_arg)
                val = imm.get("value")
                imm_expr = hex(val) if isinstance(val, int) else operand_to_expr(imm, reg_to_arg)
                lowered_text_list.append(f"{dst_expr} = {imm_expr};")
                stmt_kind = "assign"
                is_lowered = True

            elif mnemonic in {"add", "sub"}:
                if len(ops) >= 3:
                    dst, src1, src2 = ops[0], ops[1], ops[2]
                    dst_expr = operand_to_expr(dst, reg_to_arg)
                    src1_expr = operand_to_expr(src1, reg_to_arg)
                    src2_expr = operand_to_expr(src2, reg_to_arg)
                    op_sym = "+" if mnemonic == "add" else "-"
                    lowered_text_list.append(f"{dst_expr} = {src1_expr} {op_sym} {src2_expr};")
                    is_lowered = True
                elif len(ops) == 2:
                    dst, src = ops[0], ops[1]
                    dst_expr = operand_to_expr(dst, reg_to_arg)
                    src_expr = operand_to_expr(src, reg_to_arg)
                    op_sym = "+" if mnemonic == "add" else "-"
                    lowered_text_list.append(f"{dst_expr} = {dst_expr} {op_sym} {src_expr};")
                    is_lowered = True
                
                if is_lowered:
                    dst_norm = normalize_register(ops[0].get("value"))
                    if dst_norm == "sp":
                        stmt_kind = "stack_adjust"
                    else:
                        stmt_kind = "binary_op"

            elif mnemonic == "mul":
                if len(ops) >= 3:
                    dst, src1, src2 = ops[0], ops[1], ops[2]
                    dst_expr = operand_to_expr(dst, reg_to_arg)
                    src1_expr = operand_to_expr(src1, reg_to_arg)
                    src2_expr = operand_to_expr(src2, reg_to_arg)
                    lowered_text_list.append(f"{dst_expr} = {src1_expr} * {src2_expr};")
                    is_lowered = True
                elif len(ops) == 2:
                    dst, src = ops[0], ops[1]
                    dst_expr = operand_to_expr(dst, reg_to_arg)
                    src_expr = operand_to_expr(src, reg_to_arg)
                    lowered_text_list.append(f"{dst_expr} = {dst_expr} * {src_expr};")
                    is_lowered = True
                stmt_kind = "binary_op"

            elif mnemonic in {"and", "orr", "eor"}:
                op_sym = "&" if mnemonic == "and" else ("|" if mnemonic == "orr" else "^")
                if len(ops) >= 3:
                    dst, src1, src2 = ops[0], ops[1], ops[2]
                    dst_expr = operand_to_expr(dst, reg_to_arg)
                    src1_expr = operand_to_expr(src1, reg_to_arg)
                    src2_expr = operand_to_expr(src2, reg_to_arg)
                    
                    # Special case: orr with wzr/xzr
                    if mnemonic == "orr" and src1_expr == "0":
                        lowered_text_list.append(f"{dst_expr} = {src2_expr};")
                    elif mnemonic == "orr" and src2_expr == "0":
                        lowered_text_list.append(f"{dst_expr} = {src1_expr};")
                    else:
                        lowered_text_list.append(f"{dst_expr} = {src1_expr} {op_sym} {src2_expr};")
                    is_lowered = True
                elif len(ops) == 2:
                    dst, src = ops[0], ops[1]
                    dst_expr = operand_to_expr(dst, reg_to_arg)
                    src_expr = operand_to_expr(src, reg_to_arg)
                    lowered_text_list.append(f"{dst_expr} = {dst_expr} {op_sym} {src_expr};")
                    is_lowered = True
                stmt_kind = "binary_op"

            elif mnemonic in {"lsl", "lsr", "asr"}:
                op_sym = "<<" if mnemonic == "lsl" else ">>"
                extra = " /* arithmetic shift */" if mnemonic == "asr" else ""
                if len(ops) >= 3:
                    dst, src, shift = ops[0], ops[1], ops[2]
                    dst_expr = operand_to_expr(dst, reg_to_arg)
                    src_expr = operand_to_expr(src, reg_to_arg)
                    shift_expr = operand_to_expr(shift, reg_to_arg)
                    lowered_text_list.append(f"{dst_expr} = {src_expr} {op_sym} {shift_expr};{extra}")
                    is_lowered = True
                elif len(ops) == 2:
                    dst, shift = ops[0], ops[1]
                    dst_expr = operand_to_expr(dst, reg_to_arg)
                    shift_expr = operand_to_expr(shift, reg_to_arg)
                    lowered_text_list.append(f"{dst_expr} = {dst_expr} {op_sym} {shift_expr};{extra}")
                    is_lowered = True
                stmt_kind = "binary_op"

            elif mnemonic in {"ldr", "ldur", "ldrb", "ldrh", "ldrsw", "ldursw"} and len(ops) >= 2:
                dst, mem = ops[0], ops[1]
                dst_expr = operand_to_expr(dst, reg_to_arg)
                
                # Determine access size
                if mnemonic == "ldrb":
                    size = 1
                elif mnemonic == "ldrh":
                    size = 2
                elif mnemonic in {"ldrsw", "ldursw"}:
                    size = 4
                else:
                    size = mem.get("size_bytes")
                    if size is None:
                        dst_val = str(dst.get("value") or "").lower()
                        size = 4 if dst_val.startswith("w") else 8
                
                mem_expr = operand_to_expr(mem, reg_to_arg, size_override=size, is_signed_override=(mnemonic in {"ldrsw", "ldursw"}))
                lowered_text_list.append(f"{dst_expr} = {mem_expr};")
                stmt_kind = "load"
                is_lowered = True

            elif mnemonic in {"str", "stur", "strb", "strh"} and len(ops) >= 2:
                src, mem = ops[0], ops[1]
                src_expr = operand_to_expr(src, reg_to_arg)
                
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
                
                mem_expr = operand_to_expr(mem, reg_to_arg, size_override=size)
                lowered_text_list.append(f"{mem_expr} = {src_expr};")
                stmt_kind = "store"
                is_lowered = True

            elif mnemonic in {"cmp", "cmn", "tst"} and len(ops) >= 2:
                op1, op2 = ops[0], ops[1]
                op1_expr = operand_to_expr(op1, reg_to_arg)
                op2_expr = operand_to_expr(op2, reg_to_arg)
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
                reg_expr = operand_to_expr(reg, reg_to_arg)
                lowered_text_list.append(f"/* indirect call via {reg_expr} */")
                stmt_kind = "comment"
                is_lowered = True

            elif mnemonic in {"b", "br"} and len(ops) >= 1:
                target = ops[0]
                target_expr = operand_to_expr(target, reg_to_arg)
                lowered_text_list.append(f"/* branch to {target_expr} */")
                stmt_kind = "branch_comment"
                is_lowered = True

            elif mnemonic == "ret":
                lowered_text_list.append("/* return via x0 */")
                stmt_kind = "return_comment"
                is_lowered = True

            elif mnemonic in {"stp", "ldp"} and len(ops) >= 3:
                reg1, reg2, mem = ops[0], ops[1], ops[2]
                reg1_expr = operand_to_expr(reg1, reg_to_arg)
                reg2_expr = operand_to_expr(reg2, reg_to_arg)

                # Resolve base and offset
                base, offset = "", 0
                resolved = False
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

                if resolved:
                    reg1_val = str(reg1.get("value") or "").lower()
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
                        
                        lowered_text_list.append(stmt1_text)
                        lowered_text_list.append(f"{stmt2_text} /* paired load second register inferred offset +{size} */")
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
                # The first statement gets the original instruction raw comment
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
            elif ("[" in raw or "]" in raw) and (mnemonic in {"ldr", "ldur", "ldrb", "ldrh", "ldrsw", "ldursw"}):
                fallback_text = f"/* unsupported indexed memory load: {raw} */"
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
