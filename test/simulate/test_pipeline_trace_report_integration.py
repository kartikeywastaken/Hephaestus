# -*- coding: utf-8 -*-
"""
Tests for Pipeline Integration of Trace Report Generation and Validator Options
"""

from __future__ import annotations
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.pipeline.runner import run_pipeline

@pytest.fixture
def mock_stages():
    with patch("src.pipeline.runner.run_stage_extract") as m_ext, \
         patch("src.pipeline.runner.run_stage_analyze_cfg") as m_cfg, \
         patch("src.pipeline.runner.run_stage_recover_semantics") as m_rec_sem, \
         patch("src.pipeline.runner.run_stage_refine_semantics") as m_ref_sem, \
         patch("src.pipeline.runner.run_stage_recover_layouts") as m_rec_lay, \
         patch("src.pipeline.runner.run_stage_finalize_semantics") as m_fin_sem, \
         patch("src.pipeline.runner.run_stage_reconstruct_source") as m_rec_src:
         
        m_ext.return_value = ["unified_ir.json"]
        m_cfg.return_value = ["structuring_analysis.json", "structuring_regions.json"]
        m_rec_sem.return_value = ["type_recovery.json"]
        m_ref_sem.return_value = ["semantic_recovery.json"]
        m_rec_lay.return_value = ["layout_recovery.json"]
        m_fin_sem.return_value = ["phase4_semantics.json"]
        m_rec_src.return_value = ["source_reconstruction.json", "recovered.c"]
        
        yield {
            "extract": m_ext,
            "analyze_cfg": m_cfg,
            "recover_semantics": m_rec_sem,
            "refine_semantics": m_ref_sem,
            "recover_layouts": m_rec_lay,
            "finalize_semantics": m_fin_sem,
            "reconstruct_source": m_rec_src
        }

def create_dummy_decompilation_output(directory: Path):
    recon_data = {
        "schema_version": "5.7.2",
        "summary": {
            "instructions_total": 5,
            "instructions_lowered": 5,
            "instructions_commented": 0,
            "lowering_coverage_percent": 100.0,
            "condition_expressions_recovered": 0,
            "unsupported_instruction_kinds": {}
        },
        "data": {
            "functions": [
                {
                    "name": "main",
                    "c_name": "main",
                    "entry_point": "0x1000",
                    "lowered_statements": []
                }
            ]
        }
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

@patch("src.validation.clang_check.run_clang_syntax_check")
def test_pipeline_trace_report_success(mock_clang, mock_stages):
    mock_clang.return_value = {
        "attempted": True,
        "status": "ok",
        "errors": 0,
        "warnings": 0,
        "diagnostics": []
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir).resolve()
        create_dummy_decompilation_output(out_dir)
        
        manifest = run_pipeline(
            binary_path="dummy_bin",
            out_dir=str(out_dir),
            use_ghidra=False,
            use_radare2=True,
            clean=False,
            validate=True,
            trace_report=True,
            artifact_mode="debug"
        )
        
        assert manifest["status"] == "ok"
        
        # Verify stages recorded
        stages_run = [s["name"] for s in manifest["stages"]]
        assert "build_evidence_index" in stages_run
        assert "validate" in stages_run
        assert "build_trace_report" in stages_run
        
        # Verify trace files exist
        assert (out_dir / ".work" / "evidence_index.json").exists()
        assert (out_dir / ".work" / "trace_report.json").exists()
        assert (out_dir / ".work" / "trace_report.md").exists()
        assert (out_dir / ".work" / "validation_report.json").exists()
        
        # Verify final_outputs registry
        assert "trace_report" in manifest["final_outputs"]
        assert "trace_report_markdown" in manifest["final_outputs"]
        assert manifest["final_outputs"]["trace_report"] == str(out_dir / ".work" / "trace_report.json")
        assert manifest["final_outputs"]["trace_report_markdown"] == str(out_dir / ".work" / "trace_report.md")

@patch("src.validation.clang_check.run_clang_syntax_check")
def test_pipeline_require_trace_report_missing(mock_clang, mock_stages):
    mock_clang.return_value = {
        "attempted": True,
        "status": "ok",
        "errors": 0,
        "warnings": 0,
        "diagnostics": []
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir).resolve()
        create_dummy_decompilation_output(out_dir)
        
        # Run validate and require trace report, but do NOT run trace report generation stage
        manifest = run_pipeline(
            binary_path="dummy_bin",
            out_dir=str(out_dir),
            use_ghidra=False,
            use_radare2=True,
            validate=True,
            validate_strict=True,
            require_trace_report=True,
            trace_report=False,
            artifact_mode="debug"
        )
        
        # Overall status should fail because validation failed
        assert manifest["status"] == "failed"
        
        # Check validation report findings
        report_path = out_dir / ".work" / "validation_report.json"
        assert report_path.exists()
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
            
        assert report["status"] == "failed"
        
        # Check VAL-EVID-028 finding is present
        findings = report["findings"]
        finding_ids = [f["id"] for f in findings]
        assert "VAL-EVID-028" in finding_ids
        
        # Check check status
        checks = report["checks"]
        assert "trace_report_present" in checks
        assert checks["trace_report_present"]["status"] == "failed"

@patch("src.validation.clang_check.run_clang_syntax_check")
def test_pipeline_require_trace_report_present(mock_clang, mock_stages):
    mock_clang.return_value = {
        "attempted": True,
        "status": "ok",
        "errors": 0,
        "warnings": 0,
        "diagnostics": []
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir).resolve()
        create_dummy_decompilation_output(out_dir)
        
        # Run validate and require trace report, AND run trace report generation stage
        manifest = run_pipeline(
            binary_path="dummy_bin",
            out_dir=str(out_dir),
            use_ghidra=False,
            use_radare2=True,
            validate=True,
            require_trace_report=True,
            trace_report=True,
            artifact_mode="debug"
        )
        
        # Should succeed because trace report is present
        assert manifest["status"] == "ok"
        
        report_path = out_dir / ".work" / "validation_report.json"
        assert report_path.exists()
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
            
        # Check trace_report link exists
        assert report.get("trace_report") == "trace_report.json"
        
        # Check trace_report_present check is ok
        checks = report["checks"]
        assert "trace_report_present" in checks
        assert checks["trace_report_present"]["status"] == "ok"
        
        # Check VAL-EVID-028 finding is NOT present
        findings = report.get("findings", [])
        finding_ids = [f["id"] for f in findings]
        assert "VAL-EVID-028" not in finding_ids
