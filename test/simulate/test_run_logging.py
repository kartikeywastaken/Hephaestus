# -*- coding: utf-8 -*-
"""
Tests for Run Log Consolidation and Orchestration Stage Logging
"""

import unittest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.utils.run_logging import append_run_log
from src.engine.ghidra import GhidraExtractor
from src.engine.radare2 import Radare2Extractor
from src.engine.orchestrator import PipelineOrchestrator
from src.engine.base import ExtractorError


class TestRunLogging(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)
        self.binary_file = os.path.join(self.temp_dir.name, "example_elf")
        with open(self.binary_file, "wb") as f:
            f.write(b"\x7fELF\x02\x01\x01\x00_test_payload")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_append_run_log_creates_file(self):
        # 1. append_run_log creates run.log
        append_run_log(self.tmp_path, "TEST_SECTION", "hello run log")
        log_file = self.tmp_path / "run.log"
        self.assertTrue(log_file.exists())
        content = log_file.read_text(encoding="utf-8")
        self.assertIn("TEST_SECTION", content)
        self.assertIn("hello run log", content)

    def test_append_run_log_appends(self):
        # 2. append_run_log appends sections and does not overwrite
        append_run_log(self.tmp_path, "SECTION_ONE", "first message")
        append_run_log(self.tmp_path, "SECTION_TWO", "second message")
        log_file = self.tmp_path / "run.log"
        self.assertTrue(log_file.exists())
        content = log_file.read_text(encoding="utf-8")
        self.assertIn("SECTION_ONE", content)
        self.assertIn("first message", content)
        self.assertIn("SECTION_TWO", content)
        self.assertIn("second message", content)

    @patch('subprocess.run')
    @patch('src.engine.ghidra.GhidraExtractor.validate_environment', return_value=True)
    def test_ghidra_error_goes_to_run_log(self, mock_valid, mock_run):
        # 3. Ghidra error output goes to run.log
        from subprocess import CompletedProcess
        mock_run.return_value = CompletedProcess(
            args=["analyzeHeadless"],
            returncode=1,
            stdout="ghidra error stdout dump",
            stderr="ghidra error stderr dump"
        )
        
        # Setup dummy analyzeHeadless file to pass internal check in GhidraExtractor
        support_dir = os.path.join(self.temp_dir.name, "support")
        os.makedirs(support_dir, exist_ok=True)
        analyze_headless = os.path.join(support_dir, "analyzeHeadless")
        with open(analyze_headless, "w") as f:
            f.write("")

        out_json = os.path.join(self.temp_dir.name, "ghidra_out.json")
        extractor = GhidraExtractor(
            self.binary_file,
            out_json,
            config={"GHIDRA_HOME": self.temp_dir.name}
        )

        with self.assertRaises(ExtractorError) as context:
            extractor.extract()

        self.assertIn("Ghidra execution failed", str(context.exception))
        
        log_file = self.tmp_path / "run.log"
        self.assertTrue(log_file.exists())
        content = log_file.read_text(encoding="utf-8")
        self.assertIn("GHIDRA", content)
        self.assertIn("Return code: 1", content)
        self.assertIn("ghidra error stdout dump", content)
        self.assertIn("ghidra error stderr dump", content)

    @patch('subprocess.run')
    @patch('src.engine.ghidra.GhidraExtractor.validate_environment', return_value=True)
    @patch('src.engine.radare2.Radare2Extractor.validate_environment', return_value=True)
    @patch('src.engine.radare2.Radare2Extractor._execute_radare2_analysis')
    def test_no_scattered_txt_files_by_default(self, mock_r2_exec, mock_r2_valid, mock_ghidra_valid, mock_subprocess):
        # 4. No scattered txt files by default
        from subprocess import CompletedProcess
        
        def mock_subprocess_run(cmd, *args, **kwargs):
            # Find the temp JSON path argument, which follows GhidraExtractorScript.java
            script_idx = cmd.index("GhidraExtractorScript.java")
            json_path = cmd[script_idx + 1]
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({"functions": [], "symbols": [], "call_graph": {}}, f)
            return CompletedProcess(cmd, 0, "ghidra success stdout", "ghidra success stderr")

        mock_subprocess.side_effect = mock_subprocess_run
        mock_r2_exec.return_value = {"functions": [], "symbols": [], "call_graph": {"nodes": [], "edges": []}}

        # Setup dummy analyzeHeadless file
        support_dir = os.path.join(self.temp_dir.name, "support")
        os.makedirs(support_dir, exist_ok=True)
        analyze_headless = os.path.join(support_dir, "analyzeHeadless")
        with open(analyze_headless, "w") as f:
            f.write("")

        orchestrator = PipelineOrchestrator(
            self.binary_file,
            self.temp_dir.name,
            config={"GHIDRA_HOME": self.temp_dir.name}
        )

        # Run orchestrator
        manifest = orchestrator.execute_all(run_ghidra=True, run_radare2=True, run_trace=False)
        self.assertEqual(manifest["status"], "success")

        # Verify only run.log and expected json artifacts exist
        created_files = os.listdir(self.temp_dir.name)
        
        # We shouldn't see ghidra_stdout.txt or ghidra_stderr.txt
        self.assertNotIn("ghidra_stdout.txt", created_files)
        self.assertNotIn("ghidra_stderr.txt", created_files)
        
        self.assertIn("run.log", created_files)
        self.assertIn("ghidra_extraction.json", created_files)
        self.assertIn("radare2_extraction.json", created_files)
        self.assertIn("orchestration_manifest.json", created_files)

        # Verify orchestration manifest
        manifest_path = self.tmp_path / "orchestration_manifest.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
            self.assertEqual(manifest_data["status"], "success")
            self.assertIn("ghidra", manifest_data["jobs"])
            self.assertIn("radare2", manifest_data["jobs"])

    @patch('subprocess.run')
    @patch('src.engine.ghidra.GhidraExtractor.validate_environment', return_value=True)
    @patch('src.engine.radare2.Radare2Extractor.validate_environment', return_value=True)
    @patch('src.engine.radare2.Radare2Extractor._execute_radare2_analysis')
    def test_debug_logs_creates_scattered_txt_files(self, mock_r2_exec, mock_r2_valid, mock_ghidra_valid, mock_subprocess):
        # 4b. With debug_logs enabled, scattered txt files should exist
        from subprocess import CompletedProcess
        
        def mock_subprocess_run(cmd, *args, **kwargs):
            script_idx = cmd.index("GhidraExtractorScript.java")
            json_path = cmd[script_idx + 1]
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({"functions": [], "symbols": [], "call_graph": {}}, f)
            return CompletedProcess(cmd, 0, "ghidra success stdout", "ghidra success stderr")

        mock_subprocess.side_effect = mock_subprocess_run
        mock_r2_exec.return_value = {"functions": [], "symbols": [], "call_graph": {"nodes": [], "edges": []}}

        # Setup dummy analyzeHeadless file
        support_dir = os.path.join(self.temp_dir.name, "support")
        os.makedirs(support_dir, exist_ok=True)
        analyze_headless = os.path.join(support_dir, "analyzeHeadless")
        with open(analyze_headless, "w") as f:
            f.write("")

        orchestrator = PipelineOrchestrator(
            self.binary_file,
            self.temp_dir.name,
            config={"GHIDRA_HOME": self.temp_dir.name, "debug_logs": True}
        )

        manifest = orchestrator.execute_all(run_ghidra=True, run_radare2=True, run_trace=False)
        self.assertEqual(manifest["status"], "success")

        created_files = os.listdir(self.temp_dir.name)
        
        # Check that ghidra_stdout.txt and ghidra_stderr.txt are created
        self.assertIn("ghidra_stdout.txt", created_files)
        self.assertIn("ghidra_stderr.txt", created_files)
        self.assertIn("run.log", created_files)


if __name__ == "__main__":
    unittest.main()
