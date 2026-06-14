# -*- coding: utf-8 -*-
"""
Instruction Schema Validation

Validates instruction dicts against the canonical Phase 4B instruction schema
and detects fabricated/placeholder instructions that must never enter the IR.

Canonical instruction shape
---------------------------
{
    "address":    "0x...",     # required, normalized hex string
    "mnemonic":   "add",       # required (or derived from opcode/raw)
    "opcode":     "add",       # required (or derived from mnemonic/raw)
    "operands":   [...],       # required list, may be empty
    "size_bytes": 4,           # optional int or None
    "raw":        "add w8, w8, #0x1",  # optional original disassembly text
    "source":     "radare2"    # required string
}

Placeholder Detection
---------------------
Fabricated placeholder strings are detected case-insensitively across:
- Top-level:  "raw", "opcode", "mnemonic"
- Per operand: "value", "name", "raw", "base"
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Known fabricated placeholder strings (case-insensitive, strip-normalized)
# ---------------------------------------------------------------------------

KNOWN_FABRICATED_STRINGS: frozenset = frozenset({
    "mov eax",
    "cmp eax",
    "je exit_block",
    "0xdeadbeef",
    "loadlibrarya",
    "getprocaddress",
    "kernel32.dll",
    "0x0045e0c0",
    "0x00401000",
})

# Known valid extractor sources
_KNOWN_SOURCES = frozenset({"ghidra", "radare2", "r2", "dynamic_trace", "test"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_addr(addr: str) -> str:
    """Attempt to normalize an address string to 0x-prefixed hex."""
    s = str(addr).strip().lower()
    if s.startswith("0x"):
        try:
            return hex(int(s, 16))
        except ValueError:
            return s
    # Try plain integer
    try:
        return hex(int(s, 10))
    except ValueError:
        return s


def _contains_fabricated(text: str) -> bool:
    """Return True if `text` (case-insensitive, stripped) matches any known placeholder."""
    if not text:
        return False
    normalized = text.strip().lower()
    for placeholder in KNOWN_FABRICATED_STRINGS:
        if placeholder in normalized:
            return True
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_fabricated_placeholder(instr: Dict[str, Any]) -> bool:
    """
    Return True if the instruction dict contains any known fabricated placeholder.

    Scans (case-insensitive, strip-normalized):
    - Top-level fields: "raw", "opcode", "mnemonic"
    - Per-operand fields: "value", "name", "raw", "base"

    Parameters
    ----------
    instr : Instruction dict to inspect.

    Returns
    -------
    bool
        True if a known fabricated placeholder is found anywhere.
    """
    if not isinstance(instr, dict):
        return False

    # Top-level string fields
    for field in ("raw", "opcode", "mnemonic"):
        val = instr.get(field)
        if val and isinstance(val, str) and _contains_fabricated(val):
            logger.debug(
                "Fabricated placeholder found in instruction field '%s': %r", field, val
            )
            return True

    # Operand-level string fields
    operands = instr.get("operands")
    if isinstance(operands, list):
        for op in operands:
            if not isinstance(op, dict):
                continue
            for field in ("value", "name", "raw", "base"):
                val = op.get(field)
                if val and isinstance(val, str) and _contains_fabricated(val):
                    logger.debug(
                        "Fabricated placeholder found in operand field '%s': %r", field, val
                    )
                    return True
            # Also check numeric values that look like known addresses
            val = op.get("value")
            if isinstance(val, int):
                as_hex = hex(val).lower()
                if _contains_fabricated(as_hex):
                    return True

    return False


def validate_instruction(instr: Dict[str, Any]) -> bool:
    """
    Validate an instruction dict against the canonical schema.

    Normalization rules (Amendment 3):
    - If only ``opcode`` is present, ``mnemonic`` is inferred from it (and vice versa).
    - If both are absent but ``raw`` is present, the first whitespace token of
      ``raw`` is used for both ``opcode`` and ``mnemonic`` (mutating the dict
      in-place for downstream convenience).
    - If all three are absent or empty, the instruction is invalid.

    Parameters
    ----------
    instr : Instruction dict to validate.

    Returns
    -------
    bool
        True if the instruction is structurally valid; False otherwise.
        Invalid instructions should be skipped with a warning.
    """
    if not isinstance(instr, dict):
        logger.warning("Instruction is not a dict: %r", instr)
        return False

    # --- Address ---
    addr = instr.get("address", "")
    if not addr or not isinstance(addr, str):
        logger.warning("Instruction missing or non-string 'address': %r", instr)
        return False
    # Normalize address in-place
    instr["address"] = _normalize_addr(addr)

    # --- Opcode / mnemonic normalization ---
    opcode = instr.get("opcode", "")
    mnemonic = instr.get("mnemonic", "")
    raw = instr.get("raw", "")

    if not opcode and not mnemonic:
        # Try to recover from raw
        if raw and isinstance(raw, str) and raw.strip():
            first_token = raw.strip().split()[0].lower()
            if first_token:
                instr["opcode"] = first_token
                instr["mnemonic"] = first_token
                opcode = first_token
                mnemonic = first_token
            else:
                logger.warning(
                    "Instruction has no opcode/mnemonic and raw is empty: %r", instr
                )
                return False
        else:
            logger.warning(
                "Instruction has no opcode/mnemonic/raw: %r", instr
            )
            return False
    elif not opcode and mnemonic:
        instr["opcode"] = mnemonic.lower()
    elif opcode and not mnemonic:
        instr["mnemonic"] = opcode.lower()

    # --- Operands ---
    operands = instr.get("operands")
    if operands is None:
        instr["operands"] = []
    elif not isinstance(operands, list):
        logger.warning("Instruction 'operands' is not a list: %r", instr)
        return False

    # --- Source ---
    source = instr.get("source", "")
    if not source or not isinstance(source, str):
        logger.warning("Instruction missing 'source' field: %r", instr)
        return False

    # --- size_bytes (optional) ---
    size = instr.get("size_bytes")
    if size is not None:
        if not isinstance(size, int) or size <= 0:
            # Tolerate invalid size_bytes by stripping it rather than failing
            instr["size_bytes"] = None

    return True
