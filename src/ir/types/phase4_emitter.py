# -*- coding: utf-8 -*-
"""
Phase 4D: Final Phase 4 Semantic Artifact Emitter

Writes the phase4_semantics.json artifact produced by the Phase 4D merger.

Schema version: 4D.0.0

Forbidden output keys (Phase 4D-created levels):
    confidence, overall_confidence, risk, similarity,
    source_similarity, semantic_similarity, source_code,
    c_source, structs, fields, expressions, statements
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from src.ir.types.phase4_semantics import Phase4SemanticsArtifact


# ---------------------------------------------------------------------------
# Provenance path normalization (consistent with Phase 4A/4B/4C policy)
# ---------------------------------------------------------------------------

def normalize_provenance_path(
    path: Optional[str],
    output_dir: Path,
) -> Optional[str]:
    """
    Normalize a provenance path to be relative to output_dir when inside it,
    or absolute otherwise.  Always returns a POSIX path string or None.
    """
    if not path:
        return None
    abs_path = Path(path).resolve()
    abs_out_dir = output_dir.resolve()
    try:
        relative = abs_path.relative_to(abs_out_dir)
        return relative.as_posix()
    except ValueError:
        return abs_path.as_posix()


# ---------------------------------------------------------------------------
# Artifact writer
# ---------------------------------------------------------------------------

def write_phase4_semantics_artifact(
    artifact: Phase4SemanticsArtifact,
    output_path: str,
    source_type_recovery: Optional[str] = None,
    source_semantic_recovery: Optional[str] = None,
    source_layout_recovery: Optional[str] = None,
) -> None:
    """
    Write the Phase 4D semantics artifact to disk.

    Parameters
    ----------
    artifact                : The merged Phase4SemanticsArtifact.
    output_path             : Absolute or relative path for phase4_semantics.json.
    source_type_recovery    : Path to type_recovery.json consumed (provenance).
    source_semantic_recovery: Path to semantic_recovery.json consumed, or None.
    source_layout_recovery  : Path to layout_recovery.json consumed, or None.
    """
    out_dir_path = Path(output_path).parent.resolve()

    # Update provenance with normalized paths
    payload = artifact.to_dict()

    if source_type_recovery:
        payload["provenance"]["source_type_recovery"] = (
            normalize_provenance_path(source_type_recovery, out_dir_path)
        )
    if source_semantic_recovery:
        payload["provenance"]["source_semantic_recovery"] = (
            normalize_provenance_path(source_semantic_recovery, out_dir_path)
        )
    if source_layout_recovery:
        payload["provenance"]["source_layout_recovery"] = (
            normalize_provenance_path(source_layout_recovery, out_dir_path)
        )

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
