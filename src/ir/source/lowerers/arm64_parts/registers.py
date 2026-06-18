# -*- coding: utf-8 -*-
"""
ARM64 Lowerer Registers Helpers
"""

from __future__ import annotations
import re

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

def is_zero_register(reg: str) -> bool:
    """Check if register is zero register (xzr/wzr)."""
    return reg.lower().strip() in {"xzr", "wzr"}

def is_32bit_register(reg: str) -> bool:
    """Check if register is a 32-bit register."""
    r = reg.lower().strip()
    return r.startswith("w") and r[1:].isdigit()

def is_64bit_register(reg: str) -> bool:
    """Check if register is a 64-bit register."""
    r = reg.lower().strip()
    return (r.startswith("x") and r[1:].isdigit()) or r in {"x29", "x30", "sp", "fp", "lr"}

def register_width(reg: str) -> int:
    """Return register bit width."""
    if is_32bit_register(reg):
        return 32
    return 64

def canonical_register_alias(reg: str) -> str:
    """Return canonical register alias mapping."""
    r = reg.lower().strip()
    if r == "fp":
        return "x29"
    if r == "lr":
        return "x30"
    return r
