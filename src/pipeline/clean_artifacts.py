# -*- coding: utf-8 -*-
"""
Artifact Cleanup Utility
"""

from __future__ import annotations
import shutil
import logging
from pathlib import Path

logger = logging.getLogger("reconstruct.cleanup")

KNOWN_GENERATED_FILES = {
    "recovered.c",
    "recovered_readable.c",
    "recovered_agent.c",
    "hephaestus_report.json",
    "hephaestus.log",
    "run.log",
    "manifest.json",
    # Legacy files
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
    "stress_report.json",
    "validation_report.json",
    "validation.log",
    "evidence_index.json",
    "trace_report.json",
    "trace_report.md",
    "quality_gate.json",
    "quality_gate.md",
    "readability_report.json",
    "readability_report.md",
    "dynamic_inputs.resolved.json",
    "dynamic_runs.json",
    "behavior_profile.json",
    "dynamic_report.json",
    "behavior_model.json",
    "behavior_fusion_report.json",
    "agent_packet_manifest.json",
    "agent_packet_optimization_report.json",
    "agent_debate_report.json",
    "agent_suggestions.json",
    "agent_source_plan.json",
    "agent_source_report.json",
    "agent_source_validation.json",
    "dynamic_inputs.generated.json",
    "adaptive_inputs.json",
    "adaptive_dynamic_runs.json",
    "input_influence_report.json",
    "dynamic_exploration_report.json",
    "agent_packet_optimization_report.json",
}

KNOWN_GENERATED_DIRS = {
    ".work",
    "agent_packets",
    "agent_packets_compact",
    "ghidra_temp_proj",
    "outputs",
    "reports",
    "debug",
}

PROTECTED_FILES = {
    ".env",
    ".env.local",
    "notes.txt",
    "manual.md",
    "README.md",
}

def clean_artifacts(
    out_dir: Path | str,
    *,
    dry_run: bool = False,
    yes: bool = False,
) -> dict:
    """
    Safely clean generated artifacts in out_dir.
    """
    if not dry_run and not yes:
        raise ValueError("Must specify either --dry-run or --yes to clean artifacts.")

    out_dir = Path(out_dir).resolve()
    
    # Safety checks
    if out_dir == Path("/").resolve() or out_dir == Path.home().resolve():
        raise ValueError("Root or home directory are not allowed as output directory.")

    files_deleted = []
    dirs_deleted = []
    skipped = []
    diagnostics = []

    if not out_dir.exists():
        return {
            "files_deleted": [],
            "dirs_deleted": [],
            "skipped": [],
            "dry_run": dry_run,
            "diagnostics": [f"Directory {out_dir} does not exist"]
        }

    # Iterate through potential files to delete
    for name in KNOWN_GENERATED_FILES:
        target = (out_dir / name).resolve()
        
        # Ensure path resolve is strictly inside out_dir (prevents traversal)
        try:
            target.relative_to(out_dir)
        except ValueError:
            diagnostics.append(f"Skipped {name}: path traversal detected")
            continue

        if target.exists() or target.is_symlink():
            if name in PROTECTED_FILES:
                skipped.append(name)
                continue

            if dry_run:
                files_deleted.append(name)
            else:
                try:
                    target.unlink()
                    files_deleted.append(name)
                except Exception as e:
                    diagnostics.append(f"Failed to delete file {name}: {e}")

    # Iterate through potential directories to delete
    for dir_name in KNOWN_GENERATED_DIRS:
        target = (out_dir / dir_name).resolve()

        try:
            target.relative_to(out_dir)
        except ValueError:
            diagnostics.append(f"Skipped {dir_name}: path traversal detected")
            continue

        if target.exists() or target.is_symlink():
            if dry_run:
                dirs_deleted.append(dir_name)
            else:
                try:
                    if target.is_symlink():
                        target.unlink()
                    else:
                        shutil.rmtree(target)
                    dirs_deleted.append(dir_name)
                except Exception as e:
                    diagnostics.append(f"Failed to delete directory {dir_name}: {e}")

    # Identify skipped non-generated items
    try:
        for p in out_dir.iterdir():
            name = p.name
            if name in KNOWN_GENERATED_FILES or name in KNOWN_GENERATED_DIRS:
                continue
            skipped.append(name)
    except Exception:
        pass

    return {
        "files_deleted": sorted(files_deleted),
        "dirs_deleted": sorted(dirs_deleted),
        "skipped": sorted(list(set(skipped))),
        "dry_run": dry_run,
        "diagnostics": diagnostics
    }
