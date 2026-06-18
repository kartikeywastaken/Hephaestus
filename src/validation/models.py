# -*- coding: utf-8 -*-
"""
Validation Data Models
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ValidationArtifacts:
    out_dir: Path
    source_reconstruction: dict | None
    recovered_c: str | None
    pipeline_manifest: dict | None
    unified_ir: dict | None
    phase4_semantics: dict | None
    missing: list[str]
    evidence_index: dict | None = None

