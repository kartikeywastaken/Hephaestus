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

def check_evidence_index(artifacts: ValidationArtifacts, report: dict, require_evidence_index: bool = False) -> None:
    """Run validation checks on evidence_index.json."""
    strict = report.get("strict", False)
    
    # 1. Presence Check
    if artifacts.evidence_index is None:
        if require_evidence_index:
            status = "failed"
            severity = "error"
            add_finding(
                report=report,
                finding_id="VAL-EVID-023",
                severity=severity,
                category="evidence_consistency",
                title="Required evidence index is missing",
                message="evidence_index.json is required but missing from the output directory.",
                artifact="evidence_index.json",
                recommendation="Run the build-evidence-index tool or run the pipeline with --evidence-index."
            )
        elif strict:
            status = "warning"
            severity = "warning"
            add_finding(
                report=report,
                finding_id="VAL-EVID-023",
                severity=severity,
                category="evidence_consistency",
                title="Recommended evidence index is missing",
                message="evidence_index.json is missing from the output directory.",
                artifact="evidence_index.json",
                recommendation="Run the build-evidence-index tool or run the pipeline with --evidence-index."
            )
        else:
            status = "ok"
            
        add_check(
            report=report,
            name="evidence_index_present",
            status=status,
            severity="error" if require_evidence_index else "warning",
            message="evidence_index.json is missing."
        )

        
        # Skip remaining evidence index checks
        for name in (
            "evidence_index_schema_valid",
            "evidence_index_summary_valid",
            "evidence_index_unsupported_accounting",
            "evidence_index_unknown_categories"
        ):
            add_check(
                report=report,
                name=name,
                status="skipped",
                severity="warning",
                message="Skipped: evidence_index.json not loaded."
            )
        return

    # If present
    add_check(
        report=report,
        name="evidence_index_present",
        status="ok",
        severity="error",
        message="evidence_index.json is present."
    )
    
    index = artifacts.evidence_index
    
    # 2. Schema check
    schema_status = "ok"
    schema_msg = "evidence_index.json schema version is valid (evidence-index-1.0)."
    version = index.get("schema_version") if isinstance(index, dict) else None
    
    if not isinstance(index, dict) or version != "evidence-index-1.0":
        schema_status = "failed"
        schema_msg = f"evidence_index.json does not conform to schema-version evidence-index-1.0 (found {version})."
        add_finding(
            report=report,
            finding_id="VAL-EVID-024",
            severity="error",
            category="evidence_consistency",
            title="Invalid evidence index schema",
            message=schema_msg,
            artifact="evidence_index.json"
        )
        
    add_check(
        report=report,
        name="evidence_index_schema_valid",
        status=schema_status,
        severity="error",
        message=schema_msg
    )
    
    # If schema is invalid, skip the rest
    if schema_status != "ok":
        for name in (
            "evidence_index_summary_valid",
            "evidence_index_unsupported_accounting",
            "evidence_index_unknown_categories"
        ):
            add_check(
                report=report,
                name=name,
                status="skipped",
                severity="warning",
                message="Skipped: evidence_index.json schema is invalid."
            )
        return
        
    # 3. Summary validity check
    summary = index.get("summary", {})
    categories = [
        "executable_lowered_statements",
        "true_unsupported_statements",
        "comment_lowered_statements",
        "branch_evidence_comments",
        "syntax_adapter_statements",
        "helper_statements",
        "declaration_statements",
        "call_statements",
        "return_statements",
        "control_flow_scaffold_statements",
        "function_signature_statements",
        "empty_function_scaffold_statements",
        "unknown_statement_category"
    ]
    
    invalid_counts = []
    category_sum = 0
    for cat in categories:
        val = summary.get(cat)
        if val is None or not isinstance(val, int) or val < 0:
            invalid_counts.append(f"{cat}: {val}")
        else:
            category_sum += val
            
    total = summary.get("statements_total")
    if total is None or not isinstance(total, int) or total < 0:
        invalid_counts.append(f"statements_total: {total}")
        
    evidence_backed = summary.get("statements_with_instruction_evidence")
    non_evidence = summary.get("statements_without_instruction_evidence")
    
    if evidence_backed is None or not isinstance(evidence_backed, int) or evidence_backed < 0:
        invalid_counts.append(f"statements_with_instruction_evidence: {evidence_backed}")
    if non_evidence is None or not isinstance(non_evidence, int) or non_evidence < 0:
        invalid_counts.append(f"statements_without_instruction_evidence: {non_evidence}")
        
    summary_status = "ok"
    summary_msg = "evidence_index.json summary counts are valid."
    
    if invalid_counts:
        summary_status = "failed"
        summary_msg = f"Invalid or negative summary counts: {', '.join(invalid_counts)}."
        add_finding(
            report=report,
            finding_id="VAL-EVID-025",
            severity="error",
            category="evidence_consistency",
            title="Invalid evidence index summary counts",
            message=summary_msg,
            artifact="evidence_index.json",
            evidence={"invalid_counts": invalid_counts}
        )
    elif category_sum != total:
        summary_status = "failed"
        summary_msg = f"Category counts sum ({category_sum}) does not equal statements_total ({total})."
        add_finding(
            report=report,
            finding_id="VAL-EVID-025",
            severity="error",
            category="evidence_consistency",
            title="Evidence index category sum mismatch",
            message=summary_msg,
            artifact="evidence_index.json",
            evidence={"category_sum": category_sum, "statements_total": total}
        )
    elif evidence_backed + non_evidence != total:
        summary_status = "failed"
        summary_msg = f"Evidence backed + non-evidence backed sum ({evidence_backed + non_evidence}) does not equal statements_total ({total})."
        add_finding(
            report=report,
            finding_id="VAL-EVID-025",
            severity="error",
            category="evidence_consistency",
            title="Evidence index provenance sum mismatch",
            message=summary_msg,
            artifact="evidence_index.json",
            evidence={"evidence_backed": evidence_backed, "non_evidence": non_evidence, "statements_total": total}
        )
        
    add_check(
        report=report,
        name="evidence_index_summary_valid",
        status=summary_status,
        severity="error",
        message=summary_msg
    )
    
    # 4. Unsupported accounting check
    unsupported_status = "ok"
    unsupported_msg = "true_unsupported_statements matches unsupported_instruction_kinds."
    
    if artifacts.source_reconstruction is None:
        unsupported_status = "skipped"
        unsupported_msg = "Skipped: source_reconstruction.json not loaded."
    else:
        recon_summary = artifacts.source_reconstruction.get("summary", {})
        unsupported_kinds = recon_summary.get("unsupported_instruction_kinds", {})
        if not isinstance(unsupported_kinds, dict):
            unsupported_kinds = {}
        expected_unsupported = sum(unsupported_kinds.values())
        
        actual_unsupported = summary.get("true_unsupported_statements", 0)
        
        if actual_unsupported != expected_unsupported:
            unsupported_status = "failed"
            unsupported_msg = f"true_unsupported_statements ({actual_unsupported}) does not match expected ({expected_unsupported}) from source summary."
            add_finding(
                report=report,
                finding_id="VAL-EVID-026",
                severity="error",
                category="evidence_consistency",
                title="Unsupported statement count mismatch",
                message=unsupported_msg,
                artifact="evidence_index.json",
                evidence={
                    "true_unsupported_statements": actual_unsupported,
                    "expected_unsupported_from_source": expected_unsupported,
                    "unsupported_instruction_kinds": unsupported_kinds
                }
            )
            
    add_check(
        report=report,
        name="evidence_index_unsupported_accounting",
        status=unsupported_status,
        severity="error",
        message=unsupported_msg
    )
    
    # 5. Unknown categories check
    unknown_count = summary.get("unknown_statement_category", 0)
    unknown_status = "ok"
    unknown_msg = "No unknown statement categories detected."
    
    if unknown_count > 0:
        unknown_status = "failed" if strict else "warning"
        severity = "error" if strict else "warning"
        unknown_msg = f"The evidence index contains {unknown_count} statements in the unknown category."
        add_finding(
            report=report,
            finding_id="VAL-EVID-027",
            severity=severity,
            category="evidence_consistency",
            title="Unknown statement category detected",
            message=f"The evidence index contains {unknown_count} statements that could not be classified into any known statement category.",
            artifact="evidence_index.json",
            evidence={"unknown_statement_category": unknown_count},
            recommendation="Review the unclassified C statements in evidence_index.json to refine classifier logic."
        )
        if strict:
            report["findings"][-1]["strict_promoted"] = True
            
    add_check(
        report=report,
        name="evidence_index_unknown_categories",
        status=unknown_status,
        severity="warning",
        message=unknown_msg
    )

def run_all_validation_checks(artifacts: ValidationArtifacts, report: dict, no_clang: bool = False, require_evidence_index: bool = False) -> dict:
    """Run all static checks end-to-end and finalize the report."""
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
    
    # 6.5 Evidence index checks (new in Phase 6.2)
    check_evidence_index(artifacts, report, require_evidence_index=require_evidence_index)
    
    # 7. Pipeline manifest checks (requires pipeline_manifest.json)
    check_manifest(artifacts, report)
    
    # 8. Clang syntax checks (requires recovered.c)
    check_clang(artifacts, report, no_clang=no_clang)
    
    # 9. Finalize summary statistics and overall status
    finalize_report(report)
    return report

