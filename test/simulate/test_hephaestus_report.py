# -*- coding: utf-8 -*-
"""
Tests for hephaestus_report.json Consolidated Reporting
"""

from __future__ import annotations
import json
import tempfile
from pathlib import Path

from src.pipeline.artifact_finalizer import finalize_artifacts


def test_hephaestus_report_status_mapping():
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td)
        work_dir = out_dir / ".work"
        work_dir.mkdir()

        # Mock successful files
        (work_dir / "recovered.c").write_text("int x = 10;", encoding="utf-8")
        (work_dir / "recovered_readable.c").write_text("int x = 10;", encoding="utf-8")
        
        # Scenario 1: Everything passes
        manifest = {"status": "ok", "stages": [{"name": "generate_agent_source"}], "summary": {"agent_enabled": True}}
        with open(work_dir / "pipeline_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f)
            
        rep1 = finalize_artifacts(out_dir, work_dir=work_dir, artifact_mode="debug")
        assert rep1["status"] == "ok"

        # Scenario 2: Validation failure warning
        val = {"validation_passed": False, "clang_status": "failed", "issues": ["Syntax error"]}
        with open(work_dir / "agent_source_validation.json", "w", encoding="utf-8") as f:
            json.dump(val, f)

        rep2 = finalize_artifacts(out_dir, work_dir=work_dir, artifact_mode="debug")
        assert rep2["status"] == "warning"

        # Scenario 3: Forbidden claim in recovered C
        (work_dir / "recovered_readable.c").write_text("// This code is semantically equivalent to the original.", encoding="utf-8")
        rep3 = finalize_artifacts(out_dir, work_dir=work_dir, artifact_mode="debug")
        assert rep3["status"] == "failed"
        assert len(rep3["validation"]["forbidden_claims_found"]) > 0


def test_ordering_bug_detection():
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td)
        work_dir = out_dir / ".work"
        work_dir.mkdir()

        # Mock the conditions of the ordering bug
        suggestions = {"suggestions": [{"function": "_checksum"}]}
        plan = {"entries": [{"function": "_checksum", "disabled": True}]}
        report = {"function_records": [{"function": "_main", "status": "generated"}, {"function": "_checksum", "status": "copied_unchanged"}]}

        with open(work_dir / "agent_suggestions.json", "w", encoding="utf-8") as f:
            json.dump(suggestions, f)
        with open(work_dir / "agent_source_plan.json", "w", encoding="utf-8") as f:
            json.dump(plan, f)
        with open(work_dir / "agent_source_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f)

        # Finalize and check diagnostics
        rep = finalize_artifacts(out_dir, work_dir=work_dir, artifact_mode="debug")
        
        has_bug_diag = any("mismatch detected" in d for d in rep["diagnostics"])
        assert has_bug_diag is True
