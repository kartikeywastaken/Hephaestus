# -*- coding: utf-8 -*-
"""
Tests for Quality Gate CLI
"""

from __future__ import annotations
import tempfile
import json
from pathlib import Path
from src.validation.quality_gate.cli import run_quality_gate_cli

def create_mock_artifacts(out_dir: Path, status: str = "ok", schema_valid: bool = True):
    recon_data = {"schema_version": "5.7.2", "summary": {"condition_expressions_recovered": 0}}
    c_content = "int main() { return 0; }"
    findings = []
    if status == "failed":
        findings.append({
            "id": "VAL-C-001",
            "category": "c_safety",
            "severity": "error",
            "title": "Safety violation",
            "message": "Structure definition detected"
        })
    val_data = {
        "schema_version": "validation-1.0",
        "status": status,
        "findings": findings,
        "summary": {"errors": len(findings), "warnings": 0}
    }
    ev_data = {"schema_version": "evidence-index-1.0" if schema_valid else "invalid"}
    trace_data = {
        "schema_version": "trace-report-1.0",
        "summary": {
            "functions_total": 1,
            "statements_total": 10,
            "evidence_backed_statements": 9,
            "high_attention_lines": 0,
            "generated_scaffold_statements": 0,
            "commentary_only_statements": 0
        },
        "category_summary": {"executable_lowered": 9, "declaration": 1},
        "confidence_summary": {"evidence_backed": 9, "generated_scaffold": 1},
        "global_statements": [],
        "functions": [],
        "unattached_validation_findings": []
    }
    
    with open(out_dir / "source_reconstruction.json", "w") as f:
        json.dump(recon_data, f)
    with open(out_dir / "recovered.c", "w") as f:
        f.write(c_content)
    with open(out_dir / "validation_report.json", "w") as f:
        json.dump(val_data, f)
    with open(out_dir / "evidence_index.json", "w") as f:
        json.dump(ev_data, f)
    with open(out_dir / "trace_report.json", "w") as f:
        json.dump(trace_data, f)

def test_cli_help():
    # Argparse --help will raise SystemExit
    exit_code = run_quality_gate_cli(["--help"])
    assert exit_code == 2

def test_cli_ready_success(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        create_mock_artifacts(out_dir, "ok")
        
        exit_code = run_quality_gate_cli(["--out-dir", str(out_dir), "--markdown"])
        assert exit_code == 0
        assert (out_dir / "quality_gate.json").exists()
        assert (out_dir / "quality_gate.md").exists()
        
        captured = capsys.readouterr()
        assert "status=ready" in captured.out

def test_cli_blocked_failure(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        create_mock_artifacts(out_dir, "failed") # validator failed -> blocks
        
        exit_code = run_quality_gate_cli(["--out-dir", str(out_dir)])
        assert exit_code == 1
        
        captured = capsys.readouterr()
        assert "status=blocked" in captured.out
        assert "Blocking issues:" in captured.err

def test_cli_json_mode(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        create_mock_artifacts(out_dir, "ok")
        
        exit_code = run_quality_gate_cli(["--out-dir", str(out_dir), "--json"])
        assert exit_code == 0
        
        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["status"] == "ready"
        assert data["safe_to_use_for_phase7"] is True
        assert "quality_gate.json" in data["report"]
