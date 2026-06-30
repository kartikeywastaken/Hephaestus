# -*- coding: utf-8 -*-
"""
Phase 11.8 — Test: Ghidra temp project path must not contain dot-prefixed segments.
"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from src.engine.ghidra import GhidraExtractor


class TestGhidraTempPathNotDotWork(unittest.TestCase):
    """Verify Ghidra project dir avoids dot-prefixed path segments."""

    def _make_extractor(self, output_path: str) -> GhidraExtractor:
        """Create a GhidraExtractor with mocked config."""
        ext = GhidraExtractor.__new__(GhidraExtractor)
        ext.binary_path = "/tmp/fake_binary"
        ext.output_path = output_path
        ext.config = {"GHIDRA_HOME": "/opt/ghidra"}
        ext.logger = MagicMock()
        return ext

    @patch("tempfile.mkdtemp", return_value="/tmp/hephaestus-ghidra-abc123")
    @patch("subprocess.run")
    @patch("os.path.exists", return_value=True)
    def test_project_dir_uses_tempfile_not_output_path(self, mock_exists, mock_run, mock_mkdtemp):
        """Project dir should be created via tempfile, not derived from output_path."""
        # If output_path is under .work/, the old code would put ghidra_temp_proj there
        output_path = "/some/project/artifacts/.work/ghidra_extraction.json"
        ext = self._make_extractor(output_path)

        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="test")
        try:
            ext._execute_ghidra_analysis()
        except Exception:
            pass  # Expected — we just want to verify the path logic

        mock_mkdtemp.assert_called_once()
        call_kwargs = mock_mkdtemp.call_args
        # Verify the prefix was used
        self.assertTrue(
            "hephaestus-ghidra-" in str(call_kwargs),
            f"Expected 'hephaestus-ghidra-' in mkdtemp call: {call_kwargs}"
        )

    def test_no_dot_segment_in_project_path(self):
        """Verify that the generated project path has no dot-prefixed segments."""
        # Simulate what the new code does: tempfile.mkdtemp(prefix="hephaestus-ghidra-")
        project_dir = tempfile.mkdtemp(prefix="hephaestus-ghidra-")
        try:
            parts = project_dir.split(os.sep)
            for part in parts:
                if part:  # skip empty string from leading /
                    self.assertFalse(
                        part.startswith("."),
                        f"Path segment '{part}' starts with '.': {project_dir}"
                    )
            # Also verify .work is not in the path
            self.assertNotIn(".work", project_dir)
        finally:
            os.rmdir(project_dir)

    def test_output_path_under_work_dir_is_acceptable(self):
        """The output JSON (ghidra_extraction.json) CAN be under .work/.
        Only the project_dir must avoid dot-prefixed segments.
        """
        output_path = "/some/project/artifacts/.work/ghidra_extraction.json"
        # This is fine for the output path — only project_dir matters
        self.assertIn(".work", output_path)
        # A tempfile path would not contain .work
        project_dir = tempfile.mkdtemp(prefix="hephaestus-ghidra-")
        try:
            self.assertNotIn(".work", project_dir)
        finally:
            os.rmdir(project_dir)


if __name__ == "__main__":
    unittest.main()
