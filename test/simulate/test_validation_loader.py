# -*- coding: utf-8 -*-
"""
Tests for Validation Loader
"""

from __future__ import annotations
import json
import tempfile
from pathlib import Path
from src.validation.loader import load_validation_artifacts

def test_validation_loader_all_present():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        
        # Write files
        recon_data = {"schema_version": "5.7.2", "summary": {}}
        c_content = "int main() { return 0; }"
        manifest_data = {"schema_version": "pipeline-1.0"}
        ir_data = {"schema_version": "2.0.0"}
        sem_data = {"schema_version": "4D.1.0"}
        
        with open(out_dir / "source_reconstruction.json", "w") as f:
            json.dump(recon_data, f)
        with open(out_dir / "recovered.c", "w") as f:
            f.write(c_content)
        with open(out_dir / "pipeline_manifest.json", "w") as f:
            json.dump(manifest_data, f)
        with open(out_dir / "unified_ir.json", "w") as f:
            json.dump(ir_data, f)
        with open(out_dir / "phase4_semantics.json", "w") as f:
            json.dump(sem_data, f)
            
        # Load
        artifacts = load_validation_artifacts(out_dir)
        assert artifacts.source_reconstruction == recon_data
        assert artifacts.recovered_c == c_content
        assert artifacts.pipeline_manifest == manifest_data
        assert artifacts.unified_ir == ir_data
        assert artifacts.phase4_semantics == sem_data
        assert len(artifacts.missing) == 0

def test_validation_loader_missing_recommended():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        
        recon_data = {"schema_version": "5.7.2"}
        c_content = "int main() { return 0; }"
        
        with open(out_dir / "source_reconstruction.json", "w") as f:
            json.dump(recon_data, f)
        with open(out_dir / "recovered.c", "w") as f:
            f.write(c_content)
            
        # Load
        artifacts = load_validation_artifacts(out_dir)
        assert artifacts.source_reconstruction == recon_data
        assert artifacts.recovered_c == c_content
        assert artifacts.pipeline_manifest is None
        assert artifacts.unified_ir is None
        assert artifacts.phase4_semantics is None
        assert sorted(artifacts.missing) == sorted([
            "pipeline_manifest.json", "unified_ir.json", "phase4_semantics.json"
        ])

def test_validation_loader_missing_required():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        
        # Write only recommended
        manifest_data = {"schema_version": "pipeline-1.0"}
        with open(out_dir / "pipeline_manifest.json", "w") as f:
            json.dump(manifest_data, f)
            
        artifacts = load_validation_artifacts(out_dir)
        assert artifacts.source_reconstruction is None
        assert artifacts.recovered_c is None
        assert artifacts.pipeline_manifest == manifest_data
        assert sorted(artifacts.missing) == sorted([
            "source_reconstruction.json", "recovered.c", "unified_ir.json", "phase4_semantics.json"
        ])
