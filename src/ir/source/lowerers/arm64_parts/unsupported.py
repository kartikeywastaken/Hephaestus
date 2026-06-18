# -*- coding: utf-8 -*-
"""
ARM64 Lowerer Unsupported Instruction Helpers
"""

from __future__ import annotations

def unsupported_fallback_text(mnemonic: str, raw: str, addr: str) -> str:
    """
    Generate the fallback C comment text for an unsupported ARM64 instruction.
    """
    if ("[" in raw or "]" in raw) and (mnemonic in {"str", "stur", "strb", "strh"}):
        return f"/* unsupported indexed memory store: {raw} */"
    elif ("[" in raw or "]" in raw) and (mnemonic in {"ldr", "ldur", "ldrb", "ldrh", "ldurb", "ldurh", "ldrsw", "ldursw"}):
        return f"/* unsupported indexed memory load: {raw} */"
    elif mnemonic == "ldp":
        return f"/* unsupported paired load: {raw} */"
    elif mnemonic == "cset":
        return f"/* unsupported cset: {raw} */"
    else:
        return f"/* {addr}: unsupported instruction: {raw} */"
