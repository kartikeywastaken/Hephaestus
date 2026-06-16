# -*- coding: utf-8 -*-
"""
Tests for One-Shot Pipeline Runner Stage Execution and Control Flow
"""

from __future__ import annotations
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.pipeline.runner import run_pipeline, PipelineError

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

def test_run_pipeline_success(mock_stages):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        manifest = run_pipeline(
            binary_path="dummy_bin",
            out_dir=str(out_dir),
            use_ghidra=False,
            use_radare2=True,
            clean=False
        )
        
        assert manifest["status"] == "ok"
        # Check all stages were called
        for name, mock in mock_stages.items():
            mock.assert_called_once()
            
        # Check manifest output files
        manifest_path = out_dir / "pipeline_manifest.json"
        assert manifest_path.exists()
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["stages"]) == 7
        assert all(s["status"] == "ok" for s in data["stages"])

def test_run_pipeline_stop_after(mock_stages):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        manifest = run_pipeline(
            binary_path="dummy_bin",
            out_dir=str(out_dir),
            use_ghidra=False,
            use_radare2=True,
            stop_after="recover_semantics"
        )
        
        assert manifest["status"] == "ok"
        mock_stages["extract"].assert_called_once()
        mock_stages["analyze_cfg"].assert_called_once()
        mock_stages["recover_semantics"].assert_called_once()
        # Later stages must not be called
        mock_stages["refine_semantics"].assert_not_called()
        mock_stages["reconstruct_source"].assert_not_called()

def test_run_pipeline_no_source(mock_stages):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        manifest = run_pipeline(
            binary_path="dummy_bin",
            out_dir=str(out_dir),
            use_ghidra=False,
            use_radare2=True,
            no_source=True
        )
        
        assert manifest["status"] == "ok"
        mock_stages["finalize_semantics"].assert_called_once()
        mock_stages["reconstruct_source"].assert_not_called()

def test_run_pipeline_failure_stops_execution(mock_stages):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        
        # Make CFG stage fail
        mock_stages["analyze_cfg"].side_effect = RuntimeError("CFG Analysis Failed")
        
        manifest = run_pipeline(
            binary_path="dummy_bin",
            out_dir=str(out_dir),
            use_ghidra=False,
            use_radare2=True,
            continue_on_error=False
        )
        
        assert manifest["status"] == "failed"
        mock_stages["extract"].assert_called_once()
        mock_stages["analyze_cfg"].assert_called_once()
        # CFG failed, so subsequent stages must NOT be executed
        mock_stages["recover_semantics"].assert_not_called()

def test_run_pipeline_continue_on_error(mock_stages):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        
        # Make CFG stage fail
        mock_stages["analyze_cfg"].side_effect = RuntimeError("CFG Analysis Failed")
        
        manifest = run_pipeline(
            binary_path="dummy_bin",
            out_dir=str(out_dir),
            use_ghidra=False,
            use_radare2=True,
            continue_on_error=True
        )
        
        # Overall status should be partial
        assert manifest["status"] == "partial"
        mock_stages["extract"].assert_called_once()
        mock_stages["analyze_cfg"].assert_called_once()
        # CFG failed, but continue_on_error is True, so subsequent stages MUST be executed
        mock_stages["recover_semantics"].assert_called_once()
        mock_stages["reconstruct_source"].assert_called_once()
