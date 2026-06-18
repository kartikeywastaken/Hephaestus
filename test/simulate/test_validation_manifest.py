# -*- coding: utf-8 -*-
"""
Tests for Pipeline Manifest Checks
"""

from __future__ import annotations
import tempfile
import json
from pathlib import Path
from src.validation.models import ValidationArtifacts
from src.validation.report import new_report
from src.validation.manifest_checks import check_manifest

def test_check_manifest_missing_default():
    report = new_report("artifacts", strict=False)
    artifacts = ValidationArtifacts(
        out_dir=Path("artifacts"),
        source_reconstruction=None,
        recovered_c=None,
        pipeline_manifest=None,  # Missing
        unified_ir=None,
        phase4_semantics=None,
        missing=["pipeline_manifest.json"]
    )
    check_manifest(artifacts, report)
    
    assert report["checks"]["pipeline_manifest_status_ok"]["status"] == "skipped"
    assert report["checks"]["pipeline_manifest_status_ok"]["severity"] == "warning"
    assert "VAL-MANI-001" in [f["id"] for f in report["findings"]]

def test_check_manifest_missing_strict():
    report = new_report("artifacts", strict=True)
    artifacts = ValidationArtifacts(
        out_dir=Path("artifacts"),
        source_reconstruction=None,
        recovered_c=None,
        pipeline_manifest=None,  # Missing
        unified_ir=None,
        phase4_semantics=None,
        missing=["pipeline_manifest.json"]
    )
    check_manifest(artifacts, report)
    
    assert report["checks"]["pipeline_manifest_status_ok"]["status"] == "failed"
    assert report["checks"]["pipeline_manifest_status_ok"]["severity"] == "error"
    
    finding = report["findings"][0]
    assert finding["id"] == "VAL-MANI-001"
    assert finding["severity"] == "error"
    assert finding["strict_promoted"] is True

def test_check_manifest_valid():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        
        # Write declared output files
        with open(out_dir / "unified_ir.json", "w") as f:
            f.write("{}")
        with open(out_dir / "recovered.c", "w") as f:
            f.write(" ")
            
        manifest = {
            "schema_version": "pipeline-1.0",
            "status": "ok",
            "stages": [
                {
                    "name": "extract",
                    "status": "ok",
                    "outputs": ["unified_ir.json"]
                },
                {
                    "name": "reconstruct_source",
                    "status": "ok",
                    "outputs": ["recovered.c"]
                }
            ]
        }
        
        report = new_report(out_dir, strict=False)
        artifacts = ValidationArtifacts(
            out_dir=out_dir,
            source_reconstruction=None,
            recovered_c=None,
            pipeline_manifest=manifest,
            unified_ir=None,
            phase4_semantics=None,
            missing=[]
        )
        
        check_manifest(artifacts, report)
        
        assert report["checks"]["pipeline_manifest_status_ok"]["status"] == "ok"
        assert report["checks"]["pipeline_manifest_stage_order_valid"]["status"] == "ok"
        assert report["checks"]["pipeline_manifest_outputs_exist"]["status"] == "ok"
        assert len(report["findings"]) == 0

def test_check_manifest_out_of_order():
    report = new_report("artifacts", strict=False)
    # reconstruct_source ran before extract (invalid chronological order)
    manifest = {
        "status": "ok",
        "stages": [
            {
                "name": "reconstruct_source",
                "status": "ok",
                "outputs": []
            },
            {
                "name": "extract",
                "status": "ok",
                "outputs": []
            }
        ]
    }
    artifacts = ValidationArtifacts(
        out_dir=Path("artifacts"),
        source_reconstruction=None,
        recovered_c=None,
        pipeline_manifest=manifest,
        unified_ir=None,
        phase4_semantics=None,
        missing=[]
    )
    
    check_manifest(artifacts, report)
    
    assert report["checks"]["pipeline_manifest_stage_order_valid"]["status"] == "failed"
    assert "VAL-MANI-004" in [f["id"] for f in report["findings"]]

def test_check_manifest_missing_outputs():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        # We did not write recovered.c to disk!
        
        manifest = {
            "status": "ok",
            "stages": [
                {
                    "name": "reconstruct_source",
                    "status": "ok",
                    "outputs": ["recovered.c"]
                }
            ]
        }
        
        report = new_report(out_dir, strict=False)
        artifacts = ValidationArtifacts(
            out_dir=out_dir,
            source_reconstruction=None,
            recovered_c=None,
            pipeline_manifest=manifest,
            unified_ir=None,
            phase4_semantics=None,
            missing=[]
        )
        
        check_manifest(artifacts, report)
        
        assert report["checks"]["pipeline_manifest_outputs_exist"]["status"] == "failed"
        assert "VAL-MANI-005" in [f["id"] for f in report["findings"]]
