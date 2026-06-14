# -*- coding: utf-8 -*-
"""
Adversarial Instruction Validation & Assembler Unit Tests

Protects core correctness invariants against fabricated instructions,
improper validation casing, address parsing errors, operand garbage values,
mixed blocks, and deterministic instruction assembly.
"""

import unittest
import random
from src.ir.instructions.validation import (
    validate_instruction,
    is_fabricated_placeholder,
)
from src.ir.assembler import IRAssembler


class TestAdversarialInstructionValidation(unittest.TestCase):

    # Part 1 - Test 1: Fabricated placeholder hidden in operand field
    def test_fabricated_placeholder_hidden_in_operand_field(self):
        instr = {
            "address": "0x1000",
            "opcode": "add",
            "mnemonic": "add",
            "raw": "add x0, x1, x2",
            "operands": [
                {"kind": "register", "value": "x0"},
                {"kind": "symbol", "name": "kernel32.dll"}
            ],
            "source": "test"
        }
        self.assertTrue(is_fabricated_placeholder(instr))

    # Part 1 - Test 2: Fabricated placeholder with weird casing
    def test_fabricated_placeholder_weird_casing(self):
        test_strings = [
            "LoAdLiBrArYa",
            "GETPROCADDRESS",
            "0xDeadBeef",
            "mov eax",
            "cmp eax",
            "je exit_block"
        ]
        for val in test_strings:
            instr = {
                "address": "0x1000",
                "opcode": "add",
                "mnemonic": "add",
                "raw": f"add {val}",
                "operands": [],
                "source": "test"
            }
            self.assertTrue(is_fabricated_placeholder(instr))

            # Hidden in operand
            instr_op = {
                "address": "0x1000",
                "opcode": "add",
                "mnemonic": "add",
                "raw": "add x0, x1",
                "operands": [{"kind": "symbol", "name": val}],
                "source": "test"
            }
            self.assertTrue(is_fabricated_placeholder(instr_op))

    # Part 1 - Test 3: Fake x86 sequence on ARM64-style pipeline
    def test_fake_x86_sequence_on_arm64_pipeline(self):
        fake_seq = [
            {"address": "0x1000", "opcode": "mov", "mnemonic": "mov", "raw": "mov eax, [esp+4]", "operands": [], "source": "test"},
            {"address": "0x1004", "opcode": "cmp", "mnemonic": "cmp", "raw": "cmp eax, 0", "operands": [], "source": "test"},
            {"address": "0x1008", "opcode": "je", "mnemonic": "je", "raw": "je exit_block", "operands": [], "source": "test"}
        ]
        for instr in fake_seq:
            self.assertTrue(is_fabricated_placeholder(instr))

    # Part 1 - Test 4: Valid ARM64 instruction should not be rejected because of substring noise
    def test_valid_arm64_not_rejected_by_substring_noise(self):
        # Even though "mov" exists, "mov x0, x1" is NOT a placeholder (e.g. mov eax is a placeholder, mov isn't)
        instr = {
            "address": "0x1000",
            "raw": "mov x0, x1",
            "operands": [
                {"kind": "register", "value": "x0"},
                {"kind": "register", "value": "x1"}
            ],
            "source": "test"
        }
        self.assertTrue(validate_instruction(instr))
        self.assertEqual(instr["opcode"], "mov")
        self.assertEqual(instr["mnemonic"], "mov")
        self.assertFalse(is_fabricated_placeholder(instr))

    # Part 1 - Test 5: Only raw field exists
    def test_only_raw_field_exists(self):
        instr = {
            "address": "1000",
            "raw": "add x8, x8, #1",
            "operands": [],
            "source": "test"
        }
        self.assertTrue(validate_instruction(instr))
        self.assertEqual(instr["address"], "0x3e8")  # decimal 1000 normalized to hex 0x3e8
        self.assertEqual(instr["opcode"], "add")
        self.assertEqual(instr["mnemonic"], "add")

    # Part 1 - Test 6: Operand list contains garbage values
    def test_operand_list_garbage_values(self):
        instr = {
            "address": "0x1000",
            "opcode": "add",
            "mnemonic": "add",
            "raw": "add x0, x1, #1",
            "operands": [
                None,
                "not-a-dict",
                {"kind": "register", "value": "x0"}
            ],
            "source": "test"
        }
        # Validation should succeed (garbage operands ignored or tolerated)
        self.assertTrue(validate_instruction(instr))
        self.assertFalse(is_fabricated_placeholder(instr))

    # Part 1 - Test 7: Invalid size bytes does not kill real instruction
    def test_invalid_size_bytes_ignored(self):
        instr = {
            "address": "0x1000",
            "opcode": "ldr",
            "mnemonic": "ldr",
            "raw": "ldr w8, [sp, #16]",
            "operands": [],
            "size_bytes": "four",
            "source": "test"
        }
        self.assertTrue(validate_instruction(instr))
        self.assertIsNone(instr["size_bytes"])


class TestAdversarialAssembler(unittest.TestCase):

    # Part 2 - Test 1: Mixed good, malformed, and fabricated instructions in one block
    def test_mixed_block_instructions(self):
        # Valid add
        ins1 = {"address": "0x1000", "opcode": "add", "mnemonic": "add", "operands": [], "source": "ghidra"}
        # Malformed missing address
        ins2 = {"opcode": "sub", "mnemonic": "sub", "operands": [], "source": "ghidra"}
        # Fabricated
        ins3 = {"address": "0x1008", "opcode": "mov", "mnemonic": "mov", "raw": "mov eax, 0", "operands": [], "source": "ghidra"}
        # Valid ldr
        ins4 = {"address": "0x100c", "opcode": "ldr", "mnemonic": "ldr", "operands": [], "source": "ghidra"}

        func = {
            "name": "test_func",
            "entry_point": "0x1000",
            "size_bytes": 32,
            "calling_convention": "unknown",
            "local_variables": [],
            "cfg": {
                "nodes": [
                    {
                        "id": "0x1000",
                        "size": 16,
                        "instructions": [ins1, ins2, ins3, ins4],
                        "memory_accesses": []
                    }
                ],
                "edges": []
            }
        }

        ghidra_data = {
            "data": {
                "provenance": {"language_id": "AARCH64"},
                "functions": [func],
                "symbols": [],
                "call_graph": {"nodes": [], "edges": []}
            }
        }

        assembler = IRAssembler("test_binary")
        ir = assembler.assemble(ghidra_data, None, None)
        blocks = ir.to_dict()["data"]["functions"][0]["basic_blocks"]
        instructions = blocks[0]["instructions"]

        # Only ins1 and ins4 should survive (ins2 is malformed, ins3 is fabricated)
        self.assertEqual(len(instructions), 2)
        self.assertEqual(instructions[0]["address"], "0x1000")
        self.assertEqual(instructions[1]["address"], "0x100c")

    # Part 2 - Test 2: Duplicate instruction address with conflicting sources
    def test_duplicate_instruction_address_conflicting_sources(self):
        ins_g = {"address": "0x1000", "opcode": "add", "source": "ghidra"}
        ins_r = {"address": "0x1000", "opcode": "sub", "source": "radare2"}

        func_g = {
            "name": "test_func",
            "entry_point": "0x1000",
            "size_bytes": 32,
            "calling_convention": "unknown",
            "local_variables": [],
            "cfg": {
                "nodes": [{"id": "0x1000", "size": 16, "instructions": [ins_g]}],
                "edges": []
            }
        }

        func_r = {
            "name": "test_func",
            "entry_point": "0x1000",
            "size_bytes": 32,
            "calling_convention": "unknown",
            "local_variables": [],
            "cfg": {
                "nodes": [{"id": "0x1000", "size": 16, "instructions": [ins_r]}],
                "edges": []
            }
        }

        ghidra_data = {
            "data": {
                "provenance": {"language_id": "AARCH64"},
                "functions": [func_g]
            }
        }
        radare2_data = {
            "data": {
                "provenance": {"arch": "arm", "bits": 64},
                "functions": [func_r]
            }
        }

        # The tie-breaker:
        # First source-tool is determined by tie breaker in merging:
        # 1. basic block count, 2. edge count, 3. prefer Ghidra over Radare2
        # In this case they are identical except tool, so Ghidra wins, so block_g's instruction wins.
        # But we must assert determinism.
        assembler = IRAssembler("test_binary")
        ir1 = assembler.assemble(ghidra_data, radare2_data, None)
        ir2 = assembler.assemble(ghidra_data, radare2_data, None)

        self.assertEqual(
            ir1.to_dict()["data"]["functions"][0]["basic_blocks"][0]["instructions"],
            ir2.to_dict()["data"]["functions"][0]["basic_blocks"][0]["instructions"]
        )

    # Part 2 - Test 3: Instruction sorting with malformed address mixed in
    def test_instruction_sorting_with_malformed_address(self):
        ins_bad = {"address": "bad-address", "opcode": "add", "source": "ghidra"}
        ins1 = {"address": "0x1010", "opcode": "add", "source": "ghidra"}
        ins2 = {"address": "0x1000", "opcode": "sub", "source": "ghidra"}
        ins3 = {"address": "0x1008", "opcode": "orr", "source": "ghidra"}

        func = {
            "name": "test_func",
            "entry_point": "0x1000",
            "size_bytes": 32,
            "calling_convention": "unknown",
            "local_variables": [],
            "cfg": {
                "nodes": [
                    {
                        "id": "0x1000",
                        "size": 16,
                        "instructions": [ins1, ins_bad, ins2, ins3],
                        "memory_accesses": []
                    }
                ],
                "edges": []
            }
        }

        ghidra_data = {
            "data": {
                "provenance": {"language_id": "AARCH64"},
                "functions": [func]
            }
        }

        assembler = IRAssembler("test_binary")
        ir = assembler.assemble(ghidra_data, None, None)
        instructions = ir.to_dict()["data"]["functions"][0]["basic_blocks"][0]["instructions"]

        # bad-address is not crashed and sorted with key 0, so it appears first.
        # Remaining instructions are sorted ascending: 0x1000, 0x1008, 0x1010
        self.assertEqual(len(instructions), 4)
        self.assertEqual(instructions[0]["address"], "bad-address")
        self.assertEqual(instructions[1]["address"], "0x1000")
        self.assertEqual(instructions[2]["address"], "0x1008")
        self.assertEqual(instructions[3]["address"], "0x1010")

    # Part 2 - Test 4: Empty instruction list remains valid
    def test_empty_instruction_list_remains_valid(self):
        func = {
            "name": "test_func",
            "entry_point": "0x1000",
            "size_bytes": 32,
            "calling_convention": "unknown",
            "local_variables": [],
            "cfg": {
                "nodes": [{"id": "0x1000", "size": 16, "instructions": []}],
                "edges": []
            }
        }
        ghidra_data = {
            "data": {
                "provenance": {"language_id": "AARCH64"},
                "functions": [func]
            }
        }
        assembler = IRAssembler("test_binary")
        ir = assembler.assemble(ghidra_data, None, None)
        fdata = ir.to_dict()["data"]["functions"][0]
        self.assertEqual(fdata["basic_blocks"][0]["instructions"], [])

    # Part 2 - Test 5: Massive instruction list remains deterministic
    def test_massive_instruction_list_remains_deterministic(self):
        # Generate 500 valid instructions in random order
        addrs = [f"0x{i:x}" for i in range(1, 501)]
        random_addrs = list(addrs)
        random.shuffle(random_addrs)

        instructions = []
        for addr in random_addrs:
            instructions.append({
                "address": addr,
                "opcode": "add",
                "source": "ghidra"
            })

        func = {
            "name": "test_func",
            "entry_point": "0x1000",
            "size_bytes": 10000,
            "calling_convention": "unknown",
            "local_variables": [],
            "cfg": {
                "nodes": [{"id": "0x1000", "size": 10000, "instructions": instructions}],
                "edges": []
            }
        }

        ghidra_data = {
            "data": {
                "provenance": {"language_id": "AARCH64"},
                "functions": [func]
            }
        }

        assembler = IRAssembler("test_binary")
        ir1 = assembler.assemble(ghidra_data, None, None)
        ir2 = assembler.assemble(ghidra_data, None, None)

        insts1 = ir1.to_dict()["data"]["functions"][0]["basic_blocks"][0]["instructions"]
        insts2 = ir2.to_dict()["data"]["functions"][0]["basic_blocks"][0]["instructions"]

        self.assertEqual(insts1, insts2)
        # Verify they are correctly sorted
        sorted_addrs = [ins["address"] for ins in insts1]
        self.assertEqual(sorted_addrs, sorted(addrs, key=lambda x: int(x, 16)))


if __name__ == "__main__":
    unittest.main()
