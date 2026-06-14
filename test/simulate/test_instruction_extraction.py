# -*- coding: utf-8 -*-
"""
Instruction Extraction Unit Tests (5 tests)

Tests for:
1. Schema validation of valid instruction dicts
2. Fabricated placeholder rejection (Amendment 4 — scans raw/opcode/mnemonic/operands)
3. Assembler preserves real instructions
4. Assembler deduplicates instructions by address
5. Empty instruction lists produce valid Unified IR
"""

import unittest
from src.ir.instructions.validation import (
    validate_instruction,
    is_fabricated_placeholder,
    KNOWN_FABRICATED_STRINGS,
)
from src.ir.assembler import IRAssembler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_valid_instr(address="0x1000", opcode="add", source="test"):
    return {
        "address": address,
        "mnemonic": opcode,
        "opcode": opcode,
        "operands": [{"kind": "register", "value": "w0"}],
        "size_bytes": 4,
        "raw": f"{opcode} w0, w1, w2",
        "source": source,
    }


def _make_ghidra_raw(funcs):
    """Build a minimal Ghidra extraction envelope with given function list."""
    return {
        "data": {
            "provenance": {"language_id": "AARCH64"},
            "functions": funcs,
            "symbols": [],
            "call_graph": {"nodes": [], "edges": []},
        }
    }


def _make_func(name, entry, blocks):
    return {
        "name": name,
        "entry_point": entry,
        "size_bytes": 32,
        "calling_convention": "unknown",
        "local_variables": [],
        "cfg": {
            "nodes": blocks,
            "edges": [],
        }
    }


def _make_block(block_id, instructions):
    return {
        "id": block_id,
        "size": 16,
        "instructions_count": len(instructions),
        "instructions": instructions,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestInstructionExtraction(unittest.TestCase):

    # Test 1 — Valid instruction passes validation
    def test_valid_instruction_passes_validation(self):
        instr = _make_valid_instr()
        self.assertTrue(validate_instruction(instr))

    # Test 2 — Fabricated placeholder rejection
    def test_fabricated_placeholder_rejected(self):
        # Top-level raw
        self.assertTrue(is_fabricated_placeholder({
            "address": "0x1000", "opcode": "add", "mnemonic": "add",
            "raw": "mov eax, 0", "operands": [], "source": "test",
        }))
        # Top-level opcode
        self.assertTrue(is_fabricated_placeholder({
            "address": "0x1000", "opcode": "cmp eax", "mnemonic": "cmp",
            "raw": "cmp eax, 0", "operands": [], "source": "test",
        }))
        # Top-level mnemonic
        self.assertTrue(is_fabricated_placeholder({
            "address": "0x1000", "opcode": "je", "mnemonic": "je exit_block",
            "raw": "je exit_block", "operands": [], "source": "test",
        }))
        # Operand value
        self.assertTrue(is_fabricated_placeholder({
            "address": "0x1000", "opcode": "bl", "mnemonic": "bl",
            "raw": "bl LoadLibraryA",
            "operands": [{"kind": "symbol", "name": "LoadLibraryA"}],
            "source": "test",
        }))
        # Operand raw field
        self.assertTrue(is_fabricated_placeholder({
            "address": "0x1000", "opcode": "call", "mnemonic": "call",
            "raw": "call kernel32.dll",
            "operands": [{"kind": "unknown", "raw": "kernel32.dll"}],
            "source": "test",
        }))
        # Valid instruction should NOT be rejected
        self.assertFalse(is_fabricated_placeholder(_make_valid_instr()))

    # Test 3 — Assembler preserves real instructions (including Ghidra-style memory operands)
    def test_assembler_preserves_real_instructions(self):
        real_instr = {
            "address": "0x100000540",
            "mnemonic": "ldr",
            "opcode": "ldr",
            "operands": [{"kind": "memory", "base": "sp", "offset": 16, "size_bytes": 4}],
            "size_bytes": 4,
            "raw": "ldr w0, [sp, #16]",
            "source": "ghidra",
        }
        block = _make_block("0x100000540", [real_instr])
        func = _make_func("test_func", "0x100000540", [block])
        ghidra_data = _make_ghidra_raw([func])

        assembler = IRAssembler("test_binary")
        # Patch architecture detection
        ghidra_data["data"]["provenance"] = {"language_id": "AARCH64"}
        ir = assembler.assemble(ghidra_data, None, None)

        ir_dict = ir.to_dict()
        functions = ir_dict["data"]["functions"]
        self.assertEqual(len(functions), 1)
        blocks = functions[0].get("basic_blocks", [])
        self.assertTrue(len(blocks) > 0)
        # At least one block should have our real instruction
        instrs = blocks[0].get("instructions", [])
        self.assertEqual(len(instrs), 1)
        self.assertEqual(instrs[0]["opcode"], "ldr")
        self.assertEqual(instrs[0]["source"], "ghidra")
        self.assertEqual(instrs[0]["operands"][0]["kind"], "memory")
        self.assertEqual(instrs[0]["operands"][0]["base"], "sp")
        self.assertEqual(instrs[0]["operands"][0]["offset"], 16)
        self.assertEqual(instrs[0]["operands"][0]["size_bytes"], 4)

    # Test 4 — Assembler deduplicates instructions by address
    def test_assembler_deduplicates_instructions_by_address(self):
        instr_g = {**_make_valid_instr("0x1000", "add", "ghidra")}
        instr_r = {**_make_valid_instr("0x1000", "add", "radare2")}
        # Both at the same address; should result in one instruction
        block_g = _make_block("0x1000", [instr_g])
        block_r = _make_block("0x1000", [instr_r])
        func_g = _make_func("foo", "0x1000", [block_g])
        func_r = _make_func("foo", "0x1000", [block_r])
        ghidra_data = _make_ghidra_raw([func_g])
        radare2_data = {"data": {
            "provenance": {"arch": "arm", "bits": 64},
            "functions": [func_r],
            "symbols": [],
            "call_graph": {"nodes": [], "edges": []},
        }}
        ghidra_data["data"]["provenance"] = {"language_id": "AARCH64"}

        assembler = IRAssembler("test_binary")
        ir = assembler.assemble(ghidra_data, radare2_data, None)
        ir_dict = ir.to_dict()
        functions = ir_dict["data"]["functions"]
        self.assertEqual(len(functions), 1)
        blocks = functions[0].get("basic_blocks", [])
        instrs = blocks[0].get("instructions", []) if blocks else []
        # After deduplication, should have exactly 1 instruction at 0x1000
        self.assertEqual(len(instrs), 1)

    # Test 5 — Empty instruction extraction is allowed
    def test_empty_instruction_extraction_is_allowed(self):
        block = _make_block("0x2000", [])  # no instructions
        func = _make_func("empty_func", "0x2000", [block])
        ghidra_data = _make_ghidra_raw([func])
        ghidra_data["data"]["provenance"] = {"language_id": "AARCH64"}

        assembler = IRAssembler("test_binary")
        ir = assembler.assemble(ghidra_data, None, None)
        ir_dict = ir.to_dict()
        functions = ir_dict["data"]["functions"]
        self.assertEqual(len(functions), 1)
        blocks = functions[0].get("basic_blocks", [])
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].get("instructions", []), [])


if __name__ == "__main__":
    unittest.main()
