# -*- coding: utf-8 -*-
"""
C Identifier Sanitization and Naming Helpers
"""

from __future__ import annotations
import re

_C_IDENT_RE = re.compile(r"[^a-zA-Z0-9_]")

def sanitize_c_identifier(name: str) -> str:
    """
    Convert an arbitrary string into a valid C identifier.

    Rules:
    - Replace non-alphanumeric/underscore chars with '_'
    - Prefix with 'fn_' if starts with a digit
    - Ensure non-empty (fallback: 'fn_unknown')
    - Collapse consecutive underscores
    - Strip trailing underscores
    """
    if not name or not name.strip():
        return "fn_unknown"

    sanitized = _C_IDENT_RE.sub("_", name.strip())

    # Collapse consecutive underscores
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")

    # Strip leading/trailing underscores
    sanitized = sanitized.strip("_")

    if not sanitized:
        return "fn_unknown"

    # Prefix with 'fn_' if starts with digit
    if sanitized[0].isdigit():
        sanitized = f"fn_{sanitized}"

    return sanitized

def function_c_name(name: str, entry_point: str | None = None) -> str:
    """
    Compute and return the sanitized C name for a function.
    """
    if name == "main" or entry_point == "main":
        return "main"
    return sanitize_c_identifier(name)
