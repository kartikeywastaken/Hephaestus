# -*- coding: utf-8 -*-
"""
Phase 10 — Packet builder.

Reads all available Phase 1-9 artifacts and produces per-function agent packets.
Each packet contains:
  - Function metadata from source_reconstruction.json
  - Token-safe C slices from recovered.c and recovered_readable.c
  - Static summary from behavior_model.json
  - Dynamic observations from behavior_profile.json / dynamic_runs.json
  - Evidence slice from evidence_index.json
  - Trace slice from trace_report.json
  - Quality gate summary from quality_gate.json
  - Standard forbidden_claims and known_uncertainties

Hash guards: sha256 of recovered.c, recovered_readable.c,
source_reconstruction.json, behavior_model.json are checked before and after.
If any artifact changes → abort with exit code 2.

Token-safe C slicing:
  Counts opening braces '{' only when outside:
    - string literals  "..."
    - char literals    '.'
    - block comments   /* ... */
    - line comments    // ...\n
  The slice includes the complete function body (balanced braces).
  If the resulting slice exceeds MAX_SLICE_LINES, it is truncated with a comment.
  Slicing failures produce an empty slice + diagnostics — they never crash the builder.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

from src.agent.models import (
    FORBIDDEN_CLAIMS,
    KNOWN_UNCERTAINTIES,
    DEFAULT_MAX_SLICE_LINES,
    SLICE_TRUNCATION_COMMENT,
    SCHEMA_AGENT_PACKET,
)

logger = logging.getLogger("agent.packet_builder")

# Artifacts Phase 10 guards (read-only)
GUARDED_ARTIFACTS = [
    "recovered.c",
    "recovered_readable.c",
    "source_reconstruction.json",
    "behavior_model.json",
]


# ── Hash guard ────────────────────────────────────────────────────────────────

def _sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def compute_input_hashes(out_dir: Path) -> dict[str, str | None]:
    return {name: _sha256_file(out_dir / name) for name in GUARDED_ARTIFACTS}


def verify_input_hashes(out_dir: Path, before: dict[str, str | None]) -> list[str]:
    """Return list of artifact names whose hash changed (or appeared/disappeared)."""
    changed = []
    for name, old_hash in before.items():
        new_hash = _sha256_file(out_dir / name)
        if old_hash != new_hash:
            changed.append(name)
    return changed


# ── Artifact loaders ──────────────────────────────────────────────────────────

def _load_json_safe(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("[packet_builder] failed to load %s: %s", path.name, e)
        return None


def _load_text_safe(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("[packet_builder] failed to read %s: %s", path.name, e)
        return None


# ── Token-safe C slicer ───────────────────────────────────────────────────────

def _extract_function_slice(
    c_source: str,
    function_name: str,
    max_lines: int = DEFAULT_MAX_SLICE_LINES,
) -> tuple[str, list[str]]:
    """
    Extract the body of *function_name* from *c_source* using a brace-counting
    state machine that ignores braces inside strings, char literals,
    block comments, and line comments.

    Returns (slice_text, diagnostics_list).
    Empty string slice is returned if:
      - function not found
      - state machine hits EOF without balanced close
    """
    diagnostics: list[str] = []

    # Find the function definition start heuristically.
    # We look for a pattern like: [return_type] function_name (...)  {
    # This is a best-effort regex; the state machine handles correctness.
    pattern = re.compile(
        r"(?:^|\n)(?:[a-zA-Z_][a-zA-Z0-9_\s\*]*?\s+)?"
        + re.escape(function_name)
        + r"\s*\([^)]*\)\s*\{",
        re.MULTILINE,
    )
    match = pattern.search(c_source)
    if not match:
        diagnostics.append(
            f"function_slice: '{function_name}' not found in C source"
        )
        return "", diagnostics

    # The match ends with '{' which is the opening brace of the body.
    body_start = match.end() - 1  # include the '{'

    # State machine
    depth = 0
    in_string = False
    in_char = False
    in_block_comment = False
    in_line_comment = False
    escape_next = False

    i = body_start
    n = len(c_source)

    while i < n:
        ch = c_source[i]

        # Escape inside string or char
        if escape_next:
            escape_next = False
            i += 1
            continue

        if ch == "\\" and (in_string or in_char):
            escape_next = True
            i += 1
            continue

        # End of line comment
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        # End of block comment
        if in_block_comment:
            if ch == "*" and i + 1 < n and c_source[i + 1] == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        # String start/end
        if in_string:
            if ch == '"':
                in_string = False
            i += 1
            continue

        # Char literal start/end
        if in_char:
            if ch == "'":
                in_char = False
            i += 1
            continue

        # New string
        if ch == '"':
            in_string = True
            i += 1
            continue

        # New char
        if ch == "'":
            in_char = True
            i += 1
            continue

        # Block comment start
        if ch == "/" and i + 1 < n and c_source[i + 1] == "*":
            in_block_comment = True
            i += 2
            continue

        # Line comment start
        if ch == "/" and i + 1 < n and c_source[i + 1] == "/":
            in_line_comment = True
            i += 2
            continue

        # Braces
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                # Found closing brace
                raw_slice = c_source[body_start : i + 1]
                lines = raw_slice.splitlines()
                if len(lines) > max_lines:
                    truncated = "\n".join(lines[:max_lines])
                    truncated += "\n" + SLICE_TRUNCATION_COMMENT.format(
                        max_lines=max_lines
                    )
                    diagnostics.append(
                        f"function_slice: '{function_name}' truncated at {max_lines} lines"
                    )
                    return truncated, diagnostics
                return raw_slice, diagnostics

        i += 1

    diagnostics.append(
        f"function_slice: '{function_name}' — unbalanced braces or truncated source"
    )
    return "", diagnostics


# ── Per-function behavior model lookup ───────────────────────────────────────

def _find_behavior_model_entry(
    behavior_model: dict | None, fn_name: str
) -> dict:
    if behavior_model is None:
        return {}
    for entry in behavior_model.get("functions", []):
        if entry.get("function") == fn_name or entry.get("name") == fn_name:
            return entry
    return {}


def _get_global_behavior(behavior_model: dict | None) -> list:
    if behavior_model is None:
        return []
    return behavior_model.get("global_behavior", [])


# ── Evidence slice lookup ─────────────────────────────────────────────────────

def _find_evidence_slice(evidence_index: dict | None, fn_name: str) -> dict:
    if evidence_index is None:
        return {}
    for entry in evidence_index.get("functions", []):
        if entry.get("function") == fn_name or entry.get("name") == fn_name:
            return entry
    # Fallback: look in top-level statements
    return {}


# ── Trace slice lookup ────────────────────────────────────────────────────────

def _find_trace_slice(trace_report: dict | None, fn_name: str) -> dict:
    if trace_report is None:
        return {}
    for entry in trace_report.get("functions", []):
        if entry.get("function") == fn_name or entry.get("name") == fn_name:
            return entry
    return {}


# ── Quality gate summary ──────────────────────────────────────────────────────

def _quality_gate_summary(quality_gate: dict | None) -> dict:
    if quality_gate is None:
        return {}
    return {
        "status": quality_gate.get("status", "unknown"),
        "decision": quality_gate.get("decision", {}),
        "summary": quality_gate.get("summary", {}),
    }


# ── Static summary from source_reconstruction ────────────────────────────────

def _static_summary(fn_record: dict) -> dict:
    return {
        "calls": fn_record.get("calls", []),
        "loops": fn_record.get("loops", 0),
        "conditions": fn_record.get("conditions", 0),
        "returns": fn_record.get("returns", 0),
        "returns_value": fn_record.get("returns_value", None),
        "return_type": fn_record.get("return_type", None),
        "params": fn_record.get("params", []),
        "layout_candidates": fn_record.get("layout_candidates", []),
    }


# ── Dynamic summary from behavior_profile ────────────────────────────────────

def _dynamic_summary(behavior_profile: dict | None) -> dict:
    if behavior_profile is None:
        return {"available": False}
    summary = behavior_profile.get("summary", {})
    return {
        "available": True,
        "binary_path": behavior_profile.get("binary_path", ""),
        "runs_total": summary.get("runs_total", 0),
        "argv_sensitive": summary.get("argv_sensitive", False),
        "stdout_varies": summary.get("stdout_varies", False),
        "stderr_varies": summary.get("stderr_varies", False),
        "crashes_observed": summary.get("crashes_observed", False),
        "timeouts_observed": summary.get("timeouts_observed", False),
        "distinct_exit_codes": summary.get("distinct_exit_codes", []),
        "observations": behavior_profile.get("observations", []),
    }


# ── Core packet builder ───────────────────────────────────────────────────────

def build_packet(
    fn_record: dict,
    out_dir: Path,
    *,
    recovered_c: str | None,
    recovered_readable_c: str | None,
    behavior_model: dict | None,
    behavior_profile: dict | None,
    evidence_index: dict | None,
    trace_report: dict | None,
    quality_gate: dict | None,
    max_slice_lines: int = DEFAULT_MAX_SLICE_LINES,
) -> tuple[dict, list[str]]:
    """
    Build one agent packet for a single function.

    Returns (packet_dict, diagnostics_list).
    Never raises — all slicing failures are recorded in diagnostics.
    """
    fn_name = fn_record.get("name") or fn_record.get("function", "unknown")
    entry_point = fn_record.get("entry_point") or fn_record.get("address", "")
    signature = fn_record.get("signature", "")

    all_diagnostics: list[str] = []

    # Try different lookup names in order to find the function in the C source
    lookup_names = []
    if fn_record.get("c_name"):
        lookup_names.append(fn_record["c_name"])
    if fn_record.get("canonical_name"):
        lookup_names.append(fn_record["canonical_name"])
    lookup_names.append(fn_name)
    if fn_name.startswith("_"):
        lookup_names.append(fn_name[1:])
    
    # De-duplicate while preserving order
    seen = set()
    lookup_names = [x for x in lookup_names if not (x in seen or seen.add(x))]

    def _slice_with_fallbacks(c_source: str, label: str) -> tuple[str, list[str]]:
        for name in lookup_names:
            # Check if the function pattern exists in the C source
            pattern = re.compile(
                r"(?:^|\n)(?:[a-zA-Z_][a-zA-Z0-9_\s\*]*?\s+)?"
                + re.escape(name)
                + r"\s*\([^)]*\)\s*\{",
                re.MULTILINE,
            )
            if pattern.search(c_source):
                return _extract_function_slice(c_source, name, max_slice_lines)
        # Final fallback call if none matched, to produce a diagnostic
        s, diag = _extract_function_slice(c_source, fn_name, max_slice_lines)
        return s, [f"function_slice: '{fn_name}' (tried {lookup_names}) not found in {label} source"]

    # C slices
    conservative_c = ""
    readable_c_slice = ""

    if recovered_c:
        slice_c, diag = _slice_with_fallbacks(recovered_c, "conservative C")
        conservative_c = slice_c
        all_diagnostics.extend(diag)

    if recovered_readable_c:
        slice_r, diag = _slice_with_fallbacks(recovered_readable_c, "readable C")
        readable_c_slice = slice_r
        all_diagnostics.extend(diag)

    packet: dict[str, Any] = {
        "schema_version": SCHEMA_AGENT_PACKET,
        "phase": "10.1",
        "function": fn_name,
        "entry_point": entry_point,
        "signature": signature,
        "conservative_c": conservative_c,
        "readable_c": readable_c_slice,
        "static_summary": _static_summary(fn_record),
        "dynamic_summary": _dynamic_summary(behavior_profile),
        "behavior_model_entry": _find_behavior_model_entry(behavior_model, fn_name),
        "global_behavior": _get_global_behavior(behavior_model),
        "evidence_slice": _find_evidence_slice(evidence_index, fn_name),
        "trace_slice": _find_trace_slice(trace_report, fn_name),
        "quality_gate_summary": _quality_gate_summary(quality_gate),
        "known_uncertainties": list(KNOWN_UNCERTAINTIES),
        "forbidden_claims": list(FORBIDDEN_CLAIMS),
        "diagnostics": all_diagnostics,
    }

    return packet, all_diagnostics


def build_all_packets(
    out_dir: Path,
    max_slice_lines: int = DEFAULT_MAX_SLICE_LINES,
) -> tuple[list[dict], list[str], dict[str, str | None]]:
    """
    Build agent packets for all functions in source_reconstruction.json.

    Returns (packets, global_diagnostics, input_hashes_before).
    The caller must verify hashes after writing to detect artifact mutations.
    """
    out_dir = out_dir.resolve()
    global_diagnostics: list[str] = []

    # Record hashes BEFORE any work
    hashes_before = compute_input_hashes(out_dir)

    # Load all artifacts
    source_recon    = _load_json_safe(out_dir / "source_reconstruction.json")
    behavior_model  = _load_json_safe(out_dir / "behavior_model.json")
    behavior_profile = _load_json_safe(out_dir / "behavior_profile.json")
    evidence_index  = _load_json_safe(out_dir / "evidence_index.json")
    trace_report    = _load_json_safe(out_dir / "trace_report.json")
    quality_gate    = _load_json_safe(out_dir / "quality_gate.json")
    recovered_c     = _load_text_safe(out_dir / "recovered.c")
    recovered_readable_c = _load_text_safe(out_dir / "recovered_readable.c")

    if source_recon is None:
        global_diagnostics.append(
            "source_reconstruction.json missing — no functions to packet"
        )
        return [], global_diagnostics, hashes_before

    functions = source_recon.get("data", {}).get("functions", []) or source_recon.get("functions", [])
    if not isinstance(functions, list):
        global_diagnostics.append("source_reconstruction.json has no functions list")
        return [], global_diagnostics, hashes_before

    packets: list[dict] = []
    for fn_record in functions:
        try:
            packet, diag = build_packet(
                fn_record,
                out_dir,
                recovered_c=recovered_c,
                recovered_readable_c=recovered_readable_c,
                behavior_model=behavior_model,
                behavior_profile=behavior_profile,
                evidence_index=evidence_index,
                trace_report=trace_report,
                quality_gate=quality_gate,
                max_slice_lines=max_slice_lines,
            )
            packets.append(packet)
            if diag:
                global_diagnostics.extend(diag)
        except Exception as e:
            fn_name = fn_record.get("name", "unknown")
            msg = f"packet_builder: exception for function '{fn_name}': {e}"
            logger.exception(msg)
            global_diagnostics.append(msg)

    logger.info(
        "[packet_builder] built %d packets for %d functions",
        len(packets), len(functions),
    )
    return packets, global_diagnostics, hashes_before
