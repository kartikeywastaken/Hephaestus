# -*- coding: utf-8 -*-
"""
Quality Gate Markdown Report Generator
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List

def write_quality_markdown(payload: Dict[str, Any], out_dir: Path) -> Path:
    """Generate and write quality_gate.md human-readable summary."""
    md_file = out_dir / "quality_gate.md"
    
    status = payload.get("status", "unknown").upper()
    decision = payload.get("decision", {})
    scores = payload.get("scores", {})
    summary = payload.get("summary", {})
    blocking_issues = payload.get("blocking_issues", [])
    warnings = payload.get("warnings", [])
    recommendations = payload.get("recommendations", [])
    phase7_hints = payload.get("phase7_hints", {})
    
    lines: List[str] = []
    lines.append("# Hephaestus Quality Gate")
    lines.append("")
    lines.append(f"Overall Readiness Status: **{status}**")
    lines.append("")
    lines.append(f"Reason: {decision.get('reason', '')}")
    lines.append("")
    
    # Section: Decision
    lines.append("## Decision")
    lines.append("")
    lines.append(f"- **Safe to proceed to Phase 7**: {'Yes' if decision.get('safe_to_use_for_phase7') else 'No'}")
    lines.append(f"- **Requires Manual Review**: {'Yes' if decision.get('requires_review') else 'No'}")
    lines.append(f"- **Blocked**: {'Yes' if decision.get('blocked') else 'No'}")
    lines.append("")
    
    # Section: Scores
    lines.append("## Scores")
    lines.append("")
    lines.append("| Score Type | Value | Threshold / Target | Status |")
    lines.append("| :--- | :--- | :--- | :--- |")
    
    min_readiness = payload.get("thresholds", {}).get("min_readiness_score", 70.0)
    max_risk = payload.get("thresholds", {}).get("max_risk_score", 40.0)
    
    readiness_val = scores.get('readability_readiness_score', 0.0)
    readiness_status = "PASS" if readiness_val >= min_readiness else "FAIL/REVIEW"
    lines.append(f"| Readability Readiness Score | {readiness_val:.2f} | >= {min_readiness:.1f} | {readiness_status} |")
    
    lines.append(f"| Evidence Coverage Score | {scores.get('evidence_coverage_score', 0.0):.2f} | N/A | Informational |")
    lines.append(f"| Validation Health Score | {scores.get('validation_health_score', 0.0):.2f} | N/A | Informational |")
    lines.append(f"| Traceability Score | {scores.get('traceability_score', 0.0):.2f} | N/A | Informational |")
    
    risk_val = scores.get('risk_score', 0.0)
    risk_status = "PASS" if risk_val <= max_risk else "HIGH RISK"
    lines.append(f"| Risk Score | {risk_val:.2f} | <= {max_risk:.1f} | {risk_status} |")
    lines.append("")
    
    # Section: Summary Metrics
    lines.append("## Summary Metrics")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("| :--- | :--- |")
    lines.append(f"| Functions Total | {summary.get('functions_total', 0)} |")
    lines.append(f"| Statements Total | {summary.get('statements_total', 0)} |")
    lines.append(f"| Evidence-Backed Statements | {summary.get('evidence_backed_statements', 0)} |")
    lines.append(f"| Unknown Statements | {summary.get('unknown_statements', 0)} |")
    lines.append(f"| True Unsupported Statements | {summary.get('true_unsupported_statements', 0)} |")
    lines.append(f"| Comment Lowered Statements | {summary.get('comment_lowered_statements', 0)} |")
    lines.append(f"| Syntax Adapter Statements | {summary.get('syntax_adapter_statements', 0)} |")
    lines.append(f"| Validation Errors | {summary.get('validation_errors', 0)} |")
    lines.append(f"| Validation Warnings | {summary.get('validation_warnings', 0)} |")
    lines.append(f"| High-Attention Lines | {summary.get('high_attention_lines', 0)} |")
    lines.append("")

    # Section: Blocking Issues
    lines.append("## Blocking Issues")
    lines.append("")
    if not blocking_issues:
        lines.append("No blocking issues detected.")
    else:
        for issue in blocking_issues:
            if isinstance(issue, dict):
                lines.append(f"- :x: **{issue.get('title', 'Issue')}** (ID: {issue.get('id', 'unknown')}): {issue.get('message', '')}")
            else:
                lines.append(f"- :x: {issue}")
    lines.append("")
    
    # Section: Warnings
    lines.append("## Warnings")
    lines.append("")
    if not warnings:
        lines.append("No warnings generated.")
    else:
        for warning in warnings:
            if isinstance(warning, dict):
                lines.append(f"- :warning: **{warning.get('title', 'Warning')}** (ID: {warning.get('id', 'unknown')}): {warning.get('message', '')}")
            else:
                lines.append(f"- :warning: {warning}")
    lines.append("")
    
    # Section: Phase 7 Readiness & Hints
    lines.append("## Phase 7 Readiness")
    lines.append("")
    lines.append("| Option / Hint | Recommended? | Details |")
    lines.append("| :--- | :--- | :--- |")
    lines.append(f"| Predicate Recovery | {'Yes' if phase7_hints.get('predicate_recovery_recommended') else 'No'} | Highlights if syntax adapters or branch predicates are found. |")
    lines.append(f"| Local Variable Recovery | {'Yes' if phase7_hints.get('local_variable_recovery_recommended') else 'No'} | Recommended if temporary stack slots or registers are declared. |")
    lines.append(f"| Expression Simplification | {'Yes' if phase7_hints.get('expression_simplification_recommended') else 'No'} | Recommended if there are lowered executable statements to clean up. |")
    lines.append(f"| Loop Readability | {'Yes' if phase7_hints.get('loop_readability_recommended') else 'No'} | Recommended if control flow scaffolds need loop structure annotation. |")
    lines.append(f"| Agent Assistance | {'Yes' if phase7_hints.get('agent_assistance_recommended') else 'No'} | Recommended if the validation status is blocked or high-risk review. |")
    lines.append("")
    
    # Section: Recommended Next Steps
    lines.append("## Recommended Next Steps")
    lines.append("")
    if not recommendations:
        lines.append("No recommendations provided.")
    else:
        for rec in recommendations:
            lines.append(f"- {rec}")
    lines.append("")
    
    with open(md_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    return md_file
