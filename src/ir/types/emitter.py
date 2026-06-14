# -*- coding: utf-8 -*-
"""
Phase 4A: Type Recovery Artifact Emitter

Writes the type_recovery.json artifact in a deterministic, stable schema.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.ir.types.models import RecoveredFunctionSemantics
from src.utils.artifact_io import normalize_provenance_path, write_json_artifact


SCHEMA_VERSION = "4A.0.0"


def write_type_recovery_artifact(
    functions: List[RecoveredFunctionSemantics],
    output_path: str,
    source_ir: Optional[str] = None,
    source_structuring: Optional[str] = None,
) -> None:
    """
    Write the Phase 4A type recovery artifact to disk.

    Serialization properties:
    - indent=2
    - sort_keys=False (preserve insertion order)
    - stable function order (same as input list order)
    - stable variable order per function
    - stable parameter order per function

    Parameters
    ----------
    functions         : List of recovered function semantic records.
    output_path       : Absolute or relative file path to write to.
    source_ir         : Path of the Unified IR that was consumed (provenance only).
    source_structuring: Path of the structuring regions file consumed, or None.
    """
    out_dir_path = Path(output_path).parent.resolve()
    out_dir = str(out_dir_path)

    if source_ir is None:
        source_ir = os.path.join(out_dir, "unified_ir.json")
    if source_structuring is None:
        possible_structuring = os.path.join(out_dir, "structuring_regions.json")
        if os.path.exists(possible_structuring):
            source_structuring = possible_structuring

    norm_source_ir = normalize_provenance_path(source_ir, out_dir_path)
    norm_source_structuring = normalize_provenance_path(source_structuring, out_dir_path)

    payload: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "provenance": {
            "phase": "4A",
            "description": "Signature and variable recovery backbone",
            "source_ir": norm_source_ir,
            "source_structuring": norm_source_structuring,
        },
        "data": {
            "functions": [f.to_dict() for f in functions],
        },
    }

    write_json_artifact(output_path, payload)
