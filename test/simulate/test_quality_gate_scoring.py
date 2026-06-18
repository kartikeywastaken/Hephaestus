# -*- coding: utf-8 -*-
"""
Tests for Quality Gate Scoring Algorithms
"""

from __future__ import annotations
from src.validation.quality_gate.scoring import compute_scores

def test_scoring_success():
    summary = {
        "statements_total": 100,
        "evidence_backed_statements": 60,
        "generated_scaffold_statements": 20,
        "syntax_adapter_statements": 10,
        "commentary_only_statements": 5,
        "unknown_statements": 5,
        "true_unsupported_statements": 0,
        "high_attention_lines": 0,
        "validation_errors": 0,
        "validation_warnings": 0
    }
    
    # 60 evidence_backed / 100 = 60.0% coverage
    # 60 + 20 + 10 + 5 = 95 known confidence / 100 = 95.0% traceability
    # validation status ok -> health = 100.0, risk = 0
    # readiness = 0.35 * 60 + 0.30 * 95 + 0.25 * 100 + 0.10 * 100 = 21 + 28.5 + 25 + 10 = 84.5
    scores = compute_scores(summary, "ok", 0)
    assert scores["evidence_coverage_score"] == 60.0
    assert scores["traceability_score"] == 95.0
    assert scores["validation_health_score"] == 100.0
    assert scores["risk_score"] == 0.0
    assert scores["readability_readiness_score"] == 84.50

def test_scoring_clamping_and_rounding():
    summary = {
        "statements_total": 3,
        "evidence_backed_statements": 1,
        "generated_scaffold_statements": 1,
        "syntax_adapter_statements": 0,
        "commentary_only_statements": 0,
        "unknown_statements": 1,
        "true_unsupported_statements": 1,
        "high_attention_lines": 2,
        "validation_errors": 5, # health subtract 5*25 = 125 -> clamped to 0
        "validation_warnings": 2
    }
    
    # Coverage: 1/3 = 33.33%
    # Traceability: 2/3 = 66.67%
    # Health: 100 - 125 - 10 = -35 -> clamped to 0.0
    # Risk: validation warning (+10), unknown ratio = 1/3 = 33% > 15% (+20), true unsupported (+10), high attention (+10) -> total 50
    # readiness = 0.35 * 33.33 + 0.30 * 66.67 + 0.25 * 0 + 0.10 * (100 - 50) = 11.666 + 20.001 + 0 + 5 = 36.67
    scores = compute_scores(summary, "warning", 1) # unattached (+10) -> risk becomes 60
    # risk = 60
    # readiness = 0.35 * 33.333... + 0.30 * 66.666... + 0.25 * 0 + 0.10 * (100 - 60)
    #           = 11.666... + 20.0 + 0 + 4 = 35.67
    assert scores["evidence_coverage_score"] == 33.33
    assert scores["traceability_score"] == 66.67
    assert scores["validation_health_score"] == 0.0
    assert scores["risk_score"] == 60.0
    assert scores["readability_readiness_score"] == 35.67

def test_scoring_zero_statements_safe():
    summary = {
        "statements_total": 0,
        "evidence_backed_statements": 0,
        "unknown_statements": 0,
        "true_unsupported_statements": 0,
        "high_attention_lines": 0,
        "validation_errors": 0,
        "validation_warnings": 0
    }
    scores = compute_scores(summary, "ok", 0)
    assert scores["evidence_coverage_score"] == 0.0
    assert scores["traceability_score"] == 0.0
    assert scores["validation_health_score"] == 100.0
    assert scores["risk_score"] == 0.0
    assert scores["readability_readiness_score"] == 35.00
