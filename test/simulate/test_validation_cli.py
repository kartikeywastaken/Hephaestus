# -*- coding: utf-8 -*-
"""
Tests for Validation CLI
"""

from __future__ import annotations
import tempfile
import json
import hashlib
from pathlib import Path
from unittest.mock import patch
from src.validation.cli import run_validate_cli

def create_valid_test_artifacts(directory: Path):
    recon_data = {
        "schema_version": "5.7.2",
        "summary": {
            "instructions_total": 10,
            "instructions_lowered": 10,
            "instructions_commented": 0,
            "lowering_coverage_percent": 100.0,
            "condition_expressions_recovered": 0,
            "unsupported_instruction_kinds": {}
        },
        "functions": []
    }
    c_content = "int main() { return 0; }"
    manifest_data = {
        "schema_version": "pipeline-1.0",
        "status": "ok",
        "stages": []
    }
    
    with open(directory / "source_reconstruction.json", "w") as f:
        json.dump(recon_data, f)
    with open(directory / "recovered.c", "w") as f:
        f.write(c_content)
    with open(directory / "pipeline_manifest.json", "w") as f:
        json.dump(manifest_data, f)

def get_file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

@patch("src.validation.clang_check.run_clang_syntax_check")
def test_cli_success(mock_clang):
    # Mock clang to succeed with 0 errors
    mock_clang.return_value = {
        "attempted": True,
        "status": "ok",
        "errors": 0,
        "warnings": 0,
        "diagnostics": []
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        create_valid_test_artifacts(out_dir)
        
        # Verify hashes before CLI run
        recon_path = out_dir / "source_reconstruction.json"
        c_path = out_dir / "recovered.c"
        hash_recon_before = get_file_hash(recon_path)
        hash_c_before = get_file_hash(c_path)
        
        exit_code = run_validate_cli(["--out-dir", str(out_dir)])
        assert exit_code == 0
        
        # Check report was written
        report_path = out_dir / "validation_report.json"
        assert report_path.exists()
        with open(report_path, "r") as f:
            report = json.load(f)
        assert report["status"] in ("ok", "warning")
        assert report["summary"]["errors"] == 0
        
        # Verify hashes are unchanged
        assert get_file_hash(recon_path) == hash_recon_before
        assert get_file_hash(c_path) == hash_c_before

@patch("src.validation.clang_check.run_clang_syntax_check")
def test_cli_failed_check(mock_clang):
    mock_clang.return_value = {
        "attempted": True,
        "status": "ok",
        "errors": 0,
        "warnings": 0,
        "diagnostics": []
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        create_valid_test_artifacts(out_dir)
        
        # Introduce a metrics error: condition_expressions_recovered != 0
        with open(out_dir / "source_reconstruction.json", "r") as f:
            recon = json.load(f)
        recon["summary"]["condition_expressions_recovered"] = 1
        with open(out_dir / "source_reconstruction.json", "w") as f:
            json.dump(recon, f)
            
        exit_code = run_validate_cli(["--out-dir", str(out_dir)])
        assert exit_code == 1  # status failed -> exit code 1
        
        report_path = out_dir / "validation_report.json"
        with open(report_path, "r") as f:
            report = json.load(f)
        assert report["status"] == "failed"
        assert report["summary"]["errors"] == 1

@patch("src.validation.clang_check.run_clang_syntax_check")
def test_cli_json_mode(mock_clang, capsys):
    mock_clang.return_value = {
        "attempted": True,
        "status": "ok",
        "errors": 0,
        "warnings": 0,
        "diagnostics": []
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        create_valid_test_artifacts(out_dir)
        
        exit_code = run_validate_cli(["--out-dir", str(out_dir), "--json"])
        assert exit_code == 0
        
        captured = capsys.readouterr()
        # Verify stdout prints only json
        lines = captured.out.strip().splitlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["status"] in ("ok", "warning")
        assert data["errors"] == 0
        assert "report" in data

@patch("src.validation.cli.run_all_validation_checks")
def test_cli_shows_top_findings(mock_checks, capsys):
    def fake_checks(artifacts, report, no_clang=False):
        from src.validation.report import add_check, add_finding
        add_check(report, "fake_check", "failed", "error", "Failed.")
        add_finding(report, "VAL-FAKE-001", "error", "c_safety", "Fake Error", "This is a fake error message.")
        add_finding(report, "VAL-FAKE-002", "warning", "c_safety", "Fake Warning", "This is a fake warning message.")
        report["status"] = "failed"
        report["summary"]["errors"] = 1
        report["summary"]["warnings"] = 1
        
    mock_checks.side_effect = fake_checks
    
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        create_valid_test_artifacts(out_dir)
        
        exit_code = run_validate_cli(["--out-dir", str(out_dir)])
        assert exit_code == 1
        
        captured = capsys.readouterr()
        # Header lines should have prefix
        assert "[validate] status=failed" in captured.out
        assert "[validate] top findings:" in captured.out
        
        # Nested finding lines should NOT have the prefix
        assert "[validate]   error" not in captured.out
        assert "[validate]     This is a fake" not in captured.out
        
        # Check actual output text is correct
        assert "  error VAL-FAKE-001 Fake Error" in captured.out
        assert "    This is a fake error message." in captured.out
        assert "  warning VAL-FAKE-002 Fake Warning" in captured.out
        assert "    This is a fake warning message." in captured.out

@patch("src.validation.cli.run_all_validation_checks")
def test_cli_top_findings_capped(mock_checks, capsys):
    def fake_checks(artifacts, report, no_clang=False):
        from src.validation.report import add_finding
        for i in range(5):
            add_finding(report, f"VAL-FAKE-00{i}", "error", "c_safety", f"Fake Error {i}", f"Msg {i}")
        report["status"] = "failed"
        report["summary"]["errors"] = 5
        
    mock_checks.side_effect = fake_checks
    
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        create_valid_test_artifacts(out_dir)
        
        exit_code = run_validate_cli(["--out-dir", str(out_dir)])
        assert exit_code == 1
        
        captured = capsys.readouterr()
        assert "top findings:" in captured.out
        # Should contain first 3
        assert "Fake Error 0" in captured.out
        assert "Fake Error 1" in captured.out
        assert "Fake Error 2" in captured.out
        # Should NOT contain 4th and 5th
        assert "Fake Error 3" not in captured.out
        assert "Fake Error 4" not in captured.out

@patch("src.validation.cli.run_all_validation_checks")
def test_cli_json_mode_clean(mock_checks, capsys):
    def fake_checks(artifacts, report, no_clang=False):
        from src.validation.report import add_finding
        add_finding(report, "VAL-FAKE-001", "error", "c_safety", "Fake Error", "Msg")
        report["status"] = "failed"
        report["summary"]["errors"] = 1
        
    mock_checks.side_effect = fake_checks
    
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        create_valid_test_artifacts(out_dir)
        
        exit_code = run_validate_cli(["--out-dir", str(out_dir), "--json"])
        assert exit_code == 1
        
        captured = capsys.readouterr()
        # stdout should be clean JSON, no "top findings", no "[validate]"
        lines = captured.out.strip().splitlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["status"] == "failed"
        assert "top findings" not in captured.out
        assert "[validate]" not in captured.out

@patch("src.validation.clang_check.run_clang_syntax_check")
def test_strict_mode_does_not_promote_clang_warnings(mock_clang):
    # Clang runs and returns warnings but no errors
    mock_clang.return_value = {
        "attempted": True,
        "status": "ok",
        "errors": 0,
        "warnings": 5,
        "diagnostics": ["warning: test warning"]
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        create_valid_test_artifacts(out_dir)
        with open(out_dir / "unified_ir.json", "w") as f:
            f.write('{"schema_version": "2.0.0"}')
        with open(out_dir / "phase4_semantics.json", "w") as f:
            f.write('{"schema_version": "4D.1.0"}')
        
        exit_code = run_validate_cli(["--out-dir", str(out_dir), "--strict"])
        assert exit_code == 0
        
        report_path = out_dir / "validation_report.json"
        with open(report_path, "r") as f:
            report = json.load(f)
        assert report["status"] == "warning"
        assert report["summary"]["errors"] == 0
        assert report["summary"]["warnings"] > 0

@patch("src.validation.clang_check.run_clang_syntax_check")
def test_strict_mode_promotes_missing_artifact(mock_clang):
    mock_clang.return_value = {
        "attempted": True,
        "status": "ok",
        "errors": 0,
        "warnings": 0,
        "diagnostics": []
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        
        # Write ONLY required files, leave recommended files missing
        recon_data = {
            "schema_version": "5.7.2",
            "summary": {
                "instructions_total": 0,
                "instructions_lowered": 0,
                "instructions_commented": 0,
                "lowering_coverage_percent": 100.0,
                "condition_expressions_recovered": 0,
                "unsupported_instruction_kinds": {}
            },
            "functions": []
        }
        c_content = "int main() { return 0; }"
        with open(out_dir / "source_reconstruction.json", "w") as f:
            json.dump(recon_data, f)
        with open(out_dir / "recovered.c", "w") as f:
            f.write(c_content)
            
        # Default mode: missing recommended is a warning, exit 0
        exit_code_default = run_validate_cli(["--out-dir", str(out_dir)])
        assert exit_code_default == 0
        with open(out_dir / "validation_report.json", "r") as f:
            report_default = json.load(f)
        assert report_default["status"] == "warning"
        
        # Strict mode: missing recommended is an error, exit 1
        exit_code_strict = run_validate_cli(["--out-dir", str(out_dir), "--strict"])
        assert exit_code_strict == 1
        with open(out_dir / "validation_report.json", "r") as f:
            report_strict = json.load(f)
        assert report_strict["status"] == "failed"

def test_read_only_hash_invariant():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        create_valid_test_artifacts(out_dir)
        
        recon_path = out_dir / "source_reconstruction.json"
        c_path = out_dir / "recovered.c"
        
        hash_recon_before = get_file_hash(recon_path)
        hash_c_before = get_file_hash(c_path)
        
        exit_code = run_validate_cli(["--out-dir", str(out_dir)])
        assert exit_code == 0
        
        assert get_file_hash(recon_path) == hash_recon_before
        assert get_file_hash(c_path) == hash_c_before

