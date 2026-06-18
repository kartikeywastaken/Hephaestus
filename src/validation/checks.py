# -*- coding: utf-8 -*-
"""
Validation Orchestrator
"""

from __future__ import annotations
from src.validation.models import ValidationArtifacts
from src.validation.report import add_check, add_finding, finalize_report
from src.validation.schemas import check_schema_versions
from src.validation.metrics import check_source_metrics
from src.validation.c_safety import check_c_safety
from src.validation.helpers import check_helpers
from src.validation.evidence import check_evidence
from src.validation.manifest_checks import check_manifest
from src.validation.clang_check import check_clang

def check_artifact_presence(artifacts: ValidationArtifacts, report: dict) -> None:
    """Verify that required and recommended artifacts exist in the output directory."""
    strict = report.get("strict", False)
    required_missing = []
    recommended_missing = []
    
    # Required
    if artifacts.source_reconstruction is None:
        required_missing.append("source_reconstruction.json")
    if artifacts.recovered_c is None:
        required_missing.append("recovered.c")
        
    # Recommended
    if artifacts.pipeline_manifest is None:
        recommended_missing.append("pipeline_manifest.json")
    if artifacts.unified_ir is None:
        recommended_missing.append("unified_ir.json")
    if artifacts.phase4_semantics is None:
        recommended_missing.append("phase4_semantics.json")
        
    # Report required missing
    for f in required_missing:
        add_finding(
            report=report,
            finding_id="VAL-PRES-001",
            severity="error",
            category="artifact_presence",
            title=f"Required artifact '{f}' is missing",
            message=f"The required validation artifact '{f}' is missing from the output directory.",
            artifact=f,
            recommendation="Run source reconstruction to generate the required output artifacts."
        )
        
    # Report recommended missing
    for f in recommended_missing:
        severity = "error" if strict else "warning"
        add_finding(
            report=report,
            finding_id="VAL-PRES-002",
            severity=severity,
            category="artifact_presence",
            title=f"Recommended artifact '{f}' is missing",
            message=f"The recommended validation artifact '{f}' is missing from the output directory.",
            artifact=f,
            recommendation="Run the complete end-to-end run-all pipeline to produce intermediate stage artifacts."
        )
        if strict:
            report["findings"][-1]["strict_promoted"] = True
            
    # Set check status
    if required_missing:
        status = "failed"
        msg = f"Missing required artifacts: {', '.join(required_missing)}."
    elif recommended_missing:
        status = "failed" if strict else "warning"
        msg = f"All required artifacts are present. Missing recommended: {', '.join(recommended_missing)}."
    else:
        status = "ok"
        msg = "All required and recommended artifacts are present."
        
    add_check(
        report=report,
        name="required_artifacts_present",
        status=status,
        severity="error",
        message=msg
    )

def run_all_validation_checks(artifacts: ValidationArtifacts, report: dict, no_clang: bool = False) -> dict:
    """Run all Phase 6.1 static checks end-to-end and finalize the report."""
    # 1. Check artifact presence
    check_artifact_presence(artifacts, report)
    
    # 2. Schema checks (always run if any artifact present)
    check_schema_versions(artifacts, report)
    
    # 3. Metrics checks (requires source_reconstruction.json)
    check_source_metrics(artifacts, report)
    
    # 4. C Safety policy checks (requires recovered.c)
    check_c_safety(artifacts, report)
    
    # 5. Internal helpers checks (requires recovered.c)
    check_helpers(artifacts, report)
    
    # 6. Evidence consistency checks (requires source_reconstruction.json)
    check_evidence(artifacts, report)
    
    # 7. Pipeline manifest checks (requires pipeline_manifest.json)
    check_manifest(artifacts, report)
    
    # 8. Clang syntax checks (requires recovered.c)
    check_clang(artifacts, report, no_clang=no_clang)
    
    # 9. Finalize summary statistics and overall status
    finalize_report(report)
    return report
