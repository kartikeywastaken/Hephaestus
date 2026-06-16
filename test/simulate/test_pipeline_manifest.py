# -*- coding: utf-8 -*-
"""
Tests for Pipeline Manifest Generation and Serialization
"""

from __future__ import annotations
import json
import tempfile
from pathlib import Path
from src.pipeline.manifest import start_manifest, record_stage, finalize_manifest, write_manifest

def test_pipeline_manifest_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        
        # 1. Start manifest
        m = start_manifest(input_binary="./t", out_dir=str(out_dir))
        assert m["schema_version"] == "pipeline-1.0"
        assert m["tool"] == "hephaestus"
        assert m["input_binary"] == "./t"
        assert m["out_dir"] == str(out_dir)
        assert m["status"] == "ok"
        assert len(m["stages"]) == 0
        
        # 2. Record successful stage
        record_stage(
            m,
            name="extract",
            status="ok",
            outputs=["unified_ir.json"],
            started_at="2026-06-16T12:00:00Z",
            finished_at="2026-06-16T12:00:02Z",
            duration_ms=2000
        )
        assert len(m["stages"]) == 1
        assert m["stages"][0]["name"] == "extract"
        assert m["stages"][0]["status"] == "ok"
        assert m["stages"][0]["outputs"] == ["unified_ir.json"]
        assert m["stages"][0]["duration_ms"] == 2000
        assert m["stages"][0]["error"] is None
        
        # 3. Record failed stage
        record_stage(
            m,
            name="analyze_cfg",
            status="failed",
            error="Malformed CFG edges",
            started_at="2026-06-16T12:00:02Z",
            finished_at="2026-06-16T12:00:03Z",
            duration_ms=1000
        )
        assert len(m["stages"]) == 2
        assert m["stages"][1]["name"] == "analyze_cfg"
        assert m["stages"][1]["status"] == "failed"
        assert m["stages"][1]["error"] == "Malformed CFG edges"
        assert m["stages"][1]["duration_ms"] == 1000
        
        # 4. Finalize manifest
        summary = {"instructions_total": 100, "instructions_lowered": 90}
        final_outputs = {"unified_ir": "unified_ir.json"}
        m_final = finalize_manifest(m, status="failed", summary=summary, final_outputs=final_outputs)
        assert m_final["status"] == "failed"
        assert m_final["summary"] == summary
        assert m_final["final_outputs"] == final_outputs
        assert m_final["finished_at"] is not None
        
        # 5. Write manifest
        path = write_manifest(m_final, out_dir)
        assert path.exists()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["schema_version"] == "pipeline-1.0"
        assert data["status"] == "failed"
        assert len(data["stages"]) == 2
