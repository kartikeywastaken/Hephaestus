# -*- coding: utf-8 -*-
"""
Unified Evidence Model (IR) Unit Tests
Tests canonical de-serialization, confidence heuristic solvers, and schematic structural soundness.
"""

import unittest
import json
from extraction.ir.models import UnifiedIR
from extraction.ir.assembler import IRAssembler
from extraction.ir.validator import IRValidator

class TestUnifiedEvidenceModel(unittest.TestCase):

    def test_ir_building_blocks(self):
        meta = {
            "path": "test_app.exe",
            "sha256": "abcdef1234567890",
            "architecture": "x64"
        }
        ir = UnifiedIR(meta)
        
        # Add basic symbols and imports
        ir.add_symbol("0x00401000", "main", "function")
        ir.add_import("VirtualAlloc", "kernel32.dll", "0x00405000")
        
        # Add function and blocks
        ir.add_function("main", "0x00401000", 256, "__cdecl", "int main(int argc)")
        ir.add_basic_block(
            func_entry="0x00401000",
            block_id="0x00401000",
            size=32,
            instructions=["push ebp", "mov ebp, esp"]
        )

        payload = ir.to_dict()
        self.assertEqual(payload["schema_version"], "2.0.0")
        self.assertEqual(payload["provenance"]["binary_path"], "test_app.exe")
        self.assertEqual(len(payload["data"]["functions"]), 1)
        self.assertEqual(payload["data"]["functions"][0]["name"], "main")
        self.assertEqual(len(payload["data"]["functions"][0]["basic_blocks"]), 1)

    def test_validation_rules_compliance(self):
        meta = {
            "path": "test_app.exe",
            "sha256": "abcdef1234567890",
            "architecture": "x64"
        }
        ir = UnifiedIR(meta)
        ir.add_function("main", "0x00401000", 128)
        ir.add_basic_block(
            func_entry="0x00401000",
            block_id="0x00401000",
            size=16,
            instructions=["xor eax, eax", "ret"]
        )
        payload = ir.to_dict()

        success, msg = IRValidator.validate_payload(payload)
        self.assertTrue(success, f"IR payload validation failed: {msg}")

    def test_validation_failures_on_corrupt_payload(self):
        # 1. Non-dict payload
        success, msg = IRValidator.validate_payload([]) # type: ignore
        self.assertFalse(success)
        self.assertIn("must be a root dict", msg)

        # 2. Deficient schema version
        payload = {
            "schema_version": "1.0.0",
            "provenance": {"binary_path": "a.exe", "schema_version": "1.0.0"},
            "data": {}
        }
        success, msg = IRValidator.validate_payload(payload)
        self.assertFalse(success)
        self.assertIn("Unsupported schema version", msg)

    def test_assembler_merges_disassemblers(self):
        # Build mock Ghidra input data
        g_data = {
            "data": {
                "functions": [
                    {
                        "entry_point": "0x00401000",
                        "name": "main",
                        "size_bytes": 100,
                        "calling_convention": "__cdecl",
                        "local_variables": ["argc"]
                    }
                ],
                "symbols": [
                    {"address": "0x00401000", "name": "main", "type": "function"}
                ],
                "call_graph": {"nodes": ["main"], "edges": []}
            }
        }

        # Build mock IDA input data
        i_data = {
            "data": {
                "functions": [
                    {
                        "entry_point": "0x00401000",
                        "name": "main",
                        "size_bytes": 120, # Larger size takes preference
                        "calling_convention": "__cdecl",
                        "local_variables": ["argc", "argv"] # Merged variables list
                    }
                ],
                "symbols": [
                    {"address": "0x00401000", "name": "main", "type": "function"}
                ],
                "call_graph": {"nodes": ["main"], "edges": []}
            }
        }

        assembler = IRAssembler("target.bin")
        unified = assembler.assemble(g_data, i_data, None)
        payload = unified.to_dict()

        funcs = payload["data"]["functions"]
        self.assertEqual(len(funcs), 1)
        self.assertEqual(funcs[0]["size_bytes"], 120)
        self.assertEqual(funcs[0]["confidence"], 1.0) # Confirmed by both static run tools
        self.assertIn("argv", [v["name"] for v in funcs[0]["stack_variables"]])

if __name__ == "__main__":
    unittest.main()
