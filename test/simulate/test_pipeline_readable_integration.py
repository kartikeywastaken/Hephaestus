# -*- coding: utf-8 -*-
"""
Tests for E2E Pipeline Runner Readability Integration
"""

import os
import json
from pathlib import Path
import pytest

from src.pipeline.runner import run_pipeline

@pytest.fixture(autouse=True)
def mock_clang_unavailable(monkeypatch):
    """Mock clang as unavailable for integration tests."""
    import src.readability.cli
    monkeypatch.setattr(src.readability.cli, "clang_available", lambda: False)

def test_pipeline_plain_does_not_build_readable(tmp_path):
    # Mock minimal pipeline stage requirements to avoid runningGhida/r2
    # We will simulate reconstruct_source outputting recovered.c
    c_file = tmp_path / "recovered.c"
    c_file.write_text("void main() { if (HEPHAESTUS_UNKNOWN_COND(\"cbz w8\")) {} }")
    (tmp_path / "source_reconstruction.json").write_text('{"schema_version": "5.7.2", "summary": {}}')
    
    # Run pipeline with stop_after="reconstruct_source"
    # Wait, we need to run it without --readable.
    # We can mock the pipeline runner stage loop or just test stages
    # Since run_pipeline requires extractor flags or stop_after, we can mock run_stage_reconstruct_source
    # to avoid GHIDRA.
    # Let's mock extractors to do nothing and return empty list of files
    import src.pipeline.runner
    
    # Save original functions
    orig_extract = src.pipeline.runner.run_stage_extract
    orig_analyze = src.pipeline.runner.run_stage_analyze_cfg
    orig_rec_sem = src.pipeline.runner.run_stage_recover_semantics
    orig_ref_sem = src.pipeline.runner.run_stage_refine_semantics
    orig_rec_lay = src.pipeline.runner.run_stage_recover_layouts
    orig_fin_sem = src.pipeline.runner.run_stage_finalize_semantics
    orig_rec_src = src.pipeline.runner.run_stage_reconstruct_source
    
    try:
        src.pipeline.runner.run_stage_extract = lambda *a, **k: []
        src.pipeline.runner.run_stage_analyze_cfg = lambda *a: []
        src.pipeline.runner.run_stage_recover_semantics = lambda *a: []
        src.pipeline.runner.run_stage_refine_semantics = lambda *a: []
        src.pipeline.runner.run_stage_recover_layouts = lambda *a: []
        src.pipeline.runner.run_stage_finalize_semantics = lambda *a: []
        src.pipeline.runner.run_stage_reconstruct_source = lambda *a: [str(c_file), str(tmp_path / "source_reconstruction.json")]
        
        # Plain run-all E2E pipeline
        manifest = run_pipeline(
            binary_path="mock.bin",
            out_dir=str(tmp_path),
            use_ghidra=True,
            clean=False,
            artifact_mode="debug"
        )
        
        # Check build_readable did not run
        stages = manifest.get("stages", [])
        build_readable_stage = next((s for s in stages if s.get("name") == "build_readable"), None)
        assert build_readable_stage is None
        assert not (tmp_path / "recovered_readable.c").exists()
        assert not (tmp_path / ".work" / "readability_report.json").exists()
        
        # Run with readable=True
        manifest_readable = run_pipeline(
            binary_path="mock.bin",
            out_dir=str(tmp_path),
            use_ghidra=True,
            clean=False,
            readable=True,
            artifact_mode="debug"
        )
        
        # Check build_readable ran
        stages_readable = manifest_readable.get("stages", [])
        build_readable_stage = next((s for s in stages_readable if s.get("name") == "build_readable"), None)
        assert build_readable_stage is not None
        assert build_readable_stage["status"] == "ok"
        
        assert (tmp_path / "recovered_readable.c").exists()
        assert (tmp_path / ".work" / "readability_report.json").exists()
        
        # Check outputs are mapped in manifest
        assert "recovered_readable_c" in manifest_readable.get("final_outputs", {})
        assert "readability_report_json" in manifest_readable.get("final_outputs", {})
        
        # Verify no_promote_symbols flag behavior E2E
        manifest_no_promo = run_pipeline(
            binary_path="mock.bin",
            out_dir=str(tmp_path),
            use_ghidra=True,
            clean=False,
            readable=True,
            promote_symbols=False,
            artifact_mode="debug"
        )
        assert manifest_no_promo.get("status") == "ok"
        with open(tmp_path / ".work" / "readability_report.json") as f:
            rep = json.load(f)
            assert rep["mode"] == "static_predicate_recovery_only"
            assert rep["symbol_promotion"] == {"enabled": False}
            
    finally:
        # Restore original functions
        src.pipeline.runner.run_stage_extract = orig_extract
        src.pipeline.runner.run_stage_analyze_cfg = orig_analyze
        src.pipeline.runner.run_stage_recover_semantics = orig_rec_sem
        src.pipeline.runner.run_stage_refine_semantics = orig_ref_sem
        src.pipeline.runner.run_stage_recover_layouts = orig_rec_lay
        src.pipeline.runner.run_stage_finalize_semantics = orig_fin_sem
        src.pipeline.runner.run_stage_reconstruct_source = orig_rec_src
