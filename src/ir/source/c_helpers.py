# -*- coding: utf-8 -*-
"""
C Helper Functions and Type Definitions for Emitter
"""

from __future__ import annotations

RESERVED_HELPERS = {
    "HEPHAESTUS_UNKNOWN_COND",
    "HEPHAESTUS_CSET",
}

def needs_unknown_cond_helper(lines: list[str]) -> bool:
    """Check if HEPHAESTUS_UNKNOWN_COND is used in function body lines."""
    return any("HEPHAESTUS_UNKNOWN_COND(" in line for line in lines)

def needs_cset_helper(lines: list[str]) -> bool:
    """Check if HEPHAESTUS_CSET is used in function body lines."""
    return any("HEPHAESTUS_CSET(" in line for line in lines)

def emit_typedefs() -> list[str]:
    """Emit the list of custom C type definitions."""
    return [
        "typedef uint8_t u8;",
        "typedef uint16_t u16;",
        "typedef uint32_t u32;",
        "typedef uint64_t u64;",
        "typedef int8_t i8;",
        "typedef int16_t i16;",
        "typedef int32_t i32;",
        "typedef int64_t i64;",
    ]

def emit_unknown_cond_helper() -> list[str]:
    """Emit code implementation of HEPHAESTUS_UNKNOWN_COND syntax adapter."""
    return [
        "/*",
        " * HEPHAESTUS_UNKNOWN_COND is a syntax adapter for unrecovered branch",
        " * predicates. Its argument preserves low-level evidence. The return value is",
        " * not a recovered program condition and must not be used for behavioral claims.",
        " */",
        "static int HEPHAESTUS_UNKNOWN_COND(const char *evidence)",
        "{",
        "    (void)evidence;",
        "    return 0;",
        "}",
    ]

def emit_cset_helper() -> list[str]:
    """Emit code implementation of HEPHAESTUS_CSET syntax adapter."""
    return [
        "/*",
        " * HEPHAESTUS_CSET is a syntax adapter for ARM64 cset instructions.",
        " * Its argument preserves the ARM64 condition code. The return value is not a",
        " * recovered high-level condition.",
        " */",
        "static u64 HEPHAESTUS_CSET(const char *condition)",
        "{",
        "    (void)condition;",
        "    return 0;",
        "}",
    ]
