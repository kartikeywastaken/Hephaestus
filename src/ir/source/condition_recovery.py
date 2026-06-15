# -*- coding: utf-8 -*-
"""
Phase 5.5: Conservative Branch Predicate Annotation Recovery

Scans structured control-flow regions to identify condition header sites and
attempts to annotate them with predicate evidence from AArch64/ARM64 conditional
branches and comparisons.

Core Rules:
1. No executable boolean expressions are emitted.
2. Annotations contain text content only (no comment characters /* or */).
3. The backward compare scan stops at any control flow boundary.
4. Polarity is annotation-only and does not modify the structure.
5. Unsupported architectures still count condition sites but remain unknown.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from src.ir.utils.addressing import normalize_address

# ARM64 conditional branches
_COND_BRANCH_MNEMONICS = {
    "b.eq", "b.ne", "b.lt", "b.le", "b.gt", "b.ge",
    "b.lo", "b.ls", "b.hi", "b.hs", "b.mi", "b.pl",
    "b.vs", "b.vc", "cbz", "cbnz", "tbz", "tbnz"
}

# Compare/test producers
_COMPARE_MNEMONICS = {"cmp", "cmn", "tst", "subs", "ands"}

def _get_stmt_field(stmt: Any, field: str, default: Any = "") -> Any:
    """Get a field from a statement (dict or object)."""
    if isinstance(stmt, dict):
        return stmt.get(field, default)
    return getattr(stmt, field, default)

def _is_control_flow_boundary(stmt: Any, current_branch_address: str | None) -> bool:
    """Check if statement is a control flow boundary that stops backward compare search."""
    addr = _get_stmt_field(stmt, "address", None)
    if current_branch_address and addr == current_branch_address:
        return False

    kind = _get_stmt_field(stmt, "kind", "")
    text = _get_stmt_field(stmt, "text", "")

    if kind in {"call", "branch_comment", "return_comment"}:
        return True

    src_ins = _get_stmt_field(stmt, "source_instruction", None)
    if src_ins and isinstance(src_ins, dict):
        mn = (src_ins.get("mnemonic") or "").lower().strip()
        if mn in {"b", "bl", "blr", "br", "ret"} or mn.startswith("b.") or mn in {"cbz", "cbnz", "tbz", "tbnz"}:
            return True

    if kind == "comment" and "unsupported instruction" in text:
        lower_text = text.lower()
        if any(kw in lower_text for kw in ("b.", "b ", "bl ", "blr", "br ", "ret", "cbz", "cbnz", "tbz", "tbnz")):
            return True

    return False

def _addresses_match(addr1: str | None, addr2: str | None) -> bool:
    """Safely check if two addresses match canonically."""
    if addr1 is None or addr2 is None:
        return False
    norm1 = normalize_address(str(addr1))
    norm2 = normalize_address(str(addr2))
    if norm1 is not None and norm2 is not None:
        return norm1 == norm2
    return str(addr1).strip().lower() == str(addr2).strip().lower()

def _extract_branch_target(raw_text: str) -> Optional[str]:
    """Extract the target address from raw assembly text of a branch instruction."""
    cleaned = raw_text.split(";")[0].split("/*")[0]
    tokens = re.findall(r"\b(0x[0-9a-fA-F]+|\d+)\b", cleaned)
    if tokens:
        return tokens[-1]
    return None

def _parse_cbz_tbz_raw(mnemonic: str, raw: str) -> str:
    """Extract register and bit info for CBZ/TBNZ instructions."""
    m = mnemonic.lower()
    raw_clean = raw.strip()
    if m in ("cbz", "cbnz"):
        match = re.search(r"(?:cbz|cbnz)\s+([\w\d]+)", raw_clean, re.IGNORECASE)
        if match:
            return f"{m} {match.group(1)}"
        return m
    elif m in ("tbz", "tbnz"):
        match = re.search(
            r"(?:tbz|tbnz)\s+([\w\d]+)\s*,\s*(#?\d+)", raw_clean, re.IGNORECASE
        )
        if match:
            return f"{m} {match.group(1)} bit {match.group(2)}"
        return m
    return m

def get_entry_block(region: dict) -> Optional[str]:
    """Recursively find the entry block ID for a structured region."""
    if not isinstance(region, dict):
        return None
    rtype = region.get("type")
    if rtype == "block":
        return region.get("id")
    if rtype == "sequence":
        children = region.get("children", [])
        if children and isinstance(children[0], dict):
            return get_entry_block(children[0])
    if rtype in ("if", "if_else"):
        return region.get("condition_block")
    if rtype == "loop":
        return region.get("header_block")
    if rtype in ("switch", "switch_like"):
        return region.get("dispatch_block")
    return None

def _collect_condition_sites(region: dict) -> List[Dict[str, Any]]:
    """Traverse regions recursively to collect structured condition sites (no block-level dedup)."""
    if not isinstance(region, dict):
        return []

    sites: List[Dict[str, Any]] = []
    rtype = region.get("type")

    if rtype == "loop":
        header = region.get("header_block")
        if header:
            sites.append({
                "block_id": str(header),
                "structured_region_kind": "loop",
                "region": region,
            })
        body = region.get("body")
        if isinstance(body, dict):
            sites.extend(_collect_condition_sites(body))

    elif rtype == "if":
        cond_block = region.get("condition_block")
        if cond_block:
            sites.append({
                "block_id": str(cond_block),
                "structured_region_kind": "if",
                "region": region,
            })
        then_branch = region.get("then_branch")
        if isinstance(then_branch, dict):
            sites.extend(_collect_condition_sites(then_branch))

    elif rtype == "if_else":
        cond_block = region.get("condition_block")
        if cond_block:
            sites.append({
                "block_id": str(cond_block),
                "structured_region_kind": "if_else",
                "region": region,
            })
        then_branch = region.get("then_branch")
        if isinstance(then_branch, dict):
            sites.extend(_collect_condition_sites(then_branch))
        else_branch = region.get("else_branch")
        if isinstance(else_branch, dict):
            sites.extend(_collect_condition_sites(else_branch))

    # Search switch and sequence children
    if rtype in ("sequence", "switch", "switch_like"):
        for child in region.get("children", []):
            if isinstance(child, dict):
                sites.extend(_collect_condition_sites(child))

    return sites

def analyze_condition_sites(
    structured_regions: list[dict],
    lowered_blocks: dict,
    cfg_info: dict | None = None,
    architecture: str = "unknown",
) -> dict:
    """
    Analyze condition sites in structured regions and return comment-only branch predicate annotations.
    """
    is_arm64 = architecture.lower() in ("arm64", "aarch64")

    # 1. Collect all condition sites
    collected_sites: List[Dict[str, Any]] = []
    for r in structured_regions:
        collected_sites.extend(_collect_condition_sites(r))

    sites: List[Dict[str, Any]] = []
    condition_sites_with_evidence = 0
    condition_sites_unknown = 0
    conditions_inverted_for_structure = 0
    ambiguous_condition_sites = 0

    for cs in collected_sites:
        block_id = cs["block_id"]
        region_kind = cs["structured_region_kind"]
        region = cs["region"]

        site_record: Dict[str, Any] = {
            "block_id": block_id,
            "branch_address": None,
            "branch_mnemonic": None,
            "predicate": None,
            "compare_address": None,
            "compare_mnemonic": None,
            "branch_target": None,
            "fallthrough_target": None,
            "structured_region_kind": region_kind,
            "polarity": "unknown",
            "annotation": "",
            "warnings": [],
        }

        # If architecture is not ARM64, treat as unknown site
        if not is_arm64:
            site_record["annotation"] = f"condition unknown: {region_kind} header {block_id}" if region_kind == "loop" else f"condition unknown: block {block_id}"
            condition_sites_unknown += 1
            sites.append(site_record)
            continue

        stmts = lowered_blocks.get(block_id, [])
        branch_stmt_idx = -1
        branch_stmt = None
        branch_mnemonic = ""

        # Find the last conditional branch statement in the block
        for idx in range(len(stmts) - 1, -1, -1):
            stmt = stmts[idx]
            src_ins = _get_stmt_field(stmt, "source_instruction", None)
            if src_ins and isinstance(src_ins, dict):
                mn = (src_ins.get("mnemonic") or "").lower().strip()
                if mn in _COND_BRANCH_MNEMONICS:
                    branch_stmt_idx = idx
                    branch_stmt = stmt
                    branch_mnemonic = mn
                    break

        if branch_stmt is None:
            # No conditional branch found
            site_record["annotation"] = f"condition unknown: {region_kind} header {block_id}" if region_kind == "loop" else f"condition unknown: block {block_id}"
            condition_sites_unknown += 1
            sites.append(site_record)
            continue

        # Extract branch details
        branch_address = _get_stmt_field(branch_stmt, "address", None)
        src_ins = _get_stmt_field(branch_stmt, "source_instruction", {})
        raw_branch = src_ins.get("raw") or branch_mnemonic
        branch_target = _extract_branch_target(raw_branch)

        site_record["branch_address"] = branch_address
        site_record["branch_mnemonic"] = branch_mnemonic
        site_record["branch_target"] = branch_target

        if branch_mnemonic.startswith("b."):
            site_record["predicate"] = branch_mnemonic[2:]

        # Scan backward for compare/test evidence
        compare_stmt = None
        compare_mnemonic = ""
        clobbered = False

        for idx in range(branch_stmt_idx - 1, -1, -1):
            stmt = stmts[idx]
            if _is_control_flow_boundary(stmt, branch_address):
                clobbered = True
                break

            src_ins = _get_stmt_field(stmt, "source_instruction", None)
            if src_ins and isinstance(src_ins, dict):
                mn = (src_ins.get("mnemonic") or "").lower().strip()
                if mn in _COMPARE_MNEMONICS:
                    compare_stmt = stmt
                    compare_mnemonic = mn
                    break

        if compare_stmt is not None and not clobbered:
            compare_address = _get_stmt_field(compare_stmt, "address", None)
            site_record["compare_address"] = compare_address
            site_record["compare_mnemonic"] = compare_mnemonic

        # Determine Polarity
        polarity = "unknown"
        if region_kind == "loop":
            exits = region.get("exit_blocks", [])
            body = region.get("body")
            body_entry = get_entry_block(body) if isinstance(body, dict) else None

            if branch_target and any(_addresses_match(branch_target, ex) for ex in exits):
                polarity = "inverted"
            elif branch_target and _addresses_match(branch_target, body_entry):
                polarity = "direct"
        elif region_kind in ("if", "if_else"):
            then_branch = region.get("then_branch")
            else_branch = region.get("else_branch")
            then_entry = get_entry_block(then_branch) if isinstance(then_branch, dict) else None
            else_entry = get_entry_block(else_branch) if isinstance(else_branch, dict) else None

            if branch_target and _addresses_match(branch_target, then_entry):
                polarity = "direct"
            elif branch_target and _addresses_match(branch_target, else_entry):
                polarity = "inverted"

        site_record["polarity"] = polarity
        if polarity == "inverted":
            conditions_inverted_for_structure += 1
        elif polarity == "unknown":
            ambiguous_condition_sites += 1

        # Format comment-only annotation text (no /* or */)
        annot_parts = []
        is_cbz_tbz = branch_mnemonic in ("cbz", "cbnz", "tbz", "tbnz")

        if is_cbz_tbz:
            cbz_desc = _parse_cbz_tbz_raw(branch_mnemonic, raw_branch)
            annot_parts.append(f"condition evidence: {cbz_desc} at {branch_address}")
            if branch_target:
                annot_parts.append(f"targeting {branch_target}")
        else:
            annot_parts.append(f"condition evidence: {branch_mnemonic} at {branch_address}")
            if compare_stmt is not None and not clobbered:
                annot_parts.append(f"after {compare_mnemonic} at {site_record['compare_address']}")
            else:
                annot_parts.append("compare/test producer unknown")
                site_record["warnings"].append("compare/test producer unknown")

            if branch_target:
                annot_parts.append(f"target {branch_target}")

        # Polarity detail
        if polarity == "inverted":
            if region_kind == "loop":
                annot_parts.append("loop polarity inverted")
            else:
                annot_parts.append("polarity inverted")
        elif polarity == "direct":
            if region_kind == "loop":
                annot_parts.append("loop polarity direct")
            else:
                annot_parts.append("polarity direct")

        annotation_text = " ".join(annot_parts).replace(";", "").replace(",", "")
        # Normalize double spaces or spacing issues
        annotation_text = re.sub(r"\s+", " ", annotation_text).strip()
        
        # Inject standard separators back in a controlled fashion to match examples
        # Example: b.ge at 0x100000490 after subs at 0x10000048c; target 0x1000004c8; loop polarity inverted
        if is_cbz_tbz:
            # "condition evidence: cbz w8 at 0x... targeting 0x..."
            # no semicolons needed except polarity
            if polarity != "unknown":
                p_text = "loop polarity inverted" if (region_kind == "loop" and polarity == "inverted") else \
                         "loop polarity direct" if (region_kind == "loop" and polarity == "direct") else \
                         "polarity inverted" if polarity == "inverted" else "polarity direct"
                annotation_text = annotation_text.replace(f" {p_text}", f"; {p_text}")
        else:
            # E.g. "condition evidence: b.ge at 0x... after subs at 0x... target 0x..."
            if "after " in annotation_text:
                annotation_text = annotation_text.replace(" after ", " after ")
            if "target " in annotation_text:
                annotation_text = annotation_text.replace(" target ", "; target ")
            if "compare/test producer unknown" in annotation_text:
                annotation_text = annotation_text.replace(" compare/test ", "; compare/test ")
            
            if polarity != "unknown":
                p_text = "loop polarity inverted" if (region_kind == "loop" and polarity == "inverted") else \
                         "loop polarity direct" if (region_kind == "loop" and polarity == "direct") else \
                         "polarity inverted" if polarity == "inverted" else "polarity direct"
                annotation_text = annotation_text.replace(f" {p_text}", f"; {p_text}")

        # Ensure no comment characters leak
        annotation_text = annotation_text.replace("/*", "").replace("*/", "")
        site_record["annotation"] = annotation_text

        condition_sites_with_evidence += 1
        sites.append(site_record)

    return {
        "condition_sites_total": len(sites),
        "condition_sites_with_evidence": condition_sites_with_evidence,
        "condition_sites_unknown": condition_sites_unknown,
        "condition_annotations_recovered": condition_sites_with_evidence,
        "conditions_inverted_for_structure": conditions_inverted_for_structure,
        "ambiguous_condition_sites": ambiguous_condition_sites,
        "sites": sites,
        "warnings": [],
    }
