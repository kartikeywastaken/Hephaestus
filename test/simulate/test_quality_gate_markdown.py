# -*- coding: utf-8 -*-
"""
Tests for Quality Gate Markdown Generator
"""

from __future__ import annotations
import tempfile
from pathlib import Path
from src.validation.quality_gate.markdown import write_quality_markdown

def test_write_quality_markdown():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        
        payload = {
            "status": "ready",
            "decision": {
                "safe_to_use_for_phase7": True,
                "requires_review": False,
                "blocked": False,
                "reason": "Artifacts are suitable for static readable reconstruction."
            },
            "scores": {
                "readability_readiness_score": 85.23,
                "evidence_coverage_score": 75.0,
                "validation_health_score": 95.0,
                "traceability_score": 98.0,
                "risk_score": 10.0
            },
            "thresholds": {
                "min_readiness_score": 70.0,
                "max_risk_score": 40.0
            },
            "summary": {
                "functions_total": 2,
                "statements_total": 20,
                "evidence_backed_statements": 15,
                "unknown_statements": 1,
                "true_unsupported_statements": 0,
                "comment_lowered_statements": 1,
                "syntax_adapter_statements": 1,
                "validation_errors": 0,
                "validation_warnings": 1,
                "high_attention_lines": 1
            },
            "blocking_issues": [],
            "warnings": [
                {
                    "id": "QG-HIGH-ATTENTION",
                    "severity": "warning",
                    "category": "readability",
                    "title": "Contains high attention lines",
                    "message": "High attention lines count > 0",
                    "evidence": {},
                    "recommendation": ""
                }
            ],
            "recommendations": [
                "Proceed to Phase 7 readability reconstruction."
            ],
            "phase7_hints": {
                "predicate_recovery_recommended": True,
                "local_variable_recovery_recommended": True,
                "expression_simplification_recommended": True,
                "loop_readability_recommended": True,
                "agent_assistance_recommended": False
            }
        }
        
        md_file = write_quality_markdown(payload, out_dir)
        assert md_file.exists()
        
        content = md_file.read_text(encoding="utf-8")
        
        # Verify key headers exist
        assert "# Hephaestus Quality Gate" in content
        assert "## Decision" in content
        assert "## Scores" in content
        assert "## Summary Metrics" in content
        assert "## Blocking Issues" in content
        assert "## Warnings" in content
        assert "## Phase 7 Readiness" in content
        assert "## Recommended Next Steps" in content
        
        # Verify decision and scores are reported
        assert "Safe to proceed to Phase 7**: Yes" in content
        assert "Readability Readiness Score | 85.23 |" in content
        assert "Risk Score | 10.00 |" in content
        assert "Functions Total | 2 |" in content
        assert ":warning: **Contains high attention lines** (ID: QG-HIGH-ATTENTION): High attention lines count > 0" in content
        assert "Proceed to Phase 7 readability reconstruction." in content
