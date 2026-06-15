# -*- coding: utf-8 -*-
"""
Phase 5.3: Conservative Structured Control-Flow Emitter
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple, Set
from src.ir.utils.addressing import normalize_address

def deterministic_block_sort_key(block_id: str) -> tuple[int, Any]:
    """
    Address-like block IDs sort first numerically.
    Non-address IDs sort afterward lexically.
    """
    val = str(block_id).strip()
    try:
        norm = normalize_address(val)
        if norm is None:
            raise ValueError("Not an address")
        if norm.startswith("0x"):
            return (0, int(norm, 16))
        return (0, int(norm))
    except (ValueError, TypeError):
        return (1, val)


def collect_blocks_from_region(region: dict) -> list[str]:
    """
    Recursively collect block IDs from any known or unknown region shape.
    Must be conservative.
    """
    if not isinstance(region, dict):
        return []

    blocks = []
    rtype = region.get("type")

    if rtype == "block":
        b_id = region.get("id")
        if b_id:
            blocks.append(str(b_id))

    # Always check common keys for sub-regions
    if "children" in region:
        children = region["children"]
        if isinstance(children, list):
            for child in children:
                if isinstance(child, dict):
                    blocks.extend(collect_blocks_from_region(child))

    if "body" in region:
        body = region["body"]
        if isinstance(body, dict):
            blocks.extend(collect_blocks_from_region(body))

    if "then_branch" in region:
        then_b = region["then_branch"]
        if isinstance(then_b, dict):
            blocks.extend(collect_blocks_from_region(then_b))

    if "else_branch" in region:
        else_b = region["else_branch"]
        if isinstance(else_b, dict):
            blocks.extend(collect_blocks_from_region(else_b))

    # Also collect header_block and condition_block and dispatch_block if present
    for key in ("header_block", "condition_block", "dispatch_block"):
        b_id = region.get(key)
        if b_id:
            blocks.append(str(b_id))

    return blocks


def analyze_control_flow_regions(regions: list[dict]) -> dict:
    """
    Count region/control-flow metrics without generating C text.
    """
    stats = {
        "regions_total": 0,
        "structured_constructs_emitted": 0,
        "loops_emitted": 0,
        "if_constructs_emitted": 0,
        "if_else_constructs_emitted": 0,
        "switch_constructs_emitted": 0,
        "fallback_regions": 0,
        "duplicate_blocks_skipped": 0,
        "condition_expressions_recovered": 0
    }

    seen_blocks: Set[str] = set()

    def _analyze_recursive(region: dict) -> None:
        if not isinstance(region, dict):
            return

        stats["regions_total"] += 1
        rtype = region.get("type", "unknown")

        if rtype == "block":
            block_id = region.get("id")
            if block_id:
                if block_id in seen_blocks:
                    stats["duplicate_blocks_skipped"] += 1
                else:
                    seen_blocks.add(block_id)

        elif rtype == "sequence":
            for child in region.get("children", []):
                if isinstance(child, dict):
                    _analyze_recursive(child)

        elif rtype == "if":
            stats["if_constructs_emitted"] += 1
            stats["structured_constructs_emitted"] += 1
            cond_block = region.get("condition_block")
            if cond_block:
                if cond_block in seen_blocks:
                    stats["duplicate_blocks_skipped"] += 1
                else:
                    seen_blocks.add(cond_block)
            then_branch = region.get("then_branch")
            if isinstance(then_branch, dict):
                _analyze_recursive(then_branch)

        elif rtype == "if_else":
            stats["if_else_constructs_emitted"] += 1
            stats["structured_constructs_emitted"] += 1
            cond_block = region.get("condition_block")
            if cond_block:
                if cond_block in seen_blocks:
                    stats["duplicate_blocks_skipped"] += 1
                else:
                    seen_blocks.add(cond_block)
            then_branch = region.get("then_branch")
            if isinstance(then_branch, dict):
                _analyze_recursive(then_branch)
            else_branch = region.get("else_branch")
            if isinstance(else_branch, dict):
                _analyze_recursive(else_branch)

        elif rtype == "loop":
            stats["loops_emitted"] += 1
            stats["structured_constructs_emitted"] += 1
            header = region.get("header_block")
            if header:
                if header in seen_blocks:
                    stats["duplicate_blocks_skipped"] += 1
                else:
                    seen_blocks.add(header)
            body = region.get("body")
            if isinstance(body, dict):
                _analyze_recursive(body)

        elif rtype in {"switch", "switch_like"}:
            stats["switch_constructs_emitted"] += 1
            stats["structured_constructs_emitted"] += 1
            dispatch = region.get("dispatch_block")
            if dispatch:
                if dispatch in seen_blocks:
                    stats["duplicate_blocks_skipped"] += 1
                else:
                    seen_blocks.add(dispatch)
            for child in region.get("children", []):
                if isinstance(child, dict):
                    _analyze_recursive(child)

        elif rtype == "unstructured":
            stats["fallback_regions"] += 1
            blocks = sorted(list(set(collect_blocks_from_region(region))), key=deterministic_block_sort_key)
            for b_id in blocks:
                if b_id:
                    if b_id in seen_blocks:
                        stats["duplicate_blocks_skipped"] += 1
                    else:
                        seen_blocks.add(b_id)

        elif rtype in {"break", "continue"}:
            pass

        else:
            stats["fallback_regions"] += 1
            blocks = sorted(list(set(collect_blocks_from_region(region))), key=deterministic_block_sort_key)
            for b_id in blocks:
                if b_id:
                    if b_id in seen_blocks:
                        stats["duplicate_blocks_skipped"] += 1
                    else:
                        seen_blocks.add(b_id)

    for r in regions:
        if isinstance(r, dict):
            _analyze_recursive(r)

    return stats


def lookup_condition_annotation(
    condition_annotations: dict | None,
    region_kind: str,
    block_id: str,
    branch_address: str | None = None,
) -> str | None:
    if not condition_annotations:
        return None
    # 1. exact key: (region_kind, block_id)
    key2 = (region_kind, block_id)
    if key2 in condition_annotations:
        return condition_annotations[key2]
    # 2. exact key with branch address if the region carries branch address
    if branch_address is not None:
        key3 = (region_kind, block_id, branch_address)
        if key3 in condition_annotations:
            return condition_annotations[key3]
    # 3. conservative fallback: first annotation matching region_kind and block_id
    for k, val in condition_annotations.items():
        if isinstance(k, tuple) and len(k) >= 2:
            if k[0] == region_kind and k[1] == block_id:
                return val
    # 4. no annotation -> None
    return None


def emit_regions_to_c(
    regions: list[dict],
    lowered_blocks: dict,
    indent: int = 1,
    seen_blocks: set[str] | None = None,
    condition_annotations: dict | None = None,
) -> tuple[list[str], dict]:
    """
    Emit conservative C-like structured control flow.
    Preserve lowered statements exactly.
    Return emitted lines and emission stats.
    """
    if seen_blocks is None:
        seen_blocks = set()

    stats = {
        "regions_total": 0,
        "structured_constructs_emitted": 0,
        "loops_emitted": 0,
        "if_constructs_emitted": 0,
        "if_else_constructs_emitted": 0,
        "switch_constructs_emitted": 0,
        "fallback_regions": 0,
        "duplicate_blocks_skipped": 0,
        "condition_expressions_recovered": 0
    }

    lines: list[str] = []

    def _get_branch_addr(block_id: str) -> str | None:
        stmts = lowered_blocks.get(block_id, [])
        for stmt in reversed(stmts):
            src_ins = stmt.get("source_instruction") if isinstance(stmt, dict) else getattr(stmt, "source_instruction", None)
            if src_ins and isinstance(src_ins, dict):
                mn = (src_ins.get("mnemonic") or "").lower().strip()
                if mn in {"b.eq", "b.ne", "b.lt", "b.le", "b.gt", "b.ge", "b.lo", "b.ls", "b.hi", "b.hs", "b.mi", "b.pl", "b.vs", "b.vc", "cbz", "cbnz", "tbz", "tbnz"}:
                    return stmt.get("address") if isinstance(stmt, dict) else getattr(stmt, "address", None)
        return None

    def _emit_region_recursive(region: dict, indent_level: int) -> None:
        if not isinstance(region, dict):
            return

        stats["regions_total"] += 1
        prefix = "    " * indent_level
        rtype = region.get("type", "unknown")

        if rtype == "block":
            block_id = region.get("id", "?")
            if block_id in seen_blocks:
                lines.append(f"{prefix}/* block {block_id} already emitted; duplicate reference skipped */")
                stats["duplicate_blocks_skipped"] += 1
                return
            seen_blocks.add(block_id)

            stmts = lowered_blocks.get(block_id, [])
            if stmts:
                lines.append(f"{prefix}/* block {block_id} */")
                for stmt in stmts:
                    text = stmt.get("text") if isinstance(stmt, dict) else stmt.text
                    lines.append(f"{prefix}{text}")
            else:
                lines.append(f"{prefix}/* block {block_id}: no lowered statements */")

        elif rtype == "sequence":
            for child in region.get("children", []):
                if isinstance(child, dict):
                    _emit_region_recursive(child, indent_level)

        elif rtype == "if":
            cond_block = region.get("condition_block", "?")
            merge_block = region.get("merge_block")

            lines.append(f"{prefix}/* if condition block: {cond_block} */")
            if merge_block:
                lines.append(f"{prefix}/* merge block: {merge_block} */")

            b_addr = _get_branch_addr(cond_block)
            annot = lookup_condition_annotation(condition_annotations, "if", cond_block, b_addr)
            if annot:
                lines.append(f"{prefix}if (/* {annot} */) {{")
            else:
                lines.append(f"{prefix}if (/* condition unknown: block {cond_block} */) {{")

            then_branch = region.get("then_branch")
            if then_branch and isinstance(then_branch, dict):
                _emit_region_recursive(then_branch, indent_level + 1)
            else:
                lines.append(f"{prefix}    /* missing then-branch evidence */")

            lines.append(prefix + "}")

            stats["if_constructs_emitted"] += 1
            stats["structured_constructs_emitted"] += 1

        elif rtype == "if_else":
            cond_block = region.get("condition_block", "?")
            merge_block = region.get("merge_block")

            lines.append(f"{prefix}/* if/else condition block: {cond_block} */")
            if merge_block:
                lines.append(f"{prefix}/* merge block: {merge_block} */")

            b_addr = _get_branch_addr(cond_block)
            annot = lookup_condition_annotation(condition_annotations, "if_else", cond_block, b_addr)
            if annot:
                lines.append(f"{prefix}if (/* {annot} */) {{")
            else:
                lines.append(f"{prefix}if (/* condition unknown: block {cond_block} */) {{")

            then_branch = region.get("then_branch")
            if then_branch and isinstance(then_branch, dict):
                _emit_region_recursive(then_branch, indent_level + 1)
            else:
                lines.append(f"{prefix}    /* missing then-branch evidence */")

            lines.append(prefix + "} else {")

            else_branch = region.get("else_branch")
            if else_branch and isinstance(else_branch, dict):
                _emit_region_recursive(else_branch, indent_level + 1)
            else:
                lines.append(f"{prefix}    /* missing else-branch evidence */")

            lines.append(prefix + "}")

            stats["if_else_constructs_emitted"] += 1
            stats["structured_constructs_emitted"] += 1

        elif rtype == "loop":
            kind = region.get("kind", "unknown")
            header = region.get("header_block", "?")
            exits = region.get("exit_blocks", [])

            lines.append(f"{prefix}/* loop kind: {kind} */")
            lines.append(f"{prefix}/* loop header: {header} */")
            if exits:
                lines.append(f"{prefix}/* loop exits: {exits} */")

            b_addr = _get_branch_addr(header)
            annot = lookup_condition_annotation(condition_annotations, "loop", header, b_addr)
            if annot:
                lines.append(f"{prefix}while (/* {annot} */) {{")
            else:
                lines.append(f"{prefix}while (/* condition unknown: loop header {header} */) {{")

            body = region.get("body")
            if body and isinstance(body, dict):
                _emit_region_recursive(body, indent_level + 1)
            else:
                lines.append(f"{prefix}    /* missing loop body evidence */")

            lines.append(prefix + "}")

            stats["loops_emitted"] += 1
            stats["structured_constructs_emitted"] += 1

        elif rtype in {"switch", "switch_like"}:
            dispatch = region.get("dispatch_block", "0x...")
            lines.append(f"{prefix}/* switch-like region: dispatch block {dispatch} */")
            lines.append(f"{prefix}/* cases unknown; preserving blocks conservatively */")
            lines.append(prefix + "{")

            for child in region.get("children", []):
                if isinstance(child, dict):
                    _emit_region_recursive(child, indent_level + 1)
            lines.append(prefix + "}")

            stats["switch_constructs_emitted"] += 1
            stats["structured_constructs_emitted"] += 1

        elif rtype == "unstructured":
            reason = region.get("reason") or "irreducible control flow or unsupported region shape"
            lines.append(f"{prefix}/* unstructured region begin */")
            lines.append(f"{prefix}/* reason: {reason} */")
            lines.append(prefix + "{")

            blocks = sorted(list(set(collect_blocks_from_region(region))), key=deterministic_block_sort_key)
            for b_id in blocks:
                if b_id:
                    if b_id in seen_blocks:
                        lines.append(f"{prefix}    /* block {b_id} already emitted; duplicate reference skipped */")
                        stats["duplicate_blocks_skipped"] += 1
                        continue
                    seen_blocks.add(b_id)

                    stmts = lowered_blocks.get(b_id, [])
                    if stmts:
                        lines.append(f"{prefix}    /* block {b_id} */")
                        for stmt in stmts:
                            text = stmt.get("text") if isinstance(stmt, dict) else stmt.text
                            lines.append(f"{prefix}    {text}")
                    else:
                        lines.append(f"{prefix}    /* block {b_id}: no lowered statements */")
            lines.append(prefix + "}")
            lines.append(f"{prefix}/* unstructured region end */")

            stats["fallback_regions"] += 1

        elif rtype == "break":
            target = region.get("target", region.get("target_block", "0x..."))
            lines.append(f"{prefix}break; /* break edge to {target} */")

        elif rtype == "continue":
            target = region.get("target", region.get("target_block", "0x..."))
            lines.append(f"{prefix}continue; /* continue edge to loop header {target} */")

        else:
            lines.append(f"{prefix}/* unsupported region type: {rtype} */")
            lines.append(f"{prefix}/* preserving contained blocks conservatively */")
            lines.append(prefix + "{")

            blocks = sorted(list(set(collect_blocks_from_region(region))), key=deterministic_block_sort_key)
            for b_id in blocks:
                if b_id:
                    if b_id in seen_blocks:
                        lines.append(f"{prefix}    /* block {b_id} already emitted; duplicate reference skipped */")
                        stats["duplicate_blocks_skipped"] += 1
                        continue
                    seen_blocks.add(b_id)

                    stmts = lowered_blocks.get(b_id, [])
                    if stmts:
                        lines.append(f"{prefix}    /* block {b_id} */")
                        for stmt in stmts:
                            text = stmt.get("text") if isinstance(stmt, dict) else stmt.text
                            lines.append(f"{prefix}    {text}")
                    else:
                        lines.append(f"{prefix}    /* block {b_id}: no lowered statements */")
            lines.append(prefix + "}")

            stats["fallback_regions"] += 1

    for region in regions:
        if isinstance(region, dict):
            _emit_region_recursive(region, indent)

    return lines, stats
