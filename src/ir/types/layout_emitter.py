# -*- coding: utf-8 -*-
"""
Phase 4C: Layout Recovery Artifact Emitter

Writes the layout_recovery.json artifact produced by the Phase 4C engine.

Schema version: 4C.0.0

Output schema
-------------
{
  "schema_version": "4C.0.0",
  "provenance": {
    "phase": "4C",
    "description": "Conservative data layout recovery",
    "source_ir": "<relative-or-absolute POSIX path>"
  },
  "data": {
    "layout_candidates": [ ... ],
    "unbound_memory_accesses": [ ... ]
  }
}

Forbidden keys
--------------
The output MUST NOT contain:
  structs, fields, c_source, expressions, statements, source_code,
  confidence, similarity
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.ir.types.layouts import LayoutCandidate, MemoryAccessFact
from src.utils.artifact_io import normalize_provenance_path, write_json_artifact


SCHEMA_VERSION = "4C.0.0"


# ---------------------------------------------------------------------------
# Artifact writer
# ---------------------------------------------------------------------------

def write_layout_recovery_artifact(
    candidates: List[LayoutCandidate],
    unbound: List[MemoryAccessFact],
    output_path: str,
    source_ir: Optional[str] = None,
) -> None:
    """
    Write the Phase 4C layout recovery artifact to disk.

    Parameters
    ----------
    candidates   : List of LayoutCandidate objects.
    unbound      : List of MemoryAccessFacts with unresolved offsets.
    output_path  : Absolute or relative path for layout_recovery.json.
    source_ir    : Path to unified_ir.json consumed (provenance).
    """
    out_dir_path = Path(output_path).parent.resolve()

    if source_ir is None:
        source_ir = str(out_dir_path / "unified_ir.json")

    norm_ir = normalize_provenance_path(source_ir, out_dir_path)

    payload: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "provenance": {
            "phase": "4C",
            "description": "Conservative data layout recovery",
            "source_ir": norm_ir,
        },
        "data": {
            "layout_candidates": [c.to_dict() for c in candidates],
            "unbound_memory_accesses": [f.to_dict() for f in unbound],
        },
    }

    write_json_artifact(output_path, payload)

