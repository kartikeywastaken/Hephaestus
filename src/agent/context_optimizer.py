# -*- coding: utf-8 -*-
"""
Phase 11.6 — Compact LLM context optimizer.

Converts large raw agent packets into compact function-level packets
suitable for Groq / on-demand providers with limited context windows.

Optimization rules:
  DROP  raw instruction dumps, full xref lists, full evidence index,
        full source files, repeated global metadata, large CFG dumps,
        unrelated function data, library/import stubs.
  KEEP  function name, address, signature guess, calls/called_by,
        loop/conditional summaries, top constants/strings, type/layout
        hints, compact dynamic summary, one function source slice,
        uncertainty notes, forbidden_claims.

Size enforcement:
  if packet > max_packet_chars → progressively drop fields →
  raw_instructions → full_xrefs → source_slice → summary-only mode.
"""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Any

from src.agent.library_filter import classify_function_role, is_skippable_for_debate

logger = logging.getLogger("agent.context_optimizer")

SCHEMA_COMPACT_PACKET = "agent-packet-compact-1.0"


# ── Extraction helpers ────────────────────────────────────────────────────────

def _extract_structure_summary(packet: dict) -> dict:
    """Extract a compact structure summary from raw packet data."""
    cfg = packet.get("cfg_summary", {})
    loops_raw = packet.get("loops", [])
    conditionals_raw = packet.get("conditionals", [])

    loops = []
    if isinstance(loops_raw, list):
        for loop in loops_raw[:10]:
            if isinstance(loop, dict):
                loops.append({
                    "kind": loop.get("kind", "unknown"),
                    "header": loop.get("header", ""),
                    "evidence": loop.get("evidence", "static_cfg"),
                })

    conditionals = []
    if isinstance(conditionals_raw, list):
        for cond in conditionals_raw[:10]:
            if isinstance(cond, dict):
                conditionals.append({
                    "kind": cond.get("kind", "unknown"),
                    "address": cond.get("address", ""),
                })

    return {
        "basic_blocks": cfg.get("basic_blocks", packet.get("basic_blocks", 0)),
        "edges": cfg.get("edges", packet.get("edges", 0)),
        "loops": loops,
        "conditionals": conditionals,
    }


def _extract_type_summary(packet: dict) -> dict:
    """Extract compact type summary."""
    return {
        "return_type": packet.get("return_type", "unknown"),
        "params": packet.get("params", packet.get("parameters", [])),
        "uncertainties": packet.get("known_uncertainties", [
            "Exact source parameter names unknown",
            "Exact struct field names unknown",
        ]),
    }


def _extract_dynamic_summary(packet: dict) -> dict:
    """Extract compact dynamic behavior summary."""
    dyn = packet.get("dynamic_behavior", {})
    if isinstance(dyn, list):
        # Legacy format: list of observation dicts
        return {
            "observed": len(dyn) > 0,
            "tested_inputs_only": True,
            "notes": [d.get("description", "") for d in dyn[:5] if isinstance(d, dict)],
        }
    if isinstance(dyn, dict):
        return {
            "observed": dyn.get("observed", False),
            "tested_inputs_only": True,
            "argv_sensitive": dyn.get("argv_sensitive", False),
            "stdout_varies": dyn.get("stdout_varies", False),
            "exit_code_varies": dyn.get("exit_code_varies", False),
            "notes": dyn.get("notes", []),
        }
    return {
        "observed": False,
        "tested_inputs_only": True,
        "notes": [],
    }


def _extract_top_evidence(packet: dict, max_items: int = 20) -> list[str]:
    """Extract top evidence as short strings."""
    evidence: list[str] = []

    # Calls
    calls = packet.get("calls", [])
    if calls:
        evidence.append(f"Calls: {', '.join(str(c) for c in calls[:5])}")

    # Called by
    called_by = packet.get("called_by", [])
    if called_by:
        evidence.append(f"Called by: {', '.join(str(c) for c in called_by[:5])}")

    # Loops
    loop_count = packet.get("loop_count", len(packet.get("loops", [])))
    if loop_count:
        evidence.append(f"Loops detected: {loop_count}")

    # Conditionals
    cond_count = packet.get("condition_count", len(packet.get("conditionals", [])))
    if cond_count:
        evidence.append(f"Conditionals: {cond_count}")

    # Constants
    constants = packet.get("constants", [])
    if constants:
        evidence.append(f"Constants: {', '.join(str(c) for c in constants[:5])}")

    # Strings
    strings = packet.get("strings", [])
    if strings:
        evidence.append(f"Strings: {', '.join(str(s) for s in strings[:5])}")

    # Evidence refs from the packet
    evidence_refs = packet.get("evidence", [])
    if isinstance(evidence_refs, list):
        for ref in evidence_refs[:max_items - len(evidence)]:
            if isinstance(ref, dict):
                evidence.append(ref.get("detail", str(ref)))
            elif isinstance(ref, str):
                evidence.append(ref)

    return evidence[:max_items]


def _extract_source_slice(packet: dict) -> str | None:
    """Extract the source slice for this function."""
    # Try recovered_readable_slice first, then recovered_slice
    for key in ("recovered_readable_slice", "recovered_slice", "source_slice"):
        val = packet.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


# ── Compact packet builder ────────────────────────────────────────────────────

_FIELDS_TO_DROP_PROGRESSIVELY = [
    "raw_instructions",
    "disassembly",
    "xrefs",
    "full_xrefs",
    "full_cfg",
    "raw_cfg",
    "evidence_index_slice",
]


def _build_compact_packet(
    packet: dict,
    *,
    max_packet_chars: int = 16000,
    max_evidence_items: int = 20,
    include_source_slice: bool = True,
) -> dict:
    """Build a single compact packet from a raw packet."""
    fn_name = packet.get("function", "unknown")
    role = classify_function_role(packet)
    original_chars = len(json.dumps(packet, ensure_ascii=False))

    compact: dict[str, Any] = {
        "schema_version": SCHEMA_COMPACT_PACKET,
        "packet_mode": "compact",
        "function": fn_name,
        "role": role,
        "signature_guess": packet.get("signature", packet.get("signature_guess", "")),
        "address": packet.get("address", packet.get("entry_point", "")),
        "calls": packet.get("calls", [])[:20],
        "called_by": packet.get("called_by", [])[:20],
        "structure_summary": _extract_structure_summary(packet),
        "type_summary": _extract_type_summary(packet),
        "dynamic_summary": _extract_dynamic_summary(packet),
        "top_evidence": _extract_top_evidence(packet, max_evidence_items),
        "forbidden_claims": packet.get("forbidden_claims", [
            "semantic equivalence",
            "same behavior as original",
            "exact original variable names",
            "exact original struct field names",
        ]),
    }

    # Source slice
    source_slice = _extract_source_slice(packet) if include_source_slice else None
    if source_slice:
        compact["source_slice"] = source_slice

    # Known uncertainties
    compact["known_uncertainties"] = packet.get("known_uncertainties", [
        "Exact source parameter names unknown",
        "Exact struct field names unknown",
    ])

    # Check size and progressively drop fields
    dropped_fields: list[str] = []

    def _current_size() -> int:
        return len(json.dumps(compact, ensure_ascii=False))

    # Drop explicitly large fields from the raw packet that may have leaked
    for field in _FIELDS_TO_DROP_PROGRESSIVELY:
        if field in compact and _current_size() > max_packet_chars:
            del compact[field]
            dropped_fields.append(field)

    # If still too large, drop source slice
    if _current_size() > max_packet_chars and "source_slice" in compact:
        del compact["source_slice"]
        dropped_fields.append("source_slice")

    # If still too large, truncate evidence
    if _current_size() > max_packet_chars:
        compact["top_evidence"] = compact["top_evidence"][:5]
        dropped_fields.append("evidence_truncated")

    # If still too large, switch to summary-only mode
    if _current_size() > max_packet_chars:
        compact = {
            "schema_version": SCHEMA_COMPACT_PACKET,
            "packet_mode": "summary_only",
            "function": fn_name,
            "role": role,
            "signature_guess": compact.get("signature_guess", ""),
            "address": compact.get("address", ""),
            "calls": compact.get("calls", [])[:5],
            "structure_summary": {
                "basic_blocks": compact.get("structure_summary", {}).get("basic_blocks", 0),
                "edges": compact.get("structure_summary", {}).get("edges", 0),
                "loops": [],
                "conditionals": [],
            },
            "forbidden_claims": compact.get("forbidden_claims", []),
        }
        dropped_fields.append("summary_only_mode")

    compact_chars = _current_size()
    compact["optimization"] = {
        "original_chars": original_chars,
        "compact_chars": compact_chars,
        "dropped_fields": dropped_fields,
        "budget_met": compact_chars <= max_packet_chars,
    }

    return compact


# ── Public API ────────────────────────────────────────────────────────────────

def optimize_agent_packets(
    out_dir: Path,
    *,
    packet_mode: str = "compact",
    max_packet_chars: int = 16000,
    max_evidence_items: int = 20,
    include_source_slice: bool = True,
) -> tuple[list[Path], dict]:
    """
    Read ``agent_packets/*.json`` and write compact packets to
    ``agent_packets_compact/``.

    Returns ``(compact_packet_paths, optimization_report)``.
    """
    out_dir = Path(out_dir)
    packets_dir = out_dir / "agent_packets"
    compact_dir = out_dir / "agent_packets_compact"
    compact_dir.mkdir(parents=True, exist_ok=True)

    if not packets_dir.exists():
        logger.warning("[context_optimizer] agent_packets/ not found in %s", out_dir)
        return [], {
            "schema_version": "agent-packet-optimization-1.0",
            "status": "no_packets",
            "packets_optimized": 0,
        }

    raw_paths = sorted(packets_dir.glob("*.json"))
    compact_paths: list[Path] = []
    packet_summaries: list[dict] = []
    total_original = 0
    total_compact = 0
    skipped_library = 0

    for raw_path in raw_paths:
        try:
            with open(raw_path, "r", encoding="utf-8") as f:
                raw_packet = json.load(f)
        except Exception as e:
            logger.warning("[context_optimizer] failed to load %s: %s", raw_path.name, e)
            continue

        fn_name = raw_packet.get("function", "unknown")

        # Mark library functions as skippable
        if is_skippable_for_debate(raw_packet):
            skipped_library += 1
            packet_summaries.append({
                "function": fn_name,
                "status": "skipped_library",
                "original_chars": len(json.dumps(raw_packet, ensure_ascii=False)),
                "compact_chars": 0,
            })
            continue

        if packet_mode == "full":
            # Full mode: just copy to compact dir without optimization
            compact_path = compact_dir / raw_path.name
            with open(compact_path, "w", encoding="utf-8") as f:
                json.dump(raw_packet, f, indent=2, ensure_ascii=False)
            compact_paths.append(compact_path)
            orig_sz = len(json.dumps(raw_packet, ensure_ascii=False))
            total_original += orig_sz
            total_compact += orig_sz
            packet_summaries.append({
                "function": fn_name,
                "status": "full_copy",
                "original_chars": orig_sz,
                "compact_chars": orig_sz,
            })
            continue

        # Compact mode
        compact_packet = _build_compact_packet(
            raw_packet,
            max_packet_chars=max_packet_chars,
            max_evidence_items=max_evidence_items,
            include_source_slice=include_source_slice,
        )

        compact_path = compact_dir / raw_path.name
        with open(compact_path, "w", encoding="utf-8") as f:
            json.dump(compact_packet, f, indent=2, ensure_ascii=False)
        compact_paths.append(compact_path)

        opt = compact_packet.get("optimization", {})
        total_original += opt.get("original_chars", 0)
        total_compact += opt.get("compact_chars", 0)

        packet_summaries.append({
            "function": fn_name,
            "status": "optimized",
            "original_chars": opt.get("original_chars", 0),
            "compact_chars": opt.get("compact_chars", 0),
            "dropped_fields": opt.get("dropped_fields", []),
            "budget_met": opt.get("budget_met", True),
        })

    report = {
        "schema_version": "agent-packet-optimization-1.0",
        "phase": "11.6",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "packet_mode": packet_mode,
        "max_packet_chars": max_packet_chars,
        "packets_optimized": len(compact_paths),
        "packets_skipped_library": skipped_library,
        "total_original_chars": total_original,
        "total_compact_chars": total_compact,
        "compression_ratio": round(total_compact / total_original, 3) if total_original > 0 else 0,
        "packets": packet_summaries,
    }

    # Write optimization report
    report_path = out_dir / "agent_packet_optimization_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(
        "[context_optimizer] optimized %d packets (%d→%d chars, skipped %d library)",
        len(compact_paths), total_original, total_compact, skipped_library,
    )

    return compact_paths, report
