# -*- coding: utf-8 -*-
"""
Phase 11.8 — Test: Behavior fusion has_dynamic accuracy.

Verifies that the artifact finalizer correctly detects dynamic evidence
from run artifacts, even when behavior_model.json does not report it.
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path


class TestBehaviorFusionWorkdirDynamic(unittest.TestCase):
    """Verify has_dynamic is true when completed dynamic runs exist."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.out_dir = self.tmpdir / "artifacts"
        self.work_dir = self.out_dir / ".work"
        self.out_dir.mkdir(parents=True)
        self.work_dir.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_json(self, name: str, data: dict, to_work: bool = True):
        target = self.work_dir if to_work else self.out_dir
        p = target / name
        p.write_text(json.dumps(data), encoding="utf-8")

    def _write_c_file(self, name: str, content: str = "int main() { return 0; }\n"):
        (self.out_dir / name).write_text(content, encoding="utf-8")

    def _finalize(self) -> dict:
        from src.pipeline.artifact_finalizer import finalize_artifacts
        return finalize_artifacts(
            out_dir=self.out_dir,
            work_dir=self.work_dir,
            artifact_mode="debug",
            binary_path=None,
        )

    def test_has_dynamic_true_when_dynamic_runs_have_ok_status(self):
        """dynamic_runs with status=ok should set has_dynamic=true."""
        self._write_json("dynamic_runs.json", {
            "runs": [
                {"status": "ok", "exit_code": 0, "stdin": "", "args": []},
            ]
        })
        self._write_json("behavior_model.json", {
            "summary": {"functions_total": 1, "functions_with_dynamic_evidence": 0}
        })
        self._write_json("behavior_fusion_report.json", {"status": "ok"})
        self._write_json("source_reconstruction.json", {"summary": {}})
        self._write_json("pipeline_manifest.json", {"status": "ok", "stages": []})
        self._write_c_file("recovered.c")
        self._write_c_file("recovered_readable.c")

        report = self._finalize()
        self.assertTrue(report["behavior_fusion"]["has_dynamic"])

    def test_has_dynamic_true_when_adaptive_runs_have_ok_status(self):
        """adaptive_dynamic_runs with status=ok should set has_dynamic=true."""
        self._write_json("adaptive_dynamic_runs.json", {
            "runs": [
                {"status": "ok", "exit_code": 0, "stdin": "hello", "args": []},
            ]
        })
        self._write_json("dynamic_runs.json", {"runs": []})
        self._write_json("behavior_model.json", {
            "summary": {"functions_total": 1, "functions_with_dynamic_evidence": 0}
        })
        self._write_json("behavior_fusion_report.json", {"status": "ok"})
        self._write_json("source_reconstruction.json", {"summary": {}})
        self._write_json("pipeline_manifest.json", {"status": "ok", "stages": []})
        self._write_c_file("recovered.c")
        self._write_c_file("recovered_readable.c")

        report = self._finalize()
        self.assertTrue(report["behavior_fusion"]["has_dynamic"])

    def test_has_dynamic_false_when_no_runs(self):
        """No dynamic runs should set has_dynamic=false."""
        self._write_json("dynamic_runs.json", {"runs": []})
        self._write_json("behavior_model.json", {
            "summary": {"functions_total": 1, "functions_with_dynamic_evidence": 0}
        })
        self._write_json("behavior_fusion_report.json", {"status": "ok"})
        self._write_json("source_reconstruction.json", {"summary": {}})
        self._write_json("pipeline_manifest.json", {"status": "ok", "stages": []})
        self._write_c_file("recovered.c")
        self._write_c_file("recovered_readable.c")

        report = self._finalize()
        self.assertFalse(report["behavior_fusion"]["has_dynamic"])

    def test_has_dynamic_true_from_fusion_summary(self):
        """If behavior_model.json reports dynamic evidence, has_dynamic=true."""
        self._write_json("dynamic_runs.json", {"runs": []})
        self._write_json("behavior_model.json", {
            "summary": {"functions_total": 2, "functions_with_dynamic_evidence": 1}
        })
        self._write_json("behavior_fusion_report.json", {"status": "ok"})
        self._write_json("source_reconstruction.json", {"summary": {}})
        self._write_json("pipeline_manifest.json", {"status": "ok", "stages": []})
        self._write_c_file("recovered.c")
        self._write_c_file("recovered_readable.c")

        report = self._finalize()
        self.assertTrue(report["behavior_fusion"]["has_dynamic"])

    def test_diagnostic_when_runs_exist_but_fusion_missed(self):
        """Diagnostic should warn when runs exist but fusion didn't flag has_dynamic."""
        self._write_json("dynamic_runs.json", {
            "runs": [{"status": "ok", "exit_code": 0}]
        })
        self._write_json("behavior_model.json", {
            "summary": {"functions_total": 1, "functions_with_dynamic_evidence": 0}
        })
        self._write_json("behavior_fusion_report.json", {"status": "ok"})
        self._write_json("source_reconstruction.json", {"summary": {}})
        self._write_json("pipeline_manifest.json", {"status": "ok", "stages": []})
        self._write_c_file("recovered.c")
        self._write_c_file("recovered_readable.c")

        report = self._finalize()
        self.assertTrue(report["behavior_fusion"]["has_dynamic"])
        diag_text = " ".join(report.get("diagnostics", []))
        self.assertIn("Dynamic runs detected", diag_text)


if __name__ == "__main__":
    unittest.main()
