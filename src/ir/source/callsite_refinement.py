# -*- coding: utf-8 -*-
"""
Phase 5.4: Conservative Call-Site Refinement

Scans lowered blocks for call sites and refines argument lists using
same-block ABI register evidence.

Core Rule: Missing evidence is acceptable. Fabricated evidence is not.

This module does NOT:
- Invent source variable names
- Invent function pointer names
- Inflate argument lists with unknown placeholders
- Use interprocedural propagation
- Modify the ARM64 lowerer
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


# ARM64 ABI argument registers in order
_ARM64_ARG_REGS = [f"x{i}" for i in range(8)] + [f"w{i}" for i in range(8)]

# Statement kinds that form clobber boundaries for backward scans
_CLOBBER_KINDS = {"call", "branch_comment", "return_comment"}

# Regex to detect register assignment: tmp_xN = ...; or tmp_wN = ...;
_REG_ASSIGN_RE = re.compile(
    r"^tmp_([xw]\d+)\s*=\s*(.+?)\s*;",
)

# Regex to detect a call statement: call_TARGET(ARGS); /* ... */
_CALL_STMT_RE = re.compile(
    r"^(call_[a-zA-Z0-9_]+)\(([^)]*)\)\s*;(.*)$",
)

# Regex to detect indirect call comment: /* indirect call via ... */ /* blr ... */
_INDIRECT_CALL_RE = re.compile(
    r"/\*\s*indirect call via\s+(\S+)\s*\*/",
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
        lower_text = text.lower()
        if any(kw in lower_text for kw in ("b.", "b ", "bl ", "blr", "br ", "ret", "cbz", "cbnz", "tbz", "tbnz")):
            return True

    return False


def _get_stmt_field(stmt: Any, field: str, default: Any = "") -> Any:
    """Get a field from a statement (dict or object)."""
    if isinstance(stmt, dict):
        return stmt.get(field, default)
    return getattr(stmt, field, default)


def _scan_block_for_arg_evidence(
    stmts: list,
    call_stmt_idx: int,
) -> Dict[str, str]:
    """
    Scan backward from call_stmt_idx to find ABI argument register
    assignments. Stops at clobber boundaries. Returns a dict mapping
    register name (e.g. "x0", "w1") to the tmp expression (e.g. "tmp_x0").
    """
    evidence: Dict[str, str] = {}

    for scan_idx in range(call_stmt_idx - 1, -1, -1):
        scan_stmt = stmts[scan_idx]
        scan_text = _get_stmt_field(scan_stmt, "text", "").strip()

        # Check clobber boundary
        if _is_clobber_boundary(scan_stmt):
            break

        # Check for register assignment
        m = _REG_ASSIGN_RE.match(scan_text)
        if m:
            reg_name = m.group(1)  # e.g. "x0", "w1"
            # Only ABI argument registers
            if reg_name in _ARM64_ARG_REGS:
                # First found assignment wins (closest to call)
                if reg_name not in evidence:
                    evidence[reg_name] = f"tmp_{reg_name}"
                    # Also mark the wider/narrower variant as seen
                    # e.g. if we found w0, mark x0 as covered too (and vice versa)
                    if reg_name.startswith("w"):
                        alt = "x" + reg_name[1:]
                    else:
                        alt = "w" + reg_name[1:]
                    if alt not in evidence:
                        evidence[alt] = f"tmp_{reg_name}"

    return evidence


def _build_refined_call(
    call_target: str,
    original_comment: str,
    arg_evidence: Dict[str, str],
    original_arg_count: int,
) -> Optional[str]:
    """
    Build a refined call statement text using argument evidence.
    Returns None if no refinement is possible.
    """
    if not arg_evidence:
        return None

    # Determine the highest evidenced argument slot
    max_slot = -1
    slot_exprs: Dict[int, str] = {}

    for reg_name, expr in arg_evidence.items():
        # Extract slot number: x0->0, w0->0, x1->1, w1->1, etc.
        try:
            slot = int(reg_name[1:])
        except (ValueError, IndexError):
            continue
        if slot > 7:
            continue

        if slot not in slot_exprs:
            slot_exprs[slot] = expr
            if slot > max_slot:
                max_slot = slot

    if max_slot < 0:
        return None

    # Build argument list up to max_slot
    args = []
    for i in range(max_slot + 1):
        if i in slot_exprs:
            args.append(slot_exprs[i])
        else:
            # Use the generic tmp_xN for unevidenced slots within range
            args.append(f"tmp_x{i}")

    args_str = ", ".join(args)
    comment = original_comment.strip()

    # Append refinement note to the trailing comment
    if comment:
        # Insert refinement note before closing */
        if "/*" in comment and "*/" in comment:
            refined_comment = comment.rstrip().rstrip("/").rstrip("*").rstrip()
            refined_comment += "; args refined from same-block evidence */"
        else:
            refined_comment = comment + " /* args refined from same-block evidence */"
    else:
        refined_comment = "/* args refined from same-block evidence */"

    return f"{call_target}({args_str}); {refined_comment}"


def analyze_call_sites(
    lowered_blocks: dict,
    architecture: str = "arm64",
) -> dict:
    """
    Analyze call sites in lowered blocks and produce per-site refinement metadata.

    Parameters
    ----------
    lowered_blocks : Mapping of block_id -> list of lowered statements.
    architecture   : Architecture string.

    Returns
    -------
    dict with per-site metadata and aggregate metrics.
    """
    is_arm64 = architecture.lower() in ("arm64", "aarch64")

    sites: List[Dict[str, Any]] = []
    warnings: List[str] = []

    total_args_recovered = 0
    total_args_unknown = 0

    for block_id, stmts in lowered_blocks.items():
        if not isinstance(stmts, list):
            continue

        for stmt_idx, stmt in enumerate(stmts):
            kind = _get_stmt_field(stmt, "kind", "")
            text = _get_stmt_field(stmt, "text", "").strip()
            address = _get_stmt_field(stmt, "address", None)

            # Direct call
            if kind == "call":
                m = _CALL_STMT_RE.match(text)
                if not m:
                    continue

                call_target = m.group(1)
                original_args_str = m.group(2).strip()
                trailing = m.group(3).strip()

                # Count original args
                original_args = [a.strip() for a in original_args_str.split(",") if a.strip()] if original_args_str else []

                # Extract target address/name from the trailing comment
                target_ref = None
                # Look for /* bl 0x... */ or /* bl _symbol */
                bl_match = re.search(r"/\*\s*bl\s+(\S+)\s*\*/", trailing)
                if bl_match:
                    target_ref = bl_match.group(1)

                site: Dict[str, Any] = {
                    "block_id": block_id,
                    "address": address,
                    "kind": "direct",
                    "target": target_ref or call_target,
                    "original_text": text,
                    "refined_text": None,
                    "arguments": [],
                    "warnings": [],
                }

                # Try to refine arguments on ARM64
                if is_arm64:
                    arg_evidence = _scan_block_for_arg_evidence(stmts, stmt_idx)
                    if arg_evidence:
                        refined = _build_refined_call(
                            call_target, trailing, arg_evidence, len(original_args)
                        )
                        if refined:
                            site["refined_text"] = refined

                            # Build arguments list
                            for reg_name, expr in sorted(arg_evidence.items()):
                                try:
                                    idx = int(reg_name[1:])
                                except (ValueError, IndexError):
                                    continue
                                if idx <= 7 and not any(a["index"] == idx for a in site["arguments"]):
                                    site["arguments"].append({
                                        "index": idx,
                                        "expr": expr,
                                        "source": "same_block_register_evidence",
                                    })
                                    total_args_recovered += 1
                    else:
                        total_args_unknown += len(original_args) if original_args else 1

                sites.append(site)

            # Indirect call
            elif kind == "comment" and _INDIRECT_CALL_RE.search(text):
                site = {
                    "block_id": block_id,
                    "address": address,
                    "kind": "indirect",
                    "target": None,
                    "original_text": text,
                    "refined_text": None,
                    "arguments": [],
                    "warnings": [],
                }

                # Extract target register
                im = _INDIRECT_CALL_RE.search(text)
                if im:
                    site["target"] = im.group(1)

                # Try to add argument evidence for indirect calls too
                if is_arm64:
                    arg_evidence = _scan_block_for_arg_evidence(stmts, stmt_idx)
                    if arg_evidence:
                        # Build an enhanced comment with argument info
                        arg_exprs = []
                        for reg_name, expr in sorted(arg_evidence.items()):
                            try:
                                idx = int(reg_name[1:])
                            except (ValueError, IndexError):
                                continue
                            if idx <= 7 and expr not in arg_exprs:
                                arg_exprs.append(expr)
                                if not any(a["index"] == idx for a in site["arguments"]):
                                    site["arguments"].append({
                                        "index": idx,
                                        "expr": expr,
                                        "source": "same_block_register_evidence",
                                    })
                                    total_args_recovered += 1

                        if arg_exprs:
                            target_reg = im.group(1) if im else "unknown"
                            src_instr = _get_stmt_field(stmt, "source_instruction", None)
                            raw = ""
                            if isinstance(src_instr, dict):
                                raw = src_instr.get("raw", "")
                            args_note = ", ".join(sorted(set(arg_exprs)))
                            site["refined_text"] = (
                                f"/* indirect call through {target_reg} "
                                f"with args: {args_note} */"
                            )
                            if raw:
                                site["refined_text"] += f" /* {raw} */"

                sites.append(site)

    # Aggregate
    direct_calls = sum(1 for s in sites if s["kind"] == "direct")
    indirect_calls = sum(1 for s in sites if s["kind"] == "indirect")
    calls_with_args = sum(1 for s in sites if s["arguments"])

    return {
        "call_sites_total": len(sites),
        "direct_calls": direct_calls,
        "indirect_calls": indirect_calls,
        "calls_with_arguments": calls_with_args,
        "arguments_recovered": total_args_recovered,
        "arguments_unknown": total_args_unknown,
        "sites": sites,
        "warnings": warnings,
    }
