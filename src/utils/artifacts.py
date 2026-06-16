# -*- coding: utf-8 -*-
"""
Artifact Path Management and Cleanup Utility
"""

from __future__ import annotations
import os
import shutil
from pathlib import Path

KNOWN_ARTIFACT_FILES = {
    "run.log",
    "pipeline_manifest.json",
    "ghidra_extraction.json",
    "radare2_extraction.json",
    "unified_ir.json",
    "structuring_analysis.json",
    "structuring_regions.json",
    "type_recovery.json",
    "semantic_recovery.json",
    "layout_recovery.json",
    "phase4_semantics.json",
    "source_reconstruction.json",
    "recovered.c",
    "stress_report.json",
    "stress_manifest.json",
}

KNOWN_ARTIFACT_DIRS = {
    "ghidra_temp_proj",
}

def ensure_out_dir(out_dir: str | Path) -> Path:
    """
    Create out_dir if needed and return resolved Path.
    """
    p = Path(out_dir).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p

def artifact_path(out_dir: str | Path, name: str) -> Path:
    """
    Return path under out_dir for a known artifact name.
    Reject path traversal.
    """
    if name not in KNOWN_ARTIFACT_FILES:
        raise ValueError(f"Unknown artifact name: {name}")
    base = Path(out_dir).resolve()
    resolved = (base / name).resolve()
    try:
        # Check if the resolved path is inside base
        resolved.relative_to(base)
    except ValueError:
        raise ValueError(f"Path traversal detected for name: {name}")
    return resolved

def clean_known_artifacts(out_dir: str | Path) -> list[str]:
    """
    Delete only known Hephaestus-generated files and directories inside out_dir.
    Do not delete arbitrary user files.
    Return list of deleted item names.
    """
    base = Path(out_dir).resolve()
    deleted = []
    if not base.exists():
        return deleted
    for name in KNOWN_ARTIFACT_FILES:
        file_path = base / name
        if file_path.is_file() or file_path.is_symlink():
            try:
                # Security sanity check
                file_path.resolve().relative_to(base)
                file_path.unlink()
                deleted.append(name)
            except Exception:
                pass
                
    for dir_name in KNOWN_ARTIFACT_DIRS:
        dir_path = base / dir_name
        if dir_path.is_dir() and not dir_path.is_symlink():
            try:
                # Security sanity check
                dir_path.resolve().relative_to(base)
                shutil.rmtree(dir_path)
                deleted.append(dir_name)
            except Exception:
                pass
                
    return sorted(deleted)
