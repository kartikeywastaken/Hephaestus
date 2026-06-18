# -*- coding: utf-8 -*-
"""
Quality Gate Decision Rules
"""

from __future__ import annotations
from typing import Dict, Any, List

def extract_clang_diagnostic_counts(
    finding: dict | None = None,
    validation_checks: dict | None = None,
) -> tuple[int | None, int | None]:
    """
    Extract compiler error and warning counts from a finding or validation checks.
    """
    errors: int | None = None
    warnings: int | None = None

    def safe_int(v: Any) -> int | None:
        if v is None:
            return None
        try:
            return int(str(v).strip())
        except (ValueError, TypeError):
            return None

    def scan_dict(d: dict) -> tuple[int | None, int | None]:
        errs, warns = None, None
        for key in ["errors", "syntax_errors", "clang_errors"]:
            if key in d:
                errs = safe_int(d[key])
                if errs is not None:
                    break
        for key in ["warnings", "clang_warnings"]:
            if key in d:
                warns = safe_int(d[key])
                if warns is not None:
                    break
        return errs, warns

    if finding and isinstance(finding, dict):
        evidence = finding.get("evidence")
        if isinstance(evidence, dict):
            e_errs, e_warns = scan_dict(evidence)
            if e_errs is not None:
                errors = e_errs
            if e_warns is not None:
                warnings = e_warns

        details = finding.get("details")
        if isinstance(details, dict):
            d_errs, d_warns = scan_dict(details)
            if d_errs is not None and errors is None:
                errors = d_errs
            if d_warns is not None and warnings is None:
                warnings = d_warns

    if validation_checks and isinstance(validation_checks, dict):
        clang_check = validation_checks.get("clang_syntax_ok", {})
        if isinstance(clang_check, dict):
            chk_details = clang_check.get("details")
            if isinstance(chk_details, dict):
                c_errs, c_warns = scan_dict(chk_details)
                if c_errs is not None and errors is None:
                    errors = c_errs
                if c_warns is not None and warnings is None:
                    warnings = c_warns

    return errors, warnings

def normalize_record(
    item: str | Dict[str, Any],
    default_id: str,
    default_severity: str,
    default_category: str,
    default_title: str = "Quality Gate Issue",
    default_recommendation: str = ""
) -> Dict[str, Any]:
    """
    Ensure a warning or blocking issue is in standard dictionary shape.
    """
    if isinstance(item, dict):
        return {
            "id": item.get("id") or default_id,
            "severity": item.get("severity") or default_severity,
            "category": item.get("category") or default_category,
            "title": item.get("title") or default_title,
            "message": item.get("message") or "",
            "evidence": item.get("evidence") or item.get("details") or {},
            "recommendation": item.get("recommendation") or default_recommendation
        }
    return {
        "id": default_id,
        "severity": default_severity,
        "category": default_category,
        "title": default_title,
        "message": str(item),
        "evidence": {},
        "recommendation": default_recommendation
    }

def evaluate_decision(
    missing_artifacts: List[str],
    validation_status: str,
    validation_findings: List[Dict[str, Any]],
    condition_expressions_recovered: int,
    trace_report_schema_valid: bool,
    evidence_index_schema_valid: bool,
    hash_check_failed: bool,
    summary: Dict[str, Any],
    unattached_findings_count: int,
    scores: Dict[str, float],
    validation_checks: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """
    Evaluate quality gate status, decision blocks/warnings, and hints.
    """
    blocked = False
    requires_review = False
    blocking_issues: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    recommendations = []

    # 1. Evaluate hard blocking conditions
    if missing_artifacts:
        blocked = True
        blocking_issues.append(normalize_record(
            f"Missing required artifacts: {', '.join(missing_artifacts)}",
            default_id="QG-MISSING-ARTIFACTS",
            default_severity="error",
            default_category="artifact_presence",
            default_title="Missing Required Artifacts",
            default_recommendation="Ensure the full pipeline run finishes successfully to generate all outputs."
        ))

    if hash_check_failed:
        blocked = True
        blocking_issues.append(normalize_record(
            "Input artifacts were mutated during validation/trace report generation.",
            default_id="QG-HASH-MUTATION",
            default_severity="error",
            default_category="read_only_integrity",
            default_title="Read-Only Hash Mutation",
            default_recommendation="Ensure validation and trace stages do not modify recovered.c or source_reconstruction.json."
        ))

    if not trace_report_schema_valid:
        blocked = True
        blocking_issues.append(normalize_record(
            "Trace report schema is invalid (expected trace-report-1.0).",
            default_id="QG-SCHEMA-INVALID-TRACE",
            default_severity="error",
            default_category="schema",
            default_title="Trace Report Schema Mismatch",
            default_recommendation="Check the trace report schema definition and trace builder execution."
        ))

    if not evidence_index_schema_valid:
        blocked = True
        blocking_issues.append(normalize_record(
            "Evidence index schema is invalid (expected evidence-index-1.0).",
            default_id="QG-SCHEMA-INVALID-EVID",
            default_severity="error",
            default_category="schema",
            default_title="Evidence Index Schema Mismatch",
            default_recommendation="Check the evidence index schema definition."
        ))

    if condition_expressions_recovered != 0:
        blocked = True
        blocking_issues.append(normalize_record(
            f"Non-zero condition expressions recovered: {condition_expressions_recovered} (must be 0).",
            default_id="QG-COND-EXPR-RECOVERED",
            default_severity="error",
            default_category="condition_safety",
            default_title="Non-Zero Condition Expressions",
            default_recommendation="Condition recovery is disabled in Phase 6 decompiler stages."
        ))

    # 2. Evaluate validation findings
    hard_blocker_categories = {
        "artifact_presence",
        "schema",
        "condition_safety",
        "c_safety",
        "helper_consistency",
        "clang_syntax",
        "read_only_integrity"
    }

    clang_warnings_detected = False
    clang_errors_detected = False
    clang_diag_counts = (0, 0)

    for f in validation_findings:
        f_cat = f.get("category")
        f_sev = str(f.get("severity", "")).lower()

        if f_cat == "clang_syntax":
            errs, warns = extract_clang_diagnostic_counts(f, validation_checks)
            if errs is not None or warns is not None:
                err_val = errs if errs is not None else 0
                warn_val = warns if warns is not None else 0
                clang_diag_counts = (err_val, warn_val)
                if err_val > 0:
                    clang_errors_detected = True
                if warn_val > 0:
                    clang_warnings_detected = True
            else:
                # Fallback to finding severity if counts are missing
                if f_sev in ["error", "failed"]:
                    clang_errors_detected = True
                elif f_sev == "warning":
                    clang_warnings_detected = True
        else:
            if f_cat in hard_blocker_categories:
                if f_sev in ["error", "failed"]:
                    blocked = True
                    blocking_issues.append(normalize_record(
                        f,
                        default_id=f.get("id", "QG-HARD-BLOCKER"),
                        default_severity="error",
                        default_category=f_cat,
                        default_title="Safety/Policy Hard Blocker",
                        default_recommendation="Resolve safety and consistency violations in source reconstruction."
                    ))
                else:
                    requires_review = True
                    warnings.append(normalize_record(
                        f,
                        default_id=f.get("id", "QG-SAFETY-WARN"),
                        default_severity="warning",
                        default_category=f_cat,
                        default_title="Safety/Policy Warning",
                        default_recommendation="Review the safety/policy warning."
                    ))
            else:
                # Non-blocking category (strict accounting, etc.) -> Review only
                requires_review = True
                warnings.append(normalize_record(
                    f,
                    default_id=f.get("id", "QG-POLICY-WARN"),
                    default_severity="warning",
                    default_category=f_cat or "validation",
                    default_title="Policy Rule Warning",
                    default_recommendation="Verify decompiler evidence consistency rules."
                ))

    # Apply Clang Diagnostic decision rules
    if clang_errors_detected:
        blocked = True
        blocking_issues.append({
            "id": "QG-CLANG-ERR",
            "severity": "error",
            "category": "clang_syntax",
            "title": "Compiler syntax errors present",
            "message": "Recovered C failed clang syntax checking.",
            "evidence": {
                "errors": clang_diag_counts[0],
                "warnings": clang_diag_counts[1]
            },
            "recommendation": "Do not run Phase 7 readability reconstruction until syntax errors are fixed or isolated."
        })
    elif clang_warnings_detected:
        requires_review = True
        warnings.append({
            "id": "QG-CLANG-WARN",
            "severity": "warning",
            "category": "clang_syntax",
            "title": "Compiler warnings present",
            "message": "Recovered C passed syntax checking but produced compiler warnings.",
            "evidence": {
                "errors": clang_diag_counts[0],
                "warnings": clang_diag_counts[1]
            },
            "recommendation": "Proceed to Phase 7 with review status. Consider these warnings during readable reconstruction."
        })

    # Non-blocking overall validation status handling
    if validation_status == "failed" and not blocked:
        requires_review = True
        # Check if we already have it in warnings
        if not any(w.get("id") == "QG-VAL-FAILED-NON-BLOCKING" for w in warnings):
            warnings.append({
                "id": "QG-VAL-FAILED-NON-BLOCKING",
                "severity": "warning",
                "category": "validation",
                "title": "Validation failed due to non-blocking policy rules",
                "message": "Validation report status is failed, but no hard safety or schema errors were detected.",
                "evidence": {},
                "recommendation": "Proceed to Phase 7 with review status. Warnings should be considered during readable reconstruction."
            })
    elif validation_status == "warning" and not blocked:
        requires_review = True
        if not any(w.get("id") == "QG-VAL-WARNING" for w in warnings):
            warnings.append({
                "id": "QG-VAL-WARNING",
                "severity": "warning",
                "category": "validation",
                "title": "Validation report contains warnings",
                "message": "Validator produced warnings during static checking.",
                "evidence": {},
                "recommendation": "Review decompiler warnings."
            })

    # 3. Evaluate score thresholds and other warning metrics (triggers review only)
    statements_total = summary.get("statements_total", 0)
    unknown_statements = summary.get("unknown_statements", 0)
    unknown_ratio = 0.0
    if statements_total > 0:
        unknown_ratio = unknown_statements / statements_total

    if unknown_ratio > 0.15:
        requires_review = True
        warnings.append({
            "id": "QG-UNKNOWN-RATIO",
            "severity": "warning",
            "category": "readability",
            "title": "High unknown statement ratio",
            "message": f"High unknown statement ratio: {unknown_ratio:.2%} (max allowed: 15.0%).",
            "evidence": {"unknown_ratio": unknown_ratio},
            "recommendation": "Verify instruction extraction and lowering rules to decrease unknown statement count."
        })

    if summary.get("true_unsupported_statements", 0) > 0:
        requires_review = True
        warnings.append({
            "id": "QG-TRUE-UNSUPPORTED",
            "severity": "warning",
            "category": "readability",
            "title": "Contains true unsupported statements",
            "message": f"Contains true unsupported statements: {summary.get('true_unsupported_statements')}.",
            "evidence": {"true_unsupported_statements": summary.get("true_unsupported_statements")},
            "recommendation": "Verify instruction lowering coverage."
        })

    if summary.get("high_attention_lines", 0) > 0:
        requires_review = True
        warnings.append({
            "id": "QG-HIGH-ATTENTION",
            "severity": "warning",
            "category": "readability",
            "title": "Contains high attention lines",
            "message": f"Contains high attention lines: {summary.get('high_attention_lines')}.",
            "evidence": {"high_attention_lines": summary.get("high_attention_lines")},
            "recommendation": "Check high attention statements in the trace report."
        })

    if unattached_findings_count > 0:
        requires_review = True
        warnings.append({
            "id": "QG-UNATTACHED-FINDINGS",
            "severity": "warning",
            "category": "validation",
            "title": "Contains unattached validation findings",
            "message": f"Contains unattached validation findings count: {unattached_findings_count}.",
            "evidence": {"unattached_findings_count": unattached_findings_count},
            "recommendation": "Check findings that could not be mapped to statements."
        })

    readiness_score = scores.get("readability_readiness_score", 0.0)
    if readiness_score < 70.0:
        requires_review = True
        warnings.append({
            "id": "QG-LOW-READINESS",
            "severity": "warning",
            "category": "readability",
            "title": "Readability readiness score is below threshold",
            "message": f"Readability readiness score is below threshold: {readiness_score:.2f} (min: 70.0).",
            "evidence": {"readability_readiness_score": readiness_score},
            "recommendation": "Improve evidence traceability and validation health."
        })

    risk_score = scores.get("risk_score", 0.0)
    if risk_score > 40.0:
        requires_review = True
        warnings.append({
            "id": "QG-HIGH-RISK",
            "severity": "warning",
            "category": "readability",
            "title": "Risk score is above threshold",
            "message": f"Risk score is above threshold: {risk_score:.2f} (max: 40.0).",
            "evidence": {"risk_score": risk_score},
            "recommendation": "Reduce pipeline validation errors and warnings."
        })

    # Determine status and safe_to_use
    if blocked:
        status = "blocked"
        safe_to_use = False
    elif requires_review:
        status = "review"
        safe_to_use = True
    else:
        status = "ready"
        safe_to_use = True

    # Generate recommendations list
    if blocked:
        recommendations.append("Resolve all blocking issues and safety errors in the decompiler pipeline.")
    if requires_review:
        recommendations.append("Manually review warnings and trace report validation findings before proceeding to Phase 7.")
    if status == "ready":
        recommendations.append("Proceed to Phase 7 readability reconstruction.")

    # Generate Phase 7 hints
    syntax_adapter_count = summary.get("syntax_adapter_statements", 0)
    branch_evidence_count = summary.get("branch_evidence_statements", 0)
    executable_lowered_count = summary.get("executable_lowered_statements", 0)
    control_flow_scaffold_count = summary.get("control_flow_scaffold_statements", 0)

    predicate_rec = (syntax_adapter_count > 0 or branch_evidence_count > 0)
    has_tmp_stack_decls = summary.get("has_tmp_stack_decls", False)
    local_var_rec = (has_tmp_stack_decls or executable_lowered_count > 5)
    expr_simp = (executable_lowered_count > 0)
    loop_readability = (control_flow_scaffold_count > 0 or syntax_adapter_count > 0)

    agent_assistance = False
    if status == "review" and risk_score > 30.0:
        agent_assistance = True

    phase7_hints = {
        "predicate_recovery_recommended": predicate_rec,
        "local_variable_recovery_recommended": local_var_rec,
        "expression_simplification_recommended": expr_simp,
        "loop_readability_recommended": loop_readability,
        "agent_assistance_recommended": agent_assistance
    }

    reason = ""
    if status == "ready":
        reason = "Artifacts are suitable for static readable reconstruction."
    elif status == "review":
        reason = "Artifacts are acceptable but require manual review before Phase 7."
    else:
        reason = "Artifacts are blocked from Phase 7 due to safety/policy violations or missing files."

    return {
        "status": status,
        "decision": {
            "safe_to_use_for_phase7": safe_to_use,
            "requires_review": requires_review,
            "blocked": blocked,
            "reason": reason
        },
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "recommendations": recommendations,
        "phase7_hints": phase7_hints
    }

