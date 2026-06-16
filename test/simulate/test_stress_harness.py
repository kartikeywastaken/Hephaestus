# -*- coding: utf-8 -*-
"""
Tests for Deterministic Stress Test Generator and Harness
"""

from __future__ import annotations
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.pipeline.stress import generate_stress_c, compile_stress_source, run_stress_test

def test_generate_stress_c_determinism():
    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = Path(tmpdir)
        path1 = dir_path / "stress_1.c"
        path2 = dir_path / "stress_2.c"
        
        # Generate twice with same seed and check matching
        info1 = generate_stress_c("small", path1, seed=42)
        info2 = generate_stress_c("small", path2, seed=42)
        
        assert info1["loc"] == info2["loc"]
        assert info1["features"] == info2["features"]
        
        with open(path1, "r", encoding="utf-8") as f1, open(path2, "r", encoding="utf-8") as f2:
            assert f1.read() == f2.read()

def test_generate_stress_c_features():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "stress.c"
        generate_stress_c("small", out_path, seed=123)
        
        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Check presence of required features
        assert "for" in content
        assert "stack_arr" in content
        assert "div_u" in content
        assert "div_s" in content
        assert "fptr_table" in content
        assert "printf" in content
        assert "switch" in content
        assert "sink" in content

def test_generate_stress_c_profiles():
    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = Path(tmpdir)
        
        # Valid profiles
        info_small = generate_stress_c("small", dir_path / "small.c", seed=10)
        info_med = generate_stress_c("medium", dir_path / "medium.c", seed=10)
        info_hard = generate_stress_c("hard", dir_path / "hard.c", seed=10)
        
        assert info_small["loc"] < info_med["loc"]
        assert info_med["loc"] < info_hard["loc"]
        
        # Invalid profile
        with pytest.raises(ValueError, match="Unknown stress profile"):
            generate_stress_c("invalid_profile", dir_path / "err.c", seed=10)

def test_compile_stress_source_no_clang():
    # Force shutil.which to return None for clang
    with patch("shutil.which", return_value=None):
        res = compile_stress_source(Path("dummy.c"), Path("dummy_bin"))
        assert res["compiled"] is False
        assert "clang command not found" in res["compile_error"]

def test_run_stress_test_mocked_pipeline():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        
        # Mock compile_stress_source to return compiled=True and run_pipeline to return a manifest
        # so we can run stress harness end-to-end without real clang compile or extractors
        mock_manifest = {
            "status": "ok",
            "summary": {
                "source_schema_version": "5.7.2",
                "functions_total": 5,
                "instructions_total": 120,
                "instructions_lowered": 118,
                "instructions_commented": 2,
                "lowering_coverage_percent": 98.33,
                "condition_expressions_recovered": 0,
                "declarations_total": 15
            }
        }
        
        # Mock files written by decompiler run so that run_artifact_checks does not complain
        with open(out_dir / "unified_ir.json", "w") as f: f.write("{}")
        with open(out_dir / "structuring_analysis.json", "w") as f: f.write("[]")
        with open(out_dir / "structuring_regions.json", "w") as f: f.write("[]")
        with open(out_dir / "type_recovery.json", "w") as f: f.write("{}")
        with open(out_dir / "phase4_semantics.json", "w") as f: f.write("{}")
        with open(out_dir / "source_reconstruction.json", "w") as f:
            json.dump({"schema_version": "5.7.2", "summary": {"condition_expressions_recovered": 0}}, f)
        with open(out_dir / "recovered.c", "w") as f:
            f.write("static int HEPHAESTUS_UNKNOWN_COND(const char *e) { return 0; }\nvoid main() {}")
            
        with patch("src.pipeline.stress.compile_stress_source") as m_compile, \
             patch("src.pipeline.stress.run_pipeline") as m_pipeline, \
             patch("src.pipeline.stress.run_clang_syntax_check") as m_syntax:
             
            m_compile.return_value = {"path": "dummy", "compiled": True, "compile_error": None}
            m_pipeline.return_value = mock_manifest
            m_syntax.return_value = {
                "clang_syntax_check_attempted": True,
                "clang_syntax_check_status": "ok",
                "clang_syntax_errors": 0,
                "clang_syntax_warnings": 1
            }
            
            report = run_stress_test("small", str(out_dir), clean=False, seed=42)
            
            assert report["schema_version"] == "stress-1.0"
            assert report["profile"] == "small"
            assert report["status"] == "ok"
            assert report["pipeline"]["status"] == "ok"
            assert report["artifact_checks"]["required_files_present"] is True
            assert report["metrics"]["instructions_total"] == 120
            assert report["diagnostics"]["clang_syntax_errors"] == 0
            
            # Assert report file written to disk
            assert (out_dir / "stress_report.json").exists()
