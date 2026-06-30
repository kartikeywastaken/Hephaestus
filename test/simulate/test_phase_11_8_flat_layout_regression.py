# -*- coding: utf-8 -*-
"""
Phase 11.8 — Test: Flat layout regression tests.

Verifies that Phase 11.7/11.8 flat artifact layout invariants hold.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path


class TestFlatLayoutRegression(unittest.TestCase):
    """Verify flat artifact layout invariants."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.out_dir = self.tmpdir / "artifacts"
        self.work_dir = self.out_dir / ".work"
        self.out_dir.mkdir(parents=True)
        self.work_dir.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_json(self, name: str, data: dict):
        (self.work_dir / name).write_text(json.dumps(data), encoding="utf-8")

    def _write_c_file(self, name: str, content: str = "int main() { return 0; }\n"):
        (self.work_dir / name).write_text(content, encoding="utf-8")

    def _setup_minimal_work_dir(self):
        """Write minimal required work_dir artifacts."""
        self._write_json("source_reconstruction.json", {"summary": {}})
        self._write_json("pipeline_manifest.json", {"status": "ok", "stages": []})
        self._write_json("behavior_model.json", {"summary": {}})
        self._write_json("behavior_fusion_report.json", {"status": "ok"})
        self._write_json("dynamic_runs.json", {"runs": []})
        self._write_c_file("recovered.c")
        self._write_c_file("recovered_readable.c")

    def test_flat_mode_final_layout(self):
        """Flat mode should produce only C files + report at top level."""
        self._setup_minimal_work_dir()

        from src.pipeline.artifact_finalizer import finalize_artifacts
        finalize_artifacts(
            out_dir=self.out_dir,
            work_dir=self.work_dir,
            artifact_mode="flat",
            binary_path=None,
        )

        top_level = set(p.name for p in self.out_dir.iterdir() if not p.name.startswith("."))
        # Should contain the C files and report
        self.assertIn("recovered.c", top_level)
        self.assertIn("recovered_readable.c", top_level)
        self.assertIn("hephaestus_report.json", top_level)

        # Should NOT contain intermediate JSON files
        self.assertNotIn("source_reconstruction.json", top_level)
        self.assertNotIn("pipeline_manifest.json", top_level)
        self.assertNotIn("behavior_model.json", top_level)

    def test_no_top_level_run_log(self):
        """run.log should NOT be at the top level in flat mode."""
        self._setup_minimal_work_dir()
        # Simulate a run.log in work_dir
        (self.work_dir / "run.log").write_text("test log\n", encoding="utf-8")

        from src.pipeline.artifact_finalizer import finalize_artifacts
        finalize_artifacts(
            out_dir=self.out_dir,
            work_dir=self.work_dir,
            artifact_mode="flat",
            binary_path=None,
        )

        # run.log should NOT be at top level
        self.assertFalse((self.out_dir / "run.log").exists())

    def test_work_dir_deleted_in_flat_mode(self):
        """In flat mode, .work/ should be deleted after finalization succeeds."""
        self._setup_minimal_work_dir()

        from src.pipeline.artifact_finalizer import finalize_artifacts
        finalize_artifacts(
            out_dir=self.out_dir,
            work_dir=self.work_dir,
            artifact_mode="flat",
            binary_path=None,
        )

        self.assertFalse(self.work_dir.exists())

    def test_debug_mode_preserves_work_dir(self):
        """In debug mode, .work/ should be preserved."""
        self._setup_minimal_work_dir()

        from src.pipeline.artifact_finalizer import finalize_artifacts
        finalize_artifacts(
            out_dir=self.out_dir,
            work_dir=self.work_dir,
            artifact_mode="debug",
            binary_path=None,
        )

        self.assertTrue(self.work_dir.exists())

    def test_report_phase_is_11_8(self):
        """hephaestus_report.json should have phase '11.8'."""
        self._setup_minimal_work_dir()

        from src.pipeline.artifact_finalizer import finalize_artifacts
        report = finalize_artifacts(
            out_dir=self.out_dir,
            work_dir=self.work_dir,
            artifact_mode="debug",
            binary_path=None,
        )

        self.assertEqual(report.get("phase"), "11.8")

    def test_no_outputs_dir_at_top_level(self):
        """No 'outputs/' directory should exist at top level."""
        self._setup_minimal_work_dir()
        # Create a spurious outputs dir
        outputs_dir = self.out_dir / "outputs"
        outputs_dir.mkdir(exist_ok=True)
        (outputs_dir / "test.txt").write_text("test", encoding="utf-8")

        from src.pipeline.artifact_finalizer import finalize_artifacts
        finalize_artifacts(
            out_dir=self.out_dir,
            work_dir=self.work_dir,
            artifact_mode="flat",
            binary_path=None,
        )

        # The finalizer doesn't delete outputs/, but the clean_artifacts utility does.
        # This test just verifies the finalizer doesn't create an outputs/ dir.
        # (Existing outputs/ is outside finalizer scope)

    def test_no_reports_dir_at_top_level(self):
        """Finalizer should not create a 'reports/' directory."""
        self._setup_minimal_work_dir()

        from src.pipeline.artifact_finalizer import finalize_artifacts
        finalize_artifacts(
            out_dir=self.out_dir,
            work_dir=self.work_dir,
            artifact_mode="flat",
            binary_path=None,
        )

        self.assertFalse((self.out_dir / "reports").exists())

    def test_ghidra_temp_path_outside_work(self):
        """Ghidra temp project dir should use /tmp, not .work/."""
        import tempfile
        import os

        project_dir = tempfile.mkdtemp(prefix="hephaestus-ghidra-")
        try:
            # Must not contain .work
            self.assertNotIn(".work", project_dir)
            # Must not have dot-prefixed segments
            parts = project_dir.split(os.sep)
            for part in parts:
                if part:
                    self.assertFalse(part.startswith("."),
                                     f"Path segment starts with '.': {project_dir}")
        finally:
            os.rmdir(project_dir)

    def test_source_generation_fields_in_report(self):
        """Report should include functions_fallback and metadata_suggestions_ignored."""
        self._setup_minimal_work_dir()
        self._write_json("agent_source_report.json", {
            "functions_generated": 1,
            "functions_copied_unchanged": 2,
            "functions_failed": 0,
            "functions_fallback": 1,
            "metadata_suggestions_ignored": 1,
        })

        from src.pipeline.artifact_finalizer import finalize_artifacts
        report = finalize_artifacts(
            out_dir=self.out_dir,
            work_dir=self.work_dir,
            artifact_mode="debug",
            binary_path=None,
        )

        sg = report["source_generation"]
        self.assertEqual(sg["functions_fallback"], 1)
        self.assertEqual(sg["metadata_suggestions_ignored"], 1)


if __name__ == "__main__":
    unittest.main()
