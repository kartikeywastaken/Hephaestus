# -*- coding: utf-8 -*-
"""
Phase 11 — Agent-Assisted Source Generation: artifact loader.

Loads all inputs required and optional for Phase 11.
Computes and verifies SHA-256 hashes of guarded artifacts.
Enforces:
  - required artifacts exist (exit 1 if missing)
  - overwrite guard for recovered_agent.c (exit 1 unless --overwrite)
  - hash guard before and after (exit 2 if changed)
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from src.agent_source.models import GUARDED_ARTIFACTS

logger = logging.getLogger("agent_source.loader")


@dataclass
class Phase11Artifacts:
    """Container for all artifacts consumed by Phase 11."""
    # Required
    recovered_readable_c: str | None = None
    agent_suggestions: dict | None = None

    # Optional evidence
    recovered_c: str | None = None
    agent_debate_report: dict | None = None
    behavior_model: dict | None = None
    source_reconstruction: dict | None = None
    readability_report: dict | None = None
    quality_gate: dict | None = None
    trace_report: dict | None = None
    evidence_index: dict | None = None

    # Diagnostics
    missing_required: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── Hash guard ────────────────────────────────────────────────────────────────

def _sha256_file(path: Path) -> str | None:
    """Compute SHA-256 hex digest of a file, or None if missing."""
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


def compute_phase11_hashes(out_dir: Path) -> dict[str, str | None]:
    """Compute SHA-256 of each guarded artifact. Missing files → None."""
    return {name: _sha256_file(out_dir / name) for name in GUARDED_ARTIFACTS}


def verify_phase11_hashes(
    out_dir: Path, before: dict[str, str | None]
) -> list[str]:
    """Return list of artifact names whose hash changed (appeared/disappeared)."""
    changed = []
    for name, old_hash in before.items():
        new_hash = _sha256_file(out_dir / name)
        if old_hash != new_hash:
            changed.append(name)
    return changed


# ── Loaders ───────────────────────────────────────────────────────────────────

def _load_json(path: Path, name: str, missing: list[str]) -> dict | None:
    if not path.exists():
        missing.append(name)
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        missing.append(f"{name} (parse error: {e})")
        return None


def _load_text(path: Path, name: str, missing: list[str]) -> str | None:
    if not path.exists():
        missing.append(name)
        return None
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        missing.append(f"{name} (read error: {e})")
        return None


def load_phase11_artifacts(
    out_dir: Path,
    *,
    overwrite: bool = False,
) -> Phase11Artifacts:
    """
    Load all inputs for Phase 11.

    Parameters
    ----------
    out_dir:
        Directory containing Hephaestus artifacts.
    overwrite:
        If False and recovered_agent.c already exists, records it in warnings.
        The CLI enforces the exit-code; loader just records the state.

    Returns
    -------
    Phase11Artifacts
    """
    arts = Phase11Artifacts()

    # Overwrite guard
    recovered_agent_path = out_dir / "recovered_agent.c"
    if recovered_agent_path.exists() and not overwrite:
        arts.warnings.append(
            "recovered_agent.c already exists. Pass --overwrite to regenerate."
        )

    # Required artifacts
    arts.recovered_readable_c = _load_text(
        out_dir / "recovered_readable.c", "recovered_readable.c", arts.missing_required
    )
    arts.agent_suggestions = _load_json(
        out_dir / "agent_suggestions.json", "agent_suggestions.json", arts.missing_required
    )

    # Optional evidence artifacts
    arts.recovered_c = _load_text(
        out_dir / "recovered.c", "recovered.c", arts.missing_optional
    )
    arts.agent_debate_report = _load_json(
        out_dir / "agent_debate_report.json", "agent_debate_report.json", arts.missing_optional
    )
    arts.behavior_model = _load_json(
        out_dir / "behavior_model.json", "behavior_model.json", arts.missing_optional
    )
    arts.source_reconstruction = _load_json(
        out_dir / "source_reconstruction.json", "source_reconstruction.json", arts.missing_optional
    )
    arts.readability_report = _load_json(
        out_dir / "readability_report.json", "readability_report.json", arts.missing_optional
    )
    arts.quality_gate = _load_json(
        out_dir / "quality_gate.json", "quality_gate.json", arts.missing_optional
    )
    arts.trace_report = _load_json(
        out_dir / "trace_report.json", "trace_report.json", arts.missing_optional
    )
    arts.evidence_index = _load_json(
        out_dir / "evidence_index.json", "evidence_index.json", arts.missing_optional
    )

    if arts.missing_optional:
        arts.warnings.append(
            f"Optional artifacts missing (proceeding with available evidence): "
            f"{', '.join(arts.missing_optional)}"
        )

    return arts
