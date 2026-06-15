# -*- coding: utf-8 -*-
"""
Phase 5.1: Source Reconstruction Artifact Emitter

Writes the source_reconstruction.json artifact produced by the Phase 5.1
source reconstruction builder.

Schema version: 5.1.0

Provenance paths follow the same conventions as all Phase 4 emitters:
- Paths inside the output directory are stored as relative POSIX paths.
- Paths outside the output directory are stored as absolute POSIX paths.
- None values are stored as JSON null.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from src.ir.source.models import SourceReconstructionArtifact
from src.utils.artifact_io import normalize_provenance_path, write_json_artifact


# ---------------------------------------------------------------------------
# Artifact writer
# ---------------------------------------------------------------------------

def write_source_reconstruction_artifact(
    artifact: SourceReconstructionArtifact,
    output_path: str,
    source_ir: Optional[str] = None,
    source_structuring: Optional[str] = None,
    source_semantics: Optional[str] = None,
    source_layout: Optional[str] = None,
) -> None:
    """
    Write the Phase 5.1 source reconstruction artifact to disk.

    Parameters
    ----------
    artifact          : The SourceReconstructionArtifact to serialize.
    output_path       : Absolute or relative path for source_reconstruction.json.
    source_ir         : Path to unified_ir.json consumed (provenance).
    source_structuring: Path to structuring_regions.json consumed (provenance).
    source_semantics  : Path to phase4_semantics.json consumed (provenance).
    source_layout     : Path to layout_recovery.json consumed, or None.
    """
    out_dir_path = Path(output_path).parent.resolve()
    out_dir_str = str(out_dir_path)

    # Default provenance paths to sibling files in the same output directory
    if source_ir is None:
        source_ir = os.path.join(out_dir_str, "unified_ir.json")
    if source_structuring is None:
        candidate = os.path.join(out_dir_str, "structuring_regions.json")
        if os.path.exists(candidate):
            source_structuring = candidate
    if source_semantics is None:
        source_semantics = os.path.join(out_dir_str, "phase4_semantics.json")

    # Normalize provenance paths
    norm_ir = normalize_provenance_path(source_ir, out_dir_path)
    norm_st = normalize_provenance_path(source_structuring, out_dir_path)
    norm_sem = normalize_provenance_path(source_semantics, out_dir_path)
    norm_lay = normalize_provenance_path(source_layout, out_dir_path)

    # Attach provenance to artifact
    artifact.provenance = {
        "phase": "5.5",
        "description": "Conservative source reconstruction with branch predicate annotation",
        "source_ir": norm_ir,
        "source_structuring": norm_st,
        "source_semantics": norm_sem,
        "source_layout": norm_lay,
    }

    write_json_artifact(output_path, artifact.to_dict())
