# -*- coding: utf-8 -*-
"""
Phase 9 — Static-Dynamic Behavior Fusion: artifact loader.

Loads static and dynamic artifacts from out_dir.
Missing optional artifacts produce warnings, not errors.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BehaviorArtifacts:
    """Container for all artifacts consumed by Phase 9 fusion."""
    # Static artifacts
    source_reconstruction: dict | None = None
    readability_report:    dict | None = None
    phase4_semantics:      dict | None = None
    type_recovery:         dict | None = None
    layout_recovery:       dict | None = None
    unified_ir:            dict | None = None
    # Dynamic artifacts (Phase 8)
    behavior_profile:      dict | None = None
    dynamic_runs:          dict | None = None
    dynamic_report:        dict | None = None
    # Diagnostics / availability
    missing_static:  list[str] = field(default_factory=list)
    missing_dynamic: list[str] = field(default_factory=list)
    warnings:        list[str] = field(default_factory=list)


def _try_load(path: Path, name: str, container: list) -> dict | None:
    """Try to load a JSON file. Append name to container if missing."""
    if not path.exists():
        container.append(name)
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        container.append(f"{name} (parse error: {e})")
        return None


def load_behavior_artifacts(
    out_dir: Path,
    *,
    require_dynamic: bool = False,
) -> BehaviorArtifacts:
    """
    Load all available static and dynamic artifacts from out_dir.

    If require_dynamic=True and dynamic artifacts are missing, raises RuntimeError.
    Otherwise, records missing artifacts as warnings.
    """
    arts = BehaviorArtifacts()

    # Static
    arts.source_reconstruction = _try_load(
        out_dir / "source_reconstruction.json", "source_reconstruction.json", arts.missing_static
    )
    arts.readability_report = _try_load(
        out_dir / "readability_report.json", "readability_report.json", arts.missing_static
    )
    arts.phase4_semantics = _try_load(
        out_dir / "phase4_semantics.json", "phase4_semantics.json", arts.missing_static
    )
    arts.type_recovery = _try_load(
        out_dir / "type_recovery.json", "type_recovery.json", arts.missing_static
    )
    arts.layout_recovery = _try_load(
        out_dir / "layout_recovery.json", "layout_recovery.json", arts.missing_static
    )
    arts.unified_ir = _try_load(
        out_dir / "unified_ir.json", "unified_ir.json", arts.missing_static
    )

    # Dynamic
    arts.behavior_profile = _try_load(
        out_dir / "behavior_profile.json", "behavior_profile.json", arts.missing_dynamic
    )
    arts.dynamic_runs = _try_load(
        out_dir / "dynamic_runs.json", "dynamic_runs.json", arts.missing_dynamic
    )
    arts.dynamic_report = _try_load(
        out_dir / "dynamic_report.json", "dynamic_report.json", arts.missing_dynamic
    )

    # Warn or raise about missing dynamic
    if arts.missing_dynamic:
        msg = (
            f"Dynamic artifacts missing: {', '.join(arts.missing_dynamic)}. "
            f"Fusion will be static-only."
        )
        if require_dynamic:
            raise RuntimeError(msg)
        arts.warnings.append(msg)

    if arts.missing_static:
        arts.warnings.append(
            f"Static artifacts missing: {', '.join(arts.missing_static)}. "
            f"Fusion may be incomplete."
        )

    return arts
