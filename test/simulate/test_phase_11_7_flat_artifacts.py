# -*- coding: utf-8 -*-
"""
Tests for Phase 11.7 Flat Artifacts and Layout routing
"""

from __future__ import annotations
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.utils.artifact_layout import ArtifactLayout
from src.pipeline.artifact_finalizer import finalize_artifacts
from src.pipeline.runner import run_pipeline


def test_artifact_layout_creation():
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td)
        layout = ArtifactLayout(out_dir, mode="flat")
        layout.ensure_dirs()

        assert layout.root == out_dir.resolve()
        assert layout.work_dir == (out_dir / ".work").resolve()
        assert layout.work_path("test.json") == (out_dir / ".work" / "test.json").resolve()
        assert layout.final_path("test.json") == (out_dir / "test.json").resolve()

        # Path traversal check
        with pytest.raises(ValueError, match="Path traversal detected"):
            layout.work_path("../../outside.json")
        with pytest.raises(ValueError, match="Path traversal detected"):
            layout.final_path("../outside.json")


def test_finalizer_moves_files_and_writes_report():
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td)
        work_dir = out_dir / ".work"
        work_dir.mkdir()

        # Write dummy intermediate files in .work/
        (work_dir / "recovered.c").write_text("int main() { return 0; }", encoding="utf-8")
        (work_dir / "recovered_readable.c").write_text("int main() { return 0; }", encoding="utf-8")
        (work_dir / "recovered_agent.c").write_text("int main() { return 0; }", encoding="utf-8")

        # Mock binary
        binary_path = out_dir / "t"
        binary_path.write_bytes(b"\x00\x01\x02")

        # Run finalizer in debug mode
        finalize_artifacts(out_dir, work_dir=work_dir, artifact_mode="debug", binary_path=str(binary_path))

        # Check that C files exist in top-level and .work/ remains
        assert (out_dir / "recovered.c").exists()
        assert (out_dir / "recovered_readable.c").exists()
        assert (out_dir / "recovered_agent.c").exists()
        assert (out_dir / "hephaestus_report.json").exists()
        assert work_dir.exists()

        # Check hephaestus_report.json content
        with open(out_dir / "hephaestus_report.json", "r", encoding="utf-8") as f:
            report = json.load(f)
        assert report["schema_version"] == "hephaestus-report-1.0"
        assert report["status"] == "ok"
        assert report["artifact_mode"] == "debug"
        assert report["outputs"]["recovered"] == "recovered.c"

        # Now run in flat mode
        finalize_artifacts(out_dir, work_dir=work_dir, artifact_mode="flat", binary_path=str(binary_path))
        # .work/ should be deleted now
        assert not work_dir.exists()


def test_run_pipeline_uses_artifact_mode():
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td)
        
        # Patch setup_logging, runner stages, and finalizer to check parameter propagation
        with patch("main.setup_logging"), \
             patch("src.pipeline.runner.start_manifest", return_value={"status": "ok", "stages": []}), \
             patch("src.pipeline.runner.write_manifest"), \
             patch("src.pipeline.runner.finalize_manifest"), \
             patch("src.pipeline.artifact_finalizer.finalize_artifacts") as mock_finalize:

            run_pipeline(
                binary_path="./t",
                out_dir=str(out_dir),
                clean=False,
                skip_static=True,
                artifact_mode="flat"
            )

            mock_finalize.assert_called_once()
            kwargs = mock_finalize.call_args[1]
            assert kwargs["artifact_mode"] == "flat"
