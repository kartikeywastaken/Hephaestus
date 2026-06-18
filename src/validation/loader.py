# -*- coding: utf-8 -*-
"""
Validation Artifact Loader
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from src.validation.models import ValidationArtifacts

def load_validation_artifacts(out_dir: str | Path) -> ValidationArtifacts:
    """
    Load required and recommended artifacts from out_dir.
    Does not raise exceptions on missing recommended artifacts.
    """
    out_path = Path(out_dir).resolve()
    
    source_reconstruction = None
    recovered_c = None
    pipeline_manifest = None
    unified_ir = None
    phase4_semantics = None
    missing: list[str] = []
    
    # Required files
    recon_file = out_path / "source_reconstruction.json"
    if recon_file.exists():
        try:
            with open(recon_file, "r", encoding="utf-8") as f:
                source_reconstruction = json.load(f)
        except Exception:
            missing.append("source_reconstruction.json")
    else:
        missing.append("source_reconstruction.json")
        
    c_file = out_path / "recovered.c"
    if c_file.exists():
        try:
            with open(c_file, "r", encoding="utf-8") as f:
                recovered_c = f.read()
        except Exception:
            missing.append("recovered.c")
    else:
        missing.append("recovered.c")
        
    # Recommended files
    manifest_file = out_path / "pipeline_manifest.json"
    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                pipeline_manifest = json.load(f)
        except Exception:
            missing.append("pipeline_manifest.json")
    else:
        missing.append("pipeline_manifest.json")
        
    ir_file = out_path / "unified_ir.json"
    if ir_file.exists():
        try:
            with open(ir_file, "r", encoding="utf-8") as f:
                unified_ir = json.load(f)
        except Exception:
            missing.append("unified_ir.json")
    else:
        missing.append("unified_ir.json")
        
    sem_file = out_path / "phase4_semantics.json"
    if sem_file.exists():
        try:
            with open(sem_file, "r", encoding="utf-8") as f:
                phase4_semantics = json.load(f)
        except Exception:
            missing.append("phase4_semantics.json")
    else:
        missing.append("phase4_semantics.json")
        
    evidence_index = None
    ev_file = out_path / "evidence_index.json"
    if ev_file.exists():
        try:
            with open(ev_file, "r", encoding="utf-8") as f:
                evidence_index = json.load(f)
        except Exception:
            missing.append("evidence_index.json")
    else:
        missing.append("evidence_index.json")
        
    trace_report = None
    tr_file = out_path / "trace_report.json"
    if tr_file.exists():
        try:
            with open(tr_file, "r", encoding="utf-8") as f:
                trace_report = json.load(f)
        except Exception:
            missing.append("trace_report.json")
    else:
        missing.append("trace_report.json")
        
    return ValidationArtifacts(
        out_dir=out_path,
        source_reconstruction=source_reconstruction,
        recovered_c=recovered_c,
        pipeline_manifest=pipeline_manifest,
        unified_ir=unified_ir,
        phase4_semantics=phase4_semantics,
        missing=missing,
        evidence_index=evidence_index,
        trace_report=trace_report
    )


