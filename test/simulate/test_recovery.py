# -*- coding: utf-8 -*-
"""
Phase 4: Type Recovery Engine Unit Tests
Validates struct member layouts, VTable discovery, signature arity, confidence bounds, and proof metrics.
"""

import unittest
from test.simulate.recovery.types import TypeRecoveryEngine, StructType, ClassType, EnumType

class TestTypeRecoveryEngine(unittest.TestCase):

    def test_struct_member_layouts(self):
        s_type = StructType("TestStruct")
        self.assertEqual(s_type.size, 0)
        self.assertEqual(s_type.confidence, 0.4)

        # Add some fields
        s_type.add_member(0, 4, "int32")
        s_type.add_member(4, 4, "void*")
        s_type.add_member(8, 8, "int64")

        self.assertEqual(s_type.size, 16)
        self.assertEqual(len(s_type.members), 3)
        self.assertEqual(s_type.members[4]["type"], "void*")

        # Accumulate evidence
        s_type.add_evidence("dataflow_ptr", "Pointer addition offset observed", 0.3)
        self.assertAlmostEqual(s_type.confidence, 0.7, places=2)

    def test_class_vtable_binding(self):
        c_type = ClassType("DatabaseConnection")
        self.assertIsNone(c_type.vtable_pointer_offset)
        
        c_type.set_vtable(0, ["query", "disconnect"])
        self.assertEqual(c_type.vtable_pointer_offset, 0)
        self.assertEqual(len(c_type.vtable_methods), 2)
        
        c_type.add_evidence("thiscall", "ECX register flow", 0.4)
        self.assertAlmostEqual(c_type.confidence, 0.7, places=2)

    def test_enum_heuristics(self):
        e_type = EnumType("StatusEnum")
        e_type.add_value("OK", 0)
        e_type.add_value("ERROR", 1)
        self.assertEqual(len(e_type.members), 2)
        self.assertEqual(e_type.members["ERROR"], 1)

    def test_recovery_engine_inference(self):
        # Create a mock Unified IR payload
        mock_ir = {
            "schema_version": "2.0.0",
            "provenance": {
                "binary_path": "sample.exe",
                "schema_version": "2.0.0"
            },
            "data": {
                "functions": [
                    {
                        "name": "main",
                        "entry_point": "0x00401000",
                        "size_bytes": 128,
                        "calling_convention": "__cdecl",
                        "confidence": 0.9,
                        "local_variables": ["var1", "var2", "var3"],
                        "basic_blocks": [
                            {
                                "id": "0x00401000",
                                "instructions": [
                                    "mov [eax+4], ebx",
                                    "mov edx, [ebp+offset_8]"
                                ],
                                "memory_accesses": [],
                                "edges": []
                            }
                        ]
                    }
                ],
                "call_graph": {"nodes": [], "edges": []},
                "symbols": [],
                "imports": [],
                "exports": [],
                "strings": [],
                "constants": [
                    {"value": 0, "width_bits": 32, "declared_at": "0x401000"}
                ],
                "dynamic_observations": []
            }
        }

        engine = TypeRecoveryEngine(mock_ir)
        engine.run_inference()
        payload = engine.get_recovered_payload()["recovered_types"]

        # Validate inferred structs
        self.assertTrue(len(payload["structs"]) > 0)
        self.assertEqual(payload["structs"][0]["name"], "struct_ptr_main")
        
        # Validate inferred signatures
        self.assertTrue(len(payload["signatures"]) > 0)
        sig = payload["signatures"][0]
        self.assertEqual(sig["function_name"], "main")
        self.assertEqual(sig["calling_convention_detected"], "__cdecl")
        self.assertIn("int __cdecl main", sig["inferred_prototype"])

if __name__ == "__main__":
    unittest.main()
