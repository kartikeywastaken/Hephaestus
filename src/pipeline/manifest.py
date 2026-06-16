# -*- coding: utf-8 -*-
"""
Pipeline Manifest Generation Layer
"""

from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone

def now_iso() -> str:
    """Return current ISO 8601 UTC time string with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def start_manifest(input_binary: str, out_dir: str) -> dict:
    """Initialize a pipeline manifest dictionary."""
    return {
        "schema_version": "pipeline-1.0",
        "tool": "hephaestus",
        "phase": "5.8",
        "input_binary": str(input_binary),
        "out_dir": str(out_dir),
        "started_at": now_iso(),
        "finished_at": None,
        "status": "ok",
        "stages": [],
        "final_outputs": {},
        "summary": {}
    }

def record_stage(
    manifest: dict,
    name: str,
    status: str,
    outputs: list[str] | None = None,
    error: str | None = None,
    metrics: dict | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    duration_ms: int | None = None,
) -> None:
    """Append execution details for a pipeline stage."""
    manifest["stages"].append({
        "name": name,
        "status": status,
        "started_at": started_at or now_iso(),
        "finished_at": finished_at or now_iso(),
        "duration_ms": duration_ms or 0,
        "outputs": outputs or [],
        "metrics": metrics or {},
        "error": error
    })

def finalize_manifest(
    manifest: dict,
    status: str,
    summary: dict | None = None,
    final_outputs: dict | None = None,
) -> dict:
    """Finalize the manifest status, timing, outputs, and summary."""
    manifest["status"] = status
    manifest["finished_at"] = now_iso()
    manifest["summary"] = summary or {}
    manifest["final_outputs"] = final_outputs or {}
    return manifest

def write_manifest(manifest: dict, out_dir: str | Path) -> Path:
    """Serialize the manifest to pipeline_manifest.json inside out_dir."""
    from src.utils.artifacts import artifact_path, ensure_out_dir
    ensure_out_dir(out_dir)
    path = artifact_path(out_dir, "pipeline_manifest.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return path
