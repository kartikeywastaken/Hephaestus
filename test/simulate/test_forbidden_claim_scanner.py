# -*- coding: utf-8 -*-
"""
Phase 11.8 — Test: Forbidden claim scanner.

Verifies that:
  - Safe warning text ("No semantic equivalence is claimed") passes
  - "not guaranteed" no longer appears in templates
  - Claim-context phrases are caught
  - Duplicate findings are collapsed
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path


class TestForbiddenClaimScanner(unittest.TestCase):
    """Verify forbidden claim scanner behavior."""

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

    def _write_c_file(self, name: str, content: str):
        (self.out_dir / name).write_text(content, encoding="utf-8")

    def _finalize(self) -> dict:
        from src.pipeline.artifact_finalizer import finalize_artifacts
        return finalize_artifacts(
            out_dir=self.out_dir,
            work_dir=self.work_dir,
            artifact_mode="debug",
            binary_path=None,
        )

    def _setup_minimal_work_dir(self):
        """Write minimal required work_dir artifacts."""
        self._write_json("source_reconstruction.json", {"summary": {}})
        self._write_json("pipeline_manifest.json", {"status": "ok", "stages": []})
        self._write_json("behavior_model.json", {"summary": {}})
        self._write_json("behavior_fusion_report.json", {"status": "ok"})
        self._write_json("dynamic_runs.json", {"runs": []})

    def test_safe_warning_text_passes(self):
        """'No semantic equivalence is claimed' should not trigger a forbidden claim."""
        self._setup_minimal_work_dir()
        self._write_c_file("recovered.c", "int main() { return 0; }\n")
        self._write_c_file("recovered_readable.c",
            "/* No semantic equivalence is claimed. */\n"
            "int main() { return 0; }\n"
        )

        report = self._finalize()
        # Should have no forbidden claims
        self.assertEqual(report["validation"]["forbidden_claims_found"], [])

    def test_uncertain_comment_passes(self):
        """'inferred from ...; uncertain' should not trigger a forbidden claim."""
        self._setup_minimal_work_dir()
        self._write_c_file("recovered.c", "int main() { return 0; }\n")
        self._write_c_file("recovered_readable.c",
            "/* inferred from compare_site; uncertain */\n"
            "int main() { return 0; }\n"
        )

        report = self._finalize()
        self.assertEqual(report["validation"]["forbidden_claims_found"], [])

    def test_same_behavior_as_original_caught(self):
        """'same behavior as original' should be caught."""
        self._setup_minimal_work_dir()
        self._write_c_file("recovered.c",
            "/* same behavior as original */\n"
            "int main() { return 0; }\n"
        )
        self._write_c_file("recovered_readable.c", "int main() { return 0; }\n")

        report = self._finalize()
        self.assertTrue(len(report["validation"]["forbidden_claims_found"]) > 0)

    def test_semantically_equivalent_caught(self):
        """'semantically equivalent' should be caught."""
        self._setup_minimal_work_dir()
        self._write_c_file("recovered.c", "int main() { return 0; }\n")
        self._write_c_file("recovered_readable.c",
            "/* This is semantically equivalent */\n"
            "int main() { return 0; }\n"
        )

        report = self._finalize()
        self.assertTrue(len(report["validation"]["forbidden_claims_found"]) > 0)

    def test_guaranteed_equivalent_caught(self):
        """'guaranteed equivalent' should be caught."""
        self._setup_minimal_work_dir()
        self._write_c_file("recovered.c", "int main() { return 0; }\n")
        self._write_c_file("recovered_readable.c",
            "/* This output is guaranteed equivalent */\n"
            "int main() { return 0; }\n"
        )

        report = self._finalize()
        self.assertTrue(len(report["validation"]["forbidden_claims_found"]) > 0)

    def test_bare_guaranteed_in_warning_passes(self):
        """'not guaranteed' or bare 'guaranteed' in safe context should pass."""
        self._setup_minimal_work_dir()
        self._write_c_file("recovered.c", "int main() { return 0; }\n")
        self._write_c_file("recovered_readable.c",
            "/* This is not guaranteed to be correct */\n"
            "int main() { return 0; }\n"
        )

        report = self._finalize()
        # Bare "guaranteed" should NOT trigger since we removed it
        self.assertEqual(report["validation"]["forbidden_claims_found"], [])

    def test_duplicate_findings_collapsed(self):
        """Same forbidden phrase on the same line should produce only one finding."""
        self._setup_minimal_work_dir()
        self._write_c_file("recovered.c",
            "/* same behavior as original, fully equivalent */\n"
            "int main() { return 0; }\n"
        )
        self._write_c_file("recovered_readable.c", "int main() { return 0; }\n")

        report = self._finalize()
        findings = report["validation"]["forbidden_claims_found"]
        # Line 1 should appear at most once (one finding per line)
        line1_findings = [f for f in findings if ":1:" in f]
        self.assertEqual(len(line1_findings), 1)


class TestForbiddenSourcePhrases(unittest.TestCase):
    """Verify the FORBIDDEN_SOURCE_PHRASES set itself."""

    def test_no_bare_guaranteed(self):
        from src.agent_source.models import FORBIDDEN_SOURCE_PHRASES
        self.assertNotIn("guaranteed", FORBIDDEN_SOURCE_PHRASES)

    def test_no_bare_proven(self):
        from src.agent_source.models import FORBIDDEN_SOURCE_PHRASES
        self.assertNotIn("proven", FORBIDDEN_SOURCE_PHRASES)

    def test_no_bare_definitely(self):
        from src.agent_source.models import FORBIDDEN_SOURCE_PHRASES
        self.assertNotIn("definitely", FORBIDDEN_SOURCE_PHRASES)

    def test_has_claim_context_phrases(self):
        from src.agent_source.models import FORBIDDEN_SOURCE_PHRASES
        self.assertIn("semantic equivalence", FORBIDDEN_SOURCE_PHRASES)
        self.assertIn("same behavior as original", FORBIDDEN_SOURCE_PHRASES)
        self.assertIn("guaranteed equivalent", FORBIDDEN_SOURCE_PHRASES)
        self.assertIn("full behavioral equivalence", FORBIDDEN_SOURCE_PHRASES)


class TestTemplateWording(unittest.TestCase):
    """Verify template files no longer contain 'not guaranteed'."""

    def test_readable_emitter_disclaimer(self):
        from src.readability.readable_emitter import DISCLAIMER_HEADER
        self.assertNotIn("not guaranteed", DISCLAIMER_HEADER.lower())
        self.assertIn("No semantic equivalence is claimed", DISCLAIMER_HEADER)

    def test_warning_header_no_bare_guaranteed(self):
        from src.agent_source.models import WARNING_HEADER
        # WARNING_HEADER should not contain bare "guaranteed" as a claim
        self.assertNotIn("guaranteed equivalent", WARNING_HEADER.lower())


if __name__ == "__main__":
    unittest.main()
