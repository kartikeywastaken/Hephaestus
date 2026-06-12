# -*- coding: utf-8 -*-
"""
Phase 6: Validation and Repair Engine Unit Tests
Validates AST/CFG mismatch correction and JSON reports persistence.
"""

import unittest
import os
import shutil
from src.validation.engine import ValidationAndRepairEngine

class TestValidationAndRepair(unittest.TestCase):

    def setUp(self):
        self.mock_ir = {
            "schema_version": "2.0.0",
            "provenance": {
                "binary_path": "test_sample.exe"
            },
            "data": {
                "functions": [
                    {
                        "name": "calc_fn",
                        "size_bytes": 32,
                        "confidence": 0.9,
                        "basic_blocks": [
                            {"id": "entry", "instructions": ["mov eax, 1"]}
                        ]
                    }
                ]
            }
        }

        self.mock_types = {
            "recovered_types": {
                "structs": [
                    {
                        "name": "HeaderStruct",
                        "confidence": 0.8,
                        "size_bytes": 0, # Trigger repair case
                        "members": []
                    }
                ],
                "enums": [],
                "signatures": [
                    {
                        "function_name": "calc_fn",
                        "calling_convention_detected": "unknown", # Trigger repair case
                        "inferred_prototype": "int calc_fn()",
                        "args": [],
                        "return_type": "int"
                    }
                ]
            }
        }
        self.test_source_dir = "test_src"
        self.test_val_dir = "test_val_output"
        os.makedirs(self.test_source_dir, exist_ok=True)
        
        # Write mock dummy C files
        with open(os.path.join(self.test_source_dir, "recovered.c"), "w") as f:
            f.write("// Dummy C")
        with open(os.path.join(self.test_source_dir, "structs.h"), "w") as f:
            f.write("// Dummy Header")

    def tearDown(self):
        if os.path.exists(self.test_source_dir):
            shutil.rmtree(self.test_source_dir)
        if os.path.exists(self.test_val_dir):
            shutil.rmtree(self.test_val_dir)

    def test_validation_reports(self):
        engine = ValidationAndRepairEngine(self.mock_ir, self.mock_types, self.test_source_dir)
        compile_rep, cfg_rep = engine.validate_all()
        
        self.assertEqual(compile_rep["status"], "PASSED")
        self.assertTrue(compile_rep["metrics"]["syntax_valid"])
        self.assertEqual(len(cfg_rep["cross_matches"]), 1)

    def test_repair_heuristics(self):
        engine = ValidationAndRepairEngine(self.mock_ir, self.mock_types, self.test_source_dir)
        repair_logs = engine.run_repair_subsystem()
        
        # Assert empty structs obtain safe repair fallback words
        self.assertEqual(repair_logs["mended_count"], 2)
        mended_states = [log["flaw"] for log in repair_logs["repair_logs"]]
        self.assertIn("mismatched_calling_convention", mended_states)
        self.assertIn("empty_struct_layout", mended_states)

    def test_json_persistance(self):
        engine = ValidationAndRepairEngine(self.mock_ir, self.mock_types, self.test_source_dir)
        res = engine.write_reports_to_disk(self.test_val_dir)
        
        self.assertTrue(os.path.exists(os.path.join(self.test_val_dir, "compile_report.json")))
        self.assertTrue(os.path.exists(os.path.join(self.test_val_dir, "cfg_report.json")))
        self.assertTrue(os.path.exists(os.path.join(self.test_val_dir, "repair_report.json")))

if __name__ == "__main__":
    unittest.main()
