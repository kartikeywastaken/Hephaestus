# -*- coding: utf-8 -*-
"""
Tests for reconstruct pipeline integration and backwards compatibility (Phase 11.5).
"""

import os
import json
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from src.pipeline.runner import run_pipeline
from main import handle_run_all_cli


def test_default_run_all_behavior_unchanged():
    """Verify that run-all defaults and run_pipeline behavior is backwards compatible."""
    with patch("src.pipeline.runner.run_stage_extract") as mock_extract, \
         patch("src.pipeline.runner.run_stage_analyze_cfg") as mock_analyze_cfg, \
         patch("src.pipeline.runner.run_stage_recover_semantics") as mock_rec_sem, \
         patch("src.pipeline.runner.run_stage_refine_semantics") as mock_ref_sem, \
         patch("src.pipeline.runner.run_stage_recover_layouts") as mock_rec_lay, \
         patch("src.pipeline.runner.run_stage_finalize_semantics") as mock_fin_sem, \
         patch("src.pipeline.runner.run_stage_reconstruct_source") as mock_rec_src:
        
        mock_extract.return_value = ["unified_ir.json"]
        mock_analyze_cfg.return_value = ["structuring_analysis.json"]
        mock_rec_sem.return_value = ["type_recovery.json"]
        mock_ref_sem.return_value = ["semantic_recovery.json"]
        mock_rec_lay.return_value = ["layout_recovery.json"]
        mock_fin_sem.return_value = ["phase4_semantics.json"]
        mock_rec_src.return_value = ["recovered.c"]

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = run_pipeline(
                binary_path="sample.exe",
                out_dir=tmpdir,
                use_ghidra=True,
                use_radare2=True,
                clean=True
            )

            assert manifest["status"] == "ok"
            # Verify static stages were executed
            mock_extract.assert_called_once()
            mock_analyze_cfg.assert_called_once()
            mock_rec_src.assert_called_once()

            # Optional stages (readable, dynamic, debate, agent source) should NOT be run by default in run-all
            stages_run = [s["name"] for s in manifest["stages"]]
            assert "build_readable" not in stages_run
            assert "run_dynamic" not in stages_run
            assert "agent_debate" not in stages_run
            assert "generate_agent_source" not in stages_run


def test_pipeline_manifest_records_all_stages():
    """Verify that reconstruct runs optional stages and records them in the manifest."""
    with patch("src.pipeline.runner.run_stage_extract") as mock_extract, \
         patch("src.pipeline.runner.run_stage_analyze_cfg") as mock_analyze_cfg, \
         patch("src.pipeline.runner.run_stage_recover_semantics") as mock_rec_sem, \
         patch("src.pipeline.runner.run_stage_refine_semantics") as mock_ref_sem, \
         patch("src.pipeline.runner.run_stage_recover_layouts") as mock_rec_lay, \
         patch("src.pipeline.runner.run_stage_finalize_semantics") as mock_fin_sem, \
         patch("src.pipeline.runner.run_stage_reconstruct_source") as mock_rec_src, \
         patch("src.readability.cli.run_build_readable_cli", return_value=0), \
         patch("src.dynamic.cli.run_dynamic_cli", return_value=0), \
         patch("src.behavior.cli.run_fuse_behavior_cli", return_value=0), \
         patch("src.agent.cli.run_build_agent_packets_cli", return_value=0), \
         patch("src.agent.cli.run_agent_debate_cli", return_value=0), \
         patch("src.agent_source.cli.run_generate_agent_source_cli", return_value=0):
        
        mock_extract.return_value = ["unified_ir.json"]
        mock_analyze_cfg.return_value = ["structuring_analysis.json"]
        mock_rec_sem.return_value = ["type_recovery.json"]
        mock_ref_sem.return_value = ["semantic_recovery.json"]
        mock_rec_lay.return_value = ["layout_recovery.json"]
        mock_fin_sem.return_value = ["phase4_semantics.json"]
        mock_rec_src.return_value = ["recovered.c"]

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = run_pipeline(
                binary_path="sample.exe",
                out_dir=tmpdir,
                use_ghidra=True,
                use_radare2=True,
                readable=True,
                dynamic=True,
                fuse_behavior=True,
                agent_debate=True,
                generate_agent_source=True,
            )

            assert manifest["status"] == "ok"
            stages_run = [s["name"] for s in manifest["stages"]]
            
            # Check for the dynamic and agent stages present in execution manifest
            assert "extract" in stages_run
            assert "build_readable" in stages_run
            assert "run_dynamic" in stages_run
            assert "fuse_behavior" in stages_run
            assert "agent_debate" in stages_run
            assert "generate_agent_source" in stages_run
