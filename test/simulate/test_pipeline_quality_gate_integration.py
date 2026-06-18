# -*- coding: utf-8 -*-
"""
Tests for Pipeline Integration of Hephaestus Quality Gate
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
def test_pipeline_without_quality_gate(mock_clang, mock_stages):
    mock_clang.return_value = {"attempted": False}
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        create_dummy_decompilation_output(out_dir)
        
        manifest = run_pipeline(
            binary_path="dummy_bin",
            out_dir=str(out_dir),
            use_ghidra=False,
            use_radare2=True,
            clean=False,
            quality_gate=False
        )
        
        assert manifest["status"] == "ok"
        
        # Verify quality_gate stage was NOT run and files do NOT exist
        stages_run = [s["name"] for s in manifest["stages"]]
        assert "quality_gate" not in stages_run
        assert not (out_dir / "quality_gate.json").exists()

@patch("src.validation.clang_check.run_clang_syntax_check")
@patch("src.validation.quality_gate.builder.evaluate_decision")
def test_pipeline_with_quality_gate_success(mock_eval, mock_clang, mock_stages):
    mock_clang.return_value = {
        "attempted": True,
        "status": "ok",
        "errors": 0,
        "warnings": 0,
        "diagnostics": []
    }
    mock_eval.return_value = {
        "status": "ready",
        "decision": {
            "safe_to_use_for_phase7": True,
            "requires_review": False,
            "blocked": False,
            "reason": "Mocked success"
        },
        "blocking_issues": [],
        "warnings": [],
        "recommendations": [],
        "phase7_hints": {
            "predicate_recovery_recommended": True,
            "local_variable_recovery_recommended": True,
            "expression_simplification_recommended": True,
            "loop_readability_recommended": True,
            "agent_assistance_recommended": False
        }
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        create_dummy_decompilation_output(out_dir)
        
        manifest = run_pipeline(
            binary_path="dummy_bin",
            out_dir=str(out_dir),
            use_ghidra=False,
            use_radare2=True,
            clean=False,
            quality_gate=True
        )
        
        assert manifest["status"] == "ok"
        
        # Verify stages run
        stages_run = [s["name"] for s in manifest["stages"]]
        assert "build_evidence_index" in stages_run
        assert "validate" in stages_run
        assert "build_trace_report" in stages_run
        assert "quality_gate" in stages_run
        
        # Verify files exist
        assert (out_dir / "quality_gate.json").exists()
        assert (out_dir / "quality_gate.md").exists()
        
        # Verify final outputs registry
        assert "quality_gate" in manifest["final_outputs"]
        assert "quality_gate_markdown" in manifest["final_outputs"]
