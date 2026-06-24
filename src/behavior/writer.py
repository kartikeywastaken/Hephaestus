# -*- coding: utf-8 -*-
"""
Phase 9 — Static-Dynamic Behavior Fusion: artifact writer.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

from src.behavior.models import SCHEMA_BEHAVIOR_FUSION_REPORT


def _now_iso() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=False)
        f.write("\n")


def write_behavior_model(model: dict, out_dir: Path) -> Path:
    """Write behavior_model.json."""
    path = out_dir / "behavior_model.json"
    _write_json(path, model)
    return path


def write_behavior_fusion_report(
    status: str,
    artifacts: dict[str, str],
    diagnostics: list[str],
    warnings: list[str],
    out_dir: Path,
) -> Path:
    """Write behavior_fusion_report.json."""
    payload = {
        "schema_version": SCHEMA_BEHAVIOR_FUSION_REPORT,
        "phase": "9.0",
        "generated_at": _now_iso(),
        "status": status,
        "diagnostics": diagnostics,
        "warnings": warnings,
        "artifacts": artifacts,
    }
    path = out_dir / "behavior_fusion_report.json"
    _write_json(path, payload)
    return path
