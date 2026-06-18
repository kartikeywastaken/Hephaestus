# -*- coding: utf-8 -*-
"""
Tests for Validation Report Builder
"""

from __future__ import annotations
import json
import tempfile
from pathlib import Path
from src.validation.report import new_report, add_check, add_finding, finalize_report, write_report

def test_report_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        
        # 1. New Report
        report = new_report(out_dir, strict=False)
        assert report["schema_version"] == "validation-1.0"
        assert report["phase"] == "6.1"
        assert report["status"] == "ok"
        assert report["strict"] is False
        assert len(report["checks"]) == 0
        assert len(report["findings"]) == 0
        
        # 2. Add Check
        add_check(
            report=report,
            name="schema_versions_valid",
            status="ok",
            severity="error",
            message="Schema versions are fine."
        )
        assert len(report["checks"]) == 1
        assert report["checks"]["schema_versions_valid"]["status"] == "ok"
        
        # 3. Add Finding
        add_finding(
            report=report,
            finding_id="VAL-COND-001",
            severity="warning",
            category="condition_safety",
            title="Non-zero condition expressions",
            message="Condition expressions recovered was 1.",
            artifact="source_reconstruction.json"
        )
        assert len(report["findings"]) == 1
        assert report["findings"][0]["id"] == "VAL-COND-001"
        assert report["findings"][0]["severity"] == "warning"
        
        # 4. Finalize
        final_report = finalize_report(report)
        assert final_report["status"] == "warning"
        assert final_report["summary"]["errors"] == 0
        assert final_report["summary"]["warnings"] == 1
        assert final_report["summary"]["checks_total"] == 1
        assert final_report["summary"]["checks_ok"] == 1
        assert final_report["summary"]["checks_failed"] == 0
        
        # 5. Add error finding and check status failure
        add_check(
            report=report,
            name="required_artifacts_present",
            status="failed",
            severity="error",
            message="Missing required file."
        )
        add_finding(
            report=report,
            finding_id="VAL-PRES-001",
            severity="error",
            category="artifact_presence",
            title="Required file missing",
            message="recovered.c missing",
            artifact="recovered.c"
        )
        final_report = finalize_report(report)
        assert final_report["status"] == "failed"
        assert final_report["summary"]["errors"] == 1
        assert final_report["summary"]["checks_total"] == 2
        assert final_report["summary"]["checks_failed"] == 1
        
        # 6. Write
        path = write_report(final_report, out_dir)
        assert path.exists()
        with open(path, "r") as f:
            data = json.load(f)
        assert data["schema_version"] == "validation-1.0"
        assert data["status"] == "failed"
        assert len(data["findings"]) == 2

def test_val_evid_008_accounting_mismatch():
    from src.validation.models import ValidationArtifacts
    from src.validation.evidence import check_evidence
    from src.validation.report import new_report, finalize_report
    
    # sum_unsupported_kinds is 1, unsupported_comment_count is 17
    # strict = False -> warning
    artifacts = ValidationArtifacts(
        out_dir=Path("."),
        source_reconstruction={
            "summary": {
                "unsupported_instruction_kinds": {"invalid": 1}
            }
        },
        recovered_c="/* unsupported */\n" * 17,
        pipeline_manifest=None,
        unified_ir=None,
        phase4_semantics=None,
        missing=[]
    )
    
    # 1. Test default mode (strict=False) -> Warning
    report = new_report(Path("."), strict=False)
    check_evidence(artifacts, report)
    finalize_report(report)
    
    assert report["status"] == "warning"
    assert len(report["findings"]) >= 1
    
    # Find VAL-EVID-008 finding
    finding = next((f for f in report["findings"] if f["id"] == "VAL-EVID-008"), None)
    assert finding is not None
    assert finding["severity"] == "warning"
    assert finding["title"] == "Unsupported comment accounting mismatch"
    assert "do not exactly match" in finding["message"]
    assert finding["evidence"]["unsupported_comments_in_recovered_c"] == 17
    assert finding["evidence"]["unsupported_instruction_kinds_total"] == 1
    assert finding["evidence"]["difference"] == 16
    assert "Phase 6.2" in finding["recommendation"]
    
    # 2. Test strict mode (strict=True) -> Failed (due to large mismatch)
    report_strict = new_report(Path("."), strict=True)
    check_evidence(artifacts, report_strict)
    finalize_report(report_strict)
    
    assert report_strict["status"] == "failed"
    finding_strict = next((f for f in report_strict["findings"] if f["id"] == "VAL-EVID-008"), None)
    assert finding_strict is not None
    assert finding_strict["severity"] == "error"

def test_inspect_validation_report(capsys):
    from scripts.inspect_validation_report import inspect_report
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        report_data = {
            "schema_version": "validation-1.0",
            "status": "failed",
            "summary": {
                "errors": 1,
                "warnings": 1,
                "checks_total": 28,
                "checks_ok": 27,
                "checks_failed": 1
            },
            "checks": {
                "unsupported_accounting": {
                    "status": "failed",
                    "severity": "warning",
                    "message": "Unsupported instruction accounting mismatch found.",
                    "details": {"diff": 16}
                }
            },
            "findings": [
                {
                    "id": "VAL-EVID-008",
                    "severity": "error",
                    "category": "unsupported_accounting",
                    "title": "Unsupported comment accounting mismatch",
                    "message": "recovered.c contains unsupported-style comments that do not exactly match.",
                    "recommendation": "Keep the finding visible."
                }
            ]
        }
        report_path = out_dir / "validation_report.json"
        with open(report_path, "w") as f:
            json.dump(report_data, f)
            
        inspect_report(report_path)
        captured = capsys.readouterr()
        
        assert "status: failed" in captured.out
        assert "summary: errors=1 warnings=1 checks=27/28" in captured.out
        assert "failed/warning checks:" in captured.out
        assert "unsupported_accounting failed warning" in captured.out
        assert "Unsupported instruction accounting mismatch found." in captured.out
        assert "findings:" in captured.out
        assert "error VAL-EVID-008 unsupported_accounting - Unsupported comment accounting mismatch" in captured.out
        assert "recovered.c contains unsupported-style comments" in captured.out
        assert "Keep the finding visible." in captured.out
        
        # Verify no noisy labels in output
        assert "recommendation:" not in captured.out
        assert "message:" not in captured.out
