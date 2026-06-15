# -*- coding: utf-8 -*-
"""
Phase 5.4: Conservative Return Recovery

Scans lowered blocks for return sites and recovers conservative return
expressions from ABI return registers (w0/x0 on ARM64).

Core Rule: Missing evidence is acceptable. Fabricated evidence is not.

This module does NOT:
- Fold expressions (tmp_w0 = tmp_w8 + 1 → return tmp_w0, NOT return tmp_w8 + 1)
- Use interprocedural propagation
- Use SSA or loop-carried value inference
- Invent source variable names
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


# ARM64 ABI return registers
_ARM64_RETURN_REGS = {"w0", "x0"}

# Statement kinds that form clobber boundaries for backward scans
_CLOBBER_KINDS = {"call", "branch_comment", "return_comment"}

# Regex to detect literal constant assignment: tmp_w0 = <integer>;
_CONST_ASSIGN_RE = re.compile(
    r"^tmp_[wx]0\s*=\s*(-?\d+|0x[0-9a-fA-F]+)\s*;",
)

# Regex to detect any assignment to tmp_w0 or tmp_x0
_RETURN_REG_ASSIGN_RE = re.compile(
    r"^tmp_([wx]0)\s*=\s*(.+?)\s*;",
)


def _is_clobber_boundary(stmt: Any) -> bool:
    """Check if a statement is a clobber boundary that invalidates backward scan."""
    if isinstance(stmt, dict):
        kind = stmt.get("kind", "")
        text = stmt.get("text", "")
    else:
        kind = getattr(stmt, "kind", "")
        text = getattr(stmt, "text", "")

    if kind in _CLOBBER_KINDS:
        return True

    # Unsupported instructions that may affect control flow
    if kind == "comment" and "unsupported instruction" in text:
        # Check for branch-like unsupported instructions
        lower_text = text.lower()
        if any(kw in lower_text for kw in ("b.", "b ", "bl ", "blr", "br ", "ret", "cbz", "cbnz", "tbz", "tbnz")):
            return True

    return False


def _get_stmt_field(stmt: Any, field: str, default: Any = "") -> Any:
    """Get a field from a statement (dict or object)."""
    if isinstance(stmt, dict):
        return stmt.get(field, default)
    return getattr(stmt, field, default)


def _extract_constant_value(text: str) -> Optional[str]:
    """Extract a literal constant from an assignment like 'tmp_w0 = 7;'."""
    m = _CONST_ASSIGN_RE.match(text.strip())
    if m:
        val_str = m.group(1)
        # Normalize hex to int for cleaner output
        try:
            val = int(val_str, 0)
            return str(val)
        except ValueError:
            return val_str
    return None


def analyze_return_sites(
    lowered_blocks: dict,
    return_type: str,
    architecture: str,
) -> dict:
    """
    Analyze return sites in lowered blocks and recover conservative return expressions.

    Parameters
    ----------
    lowered_blocks : Mapping of block_id -> list of lowered statements.
    return_type    : The function's return type string (e.g. "u64", "i32", "void").
    architecture   : Architecture string (e.g. "arm64", "x86_64", "unsupported").

    Returns
    -------
    dict with per-site evidence and aggregate metrics.
    """
    is_void = return_type in ("void",)
    is_arm64 = architecture.lower() in ("arm64", "aarch64")

    sites: List[Dict[str, Any]] = []
    warnings: List[str] = []
    registers_observed: List[str] = []

    for block_id, stmts in lowered_blocks.items():
        if not isinstance(stmts, list):
            continue

        for stmt_idx, stmt in enumerate(stmts):
            kind = _get_stmt_field(stmt, "kind", "")
            text = _get_stmt_field(stmt, "text", "")
            address = _get_stmt_field(stmt, "address", None)

            # Also check source_instruction for mnemonic
            src_instr = _get_stmt_field(stmt, "source_instruction", None)
            mnemonic = ""
            if isinstance(src_instr, dict):
                mnemonic = src_instr.get("mnemonic", "")

            is_ret = (kind == "return_comment") or (mnemonic == "ret")
            if not is_ret:
                continue

            # Found a return site
            site: Dict[str, Any] = {
                "block_id": block_id,
                "address": address,
                "register": None,
                "expression_kind": "unknown",
                "expression": None,
                "replacement_text": None,
                "evidence_statement_address": None,
                "warnings": [],
            }

            if is_void:
                site["expression_kind"] = "void"
                site["replacement_text"] = "return; /* void return */"
                sites.append(site)
                continue

            if not is_arm64:
                site["expression_kind"] = "unknown"
                site["warnings"].append("unsupported_architecture_for_return_recovery")
                sites.append(site)
                continue

            # Same-block backward scan for w0/x0 assignment
            found_reg = None
            found_expr = None
            found_const = None
            found_address = None
            clobbered = False

            for scan_idx in range(stmt_idx - 1, -1, -1):
                scan_stmt = stmts[scan_idx]
                scan_text = _get_stmt_field(scan_stmt, "text", "").strip()
                scan_kind = _get_stmt_field(scan_stmt, "kind", "")
                scan_addr = _get_stmt_field(scan_stmt, "address", None)

                # Check clobber boundary
                if _is_clobber_boundary(scan_stmt):
                    clobbered = True
                    break

                # Check for return register assignment
                m = _RETURN_REG_ASSIGN_RE.match(scan_text)
                if m:
                    reg_name = m.group(1)  # "w0" or "x0"
                    found_reg = reg_name
                    found_address = scan_addr

                    # Check if it's a constant
                    const_val = _extract_constant_value(scan_text)
                    if const_val is not None:
                        found_const = const_val
                    else:
                        found_expr = f"tmp_{reg_name}"
                    break

            if clobbered or found_reg is None:
                site["expression_kind"] = "unknown"
                if clobbered:
                    site["warnings"].append("return_register_clobbered_by_intervening_call_or_branch")
            elif found_const is not None:
                site["register"] = found_reg
                site["expression_kind"] = "constant"
                site["expression"] = found_const
                site["replacement_text"] = f"return {found_const}; /* return constant from {found_reg} before ret */"
                site["evidence_statement_address"] = found_address
                if found_reg not in registers_observed:
                    registers_observed.append(found_reg)
            elif found_expr is not None:
                site["register"] = found_reg
                site["expression_kind"] = "register"
                site["expression"] = found_expr
                site["replacement_text"] = f"return {found_expr}; /* return value from {found_reg} before ret */"
                site["evidence_statement_address"] = found_address
                if found_reg not in registers_observed:
                    registers_observed.append(found_reg)

            sites.append(site)

    # Aggregate
    sites_with_value = sum(1 for s in sites if s["expression_kind"] in ("register", "constant", "void"))
    sites_unknown = sum(1 for s in sites if s["expression_kind"] == "unknown")

    # Function-level return expression (only if all non-void sites agree)
    non_void_sites = [s for s in sites if s["expression_kind"] not in ("void",)]
    func_expression = None
    func_expression_kind = "unknown"

    if non_void_sites:
        exprs = set()
        kinds = set()
        for s in non_void_sites:
            if s["expression"] is not None:
                exprs.add(s["expression"])
                kinds.add(s["expression_kind"])

        if len(exprs) == 1 and len(kinds) == 1:
            func_expression = exprs.pop()
            func_expression_kind = kinds.pop()
        elif len(exprs) == 0:
            func_expression_kind = "unknown"
    elif sites and all(s["expression_kind"] == "void" for s in sites):
        func_expression_kind = "void"

    return {
        "return_sites_total": len(sites),
        "return_sites_with_value": sites_with_value,
        "return_sites_unknown": sites_unknown,
        "return_registers_observed": registers_observed,
        "return_expression_kind": func_expression_kind,
        "return_expression": func_expression,
        "sites": sites,
        "warnings": warnings,
    }
