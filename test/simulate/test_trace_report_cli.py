# -*- coding: utf-8 -*-
"""
Tests for Trace Report CLI
"""

from __future__ import annotations
import tempfile
import json
import hashlib
from pathlib import Path
from src.validation.trace_report.cli import run_build_trace_report_cli

def get_file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def create_valid_trace_inputs(directory: Path):
    evidence_index = {
        "schema_version": "evidence-index-1.0",
        "phase": "6.2",
        "summary": {
            "functions_total": 0,
            "statements_total": 0
        },
        "global_statements": [],
        "functions": []
    }
    
    validation_report = {
        "schema_version": "1.0",
        "status": "ok",
        "findings": []
    }
    
    recon_data = {
        "schema_version": "5.7.2",
        "summary": {}
    }
    
    c_content = "int main() { return 0; }"
    
    with open(directory / "evidence_index.json", "w") as f:
        json.dump(evidence_index, f)
    with open(directory / "validation_report.json", "w") as f:
        json.dump(validation_report, f)
    with open(directory / "source_reconstruction.json", "w") as f:
        json.dump(recon_data, f)
    with open(directory / "recovered.c", "w") as f:
        f.write(c_content)

def test_cli_help():
    # Calling with invalid arguments or help should raise/exit, handled by argparse
    # Argparse raises SystemExit on --help
    exit_code = run_build_trace_report_cli(["--help"])
    assert exit_code == 2

def test_cli_success_default():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        create_valid_trace_inputs(out_dir)
        
        # Verify hashes
        hashes_before = {
            "recovered.c": get_file_hash(out_dir / "recovered.c"),
            "source_reconstruction.json": get_file_hash(out_dir / "source_reconstruction.json"),
            "evidence_index.json": get_file_hash(out_dir / "evidence_index.json"),
            "validation_report.json": get_file_hash(out_dir / "validation_report.json")
        }
        
        exit_code = run_build_trace_report_cli([
            "--out-dir", str(out_dir),
            "--markdown"
        ])
        assert exit_code == 0
        
        # Verify artifacts written
        assert (out_dir / "trace_report.json").exists()
        assert (out_dir / "trace_report.md").exists()
        
        # Verify hashes remained identical
        assert get_file_hash(out_dir / "recovered.c") == hashes_before["recovered.c"]
        assert get_file_hash(out_dir / "source_reconstruction.json") == hashes_before["source_reconstruction.json"]
        assert get_file_hash(out_dir / "evidence_index.json") == hashes_before["evidence_index.json"]
        assert get_file_hash(out_dir / "validation_report.json") == hashes_before["validation_report.json"]

def test_cli_missing_evidence_index():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        create_valid_trace_inputs(out_dir)
        
        # Remove evidence_index.json
        (out_dir / "evidence_index.json").unlink()
        
        exit_code = run_build_trace_report_cli([
            "--out-dir", str(out_dir),
            "--require-evidence-index"
        ])
        assert exit_code == 1

def test_cli_missing_validation_report():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        create_valid_trace_inputs(out_dir)
        
        # Remove validation_report.json
        (out_dir / "validation_report.json").unlink()
        
        # Require validation report
        exit_code = run_build_trace_report_cli([
            "--out-dir", str(out_dir),
            "--require-validation"
        ])
        assert exit_code == 1

def test_cli_mutated_during_generation():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        create_valid_trace_inputs(out_dir)
        
        # To simulate a mutation during generation, we patch build_trace_report_payload
        # to mutate recovered.c when it runs.
        from unittest.mock import patch
        
        original_build = "src.validation.trace_report.cli.build_trace_report_payload"
        
        def fake_build(*args, **kwargs):
            # Mutate recovered.c
            with open(out_dir / "recovered.c", "w") as f:
                f.write("MUTATED!")
            return {"summary": {"statements_total": 0, "high_attention_lines": 0}, "schema_version": "trace-report-1.0"}
            
        with patch(original_build, side_effect=fake_build):
            exit_code = run_build_trace_report_cli([
                "--out-dir", str(out_dir)
            ])
            assert exit_code == 2 # verify it reports error on mutation
