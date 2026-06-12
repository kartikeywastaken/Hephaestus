# -*- coding: utf-8 -*-
"""
Phase 5: Source Reconstruction Engine Unit Tests
Validates AST mapping, explicit uncertain variable flags, structs headers formatting, and report output serialization.
"""

import unittest
import os
import shutil
from src.reconstruction.generator import SourceReconstructor

class TestSourceReconstruction(unittest.TestCase):

    def setUp(self):
        self.mock_ir = {
            "schema_version": "2.0.0",
            "provenance": {
                "binary_path": "test_sample.exe"
            },
            "data": {
                "functions": [
                    {
                        "name": "calculate_hash",
                        "size_bytes": 64,
                        "confidence": 0.85,
                        "stack_variables": [
                            {"name": "local_val", "offset_bytes": -8}
                        ],
                        "basic_blocks": [
                            {
                                "id": "0x401050",
                                "instructions": [
                                    "mov eax, [ecx+4]",
                                    "add eax, edx"
                                ],
                                "memory_accesses": [
                                    {"address": "0x401050", "type": "read", "size_bytes": 4}
                                ],
                                "edges": []
                            }
                        ]
                    }
                ]
            }
        }

        self.mock_types = {
            "recovered_types": {
                "structs": [
                    {
                        "name": "StaticConfig",
                        "confidence": 0.75,
                        "size_bytes": 16,
                        "members": [
                            {"offset": 0, "size": 4, "type": "int32", "usage_count": 5},
                            {"offset": 8, "size": 8, "type": "void*", "usage_count": 2}
                        ],
                        "evidence": [
                            {"rule": "stack_offset_analysis", "description": "Derived from stack alignment offsets", "weight": 0.35}
                        ]
                    }
                ],
                "enums": [
                    {
                        "name": "StateEnum",
                        "confidence": 0.9,
                        "members": {"INIT": 0, "RUNNING": 1}
                    }
                ],
                "signatures": [
                    {
                        "function_name": "calculate_hash",
                        "calling_convention_detected": "__cdecl",
                        "inferred_prototype": "int __cdecl calculate_hash(int32_t arg_0, void* arg_1)",
                        "args": [
                            {"name": "arg_0", "type": "int32_t", "source_register": "rcx"},
                            {"name": "arg_1", "type": "void*", "source_register": "rdx"}
                        ],
                        "return_type": "int32_t"
                    }
                ]
            }
        }
        self.test_dir = "test_output_reconstruct"

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_headers_generation(self):
        reconstructor = SourceReconstructor(self.mock_ir, self.mock_types)
        headers = reconstructor.generate_headers()
        
        self.assertIn("typedef struct StaticConfig", headers)
        self.assertIn("typedef enum StateEnum", headers)
        self.assertIn("uint8_t _pad_4[4];", headers) # Alignment padding between 4 and 8
        self.assertIn("int32_t field_0;", headers)
        self.assertIn("void* field_8;", headers)

    def test_function_reconstruction_with_annotations(self):
        reconstructor = SourceReconstructor(self.mock_ir, self.mock_types)
        body = reconstructor.generate_function_body("calculate_hash")
        
        self.assertIn("int __cdecl calculate_hash(int32_t arg_0, void* arg_1)", body)
        # Verify uncertain variable flags
        self.assertIn("uncertain variable type", body)
        self.assertIn("local_val", body)
        self.assertIn("block_0x401050:", body)
        self.assertIn("mov eax, [ecx+4]", body)

    def test_full_pipeline_emission(self):
        reconstructor = SourceReconstructor(self.mock_ir, self.mock_types)
        report = reconstructor.generate_all_to_disk(self.test_dir)
        
        self.assertEqual(report["total_functions_generated"], 1)
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "structs.h")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "recovered.h")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "recovered.c")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "reconstruction_report.json")))

if __name__ == "__main__":
    unittest.main()
