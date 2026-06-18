# -*- coding: utf-8 -*-
"""
Tests for Source Summary Metrics Checks
"""

from __future__ import annotations
import tempfile
from pathlib import Path
from src.validation.models import ValidationArtifacts
from src.validation.report import new_report
from src.validation.metrics import check_source_metrics

def test_check_source_metrics_valid():
    report = new_report("artifacts", strict=False)
    recon = {
        "schema_version": "5.7.2",
        "summary": {
            "instructions_total": 100,
            "instructions_lowered": 80,
            "instructions_commented": 20,
            "lowering_coverage_percent": 80.0,
            "condition_expressions_recovered": 0,
            "unsupported_instruction_kinds": {"invalid": 1}
        }
    }
    artifacts = ValidationArtifacts(
        out_dir=Path("artifacts"),
        source_reconstruction=recon,
        recovered_c="int main() { return 0; }",
        pipeline_manifest=None,
        unified_ir=None,
        phase4_semantics=None,
        missing=[]
    )
    check_source_metrics(artifacts, report)
    
    assert report["checks"]["source_summary_present"]["status"] == "ok"
    assert report["checks"]["source_summary_metrics_nonnegative"]["status"] == "ok"
    assert report["checks"]["instruction_counts_consistent"]["status"] == "ok"
    assert report["checks"]["lowering_coverage_math_valid"]["status"] == "ok"
    assert report["checks"]["unsupported_instruction_kinds_valid"]["status"] == "ok"
    assert report["checks"]["condition_expressions_zero"]["status"] == "ok"
    assert len(report["findings"]) == 0

def test_check_source_metrics_invalid():
    report = new_report("artifacts", strict=False)
    recon = {
        "schema_version": "5.7.2",
        "summary": {
            "instructions_total": 100,
            "instructions_lowered": 80,
            "instructions_commented": -10,  # Negative value
            "lowering_coverage_percent": 50.0,  # Coverage math mismatch
            "condition_expressions_recovered": 1,  # Non-zero recovered conditions
            "unsupported_instruction_kinds": {"cset": 1}  # Warning trigger
        }
    }
    artifacts = ValidationArtifacts(
        out_dir=Path("artifacts"),
        source_reconstruction=recon,
        recovered_c="int main() { return 0; }",
        pipeline_manifest=None,
        unified_ir=None,
        phase4_semantics=None,
        missing=[]
    )
    check_source_metrics(artifacts, report)
    
    # Negative value checks
    assert report["checks"]["source_summary_metrics_nonnegative"]["status"] == "failed"
    
    # Count consistency: 80 + -10 = 70 != 100
    assert report["checks"]["instruction_counts_consistent"]["status"] == "failed"
    
    # Coverage mismatch: 80/100*100 = 80.0 != 50.0
    assert report["checks"]["lowering_coverage_math_valid"]["status"] == "failed"
    
    # Non-zero recovered conditions
    assert report["checks"]["condition_expressions_zero"]["status"] == "failed"
    
    # Unsupported contains cset (warning in default mode, error in strict mode)
    assert report["checks"]["unsupported_instruction_kinds_valid"]["status"] == "warning"
    
    findings_ids = [f["id"] for f in report["findings"]]
    assert "VAL-METR-002" in findings_ids # Negative count
    assert "VAL-METR-003" in findings_ids # Math inconsistent
    assert "VAL-METR-005" in findings_ids # Coverage invalid
    assert "VAL-METR-009" in findings_ids # cset/ldp warning
    assert "VAL-COND-001" in findings_ids # Condition expressions nonzero
