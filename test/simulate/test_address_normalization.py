# -*- coding: utf-8 -*-
"""
Unit and regression tests for address normalization across disassemblers, 
IR assembly, CFG structuring, layout recovery, and Phase 4D semantics merger.
"""

import unittest
from unittest.mock import MagicMock
from src.ir.utils.addressing import normalize_address, address_to_int
from src.ir.assembler import IRAssembler, score_instruction_for_merge
from src.ir.types.phase4_semantics import _attach_layouts
from src.ir.types.layout_recovery import collect_memory_access_facts

class TestAddressNormalization(unittest.TestCase):

    # Test 1 — Bare Ghidra hex string
    def test_bare_ghidra_hex_string(self):
        self.assertEqual(normalize_address("100000460"), "0x100000460")
        self.assertEqual(normalize_address("ABCDEF"), "0xabcdef")

    # Test 2 — Existing hex string
    def test_existing_hex_string(self):
        self.assertEqual(normalize_address("0x100000460"), "0x100000460")
        self.assertEqual(normalize_address("0X100000460"), "0x100000460")

    # Test 3 — Decimal corruption regression
    def test_decimal_corruption_regression(self):
        self.assertNotEqual(normalize_address("100000460"), "0x5f5e2cc")

    # Test 4 — Small decimal string
    def test_small_decimal_string(self):
        self.assertEqual(normalize_address("16"), "0x10")

    # Test 5 — Invalid address
    def test_invalid_address(self):
        self.assertIsNone(normalize_address("unknown"))
        self.assertIsNone(normalize_address(""))
        self.assertIsNone(normalize_address(None))

    # Test 6 — Assembler dedupes address spelling
    def test_assembler_dedupes_address_spelling(self):
        ghidra_data = {
            "provenance": {"language_id": "AARCH64:LE:64:v8A"},
            "functions": [{
                "name": "_basic_score",
                "entry_point": "100000460",
                "cfg": {
                    "nodes": [{
                        "id": "100000460",
                        "size": 16,
                        "instructions": [
                            {"address": "100000470", "opcode": "ldr", "source": "ghidra", "operands": [{"kind": "memory", "base": "x0", "offset": 0}]}
                        ]
                    }],
                    "edges": []
                }
            }],
            "symbols": [{"name": "_basic_score", "address": "100000460", "type": "function"}]
        }
        radare2_data = {
            "provenance": {"arch": "arm", "bits": 64},
            "functions": [{
                "name": "sym._basic_score",
                "entry_point": "0x100000460",
                "cfg": {
                    "nodes": [{
                        "id": "0x100000460",
                        "size": 16,
                        "instructions": [
                            {"address": "0x100000470", "opcode": "ldr", "source": "radare2", "operands": []}
                        ]
                    }],
                    "edges": []
                }
            }],
            "symbols": [{"name": "sym._basic_score", "address": "0x100000460", "type": "function"}]
        }

        assembler = IRAssembler("dummy_path")
        ir = assembler.assemble(ghidra_data=ghidra_data, radare2_data=radare2_data)

        # Confirm function was merged and has only 1 instruction
        func = next(f for f in ir.functions if f["entry_point"] == "0x100000460")
        self.assertEqual(func["name"], "_basic_score")
        
        bb = next(b for b in func["basic_blocks"] if b["id"] == "0x100000460")
        self.assertEqual(len(bb["instructions"]), 1)
        # Kept the Ghidra one due to memory operands scoring policy
        self.assertEqual(bb["instructions"][0]["address"], "0x100000470")
        self.assertEqual(bb["instructions"][0]["source"], "ghidra")

    # Test 7 — Function entry not ret address
    def test_function_entry_not_ret_address(self):
        # Explicit entry is at 0x100000530, but that contains a return instruction or is last block.
        # We prefer explicit extractor entry point if valid, but if symbols or blocks give a better start:
        ghidra_data = {
            "provenance": {"language_id": "AARCH64:LE:64:v8A"},
            "functions": [{
                "name": "_basic_score",
                "entry_point": "100000530",
                "cfg": {
                    "nodes": [
                        {
                            "id": "100000460",
                            "size": 16,
                            "instructions": [{"address": "100000460", "opcode": "ldr", "source": "ghidra", "operands": []}]
                        },
                        {
                            "id": "100000530",
                            "size": 4,
                            "instructions": [{"address": "100000530", "opcode": "ret", "source": "ghidra", "operands": []}]
                        }
                    ],
                    "edges": []
                }
            }],
            "symbols": [
                {"name": "_basic_score", "address": "100000460", "type": "function"}
            ]
        }

        assembler = IRAssembler("dummy_path")
        ir = assembler.assemble(ghidra_data=ghidra_data)

        # Expected entry point should be resolved using symbol table to 0x100000460, not the ret instruction block at 0x100000530.
        self.assertTrue(any(f["entry_point"] == "0x100000460" for f in ir.functions))
        self.assertFalse(any(f["entry_point"] == "0x100000530" for f in ir.functions))

    # Test 8 — Layout source addresses normalized
    def test_layout_source_addresses_normalized(self):
        unified_ir = {
            "functions": [{
                "name": "_basic_score",
                "entry_point": "100000460",
                "basic_blocks": [{
                    "id": "100000460",
                    "instructions": [
                        {
                            "address": "100000470",
                            "opcode": "ldr",
                            "operands": [{"kind": "memory", "base": "x0", "offset": 16}]
                        }
                    ]
                }]
            }]
        }
        facts = collect_memory_access_facts(unified_ir)
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0].function_entry, "0x100000460")
        self.assertEqual(facts[0].instr_address, "0x100000470")

    # Test 9 — Phase 4D preserves normalized addresses
    def test_phase4d_preserves_normalized_addresses(self):
        all_candidates = [
            {
                "function_entry": "100000460",
                "function_name": "_basic_score",
                "base_id": "x0",
                "layout_kind": "scalar",
                "source_instrs": ["100000470"]
            }
        ]
        all_unbound = [
            {
                "function_entry": "100000460",
                "function_name": "_basic_score",
                "base_id": "sp",
                "block_id": "100000460",
                "instr_address": "100000470"
            }
        ]
        matched_candidates, matched_unbound = _attach_layouts(
            "0x100000460", "_basic_score", all_candidates, all_unbound
        )

        self.assertEqual(len(matched_candidates), 1)
        self.assertEqual(matched_candidates[0]["function_entry"], "0x100000460")
        self.assertEqual(matched_candidates[0]["source_instrs"], ["0x100000470"])

        self.assertEqual(len(matched_unbound), 1)
        self.assertEqual(matched_unbound[0]["function_entry"], "0x100000460")
        self.assertEqual(matched_unbound[0]["block_id"], "0x100000460")
        self.assertEqual(matched_unbound[0]["instr_address"], "0x100000470")

    # Test 10 — Artifact scan for bare long hex and 0x5f5e corrupted addresses
    def test_artifact_scan(self):
        import os
        import json
        import re
        
        artifacts_dir = "artifacts"
        if not os.path.exists(artifacts_dir):
            return
            
        address_keys = {
            "entry_point", "address", "id", "source", "target", "caller", "callee", 
            "function_entry", "block_id", "instr_address", "base_id", "source_instrs"
        }
        hex_pattern = re.compile(r'^[0-9a-fA-F]+$')
        
        def scan_value(val, key, path):
            issues = []
            if isinstance(val, str):
                if "0x5f5e" in val:
                    issues.append(f"Corrupted address 0x5f5e found at {path} ({key}: {val})")
                is_address_key = any(k in key for k in address_keys) if key else False
                if is_address_key:
                    if hex_pattern.match(val) and len(val) >= 6:
                        issues.append(f"Bare long hex-like address found at {path} ({key}: {val})")
            elif isinstance(val, dict):
                for k, v in val.items():
                    issues.extend(scan_value(v, k, f"{path}.{k}"))
            elif isinstance(val, list):
                for idx, item in enumerate(val):
                    issues.extend(scan_value(item, key, f"{path}[{idx}]"))
            return issues
            
        all_issues = []
        for filename in os.listdir(artifacts_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(artifacts_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    all_issues.extend(scan_value(data, None, filename))
                except Exception:
                    pass
                    
        self.assertEqual(all_issues, [], f"Address scan issues found: {all_issues}")

if __name__ == "__main__":
    unittest.main()
