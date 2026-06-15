# -*- coding: utf-8 -*-
"""
Phase 4B: Semantic Recovery Artifact Emitter

Writes the semantic_recovery.json artifact produced by the Phase 4B type
constraint refinement engine.

Schema version: 4B.0.0

Provenance paths:
- Paths inside the resolved output directory are stored as relative POSIX paths.
- Paths outside the output directory are stored as absolute POSIX paths.
- All paths use .as_posix() for forward-slash formatting.
- None values are stored as JSON null.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.ir.types.models import RefinedFunctionRecord
from src.utils.artifact_io import normalize_provenance_path, write_json_artifact


SCHEMA_VERSION = "4B.2.0"


# ---------------------------------------------------------------------------
# Artifact writer
# ---------------------------------------------------------------------------

def write_semantic_recovery_artifact(
    results: List[RefinedFunctionRecord],
    output_path: str,
    source_ir: Optional[str] = None,
    source_type_recovery: Optional[str] = None,
    source_structuring: Optional[str] = None,
) -> None:
    """
    Write the Phase 4B semantic recovery artifact to disk.

    Parameters
    ----------
    results              : List of RefinedFunctionRecord objects.
    output_path          : Absolute or relative path for semantic_recovery.json.
    source_ir            : Path to unified_ir.json consumed (provenance).
    source_type_recovery : Path to type_recovery.json consumed (provenance).
    source_structuring   : Path to structuring_regions.json consumed, or None.
    """
    out_dir_path = Path(output_path).parent.resolve()
    out_dir_str = str(out_dir_path)

    # Default provenance paths to sibling files in the same output directory
    if source_ir is None:
        source_ir = os.path.join(out_dir_str, "unified_ir.json")
    if source_type_recovery is None:
        source_type_recovery = os.path.join(out_dir_str, "type_recovery.json")
    if source_structuring is None:
        candidate = os.path.join(out_dir_str, "structuring_regions.json")
        if os.path.exists(candidate):
            source_structuring = candidate

    # Normalize
    norm_ir = normalize_provenance_path(source_ir, out_dir_path)
    norm_tr = normalize_provenance_path(source_type_recovery, out_dir_path)
    norm_st = normalize_provenance_path(source_structuring, out_dir_path)

    payload: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "provenance": {
            "phase": "4B",
            "description": "Type constraint refinement engine",
            "source_ir": norm_ir,
            "source_type_recovery": norm_tr,
            "source_structuring": norm_st,
        },
        "data": {
            "functions": [r.to_dict() for r in results],
        },
    }

    write_json_artifact(output_path, payload)

