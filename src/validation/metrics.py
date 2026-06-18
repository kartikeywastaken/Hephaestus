# -*- coding: utf-8 -*-
"""
Source Summary Metrics Checks
"""

from __future__ import annotations
from src.validation.models import ValidationArtifacts
from src.validation.report import add_check, add_finding

def check_source_metrics(artifacts: ValidationArtifacts, report: dict) -> None:
    """Perform mathematical checks on reconstruction metadata metrics."""
    strict = report.get("strict", False)
    
    # Check 1: source_summary_present
    if artifacts.source_reconstruction is None:
        add_check(
            report=report,
            name="source_summary_present",
            status="skipped",
            severity="error",
            message="Skipped: source_reconstruction.json not loaded."
        )
        return
        
    summary = artifacts.source_reconstruction.get("summary")
    if summary is None:
        add_check(
            report=report,
            name="source_summary_present",
            status="failed",
            severity="error",
            message="source_reconstruction.json is missing 'summary' field."
        )
        add_finding(
            report=report,
            finding_id="VAL-METR-001",
            severity="error",
            category="metrics",
            title="Missing summary object",
            message="No summary object found in source_reconstruction.json.",
            artifact="source_reconstruction.json"
        )
        return
        
    add_check(
        report=report,
        name="source_summary_present",
        status="ok",
        severity="error",
        message="source_reconstruction.json contains a summary object."
    )
    
    # Read metrics from summary
    total = summary.get("instructions_total", 0)
    lowered = summary.get("instructions_lowered", 0)
    commented = summary.get("instructions_commented", 0)
    coverage = summary.get("lowering_coverage_percent", 0.0)
    cond_recovered = summary.get("condition_expressions_recovered", 0)
    unsupported_kinds = summary.get("unsupported_instruction_kinds")
    
    # Check 2: source_summary_metrics_nonnegative
    has_negative = False
    if total < 0 or lowered < 0 or commented < 0:
        has_negative = True
        add_finding(
            report=report,
            finding_id="VAL-METR-002",
            severity="error",
            category="metrics",
            title="Negative metric values detected",
            message=f"Found negative metrics: total={total}, lowered={lowered}, commented={commented}.",
            artifact="source_reconstruction.json",
            evidence={"total": total, "lowered": lowered, "commented": commented}
        )
        
    add_check(
        report=report,
        name="source_summary_metrics_nonnegative",
        status="failed" if has_negative else "ok",
        severity="error",
        message="Metrics counts must be non-negative." if not has_negative else "Found negative metrics count."
    )
    
    # Check 3: instruction_counts_consistent
    consistent = (lowered + commented == total)
    if not consistent:
        add_finding(
            report=report,
            finding_id="VAL-METR-003",
            severity="error",
            category="metrics",
            title="Instruction count inconsistency",
            message=f"lowered ({lowered}) + commented ({commented}) = {lowered + commented}, expected total ({total}).",
            artifact="source_reconstruction.json",
            evidence={"lowered": lowered, "commented": commented, "expected_total": total}
        )
    add_check(
        report=report,
        name="instruction_counts_consistent",
        status="ok" if consistent else "failed",
        severity="error",
        message="Sum of lowered and commented instructions equals total." if consistent else "Sum of lowered and commented instructions does not equal total."
    )
    
    # Check 4: lowering_coverage_math_valid
    coverage_status = "ok"
    if total == 0:
        if coverage not in (0.0, 100.0):
            coverage_status = "warning"
            add_finding(
                report=report,
                finding_id="VAL-METR-004",
                severity="warning",
                category="metrics",
                title="Unexpected coverage for empty instruction count",
                message=f"instructions_total is 0, but lowering_coverage_percent was {coverage} (expected 0.0 or 100.0).",
                artifact="source_reconstruction.json",
                evidence={"total": total, "coverage": coverage}
            )
    else:
        expected_coverage = (lowered / total) * 100
        if abs(expected_coverage - coverage) > 0.01:
            coverage_status = "failed"
            add_finding(
                report=report,
                finding_id="VAL-METR-005",
                severity="error",
                category="metrics",
                title="Invalid lowering coverage calculation",
                message=f"Reported coverage {coverage}%, calculated {expected_coverage}%. Difference exceeds 0.01 tolerance.",
                artifact="source_reconstruction.json",
                evidence={"observed": coverage, "expected": expected_coverage}
            )
            
    add_check(
        report=report,
        name="lowering_coverage_math_valid",
        status=coverage_status,
        severity="error",
        message="Coverage math is within 0.01 tolerance." if coverage_status == "ok" else "Coverage math mismatch or unexpected value."
    )
    
    # Check 5: unsupported_instruction_kinds_valid
    unsupported_status = "ok"
    if commented > 0 and unsupported_kinds is None:
        unsupported_status = "failed"
        add_finding(
            report=report,
            finding_id="VAL-METR-006",
            severity="error",
            category="unsupported_accounting",
            title="Missing unsupported_instruction_kinds dictionary",
            message=f"Reconstruction summary contains {commented} commented instructions, but unsupported_instruction_kinds is missing.",
            artifact="source_reconstruction.json"
        )
    elif unsupported_kinds is not None:
        if not isinstance(unsupported_kinds, dict):
            unsupported_status = "failed"
            add_finding(
                report=report,
                finding_id="VAL-METR-007",
                severity="error",
                category="unsupported_accounting",
                title="Malformed unsupported_instruction_kinds dict",
                message="unsupported_instruction_kinds is not a dictionary.",
                artifact="source_reconstruction.json",
                evidence={"type": str(type(unsupported_kinds))}
            )
        else:
            for k, v in unsupported_kinds.items():
                if not isinstance(k, str) or not isinstance(v, int) or v < 0:
                    unsupported_status = "failed"
                    add_finding(
                        report=report,
                        finding_id="VAL-METR-008",
                        severity="error",
                        category="unsupported_accounting",
                        title="Invalid entry in unsupported_instruction_kinds",
                        message=f"Key '{k}' (type {type(k)}) must be a string and value '{v}' (type {type(v)}) must be a non-negative integer.",
                        artifact="source_reconstruction.json"
                    )
            
            # Warn on cset/ldp
            if "cset" in unsupported_kinds or "ldp" in unsupported_kinds:
                sev = "error" if strict else "warning"
                if unsupported_status == "ok":
                    unsupported_status = "failed" if strict else "warning"
                add_finding(
                    report=report,
                    finding_id="VAL-METR-009",
                    severity=sev,
                    category="unsupported_accounting",
                    title="Regression instruction kinds present",
                    message="cset/ldp appeared in unsupported instructions; these were expected to be handled after Phase 5.8.1.",
                    artifact="source_reconstruction.json",
                    evidence={"unsupported_instruction_kinds": unsupported_kinds},
                    recommendation="Ensure ARM64 lowering split models support the latest cset and ldp formats."
                )
                if strict:
                    report["findings"][-1]["strict_promoted"] = True
                    
    add_check(
        report=report,
        name="unsupported_instruction_kinds_valid",
        status=unsupported_status,
        severity="error",
        message="Unsupported instructions kinds metrics are valid." if unsupported_status == "ok" else "Unsupported instruction kinds malformed or contain warnings."
    )
    
    # Check 6: condition_expressions_zero
    cond_status = "ok"
    if cond_recovered != 0:
        cond_status = "failed"
        add_finding(
            report=report,
            finding_id="VAL-COND-001",
            severity="error",
            category="condition_safety",
            title="Recovered condition expressions must remain zero",
            message=f"condition_expressions_recovered was {cond_recovered}, expected 0.",
            artifact="source_reconstruction.json",
            evidence={"observed": cond_recovered, "expected": 0},
            recommendation="Do not emit executable recovered conditions. Use HEPHAESTUS_UNKNOWN_COND adapters."
        )
        
    add_check(
        report=report,
        name="condition_expressions_zero",
        status=cond_status,
        severity="error",
        message="Condition expressions recovered remains zero." if cond_status == "ok" else "Condition expressions recovered count is non-zero."
    )
