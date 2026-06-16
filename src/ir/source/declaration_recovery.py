# -*- coding: utf-8 -*-
"""
Phase 5.6: Conservative Declaration and Compile-Shape Stabilization Engine
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict

# Regexes for pseudo-identifiers
TMP_RE = re.compile(r"\btmp_[A-Za-z0-9_]+\b")
STACK_RE = re.compile(r"\bstack_m?\d+\b")
CALL_RE = re.compile(r"\bcall_0x[0-9a-fA-F]+\b")

DECL_TYPES = {
    "u8", "u16", "u32", "u64", "i8", "i16", "i32", "i64",
    "uint8_t", "uint16_t", "uint32_t", "uint64_t", "int8_t", "int16_t", "int32_t", "int64_t"
}


def strip_c_comments(line: str) -> str:
    """Strip standard C block comments /* ... */ from a line."""
    return re.sub(r"/\*.*?\*/", "", line, flags=re.DOTALL)


def is_declaration_line(line: str) -> bool:
    """Check if a line already contains a C declaration to prevent re-scanning."""
    stripped = line.strip()
    if "Conservative pseudo declarations" in stripped:
        return True
    if not stripped:
        return False
    parts = re.split(r"[\s\(\*]+", stripped)
    if parts and parts[0] in DECL_TYPES:
        return True
    return False


def declaration_sort_key(name: str) -> tuple:
    """
    Deterministic sort key for local declarations.
    Order:
      1. tmp_sp
      2. tmp_x* numerically
      3. tmp_w* numerically
      4. other tmp_* lexically
      5. stack_m* numerically
      6. stack_* numerically
    """
    if name == "tmp_sp":
        return (0, 0, "")
    if name.startswith("tmp_x"):
        suffix = name[5:]
        if suffix.isdigit():
            return (1, int(suffix), "")
    if name.startswith("tmp_w"):
        suffix = name[5:]
        if suffix.isdigit():
            return (2, int(suffix), "")
    if name.startswith("tmp_"):
        return (3, 0, name)
    if name.startswith("stack_m"):
        suffix = name[7:]
        if suffix.isdigit():
            return (4, int(suffix), "")
    if name.startswith("stack_"):
        suffix = name[6:]
        if suffix.isdigit():
            return (5, int(suffix), "")
    return (6, 0, name)


def analyze_declarations_for_function(
    function_name: str,
    return_type: str,
    parameters: list[dict],
    lowered_blocks: dict,
    structured_regions: list[dict],
    emitted_body_lines: list[str] | None = None,
) -> dict:
    """
    Analyze local pseudo register and stack slot declarations for a single function.
    Returns metadata dict.
    """
    param_names = {p.get("name") for p in parameters if isinstance(p, dict) and p.get("name")}
    warnings = []
    
    # 1. Collect all usage lines/statements
    # Also track block IDs for lines from emitted_body_lines
    usage_texts: list[str] = []
    
    # Trace source flag
    source = "identifier_usage_scan"
    
    if emitted_body_lines is not None:
        for line in emitted_body_lines:
            if is_declaration_line(line):
                # Skip declaration lines to avoid loops/duplicates
                continue
            usage_texts.append(line)
    else:
        source = "identifier_usage_scan_lowered_blocks_only"
        warnings.append("declaration_scan_from_lowered_blocks_only")
        # Gather from lowered_blocks
        for b_id, stmts in lowered_blocks.items():
            for stmt in stmts:
                if isinstance(stmt, dict):
                    txt = stmt.get("text", "")
                else:
                    txt = getattr(stmt, "text", "")
                usage_texts.append(txt)

    # 2. Extract found identifiers outside comments
    found_tmps: Set[str] = set()
    found_stacks: Set[str] = set()
    found_helpers: Set[str] = set()
    
    # Keep track of where each identifier is seen for type/width evidence
    # Map slot -> set of evidence types ("u32", "u64", "u32_cast")
    slot_evidence = defaultdict(set)
    
    # Map identifier -> set of addresses
    evidence_map = defaultdict(set)
    
    # Pre-build address map from lowered_blocks for quick lookup
    # statement text -> address
    stmt_addr_map = {}
    for b_id, stmts in lowered_blocks.items():
        for stmt in stmts:
            if isinstance(stmt, dict):
                txt = stmt.get("text", "")
                addr = stmt.get("address")
            else:
                txt = getattr(stmt, "text", "")
                addr = getattr(stmt, "address", None)
            if txt and addr:
                stmt_addr_map[txt.strip()] = str(addr)

    # Scan usage texts
    for line in usage_texts:
        stripped = strip_c_comments(line)
        
        tmps = TMP_RE.findall(stripped)
        stacks = STACK_RE.findall(stripped)
        helpers = CALL_RE.findall(stripped)
        
        # Determine statement address
        addr_match = re.search(r"0x[0-9a-fA-F]+", line)
        line_addr = addr_match.group(0) if addr_match else None
        
        # If line contains an address but is not in our statement map, use line address
        # Otherwise try exact statement match
        stripped_line = line.strip()
        matched_addr = stmt_addr_map.get(stripped_line, line_addr)
        
        # Update sets and slot evidence
        for t in tmps:
            found_tmps.add(t)
            if matched_addr:
                evidence_map[t].add(matched_addr)
                
        for s in stacks:
            found_stacks.add(s)
            if matched_addr:
                evidence_map[s].add(matched_addr)
                
            # Collect slot width evidence
            # 64-bit Pseudo-reg or 64-bit cast checks
            if (
                any(cast in stripped for cast in ("(i64)", "(u64)", "(int64_t)", "(uint64_t)")) or
                any(reg in stripped for reg in ("tmp_x", "tmp_sp", "tmp_fp", "tmp_lr"))
            ):
                slot_evidence[s].add("u64")
            
            # 32-bit Pseudo-reg checks
            if any(reg in stripped for reg in ("tmp_w",)):
                slot_evidence[s].add("u32")
                
            # 32-bit cast checks
            if any(cast in stripped for cast in ("(i32)", "(u32)", "(int32_t)", "(uint32_t)")):
                slot_evidence[s].add("u32_cast")

        for h in helpers:
            found_helpers.add(h)
            if matched_addr:
                evidence_map[h].add(matched_addr)

    # 3. Filter out parameters and record warnings for parameter skips
    local_tmps = []
    for name in found_tmps:
        if name in param_names:
            warnings.append(f"parameter_name_skipped:{name}")
        else:
            local_tmps.append(name)
            
    local_stacks = []
    for name in found_stacks:
        if name in param_names:
            warnings.append(f"parameter_name_skipped:{name}")
        else:
            local_stacks.append(name)

    # 4. Resolve stack slot widths and compile local declarations list
    declarations_list = []
    
    # Sort local tmps deterministically
    sorted_tmps = sorted(local_tmps, key=declaration_sort_key)
    for name in sorted_tmps:
        # Determine ctype for pseudo-registers
        if name.startswith("tmp_w"):
            ctype = "u32"
        elif name.startswith("tmp_x") or name == "tmp_sp" or name == "tmp_fp" or name == "tmp_lr":
            ctype = "u64"
        else:
            ctype = "u64"
            
        evidence = sorted(list(evidence_map[name]))
        declarations_list.append({
            "name": name,
            "kind": "pseudo_register",
            "ctype": ctype,
            "scope": "function",
            "source": source,
            "evidence": evidence,
            "warnings": []
        })

    # Sort local stack slots deterministically
    sorted_stacks = sorted(local_stacks, key=declaration_sort_key)
    for name in sorted_stacks:
        evidence = sorted(list(evidence_map[name]))
        
        # Conflict check and resolution
        ev = slot_evidence[name]
        slot_warnings = []
        if "u64" in ev:
            if "u32" in ev or "u32_cast" in ev:
                ctype = "u64"
                slot_warnings.append("width_conflict_promoted_to_u64")
                warnings.append(f"width_conflict_promoted_to_u64:{name}")
            else:
                ctype = "u64"
        elif "u32" in ev:
            ctype = "u32"
        elif "u32_cast" in ev:
            ctype = "u32"
        else:
            ctype = "u64" # default
            
        declarations_list.append({
            "name": name,
            "kind": "pseudo_stack_slot",
            "ctype": ctype,
            "scope": "function",
            "source": source,
            "evidence": evidence,
            "warnings": slot_warnings
        })

    return {
        "pseudo_registers_declared": len(sorted_tmps),
        "pseudo_stack_slots_declared": len(sorted_stacks),
        "call_helpers_declared": len(found_helpers),
        "declarations_total": len(sorted_tmps) + len(sorted_stacks),
        "declarations": declarations_list,
        "warnings": warnings,
        "call_helpers": sorted(list(found_helpers))
    }
