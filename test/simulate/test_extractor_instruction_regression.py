# -*- coding: utf-8 -*-
"""
Regression tests for Phase 1 instruction extraction fixes (Tweaks 1-12).
"""

import unittest
from unittest.mock import MagicMock
from src.engine.radare2 import Radare2Extractor
from src.engine.ghidra import GhidraExtractor
from src.ir.instructions.validation import validate_instruction, is_fabricated_placeholder

class TestExtractorInstructionRegression(unittest.TestCase):

    def setUp(self):
        self.binary_file = "eh"  # Dummy path, won't be opened directly for unit mock tests
        self.output_json = "out.json"

    # Test 1 — Radare2 aoj returns instructions
    def test_r2_aoj_returns_instructions(self):
        mock_r2 = MagicMock()
        mock_r2.cmdj.side_effect = lambda cmd: (
            [{"addr": 4096, "disasm": "add x0, x1, x2", "mnemonic": "add"}]
            if "aoj" in cmd else None
        )
        ext = Radare2Extractor(self.binary_file, self.output_json)
        instrs = ext._extract_block_instructions(mock_r2, 4096, 4, "radare2", ninstr=1)
        self.assertEqual(len(instrs), 1)
        self.assertEqual(instrs[0]["mnemonic"], "add")
        self.assertTrue(any("aoj" in call[0][0] for call in mock_r2.cmdj.call_args_list))

    # Test 2 — Radare2 aoj empty, pdj fallback works
    def test_r2_pdj_fallback_works(self):
        mock_r2 = MagicMock()
        mock_r2.cmdj.side_effect = lambda cmd: (
            [{"addr": 4096, "disasm": "sub x0, x1, x2", "mnemonic": "sub"}]
            if "pdj" in cmd else None
        )
        ext = Radare2Extractor(self.binary_file, self.output_json)
        instrs = ext._extract_block_instructions(mock_r2, 4096, 4, "radare2", ninstr=1)
        self.assertEqual(len(instrs), 1)
        self.assertEqual(instrs[0]["mnemonic"], "sub")
        cmds = [call[0][0] for call in mock_r2.cmdj.call_args_list]
        self.assertTrue(any("aoj" in c for c in cmds))
        self.assertTrue(any("pdj" in c for c in cmds))

    # Test 3 — Radare2 aoj/pdj empty, pDj fallback works
    def test_r2_pDj_fallback_works(self):
        mock_r2 = MagicMock()
        mock_r2.cmdj.side_effect = lambda cmd: (
            [{"addr": 4096, "disasm": "mul x0, x1, x2"}]
            if "pDj" in cmd else None
        )
        ext = Radare2Extractor(self.binary_file, self.output_json)
        instrs = ext._extract_block_instructions(mock_r2, 4096, 4, "radare2", ninstr=1)
        self.assertEqual(len(instrs), 1)
        self.assertEqual(instrs[0]["mnemonic"], "mul")
        cmds = [call[0][0] for call in mock_r2.cmdj.call_args_list]
        self.assertTrue(any("aoj" in c for c in cmds))
        self.assertTrue(any("pdj" in c for c in cmds))
        self.assertTrue(any("pDj" in c for c in cmds))

    # Test 4 — Radare2 uses addr/address when offset is missing
    def test_r2_address_keys_fallback(self):
        mock_r2 = MagicMock()
        ext = Radare2Extractor(self.binary_file, self.output_json)

        # Uses 'addr' key
        mock_r2.cmdj.return_value = [{"addr": 4096, "disasm": "mov x0, 0"}]
        instrs = ext._extract_block_instructions(mock_r2, 4096, 4, "radare2", ninstr=1)
        self.assertEqual(instrs[0]["address"], "0x1000")

        # Uses 'address' key
        mock_r2.cmdj.return_value = [{"address": 8192, "disasm": "mov x0, 0"}]
        instrs = ext._extract_block_instructions(mock_r2, 8192, 4, "radare2", ninstr=1)
        self.assertEqual(instrs[0]["address"], "0x2000")

    # Test 5 — Radare2 mnemonic is extracted from mnemonic field or disasm fallback
    def test_r2_mnemonic_precedence(self):
        mock_r2 = MagicMock()
        ext = Radare2Extractor(self.binary_file, self.output_json)

        # Case A: has mnemonic
        mock_r2.cmdj.return_value = [{"addr": 4096, "mnemonic": "ldr", "disasm": "ldr x0, [sp]"}]
        instrs = ext._extract_block_instructions(mock_r2, 4096, 4, "radare2", ninstr=1)
        self.assertEqual(instrs[0]["mnemonic"], "ldr")

        # Case B: no mnemonic, fallback to disasm splitting
        mock_r2.cmdj.return_value = [{"addr": 4096, "disasm": "str w0, [sp]"}]
        instrs = ext._extract_block_instructions(mock_r2, 4096, 4, "radare2", ninstr=1)
        self.assertEqual(instrs[0]["mnemonic"], "str")

    # Test 6 — Radare2 structured memory operand becomes canonical memory operand
    def test_r2_structured_memory_operand(self):
        mock_r2 = MagicMock()
        ext = Radare2Extractor(self.binary_file, self.output_json)
        mock_r2.cmdj.return_value = [{
            "addr": 4096,
            "mnemonic": "ldr",
            "disasm": "ldr w0, [sp, #16]",
            "size": 4,
            "opex": {
                "operands": [
                    {"type": "reg", "value": "w0"},
                    {"type": "mem", "reg": "sp", "disp": 16, "size": 4}
                ]
            }
        }]
        instrs = ext._extract_block_instructions(mock_r2, 4096, 4, "radare2", ninstr=1)
        self.assertEqual(len(instrs), 1)
        self.assertEqual(len(instrs[0]["operands"]), 2)
        mem_op = instrs[0]["operands"][1]
        self.assertEqual(mem_op["kind"], "memory")
        self.assertEqual(mem_op["base"], "sp")
        self.assertEqual(mem_op["offset"], 16)
        self.assertEqual(mem_op["size_bytes"], 4)

    # Test 7 — Raw-only memory-looking text does not become memory operand
    def test_r2_raw_only_memory_text_does_not_become_memory(self):
        mock_r2 = MagicMock()
        ext = Radare2Extractor(self.binary_file, self.output_json)
        # No opex, only disasm text
        mock_r2.cmdj.return_value = [{
            "addr": 4096,
            "disasm": "ldr w0, [sp, #16]",
            "size": 4
        }]
        instrs = ext._extract_block_instructions(mock_r2, 4096, 4, "radare2", ninstr=1)
        self.assertEqual(len(instrs), 1)
        # Radare2 fallback doesn't aggressively parse raw strings to memory operand
        self.assertEqual(len(instrs[0]["operands"]), 1)
        self.assertEqual(instrs[0]["operands"][0]["kind"], "unknown")
        self.assertEqual(instrs[0]["operands"][0]["raw"], "w0, [sp, #16]")

    # Test 8 — instructions_count equals len(instructions)
    from unittest.mock import patch
    @patch('r2pipe.open')
    def test_instructions_count_equals_real_length(self, mock_open):
        mock_r2 = MagicMock()
        def cmdj_side_effect(cmd):
            if "ij" in cmd:
                return {"bin": {"arch": "arm", "bits": 64}}
            if "aflj" in cmd:
                return [{"name": "sym.func", "addr": 4096, "size": 8}]
            if "isj" in cmd:
                return []
            if "afbj" in cmd:
                return [{"addr": 4096, "ninstr": 2, "size": 8}]
            if "aoj" in cmd or "pdj" in cmd or "pDj" in cmd:
                return [{"addr": 4096, "disasm": "mov x0, 0"}, {"addr": 4104, "disasm": "mov x1, 1"}]
            if "axffj" in cmd:
                return []
            return None
        mock_r2.cmdj.side_effect = cmdj_side_effect
        mock_open.return_value = mock_r2

        ext = Radare2Extractor(self.binary_file, self.output_json)
        # Block size is 8, but range filter is [4096, 4096 + 8) = [4096, 4104)
        # The second instruction is at 4104, so it is filtered out!
        data = ext._execute_radare2_analysis()
        func = data["functions"][0]
        nodes = func["cfg"]["nodes"]
        self.assertEqual(len(nodes), 1)
        # Instructions count is actual length (1), not estimated block instruction count (2)
        self.assertEqual(nodes[0]["instructions_count"], 1)
        self.assertEqual(nodes[0]["estimated_instructions_count"], 2)
        self.assertEqual(len(nodes[0]["instructions"]), 1)

    # Test 9 — Ghidra-style memory operands are parsed correctly
    def test_ghidra_style_memory_operands_parsing(self):
        canonical_ghidra_instr = {
            "address": "0x1000",
            "mnemonic": "ldr",
            "opcode": "ldr",
            "operands": [
                {"kind": "register", "value": "w0"},
                {"kind": "memory", "base": "sp", "offset": 16, "size_bytes": 4}
            ],
            "size_bytes": 4,
            "raw": "ldr w0, [sp, #16]",
            "source": "ghidra"
        }
        self.assertTrue(validate_instruction(canonical_ghidra_instr))

    # Test 10 — Empty instruction extraction remains allowed
    def test_empty_instruction_extraction_is_allowed(self):
        mock_r2 = MagicMock()
        mock_r2.cmdj.return_value = [] # no instructions returned
        ext = Radare2Extractor(self.binary_file, self.output_json)
        instrs = ext._extract_block_instructions(mock_r2, 4096, 4, "radare2", ninstr=1)
        self.assertEqual(instrs, [])

    # Test 11 — No fake placeholder instructions are inserted
    def test_no_fake_placeholder_instructions(self):
        instr = {
            "address": "0x1000",
            "mnemonic": "mov",
            "opcode": "mov",
            "operands": [{"kind": "register", "value": "eax"}],
            "size_bytes": 4,
            "raw": "mov eax, 0",  # Fake placeholder raw string
            "source": "radare2"
        }
        self.assertTrue(is_fabricated_placeholder(instr))

if __name__ == "__main__":
    unittest.main()
