# -*- coding: utf-8 -*-
"""
Phase 8 — Dynamic Behavior Capture: artifact writer.

Writes all Phase 8 artifacts deterministically.
Does not touch any static artifact.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

from src.dynamic.models import (
    SCHEMA_DYNAMIC_INPUTS_RESOLVED,
    SCHEMA_DYNAMIC_RUNS,
    SCHEMA_BEHAVIOR_PROFILE,
    SCHEMA_DYNAMIC_REPORT,
)


def _now_iso() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=False)
        f.write("\n")


# ---------------------------------------------------------------------------
# Individual writers
# ---------------------------------------------------------------------------

def write_dynamic_inputs_resolved(
    spec: dict,
    binary_path: str,
    out_dir: Path,
    *,
    using_default: bool = False,
) -> Path:
    """Write dynamic_inputs.resolved.json."""
    runs = spec.get("runs", [])
    payload = {
        "schema_version": SCHEMA_DYNAMIC_INPUTS_RESOLVED,
        "phase": "8.0",
        "generated_at": _now_iso(),
        "binary_path": str(binary_path),
        "using_default_inputs": using_default,
        "runs_total": len(runs),
        "runs": runs,
    }
    path = out_dir / "dynamic_inputs.resolved.json"
    _write_json(path, payload)
    return path


def write_dynamic_runs(
    results: list[dict],
    binary_path: str,
    binary_sha256: str,
    timeout_s: float,
    out_dir: Path,
) -> Path:
    """Write dynamic_runs.json."""
    runs_completed = sum(1 for r in results if r.get("status") == "ok")
    runs_timed_out = sum(1 for r in results if r.get("timed_out"))
    runs_crashed = sum(1 for r in results if r.get("signal") is not None)

    payload = {
        "schema_version": SCHEMA_DYNAMIC_RUNS,
        "phase": "8.0",
        "generated_at": _now_iso(),
        "binary_path": str(binary_path),
        "binary_sha256": binary_sha256,
        "timeout_s": timeout_s,
        "runs_total": len(results),
        "runs_completed": runs_completed,
        "runs_timed_out": runs_timed_out,
        "runs_crashed": runs_crashed,
        "runs": results,
        "diagnostics": [],
    }
    path = out_dir / "dynamic_runs.json"
    _write_json(path, payload)
    return path


def write_behavior_profile(profile: dict, out_dir: Path) -> Path:
    """Write behavior_profile.json."""
    path = out_dir / "behavior_profile.json"
    _write_json(path, profile)
    return path


def write_dynamic_report(
    status: str,
    artifacts: dict[str, str],
    diagnostics: list[str],
    warnings: list[str],
    out_dir: Path,
    *,
    using_default_inputs: bool = False,
) -> Path:
    """Write dynamic_report.json."""
    payload = {
        "schema_version": SCHEMA_DYNAMIC_REPORT,
        "phase": "8.0",
        "generated_at": _now_iso(),
        "status": status,
        "using_default_inputs": using_default_inputs,
        "diagnostics": diagnostics,
        "warnings": warnings,
        "artifacts": artifacts,
    }
    path = out_dir / "dynamic_report.json"
    _write_json(path, payload)
    return path
