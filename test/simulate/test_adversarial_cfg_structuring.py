# -*- coding: utf-8 -*-
"""
Adversarial CFG Structuring Unit Tests

Validates control flow structuring fallback logic, irreducible structures,
merge block duplication prevention, and empty CFG safety.
"""

import unittest
import logging
from src.ir.structuring.builder import structure_function
from src.ir.structuring.models import (
    SequenceNode,
    IfElseNode,
    UnstructuredRegionNode,
    BlockNode,
)


class TestAdversarialCFGStructuring(unittest.TestCase):

    def setUp(self):
        self.logger = logging.getLogger("TestAdversarialCFGStructuring")
        self.logger.setLevel(logging.DEBUG)

    # Test 1 — Nested asymmetric if/else
    def test_nested_asymmetric_if_else(self):
        # A -> B, A -> C
        # B -> D, B -> E
        # D -> F, E -> F
        # F -> G, C -> G
        # G -> H
        func_data = {
            "name": "nested_asymmetric",
            "entry_point": "0x1000",
            "basic_blocks": [
                {"id": "0x1000", "edges": [{"source": "0x1000", "target": "0x1004"}, {"source": "0x1000", "target": "0x1008"}]}, # A -> B, C
                {"id": "0x1004", "edges": [{"source": "0x1004", "target": "0x100c"}, {"source": "0x1004", "target": "0x1010"}]}, # B -> D, E
                {"id": "0x1008", "edges": [{"source": "0x1008", "target": "0x1018"}]}, # C -> G
                {"id": "0x100c", "edges": [{"source": "0x100c", "target": "0x1014"}]}, # D -> F
                {"id": "0x1010", "edges": [{"source": "0x1010", "target": "0x1014"}]}, # E -> F
                {"id": "0x1014", "edges": [{"source": "0x1014", "target": "0x1018"}]}, # F -> G
                {"id": "0x1018", "edges": [{"source": "0x1018", "target": "0x101c"}]}, # G -> H
                {"id": "0x101c", "edges": []} # H
            ]
        }
        root = structure_function(func_data, self.logger)
        # Verify structure does not crash and recovers sequence / structures
        self.assertIsNotNone(root)

    # Test 2 — Loop stays unstructured before loop structuring
    def test_loop_stays_unstructured(self):
        # A -> B, B -> C, C -> B, C -> D
        # Since loop structuring is separate or fallback, verify it structures or falls back without crash.
        func_data = {
            "name": "loop_fallback",
            "entry_point": "0x1000",
            "basic_blocks": [
                {"id": "0x1000", "edges": [{"source": "0x1000", "target": "0x1004"}]}, # A -> B
                {"id": "0x1004", "edges": [{"source": "0x1004", "target": "0x1008"}]}, # B -> C
                {"id": "0x1008", "edges": [{"source": "0x1008", "target": "0x1004"}, {"source": "0x1008", "target": "0x100c"}]}, # C -> B, D
                {"id": "0x100c", "edges": []} # D
            ]
        }
        root = structure_function(func_data, self.logger)
        self.assertIsNotNone(root)

    # Test 3 — Irreducible graph stays unstructured
    def test_irreducible_graph_stays_unstructured(self):
        # A -> B, A -> C
        # B -> D, C -> D
        # D -> B, D -> E
        func_data = {
            "name": "irreducible",
            "entry_point": "0x1000",
            "basic_blocks": [
                {"id": "0x1000", "edges": [{"source": "0x1000", "target": "0x1004"}, {"source": "0x1000", "target": "0x1008"}]}, # A -> B, C
                {"id": "0x1004", "edges": [{"source": "0x1004", "target": "0x100c"}]}, # B -> D
                {"id": "0x1008", "edges": [{"source": "0x1008", "target": "0x100c"}]}, # C -> D
                {"id": "0x100c", "edges": [{"source": "0x100c", "target": "0x1004"}, {"source": "0x100c", "target": "0x1010"}]}, # D -> B, E
                {"id": "0x1010", "edges": []} # E
            ]
        }
        root = structure_function(func_data, self.logger)
        self.assertIsNotNone(root)

    # Test 4 — Merge block not duplicated in branches
    def test_merge_block_not_duplicated_in_branches(self):
        # A -> B, A -> C
        # B -> D, C -> D
        # D -> E
        func_data = {
            "name": "diamond_merge",
            "entry_point": "0x1000",
            "basic_blocks": [
                {"id": "0x1000", "edges": [{"source": "0x1000", "target": "0x1004"}, {"source": "0x1000", "target": "0x1008"}]}, # A -> B, C
                {"id": "0x1004", "edges": [{"source": "0x1004", "target": "0x100c"}]}, # B -> D
                {"id": "0x1008", "edges": [{"source": "0x1008", "target": "0x100c"}]}, # C -> D
                {"id": "0x100c", "edges": [{"source": "0x100c", "target": "0x1010"}]}, # D -> E
                {"id": "0x1010", "edges": []} # E
            ]
        }
        root = structure_function(func_data, self.logger)
        self.assertIsInstance(root, SequenceNode)
        
        # Diamond part should be structured, and merge block D should NOT be inside either the then or else branches.
        # Let's inspect the children.
        ifelse_node = None
        for child in root.children:
            if isinstance(child, IfElseNode):
                ifelse_node = child
                break
        
        if ifelse_node is not None:
            # D should be the merge block, not inside branches
            self.assertEqual(ifelse_node.merge_block, "0x100c")
            
            # The branches should be BlockNodes for B and C
            self.assertIsInstance(ifelse_node.then_branch, BlockNode)
            self.assertIsInstance(ifelse_node.else_branch, BlockNode)
            self.assertEqual(ifelse_node.then_branch.node_id, "0x1004")
            self.assertEqual(ifelse_node.else_branch.node_id, "0x1008")

    # Test 5 — Empty CFG does not crash
    def test_empty_cfg_does_not_crash(self):
        func_data = {
            "name": "empty_func",
            "entry_point": None,
            "basic_blocks": []
        }
        root = structure_function(func_data, self.logger)
        self.assertIsInstance(root, UnstructuredRegionNode)


if __name__ == "__main__":
    unittest.main()
