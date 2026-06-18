# -*- coding: utf-8 -*-
"""
Quality Gate Scoring Algorithms
"""

from __future__ import annotations
from typing import Dict, Any

def compute_scores(summary: Dict[str, Any], validation_status: str, unattached_findings_count: int) -> Dict[str, float]:
    """
    Compute readiness, coverage, validation health, traceability, and risk scores.
    """
    statements_total = summary.get("statements_total", 0)
    evidence_backed = summary.get("evidence_backed_statements", 0)
    
    # 1. evidence_coverage_score
    if statements_total == 0:
        coverage_score = 0.0
    else:
        coverage_score = (evidence_backed / statements_total) * 100.0
        
    # 2. traceability_score
    # Count statements with known confidence labels:
    # evidence_backed, generated_scaffold, syntax_adapter, commentary_only.
    known_conf_count = (
        summary.get("evidence_backed_statements", 0) +
        summary.get("generated_scaffold_statements", 0) +
        summary.get("syntax_adapter_statements", 0) +
        summary.get("commentary_only_statements", 0)
    )
    if statements_total == 0:
        traceability_score = 0.0
    else:
        traceability_score = (known_conf_count / statements_total) * 100.0
        
    # 3. validation_health_score
    errors = summary.get("validation_errors", 0)
    warnings = summary.get("validation_warnings", 0)
    health_score = 100.0 - (25.0 * errors) - (5.0 * warnings)
    health_score = max(0.0, min(100.0, health_score))
    
    # 4. risk_score
    risk = 0.0
    if validation_status == "failed":
        risk += 30.0
    elif validation_status == "warning":
        risk += 10.0
        
    unknown_statements = summary.get("unknown_statements", 0)
    unknown_ratio = 0.0
    if statements_total > 0:
        unknown_ratio = unknown_statements / statements_total
        
    if unknown_ratio > 0.15:
        risk += 20.0
    if summary.get("true_unsupported_statements", 0) > 0:
        risk += 10.0
    if summary.get("high_attention_lines", 0) > 0:
        risk += 10.0
    if unattached_findings_count > 0:
        risk += 10.0
        
    risk_score = max(0.0, min(100.0, risk))
    
    # 5. readability_readiness_score
    readiness_score = (
        0.35 * coverage_score +
        0.30 * traceability_score +
        0.25 * health_score +
        0.10 * (100.0 - risk_score)
    )
    
    return {
        "readability_readiness_score": round(readiness_score, 2),
        "evidence_coverage_score": round(coverage_score, 2),
        "validation_health_score": round(health_score, 2),
        "traceability_score": round(traceability_score, 2),
        "risk_score": round(risk_score, 2)
    }
