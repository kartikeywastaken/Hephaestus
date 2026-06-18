# -*- coding: utf-8 -*-
"""
Tests for Trace Report Explainer
"""

from __future__ import annotations
from src.validation.trace_report.explainer import get_statement_explanation, compute_attention_level

def test_get_statement_explanation():
    # Test typical combinations
    assert "Executable lowered statement backed by instruction evidence." in get_statement_explanation("executable_lowered", "evidence_backed")
    assert "unsupported" in get_statement_explanation("true_unsupported", "evidence_backed")
    assert "conservative commentary" in get_statement_explanation("comment_lowered", "commentary_only")
    assert "could not be classified" in get_statement_explanation("unknown", "unknown")

def test_compute_attention_level_empty_findings():
    # Test levels with no findings
    assert compute_attention_level("executable_lowered", "evidence_backed", []) == "none"
    assert compute_attention_level("true_unsupported", "evidence_backed", []) == "warning"
    assert compute_attention_level("unknown", "evidence_backed", []) == "warning"
    assert compute_attention_level("executable_lowered", "unknown", []) == "warning"
    assert compute_attention_level("comment_lowered", "evidence_backed", []) == "info"
    assert compute_attention_level("branch_evidence", "evidence_backed", []) == "info"
    assert compute_attention_level("syntax_adapter", "evidence_backed", []) == "info"
    assert compute_attention_level("helper", "evidence_backed", []) == "none"

def test_compute_attention_level_with_findings():
    # Test level promotion due to findings
    warning_finding = {"severity": "warning", "category": "syntax_safety"}
    error_finding = {"severity": "error", "category": "syntax_safety"}
    failed_finding = {"severity": "failed", "category": "syntax_safety"}
    
    assert compute_attention_level("executable_lowered", "evidence_backed", [warning_finding]) == "warning"
    assert compute_attention_level("executable_lowered", "evidence_backed", [error_finding]) == "error"
    assert compute_attention_level("executable_lowered", "evidence_backed", [failed_finding]) == "error"
    assert compute_attention_level("comment_lowered", "evidence_backed", [warning_finding, error_finding]) == "error"
    assert compute_attention_level("true_unsupported", "evidence_backed", [warning_finding]) == "warning"
