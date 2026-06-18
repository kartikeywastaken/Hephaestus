# -*- coding: utf-8 -*-
"""
Tests for Evidence Index CLI
"""

from __future__ import annotations
import json
import tempfile
from pathlib import Path
from src.validation.evidence_index.cli import run_build_evidence_index_cli

def test_evidence_index_cli_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        
        recon_data = {
            "schema_version": "5.7.2",
            "summary": {"unsupported_instruction_kinds": {}},
            "data": {"functions": []}
        }
        c_content = "int main() { return 0; }"
        
        with open(out_dir / "source_reconstruction.json", "w") as f:
            json.dump(recon_data, f)
        with open(out_dir / "recovered.c", "w") as f:
            f.write(c_content)
            
        # Run CLI
        exit_code = run_build_evidence_index_cli(["--out-dir", str(out_dir)])
        assert exit_code == 0
        
        # Verify evidence_index.json is written
        idx_file = out_dir / "evidence_index.json"
        assert idx_file.exists()

def test_evidence_index_cli_json_mode():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        
        recon_data = {
            "schema_version": "5.7.2",
            "summary": {"unsupported_instruction_kinds": {}},
            "data": {"functions": []}
        }
        c_content = "int main() { return 0; }"
        
        with open(out_dir / "source_reconstruction.json", "w") as f:
            json.dump(recon_data, f)
        with open(out_dir / "recovered.c", "w") as f:
            f.write(c_content)
            
        # Run CLI in JSON mode
        import io
        import sys
        
        stdout_capture = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = stdout_capture
            exit_code = run_build_evidence_index_cli(["--out-dir", str(out_dir), "--json"])
        finally:
            sys.stdout = old_stdout
            
        assert exit_code == 0
        output = json.loads(stdout_capture.getvalue())
        assert output["status"] == "ok"
        assert "statements_total" in output

def test_evidence_index_cli_missing_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        
        # Missing inputs
        exit_code = run_build_evidence_index_cli(["--out-dir", str(out_dir)])
        assert exit_code == 1
