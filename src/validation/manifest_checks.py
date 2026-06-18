# -*- coding: utf-8 -*-
"""
Pipeline Manifest Checks
"""

from __future__ import annotations
from src.validation.models import ValidationArtifacts
from src.validation.report import add_check, add_finding

def check_manifest(artifacts: ValidationArtifacts, report: dict) -> None:
    """Validate pipeline manifest stage order, final status, and stage outputs."""
    strict = report.get("strict", False)
    
    # 1. Check if pipeline manifest was loaded
    if artifacts.pipeline_manifest is None:
        status = "failed" if strict else "skipped"
        sev = "error" if strict else "warning"
        add_check(
            report=report,
            name="pipeline_manifest_status_ok",
            status=status,
            severity=sev,
            message="Skipped: pipeline_manifest.json not loaded."
        )
        add_check(
            report=report,
            name="pipeline_manifest_stage_order_valid",
            status=status,
            severity=sev,
            message="Skipped: pipeline_manifest.json not loaded."
        )
        add_check(
            report=report,
            name="pipeline_manifest_outputs_exist",
            status=status,
            severity=sev,
            message="Skipped: pipeline_manifest.json not loaded."
        )
        
        add_finding(
            report=report,
            finding_id="VAL-MANI-001",
            severity=sev,
            category="pipeline_manifest",
            title="Pipeline manifest is missing",
            message="pipeline_manifest.json was not found in the output directory.",
            artifact="pipeline_manifest.json"
        )
        if strict:
            report["findings"][-1]["strict_promoted"] = True
        return
        
    manifest = artifacts.pipeline_manifest
    
    # 2. Check: pipeline_manifest_status_ok
    manifest_status = manifest.get("status", "unknown")
    status_ok = (manifest_status == "ok")
    check_status = "ok"
    if not status_ok:
        sev = "error" if strict else "warning"
        check_status = "failed" if strict else "warning"
        add_finding(
            report=report,
            finding_id="VAL-MANI-002",
            severity=sev,
            category="pipeline_manifest",
            title="Pipeline manifest execution status was not ok",
            message=f"Pipeline manifest reported status: '{manifest_status}'.",
            artifact="pipeline_manifest.json",
            evidence={"observed_status": manifest_status},
            recommendation="Review pipeline stage errors in pipeline_manifest.json."
        )
        if strict:
            report["findings"][-1]["strict_promoted"] = True
            
    add_check(
        report=report,
        name="pipeline_manifest_status_ok",
        status=check_status,
        severity="error" if strict else "warning",
        message="Pipeline manifest status is ok." if status_ok else f"Pipeline manifest status is '{manifest_status}'."
    )
    
    expected_order = [
        "extract",
        "analyze_cfg",
        "recover_semantics",
        "refine_semantics",
        "recover_layouts",
        "finalize_semantics",
        "reconstruct_source",
        "build_evidence_index",
        "validate",
        "build_trace_report",
        "quality_gate"
    ]
    stages = manifest.get("stages", [])
    executed_names = [s.get("name") for s in stages if s.get("name")]
    
    # Map stage names to expected order indices
    indices = []
    has_unknown_stage = False
    for name in executed_names:
        if name in expected_order:
            indices.append(expected_order.index(name))
        else:
            has_unknown_stage = True
            
    order_valid = True
    if has_unknown_stage:
        order_valid = False
        add_finding(
            report=report,
            finding_id="VAL-MANI-003",
            severity="error",
            category="pipeline_manifest",
            title="Unknown pipeline stage found",
            message=f"Pipeline manifest contains stages outside expected definition list: {executed_names}.",
            artifact="pipeline_manifest.json"
        )
    else:
        # Check non-decreasing order of indices
        order_valid = all(indices[i] <= indices[i+1] for i in range(len(indices) - 1))
        if not order_valid:
            add_finding(
                report=report,
                finding_id="VAL-MANI-004",
                severity="error",
                category="pipeline_manifest",
                title="Invalid pipeline stage order execution",
                message=f"Pipeline stages executed out of sequence order: {executed_names}.",
                artifact="pipeline_manifest.json",
                evidence={"sequence": executed_names}
            )
            
    add_check(
        report=report,
        name="pipeline_manifest_stage_order_valid",
        status="ok" if order_valid else "failed",
        severity="error",
        message="Pipeline stages executed in valid chronological sequence." if order_valid else "Pipeline stages executed out of sequence order."
    )
    
    # 4. Check: pipeline_manifest_outputs_exist
    missing_outputs = []
    for stage in stages:
        stage_name = stage.get("name", "unknown")
        # Check output only for stages that did not fail
        if stage.get("status") != "failed":
            outputs = stage.get("outputs", [])
            for file_name in outputs:
                file_path = artifacts.out_dir / file_name
                if not file_path.exists():
                    missing_outputs.append((stage_name, file_name))
                    add_finding(
                        report=report,
                        finding_id="VAL-MANI-005",
                        severity="error",
                        category="pipeline_manifest",
                        title="Declared stage output file is missing from disk",
                        message=f"Stage '{stage_name}' finished successfully, but declared output '{file_name}' was not found.",
                        artifact=file_name,
                        evidence={"stage": stage_name, "missing_file": file_name}
                    )
                    
    outputs_exist = (len(missing_outputs) == 0)
    add_check(
        report=report,
        name="pipeline_manifest_outputs_exist",
        status="ok" if outputs_exist else "failed",
        severity="error",
        message="All declared successful stage output files exist." if outputs_exist else f"Found {len(missing_outputs)} missing declared stage outputs."
    )
