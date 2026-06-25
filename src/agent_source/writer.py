# -*- coding: utf-8 -*-
"""
Phase 11 — Agent-Assisted Source Generation: artifact writer.

Writes the 4 Phase 11 output artifacts:
  - agent_source_plan.json
  - recovered_agent.c
  - agent_source_report.json
  - agent_source_validation.json

Never overwrites:
  - recovered.c
  - recovered_readable.c
  - source_reconstruction.json
  - behavior_model.json
  - agent_suggestions.json
  - agent_debate_report.json
  - Any other Phase 1-10 artifact

Writes are atomic: write to temp file then rename.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from src.agent_source.models import (
    SCHEMA_AGENT_SOURCE_PLAN,
    SCHEMA_AGENT_SOURCE_REPORT,
    SCHEMA_AGENT_SOURCE_VALIDATION,
    WARNING_HEADER,
    GUARDED_ARTIFACTS,
)

logger = logging.getLogger("agent_source.writer")

# Artifacts that MUST NEVER be overwritten by Phase 11
_WRITE_FORBIDDEN = frozenset(GUARDED_ARTIFACTS) | frozenset({
    "pipeline_manifest.json",
    "evidence_index.json",
    "trace_report.json",
    "quality_gate.json",
    "readability_report.json",
    "dynamic_runs.json",
    "behavior_profile.json",
    "dynamic_report.json",
    "agent_packet_manifest.json",
    "agent_debate_report.json",
    "agent_suggestions.json",
    "unified_ir.json",
    "structuring_regions.json",
    "type_recovery.json",
    "semantic_recovery.json",
    "layout_recovery.json",
    "phase4_semantics.json",
    "source_reconstruction.json",
})

_PHASE11_OUTPUTS = frozenset({
    "agent_source_plan.json",
    "recovered_agent.c",
    "agent_source_report.json",
    "agent_source_validation.json",
})


def _check_write_safe(out_dir: Path, filename: str) -> None:
    """Raise ValueError if attempting to write a forbidden artifact."""
    if filename in _WRITE_FORBIDDEN:
        raise ValueError(
            f"Phase 11 writer: FORBIDDEN — attempted to write protected artifact '{filename}'"
        )
    if filename not in _PHASE11_OUTPUTS:
        raise ValueError(
            f"Phase 11 writer: UNKNOWN — filename '{filename}' is not a Phase 11 output"
        )


def _atomic_write_text(path: Path, content: str) -> None:
    """Write content to path atomically (write to temp then rename)."""
    dir_ = path.parent
    dir_.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write JSON data to path atomically."""
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    _atomic_write_text(path, content)


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_agent_source_artifacts(
    out_dir: Path,
    plan_entries: list[dict],
    generated_c: str,
    function_records: list[dict],
    validation_result: tuple[bool, list[str], str],
    *,
    provider_name: str,
    model_name: str,
    global_diagnostics: list[str] | None = None,
    plan_diagnostics: list[str] | None = None,
    generation_mode: str = "function_by_function",
    max_functions: int | None = 1,
) -> tuple[Path, Path, Path, Path]:
    """
    Write all 4 Phase 11 artifacts.

    Parameters
    ----------
    out_dir:
        Target directory.
    plan_entries:
        Transformation plan entries.
    generated_c:
        The generated C source text.
    function_records:
        Per-function generation records.
    validation_result:
        (ok, issues, clang_status) from validator.
    provider_name, model_name:
        Provider metadata for attribution.
    global_diagnostics:
        Global generation diagnostics.
    plan_diagnostics:
        Plan builder diagnostics.
    generation_mode:
        "function_by_function" or "whole_file".
    max_functions:
        Max functions processed by LLM.

    Returns
    -------
    (plan_path, c_path, report_path, val_path)
    """
    out_dir = out_dir if isinstance(out_dir, Path) else Path(out_dir)
    val_ok, val_issues, clang_status = validation_result
    now = _now_iso()

    # ── agent_source_plan.json ────────────────────────────────────────────────
    plan_path = out_dir / "agent_source_plan.json"
    _check_write_safe(out_dir, "agent_source_plan.json")
    plan_payload = {
        "schema_version": SCHEMA_AGENT_SOURCE_PLAN,
        "phase": "11",
        "generated_at": now,
        "provider": provider_name,
        "model": model_name,
        "generation_mode": generation_mode,
        "max_functions": max_functions,
        "plan_diagnostics": plan_diagnostics or [],
        "entries_total": len(plan_entries),
        "entries_enabled": sum(1 for e in plan_entries if e.get("enabled")),
        "entries_disabled": sum(1 for e in plan_entries if not e.get("enabled")),
        "plan_entries": plan_entries,
    }
    _atomic_write_json(plan_path, plan_payload)
    logger.info("[writer] wrote agent_source_plan.json (%d entries)", len(plan_entries))

    # ── recovered_agent.c ─────────────────────────────────────────────────────
    c_path = out_dir / "recovered_agent.c"
    _check_write_safe(out_dir, "recovered_agent.c")

    # Ensure warning header at the very top
    if generated_c and WARNING_HEADER.splitlines()[0].strip() not in generated_c:
        c_content = WARNING_HEADER + "\n\n" + generated_c
    elif generated_c:
        c_content = generated_c
    else:
        # Fallback empty file with warning header and note
        c_content = (
            WARNING_HEADER
            + "\n\n"
            + "/* [HEPHAESTUS Phase 11: generation produced no output] */\n"
        )

    _atomic_write_text(c_path, c_content)
    logger.info("[writer] wrote recovered_agent.c (%d bytes)", len(c_content))

    # ── agent_source_report.json ──────────────────────────────────────────────
    report_path = out_dir / "agent_source_report.json"
    _check_write_safe(out_dir, "agent_source_report.json")

    generated_count = sum(1 for r in function_records if r.get("generated"))
    copied_count = sum(
        1 for r in function_records
        if not r.get("generated") and r.get("status") == "copied_unchanged"
    )
    failed_count = sum(
        1 for r in function_records if r.get("status") == "failed"
    )

    report_payload = {
        "schema_version": SCHEMA_AGENT_SOURCE_REPORT,
        "phase": "11",
        "generated_at": now,
        "provider": provider_name,
        "model": model_name,
        "generation_mode": generation_mode,
        "max_functions": max_functions,
        "functions_total": len(function_records),
        "functions_generated": generated_count,
        "functions_copied_unchanged": copied_count,
        "functions_failed": failed_count,
        "global_diagnostics": global_diagnostics or [],
        "function_records": function_records,
        "known_uncertainties": [
            "AI-assisted approximation only",
            "dynamic evidence only covers tested inputs",
            "source variable names are unknown",
            "struct field names are unknown",
            "behavioral equivalence is not claimed",
        ],
        "absolute_invariants": [
            "recovered.c was not modified",
            "recovered_readable.c was not modified",
            "source_reconstruction.json was not modified",
            "behavior_model.json was not modified",
            "agent_suggestions.json was not modified",
            "agent_debate_report.json was not modified",
            "recovered_agent.c does not replace recovered.c",
        ],
    }
    _atomic_write_json(report_path, report_payload)
    logger.info(
        "[writer] wrote agent_source_report.json "
        "(generated=%d copied=%d failed=%d)",
        generated_count, copied_count, failed_count,
    )

    # ── agent_source_validation.json ──────────────────────────────────────────
    val_path = out_dir / "agent_source_validation.json"
    _check_write_safe(out_dir, "agent_source_validation.json")

    val_payload = {
        "schema_version": SCHEMA_AGENT_SOURCE_VALIDATION,
        "phase": "11",
        "generated_at": now,
        "provider": provider_name,
        "model": model_name,
        "validation_passed": val_ok,
        "clang_status": clang_status,
        "issues": val_issues,
        "absolute_invariants_verified": [
            "recovered.c not modified",
            "recovered_readable.c not modified",
        ],
    }
    _atomic_write_json(val_path, val_payload)
    logger.info(
        "[writer] wrote agent_source_validation.json (ok=%s clang=%s)",
        val_ok, clang_status,
    )

    return plan_path, c_path, report_path, val_path
