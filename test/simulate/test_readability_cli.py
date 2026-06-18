# -*- coding: utf-8 -*-
"""
Tests for Readability CLI
"""

import json
import os
import sys
from pathlib import Path
import pytest

from src.readability.cli import run_build_readable_cli
from src.readability.loader import calculate_sha256
from src.readability.readable_emitter import emit_readable_c

@pytest.fixture(autouse=True)
def mock_clang_unavailable(monkeypatch):
    """By default, mock clang as unavailable so tests do not run host clang on invalid mock C code."""
    import src.readability.cli
    monkeypatch.setattr(src.readability.cli, "clang_available", lambda: False)

def test_cli_missing_recovered_c(tmp_path, capsys):
    # recovered.c is missing
    code = run_build_readable_cli(["--out-dir", str(tmp_path)])
    assert code == 1
    
    # Check JSON stdout error
    capsys.readouterr() # clear
    code_json = run_build_readable_cli(["--out-dir", str(tmp_path), "--json"])
    assert code_json == 1
    out, err = capsys.readouterr()
    data = json.loads(out.strip())
    assert data["status"] == "failed"
    assert "missing" in data["error"]

def test_cli_quality_gate_ok_and_review(tmp_path, capsys):
    # Setup recovered.c
    recovered_c = """
void main() {
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: cbz w8")) {
        return;
    }
}
"""
    (tmp_path / "recovered.c").write_text(recovered_c)
    
    # Setup quality_gate.json in review status
    qg_data = {
        "status": "review",
        "decision": {
            "safe_to_use_for_phase7": True,
            "blocked": False
        }
    }
    with open(tmp_path / "quality_gate.json", "w") as f:
        json.dump(qg_data, f)
        
    code = run_build_readable_cli(["--out-dir", str(tmp_path), "--markdown", "--no-promote-symbols"])
    assert code == 0
    
    # Check that output exists
    assert (tmp_path / "recovered_readable.c").exists()
    assert (tmp_path / "readability_report.json").exists()
    assert (tmp_path / "readability_report.md").exists()
    
    # Verify report JSON fields
    with open(tmp_path / "readability_report.json", "r") as f:
        report = json.load(f)
    assert report["schema_version"] == "readability-1.0"
    assert report["summary"]["quality_gate_status"] == "review"
    assert report["summary"]["predicates_recovered"] == 1
    assert any("quality gate requires review" in d.lower() for d in report["diagnostics"])

def test_cli_quality_gate_blocked_and_override(tmp_path, capsys):
    # Setup files
    (tmp_path / "recovered.c").write_text("void main() { if (HEPHAESTUS_UNKNOWN_COND(\"cbz w8\")) {} }")
    qg_data = {
        "status": "blocked",
        "decision": {
            "safe_to_use_for_phase7": False,
            "blocked": True
        }
    }
    with open(tmp_path / "quality_gate.json", "w") as f:
        json.dump(qg_data, f)
        
    # Blocked check
    code = run_build_readable_cli(["--out-dir", str(tmp_path)])
    assert code == 1
    assert not (tmp_path / "recovered_readable.c").exists()
    
    # Ignore check (override)
    code_override = run_build_readable_cli(["--out-dir", str(tmp_path), "--ignore-quality-gate"])
    assert code_override == 0
    assert (tmp_path / "recovered_readable.c").exists()
    
    with open(tmp_path / "readability_report.json", "r") as f:
        report = json.load(f)
    assert report["summary"]["quality_gate_status"] == "ignored"
    assert any("ignored" in d.lower() for d in report["diagnostics"])

def test_cli_hash_watchdog_violation(tmp_path, monkeypatch):
    # Setup files
    c_file = tmp_path / "recovered.c"
    c_file.write_text("void main() { if (HEPHAESTUS_UNKNOWN_COND(\"cbz w8\")) {} }")
    
    original_emit = emit_readable_c
    def fake_emit(c_code, mapping):
        # Mutate recovered.c
        c_file.write_text("void main() { /* mutated */ }")
        return original_emit(c_code, mapping)
        
    import src.readability.cli
    monkeypatch.setattr(src.readability.cli, "emit_readable_c", fake_emit)
    
    code = run_build_readable_cli(["--out-dir", str(tmp_path)])
    assert code == 1
    # Check that output was deleted or rolled back
    assert not (tmp_path / "recovered_readable.c").exists()

def test_cli_clang_mocked_results(tmp_path, monkeypatch):
    # Setup files
    (tmp_path / "recovered.c").write_text("void main() { if (HEPHAESTUS_UNKNOWN_COND(\"cbz w8\")) {} }")
    
    import src.readability.cli
    monkeypatch.setattr(src.readability.cli, "clang_available", lambda: True)
    
    # Test case 1: Clang returns error
    monkeypatch.setattr(src.readability.cli, "run_clang_syntax_check", lambda path: {"status": "failed", "errors": 1, "warnings": 0})
    code_err = run_build_readable_cli(["--out-dir", str(tmp_path)])
    assert code_err == 1
    with open(tmp_path / "readability_report.json", "r") as f:
        report = json.load(f)
    assert report["summary"]["clang_syntax_status"] == "failed"
    
    # Test case 2: Clang returns warning
    monkeypatch.setattr(src.readability.cli, "run_clang_syntax_check", lambda path: {"status": "ok", "errors": 0, "warnings": 2})
    code_warn = run_build_readable_cli(["--out-dir", str(tmp_path)])
    assert code_warn == 0
    with open(tmp_path / "readability_report.json", "r") as f:
        report2 = json.load(f)
    assert report2["summary"]["clang_syntax_status"] == "warning"
