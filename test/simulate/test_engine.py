# -*- coding: utf-8 -*-
"""
Python Extraction Engine Units Tests
Testing individual extractors, schema validation, structured envelopes and error protocols.
"""

import unittest
import tempfile
import json
import os
from src.engine.base import BaseExtractor, ExtractorError, execute_with_retry, ExtractorRecoverableError
from src.engine.ghidra import GhidraExtractor
from src.engine.radare2 import Radare2Extractor
from src.engine.trace import TraceExtractor
from src.engine.orchestrator import PipelineOrchestrator

class MockRecoverableOperation:
    """Simulates a volatile operation for testing retry sequences."""
    def __init__(self, fail_count=2):
        self.fail_count = fail_count
        self.attempts = 0

    def call_me(self) -> str:
        self.attempts += 1
        if self.attempts <= self.fail_count:
            raise ExtractorRecoverableError(f"Transient error branch {self.attempts}")
        return "success"

from unittest.mock import patch

class TestExtractionBaseAndExtractors(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.binary_file = os.path.join(self.temp_dir.name, "example_elf")
        with open(self.binary_file, "wb") as f:
            f.write(b"\x7fELF\x02\x01\x01\x00_test_payload")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_retry_success(self):
        op = MockRecoverableOperation(fail_count=2)
        res = execute_with_retry(op.call_me, retries=3)
        self.assertEqual(res, "success")
        self.assertEqual(op.attempts, 3)

    def test_retry_max_exhaustion(self):
        op = MockRecoverableOperation(fail_count=4)
        with self.assertRaises(ExtractorError):
            execute_with_retry(op.call_me, retries=3)

    @patch('src.engine.ghidra.GhidraExtractor.validate_environment', return_value=True)
    @patch('src.engine.ghidra.GhidraExtractor._execute_ghidra_analysis')
    def test_ghidra_extractor_validates_and_extracts(self, mock_ghidra, mock_valid):
        mock_ghidra.return_value = {
            "functions": [{"entry_point": "0x401000", "name": "main", "cfg": {"nodes": [], "edges": []}}],
            "symbols": [],
            "call_graph": {}
        }
        out_json = os.path.join(self.temp_dir.name, "ghidra_out.json")
        ext = GhidraExtractor(self.binary_file, out_json)
        res = ext.extract()

        self.assertEqual(res["schema_version"], "1.0.0")
        self.assertIn("symbols", res["data"])
        self.assertIn("functions", res["data"])
        self.assertTrue(os.path.exists(out_json))

    @patch('src.engine.radare2.Radare2Extractor.validate_environment', return_value=True)
    @patch('src.engine.radare2.Radare2Extractor._execute_radare2_analysis')
    def test_radare2_extractor_validates_and_extracts(self, mock_r2, mock_valid):
        mock_r2.return_value = {
            "functions": [],
            "symbols": [],
            "call_graph": {"nodes": [], "edges": []}
        }
        out_json = os.path.join(self.temp_dir.name, "radare2_out.json")
        ext = Radare2Extractor(self.binary_file, out_json)
        res = ext.extract()

        self.assertEqual(res["schema_version"], "1.0.0")
        self.assertIn("call_graph", res["data"])
        self.assertTrue(os.path.exists(out_json))

    @patch('src.engine.trace.TraceExtractor._parse_trace_file')
    def test_trace_extractor_validates_and_extracts(self, mock_trace):
        mock_trace.return_value = {
            "instructions_executed": [],
            "loops_detected": [],
            "dynamic_cfg_nodes": [],
            "trace_provenance": "Mock trace"
        }
        out_json = os.path.join(self.temp_dir.name, "trace_out.json")
        ext = TraceExtractor(self.binary_file, out_json)
        res = ext.extract()

        self.assertEqual(res["schema_version"], "1.0.0")
        self.assertIn("loops_detected", res["data"])
        self.assertTrue(os.path.exists(out_json))

    @patch('src.engine.ghidra.GhidraExtractor.validate_environment', return_value=True)
    @patch('src.engine.ghidra.GhidraExtractor._execute_ghidra_analysis')
    @patch('src.engine.radare2.Radare2Extractor.validate_environment', return_value=True)
    @patch('src.engine.radare2.Radare2Extractor._execute_radare2_analysis')
    @patch('src.engine.trace.TraceExtractor._parse_trace_file')
    def test_pipeline_orchestration(self, mock_trace, mock_r2, mock_r2_valid, mock_ghidra, mock_ghidra_valid):
        mock_ghidra.return_value = {"functions": [], "symbols": [], "call_graph": {}}
        mock_r2.return_value = {"functions": [], "symbols": [], "call_graph": {"nodes": [], "edges": []}}
        mock_trace.return_value = {"instructions_executed": [], "loops_detected": [], "dynamic_cfg_nodes": []}
        
        orch = PipelineOrchestrator(self.binary_file, self.temp_dir.name)
        manifest = orch.execute_all(run_ghidra=True, run_radare2=True, run_trace=True)

        self.assertEqual(manifest["status"], "success")
        self.assertEqual(manifest["total_jobs_run"], 3)
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir.name, "orchestration_manifest.json")))

    def test_radare2_fallback_order(self):
        from unittest.mock import MagicMock
        mock_r2 = MagicMock()
        
        # Test 1: aoj succeeds
        mock_r2.cmdj.side_effect = lambda cmd: [{"addr": 0x1000, "disasm": "add x0, x1, x2"}] if "aoj" in cmd else None
        ext = Radare2Extractor(self.binary_file, os.path.join(self.temp_dir.name, "r2.json"))
        res = ext._extract_block_instructions(mock_r2, 0x1000, 4, "radare2", ninstr=1)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["address"], "0x1000")
        self.assertEqual(res[0]["mnemonic"], "add")
        self.assertTrue(mock_r2.cmdj.call_args_list[0][0][0].startswith("aoj"))

        # Test 2: aoj fails, pdj succeeds
        mock_r2.reset_mock()
        mock_r2.cmdj.side_effect = lambda cmd: [{"addr": 0x1000, "disasm": "sub x0, x1, x2"}] if "pdj" in cmd else None
        res = ext._extract_block_instructions(mock_r2, 0x1000, 4, "radare2", ninstr=1)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["mnemonic"], "sub")
        cmds = [call_args[0][0] for call_args in mock_r2.cmdj.call_args_list]
        self.assertTrue(any(c.startswith("aoj") for c in cmds))
        self.assertTrue(any(c.startswith("pdj") for c in cmds))

        # Test 3: aoj and pdj fail, pDj succeeds
        mock_r2.reset_mock()
        mock_r2.cmdj.side_effect = lambda cmd: [{"addr": 0x1000, "disasm": "mul x0, x1, x2"}] if "pDj" in cmd else None
        res = ext._extract_block_instructions(mock_r2, 0x1000, 4, "radare2", ninstr=1)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["mnemonic"], "mul")
        cmds = [call_args[0][0] for call_args in mock_r2.cmdj.call_args_list]
        self.assertTrue(any(c.startswith("aoj") for c in cmds))
        self.assertTrue(any(c.startswith("pdj") for c in cmds))
        self.assertTrue(any(c.startswith("pDj") for c in cmds))

    def test_radare2_address_keys(self):
        from unittest.mock import MagicMock
        mock_r2 = MagicMock()
        ext = Radare2Extractor(self.binary_file, os.path.join(self.temp_dir.name, "r2.json"))

        # Test key: offset
        mock_r2.cmdj.return_value = [{"offset": 4096, "disasm": "mov x0, 0"}]
        res = ext._extract_block_instructions(mock_r2, 4096, 4, "radare2", ninstr=1)
        self.assertEqual(res[0]["address"], "0x1000")

        # Test key: addr
        mock_r2.cmdj.return_value = [{"addr": 4096, "disasm": "mov x0, 0"}]
        res = ext._extract_block_instructions(mock_r2, 4096, 4, "radare2", ninstr=1)
        self.assertEqual(res[0]["address"], "0x1000")

        # Test key: address
        mock_r2.cmdj.return_value = [{"address": 4096, "disasm": "mov x0, 0"}]
        res = ext._extract_block_instructions(mock_r2, 4096, 4, "radare2", ninstr=1)
        self.assertEqual(res[0]["address"], "0x1000")

    def test_radare2_opex_operand_mapping(self):
        from unittest.mock import MagicMock
        mock_r2 = MagicMock()
        ext = Radare2Extractor(self.binary_file, os.path.join(self.temp_dir.name, "r2.json"))

        # Test memory base/reg, disp/offset/delta/imm
        mock_r2.cmdj.return_value = [{
            "addr": 4096,
            "mnemonic": "ldr",
            "disasm": "ldr x0, [sp, 8]",
            "size": 4,
            "opex": {
                "operands": [
                    {"type": "reg", "value": "x0"},
                    {"type": "mem", "reg": "sp", "offset": 8, "size": 8}
                ]
            }
        }]
        res = ext._extract_block_instructions(mock_r2, 4096, 4, "radare2", ninstr=1)
        self.assertEqual(len(res), 1)
        ops = res[0]["operands"]
        self.assertEqual(len(ops), 2)
        self.assertEqual(ops[0], {"kind": "register", "value": "x0"})
        self.assertEqual(ops[1], {"kind": "memory", "base": "sp", "offset": 8, "size_bytes": 8})

if __name__ == "__main__":
    unittest.main()
