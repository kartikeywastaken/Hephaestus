# -*- coding: utf-8 -*-
"""
Phase 3: CFG Structuring & Control Flow Analysis Unit Tests
"""

import unittest
import logging
from src.ir.structuring.analysis import analyze_function
from src.ir.structuring.builder import structure_function
from src.ir.structuring.models import (
    BlockNode,
    SequenceNode,
    IfNode,
    IfElseNode,
    UnstructuredRegionNode,
    LoopNode,
)

class TestCFGStructuringAnalysis(unittest.TestCase):

    def setUp(self):
        self.logger = logging.getLogger("TestCFGStructuringAnalysis")
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s'))
            self.logger.addHandler(handler)

    def test_straight_line_cfg(self):
        """
        Tests a basic straight-line CFG topology: 0x1000 -> 0x1004 -> 0x1008
        """
        func_data = {
            "name": "straight_line",
            "entry_point": "0x1000",
            "basic_blocks": [
                {
                    "id": "0x1000",
                    "edges": [{"source": "0x1000", "target": "0x1004"}]
                },
                {
                    "id": "0x1004",
                    "edges": [{"source": "0x1004", "target": "0x1008"}]
                },
                {
                    "id": "0x1008",
                    "edges": []
                }
            ]
        }
        
        report = analyze_function(func_data, self.logger)
        
        # Verify basic attributes
        self.assertEqual(report["function_name"], "straight_line")
        self.assertEqual(report["entry_node"], "0x1000")
        self.assertEqual(report["exit_nodes"], ["0x1008"])
        self.assertEqual(report["nodes"], ["0x1000", "0x1004", "0x1008"])
        self.assertEqual(len(report["edges"]), 2)
        
        # Verify dominator sets
        doms = report["dominator_sets"]
        self.assertEqual(doms["0x1000"], ["0x1000"])
        self.assertEqual(doms["0x1004"], ["0x1000", "0x1004"])
        self.assertEqual(doms["0x1008"], ["0x1000", "0x1004", "0x1008"])
        
        # Verify immediate dominators (idom)
        idoms = report["immediate_dominators"]
        self.assertIsNone(idoms["0x1000"])
        self.assertEqual(idoms["0x1004"], "0x1000")
        self.assertEqual(idoms["0x1008"], "0x1004")
        
        # Verify post-dominator sets
        pdoms = report["post_dominator_sets"]
        self.assertEqual(pdoms["0x1000"], ["0x1000", "0x1004", "0x1008"])
        self.assertEqual(pdoms["0x1004"], ["0x1004", "0x1008"])
        self.assertEqual(pdoms["0x1008"], ["0x1008"])
        
        # Verify immediate post-dominators (ipdom)
        ipdoms = report["immediate_post_dominators"]
        self.assertEqual(ipdoms["0x1000"], "0x1004")
        self.assertEqual(ipdoms["0x1004"], "0x1008")
        self.assertIsNone(ipdoms["0x1008"])
        
        # Verify no back-edges
        self.assertEqual(len(report["detected_back_edges"]), 0)

    def test_if_else_cfg(self):
        """
        Tests a branch/diamond CFG topology:
              0x1000
             /      \
          0x1004   0x1008
             \      /
              0x100c
        """
        func_data = {
            "name": "if_else",
            "entry_point": "0x1000",
            "basic_blocks": [
                {
                    "id": "0x1000",
                    "edges": [
                        {"source": "0x1000", "target": "0x1004"},
                        {"source": "0x1000", "target": "0x1008"}
                    ]
                },
                {
                    "id": "0x1004",
                    "edges": [{"source": "0x1004", "target": "0x100c"}]
                },
                {
                    "id": "0x1008",
                    "edges": [{"source": "0x1008", "target": "0x100c"}]
                },
                {
                    "id": "0x100c",
                    "edges": []
                }
            ]
        }
        
        report = analyze_function(func_data, self.logger)
        
        # Verify basic attributes
        self.assertEqual(report["entry_node"], "0x1000")
        self.assertEqual(report["exit_nodes"], ["0x100c"])
        self.assertEqual(report["nodes"], ["0x1000", "0x1004", "0x1008", "0x100c"])
        
        # Verify dominator sets
        doms = report["dominator_sets"]
        self.assertEqual(doms["0x1000"], ["0x1000"])
        self.assertEqual(doms["0x1004"], ["0x1000", "0x1004"])
        self.assertEqual(doms["0x1008"], ["0x1000", "0x1008"])
        self.assertEqual(doms["0x100c"], ["0x1000", "0x100c"])
        
        # Verify immediate dominators
        idoms = report["immediate_dominators"]
        self.assertIsNone(idoms["0x1000"])
        self.assertEqual(idoms["0x1004"], "0x1000")
        self.assertEqual(idoms["0x1008"], "0x1000")
        self.assertEqual(idoms["0x100c"], "0x1000")
        
        # Verify post-dominator sets
        pdoms = report["post_dominator_sets"]
        self.assertEqual(pdoms["0x1000"], ["0x1000", "0x100c"])
        self.assertEqual(pdoms["0x1004"], ["0x1004", "0x100c"])
        self.assertEqual(pdoms["0x1008"], ["0x1008", "0x100c"])
        self.assertEqual(pdoms["0x100c"], ["0x100c"])
        
        # Verify immediate post-dominators
        ipdoms = report["immediate_post_dominators"]
        self.assertEqual(ipdoms["0x1000"], "0x100c")
        self.assertEqual(ipdoms["0x1004"], "0x100c")
        self.assertEqual(ipdoms["0x1008"], "0x100c")
        self.assertIsNone(ipdoms["0x100c"])
        
        # Verify no back-edges
        self.assertEqual(len(report["detected_back_edges"]), 0)

    def test_loop_cfg(self):
        """
        Tests a loop CFG topology:
          0x1000 -> 0x1004 -> 0x1008 -> 0x100c
                                ^       /
                                 \_____/ (back edge)
                                0x1008 -> 0x1010 (exit)
        """
        func_data = {
            "name": "loop_cfg",
            "entry_point": "0x1000",
            "basic_blocks": [
                {
                    "id": "0x1000",
                    "edges": [{"source": "0x1000", "target": "0x1004"}]
                },
                {
                    "id": "0x1004",
                    "edges": [{"source": "0x1004", "target": "0x1008"}]
                },
                {
                    "id": "0x1008",
                    "edges": [
                        {"source": "0x1008", "target": "0x100c"},
                        {"source": "0x1008", "target": "0x1010"}
                    ]
                },
                {
                    "id": "0x100c",
                    "edges": [{"source": "0x100c", "target": "0x1008"}]
                },
                {
                    "id": "0x1010",
                    "edges": []
                }
            ]
        }
        
        report = analyze_function(func_data, self.logger)
        
        # Verify basic attributes
        self.assertEqual(report["entry_node"], "0x1000")
        self.assertEqual(report["exit_nodes"], ["0x1010"])
        
        # Verify dominator sets
        doms = report["dominator_sets"]
        self.assertEqual(doms["0x1000"], ["0x1000"])
        self.assertEqual(doms["0x1004"], ["0x1000", "0x1004"])
        self.assertEqual(doms["0x1008"], ["0x1000", "0x1004", "0x1008"])
        self.assertEqual(doms["0x100c"], ["0x1000", "0x1004", "0x1008", "0x100c"])
        self.assertEqual(doms["0x1010"], ["0x1000", "0x1004", "0x1008", "0x1010"])
        
        # Verify back-edge detection: 0x100c -> 0x1008 is a back-edge because 0x1008 dominates 0x100c
        back_edges = report["detected_back_edges"]
        self.assertEqual(len(back_edges), 1)
        self.assertEqual(back_edges[0]["source"], "0x100c")
        self.assertEqual(back_edges[0]["destination"], "0x1008")
        self.assertEqual(back_edges[0]["candidate_loop_header"], "0x1008")
        self.assertEqual(back_edges[0]["candidate_latch"], "0x100c")
        
        # Verify post-dominator sets
        pdoms = report["post_dominator_sets"]
        self.assertEqual(pdoms["0x1000"], ["0x1000", "0x1004", "0x1008", "0x1010"])
        self.assertEqual(pdoms["0x1004"], ["0x1004", "0x1008", "0x1010"])
        self.assertEqual(pdoms["0x1008"], ["0x1008", "0x1010"])
        self.assertEqual(pdoms["0x100c"], ["0x1008", "0x100c", "0x1010"])
        self.assertEqual(pdoms["0x1010"], ["0x1010"])
        
        # Verify immediate post-dominators
        ipdoms = report["immediate_post_dominators"]
        self.assertEqual(ipdoms["0x1000"], "0x1004")
        self.assertEqual(ipdoms["0x1004"], "0x1008")
        self.assertEqual(ipdoms["0x1008"], "0x1010")
        self.assertEqual(ipdoms["0x100c"], "0x1008")
        self.assertIsNone(ipdoms["0x1010"])

    def test_recursive_multi_exit_cfg(self):
        """
        Tests a recursive function topology with multiple exits (no shared single exit block):
              0x2000
             /      \
          0x2004   0x2008
          (exit)   (exit)
        """
        func_data = {
            "name": "recursive_fact",
            "entry_point": "0x2000",
            "basic_blocks": [
                {
                    "id": "0x2000",
                    "edges": [
                        {"source": "0x2000", "target": "0x2004"},
                        {"source": "0x2000", "target": "0x2008"}
                    ]
                },
                {
                    "id": "0x2004",
                    "edges": []
                },
                {
                    "id": "0x2008",
                    "edges": []
                }
            ]
        }
        
        report = analyze_function(func_data, self.logger)
        
        # Verify entry & exit nodes
        self.assertEqual(report["entry_node"], "0x2000")
        self.assertEqual(report["exit_nodes"], ["0x2004", "0x2008"])
        
        # Verify dominator sets
        doms = report["dominator_sets"]
        self.assertEqual(doms["0x2000"], ["0x2000"])
        self.assertEqual(doms["0x2004"], ["0x2000", "0x2004"])
        self.assertEqual(doms["0x2008"], ["0x2000", "0x2008"])
        
        # Verify post-dominators
        pdoms = report["post_dominator_sets"]
        self.assertEqual(pdoms["0x2000"], ["0x2000"])
        self.assertEqual(pdoms["0x2004"], ["0x2004"])
        self.assertEqual(pdoms["0x2008"], ["0x2008"])
        
        # Verify immediate post-dominators
        ipdoms = report["immediate_post_dominators"]
        self.assertIsNone(ipdoms["0x2000"])
        self.assertIsNone(ipdoms["0x2004"])
        self.assertIsNone(ipdoms["0x2008"])

    def test_straight_line_structuring(self):
        """
        Verify that 0x1000 -> 0x1004 -> 0x1008 collapses entirely to SequenceNode
        """
        func_data = {
            "name": "seq_structuring",
            "entry_point": "0x1000",
            "basic_blocks": [
                {"id": "0x1000", "edges": [{"source": "0x1000", "target": "0x1004"}]},
                {"id": "0x1004", "edges": [{"source": "0x1004", "target": "0x1008"}]},
                {"id": "0x1008", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        self.assertIsInstance(root, SequenceNode)
        self.assertEqual(len(root.children), 3)
        self.assertEqual(root.children[0].node_id, "0x1000")
        self.assertEqual(root.children[1].node_id, "0x1004")
        self.assertEqual(root.children[2].node_id, "0x1008")

    def test_simple_if_structuring(self):
        """
        Verify that simple if collapses: s -> a, s -> m, a -> m
        """
        func_data = {
            "name": "simple_if_structuring",
            "entry_point": "0x1000",
            "basic_blocks": [
                {
                    "id": "0x1000",
                    "edges": [
                        {"source": "0x1000", "target": "0x1004"},
                        {"source": "0x1000", "target": "0x1008"}
                    ]
                },
                {"id": "0x1004", "edges": [{"source": "0x1004", "target": "0x1008"}]},
                {"id": "0x1008", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        # Expect SequenceNode([IfNode(0x1000, then=0x1004, merge=0x1008), BlockNode(0x1008)])
        self.assertIsInstance(root, SequenceNode)
        self.assertEqual(len(root.children), 2)
        
        if_node = root.children[0]
        self.assertIsInstance(if_node, IfNode)
        self.assertEqual(if_node.condition_block, "0x1000")
        self.assertEqual(if_node.then_branch.node_id, "0x1004")
        self.assertEqual(if_node.merge_block, "0x1008")
        
        merge_node = root.children[1]
        self.assertIsInstance(merge_node, BlockNode)
        self.assertEqual(merge_node.node_id, "0x1008")

    def test_if_else_diamond_structuring(self):
        """
        Verify diamond if-else collapses to IfElseNode
        """
        func_data = {
            "name": "if_else_diamond",
            "entry_point": "0x1000",
            "basic_blocks": [
                {
                    "id": "0x1000",
                    "edges": [
                        {"source": "0x1000", "target": "0x1004"},
                        {"source": "0x1000", "target": "0x1008"}
                    ]
                },
                {"id": "0x1004", "edges": [{"source": "0x1004", "target": "0x100c"}]},
                {"id": "0x1008", "edges": [{"source": "0x1008", "target": "0x100c"}]},
                {"id": "0x100c", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        # Expect SequenceNode([IfElseNode(0x1000, then=0x1004, else=0x1008, merge=0x100c), BlockNode(0x100c)])
        self.assertIsInstance(root, SequenceNode)
        self.assertEqual(len(root.children), 2)
        
        ifelse_node = root.children[0]
        self.assertIsInstance(ifelse_node, IfElseNode)
        self.assertEqual(ifelse_node.condition_block, "0x1000")
        self.assertEqual(ifelse_node.then_branch.node_id, "0x1004")
        self.assertEqual(ifelse_node.else_branch.node_id, "0x1008")
        self.assertEqual(ifelse_node.merge_block, "0x100c")
        
        merge_node = root.children[1]
        self.assertIsInstance(merge_node, BlockNode)
        self.assertEqual(merge_node.node_id, "0x100c")

    def test_asymmetric_if_else_structuring(self):
        """
        Verify asymmetric branch extraction: s -> a, s -> b, a -> m, b -> b2 -> m
        """
        func_data = {
            "name": "asymmetric_if_else",
            "entry_point": "0x1000",
            "basic_blocks": [
                {
                    "id": "0x1000",
                    "edges": [
                        {"source": "0x1000", "target": "0x1004"},
                        {"source": "0x1000", "target": "0x1008"}
                    ]
                },
                {"id": "0x1004", "edges": [{"source": "0x1004", "target": "0x100c"}]},
                {"id": "0x1008", "edges": [{"source": "0x1008", "target": "0x100a"}]},
                {"id": "0x100a", "edges": [{"source": "0x100a", "target": "0x100c"}]},
                {"id": "0x100c", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        self.assertIsInstance(root, SequenceNode)
        self.assertEqual(len(root.children), 2)
        
        ifelse_node = root.children[0]
        self.assertIsInstance(ifelse_node, IfElseNode)
        self.assertEqual(ifelse_node.condition_block, "0x1000")
        
        # then branch should be 0x1004
        self.assertIsInstance(ifelse_node.then_branch, BlockNode)
        self.assertEqual(ifelse_node.then_branch.node_id, "0x1004")
        
        # else branch should be SequenceNode([0x1008, 0x100a])
        self.assertIsInstance(ifelse_node.else_branch, SequenceNode)
        self.assertEqual(len(ifelse_node.else_branch.children), 2)
        self.assertEqual(ifelse_node.else_branch.children[0].node_id, "0x1008")
        self.assertEqual(ifelse_node.else_branch.children[1].node_id, "0x100a")
        
        self.assertEqual(ifelse_node.merge_block, "0x100c")

    def test_nested_if_else_structuring(self):
        """
        Verify nested diamond conditional:
              0x1000
             /      \
          0x1004   0x1008
             \      /    \
              \  0x1010  0x1014
               \    \      /
                \    0x1018
                 \    /
                 0x100c
        """
        func_data = {
            "name": "nested_if_else",
            "entry_point": "0x1000",
            "basic_blocks": [
                {
                    "id": "0x1000",
                    "edges": [
                        {"source": "0x1000", "target": "0x1004"},
                        {"source": "0x1000", "target": "0x1008"}
                    ]
                },
                {"id": "0x1004", "edges": [{"source": "0x1004", "target": "0x100c"}]},
                {
                    "id": "0x1008",
                    "edges": [
                        {"source": "0x1008", "target": "0x1010"},
                        {"source": "0x1008", "target": "0x1014"}
                    ]
                },
                {"id": "0x1010", "edges": [{"source": "0x1010", "target": "0x1018"}]},
                {"id": "0x1014", "edges": [{"source": "0x1014", "target": "0x1018"}]},
                {"id": "0x1018", "edges": [{"source": "0x1018", "target": "0x100c"}]},
                {"id": "0x100c", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        self.assertIsInstance(root, SequenceNode)
        self.assertEqual(len(root.children), 2)
        
        outer_ifelse = root.children[0]
        self.assertIsInstance(outer_ifelse, IfElseNode)
        self.assertEqual(outer_ifelse.condition_block, "0x1000")
        
        # outer then branch is 0x1004
        self.assertEqual(outer_ifelse.then_branch.node_id, "0x1004")
        
        # outer else branch should be SequenceNode([IfElseNode(0x1008), BlockNode(0x1018)])
        outer_else = outer_ifelse.else_branch
        self.assertIsInstance(outer_else, SequenceNode)
        self.assertEqual(len(outer_else.children), 2)
        
        inner_ifelse = outer_else.children[0]
        self.assertIsInstance(inner_ifelse, IfElseNode)
        self.assertEqual(inner_ifelse.condition_block, "0x1008")
        self.assertEqual(inner_ifelse.then_branch.node_id, "0x1010")
        self.assertEqual(inner_ifelse.else_branch.node_id, "0x1014")
        self.assertEqual(inner_ifelse.merge_block, "0x1018")
        
        inner_merge = outer_else.children[1]
        self.assertEqual(inner_merge.node_id, "0x1018")
        
        self.assertEqual(outer_ifelse.merge_block, "0x100c")

    def test_early_return_conditional_structuring(self):
        """
        Verify structuring with exits as merge points: s -> a (exit), s -> b (exit)
        """
        func_data = {
            "name": "early_return",
            "entry_point": "0x2000",
            "basic_blocks": [
                {
                    "id": "0x2000",
                    "edges": [
                        {"source": "0x2000", "target": "0x2004"},
                        {"source": "0x2000", "target": "0x2008"}
                    ]
                },
                {"id": "0x2004", "edges": []},
                {"id": "0x2008", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        # Expect an IfElseNode with merge_block = None
        self.assertIsInstance(root, IfElseNode)
        self.assertEqual(root.condition_block, "0x2000")
        self.assertEqual(root.then_branch.node_id, "0x2004")
        self.assertEqual(root.else_branch.node_id, "0x2008")
        self.assertIsNone(root.merge_block)

    def test_partial_unstructured_fallback(self):
        """
        Verify fallback wrapper for irreducible CFG cross jump cycles
        """
        func_data = {
            "name": "unstructured",
            "entry_point": "0x1000",
            "basic_blocks": [
                {
                    "id": "0x1000",
                    "edges": [
                        {"source": "0x1000", "target": "0x1004"},
                        {"source": "0x1000", "target": "0x1008"}
                    ]
                },
                {"id": "0x1004", "edges": [{"source": "0x1004", "target": "0x1008"}]},
                {"id": "0x1008", "edges": [{"source": "0x1008", "target": "0x1004"}]}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        self.assertIsInstance(root, UnstructuredRegionNode)
        self.assertTrue(len(root.children) > 1)

    def test_simple_while_loop_structuring(self):
        """
        Verify detection, loop header, latch, body containment, and 'while_like' heuristic.
        0x1000 (entry) -> 0x1004 (header)
        0x1004 -> 0x1008 (body) & 0x1004 -> 0x100c (exit)
        0x1008 -> 0x1004 (latch back-edge)
        """
        func_data = {
            "name": "simple_while",
            "entry_point": "0x1000",
            "basic_blocks": [
                {"id": "0x1000", "edges": [{"source": "0x1000", "target": "0x1004"}]},
                {
                    "id": "0x1004",
                    "edges": [
                        {"source": "0x1004", "target": "0x1008"},
                        {"source": "0x1004", "target": "0x100c"}
                    ]
                },
                {"id": "0x1008", "edges": [{"source": "0x1008", "target": "0x1004"}]},
                {"id": "0x100c", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        # Expect: SequenceNode([BlockNode(0x1000), LoopNode(while_like, header=0x1004), BlockNode(0x100c)])
        self.assertIsInstance(root, SequenceNode)
        self.assertEqual(len(root.children), 3)
        
        entry = root.children[0]
        self.assertEqual(entry.node_id, "0x1000")
        
        loop = root.children[1]
        self.assertIsInstance(loop, LoopNode)
        self.assertEqual(loop.kind, "while_like")
        self.assertEqual(loop.header_block, "0x1004")
        self.assertEqual(loop.exit_blocks, ["0x100c"])
        
        # Body contains the header and latch as a SequenceNode([0x1004, 0x1008])
        self.assertIsInstance(loop.body, SequenceNode)
        self.assertEqual(len(loop.body.children), 2)
        self.assertEqual(loop.body.children[0].node_id, "0x1004")
        self.assertEqual(loop.body.children[1].node_id, "0x1008")
        
        exit_block = root.children[2]
        self.assertEqual(exit_block.node_id, "0x100c")

    def test_simple_for_loop_structuring(self):
        """
        Verify loops with increment/latch sequence are collapsed.
        0x1004 (header) -> 0x1008 (body)
        0x1008 -> 0x100a (increment) -> 0x1004 (latch)
        0x1004 -> 0x100c (exit)
        """
        func_data = {
            "name": "for_loop",
            "entry_point": "0x1004",
            "basic_blocks": [
                {
                    "id": "0x1004",
                    "edges": [
                        {"source": "0x1004", "target": "0x1008"},
                        {"source": "0x1004", "target": "0x100c"}
                    ]
                },
                {"id": "0x1008", "edges": [{"source": "0x1008", "target": "0x100a"}]},
                {"id": "0x100a", "edges": [{"source": "0x100a", "target": "0x1004"}]},
                {"id": "0x100c", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        self.assertIsInstance(root, SequenceNode)
        self.assertEqual(len(root.children), 2)
        
        loop = root.children[0]
        self.assertIsInstance(loop, LoopNode)
        self.assertEqual(loop.header_block, "0x1004")
        
        # Body is Sequence([BlockNode(0x1004), SequenceNode([0x1008, 0x100a])])
        self.assertIsInstance(loop.body, SequenceNode)
        self.assertEqual(len(loop.body.children), 2)
        self.assertEqual(loop.body.children[0].node_id, "0x1004")
        self.assertIsInstance(loop.body.children[1], SequenceNode)
        self.assertEqual(len(loop.body.children[1].children), 2)

    def test_loop_with_nested_if_else(self):
        """
        Verify that inner conditional diamond collapses inside the loop body.
        """
        func_data = {
            "name": "loop_nested_if",
            "entry_point": "0x1004",
            "basic_blocks": [
                {
                    "id": "0x1004",
                    "edges": [
                        {"source": "0x1004", "target": "0x1008"},
                        {"source": "0x1004", "target": "0x100c"}
                    ]
                },
                {
                    "id": "0x1008",
                    "edges": [
                        {"source": "0x1008", "target": "0x1010"},
                        {"source": "0x1008", "target": "0x1014"}
                    ]
                },
                {"id": "0x1010", "edges": [{"source": "0x1010", "target": "0x1018"}]},
                {"id": "0x1014", "edges": [{"source": "0x1014", "target": "0x1018"}]},
                {"id": "0x1018", "edges": [{"source": "0x1018", "target": "0x1004"}]},
                {"id": "0x100c", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        self.assertIsInstance(root, SequenceNode)
        loop = root.children[0]
        self.assertIsInstance(loop, LoopNode)
        
        # Body should be SequenceNode([Block(0x1004), SequenceNode([IfElseNode, Block(0x1018)])])
        body_seq = loop.body
        self.assertIsInstance(body_seq, SequenceNode)
        self.assertEqual(len(body_seq.children), 2)
        self.assertEqual(body_seq.children[0].node_id, "0x1004")
        
        inner_seq = body_seq.children[1]
        self.assertIsInstance(inner_seq, SequenceNode)
        self.assertIsInstance(inner_seq.children[0], IfElseNode)
        self.assertEqual(inner_seq.children[1].node_id, "0x1018")

    def test_loop_with_asymmetric_body(self):
        """
        Verify asymmetric body inside the loop.
        """
        func_data = {
            "name": "loop_asymmetric",
            "entry_point": "0x1004",
            "basic_blocks": [
                {
                    "id": "0x1004",
                    "edges": [
                        {"source": "0x1004", "target": "0x1008"},
                        {"source": "0x1004", "target": "0x100c"}
                    ]
                },
                {
                    "id": "0x1008",
                    "edges": [
                        {"source": "0x1008", "target": "0x100a"},
                        {"source": "0x1008", "target": "0x100e"}
                    ]
                },
                {"id": "0x100a", "edges": [{"source": "0x100a", "target": "0x1010"}]},
                {"id": "0x100e", "edges": [{"source": "0x100e", "target": "0x1010"}]},
                {"id": "0x1010", "edges": [{"source": "0x1010", "target": "0x1004"}]},
                {"id": "0x100c", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        self.assertIsInstance(root, SequenceNode)
        loop = root.children[0]
        self.assertIsInstance(loop, LoopNode)
        
        # Body contains h, and then the structured IfElseNode and merge block
        self.assertIsInstance(loop.body, SequenceNode)
        self.assertEqual(loop.body.children[0].node_id, "0x1004")
        
        body_rest = loop.body.children[1]
        self.assertIsInstance(body_rest, SequenceNode)
        self.assertIsInstance(body_rest.children[0], IfElseNode)
        self.assertEqual(body_rest.children[1].node_id, "0x1010")

    def test_loop_with_post_loop_continuation(self):
        """
        Verify that continuation blocks after the loop are not absorbed.
        """
        func_data = {
            "name": "loop_continuation",
            "entry_point": "0x1000",
            "basic_blocks": [
                {"id": "0x1000", "edges": [{"source": "0x1000", "target": "0x1004"}]},
                {
                    "id": "0x1004",
                    "edges": [
                        {"source": "0x1004", "target": "0x1008"},
                        {"source": "0x1004", "target": "0x100c"}
                    ]
                },
                {"id": "0x1008", "edges": [{"source": "0x1008", "target": "0x1004"}]},
                {"id": "0x100c", "edges": [{"source": "0x100c", "target": "0x1010"}]},
                {"id": "0x1010", "edges": [{"source": "0x1010", "target": "0x1014"}]},
                {"id": "0x1014", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        # Sequence([Block(0x1000), LoopNode, SequenceNode([0x100c, 0x1010, 0x1014])])
        self.assertIsInstance(root, SequenceNode)
        self.assertEqual(len(root.children), 3)
        self.assertEqual(root.children[0].node_id, "0x1000")
        self.assertIsInstance(root.children[1], LoopNode)
        self.assertIsInstance(root.children[2], SequenceNode)
        self.assertEqual(len(root.children[2].children), 3)

    def test_nested_loops_structuring(self):
        """
        Verify that inner loops collapse first.
        """
        func_data = {
            "name": "nested_loops",
            "entry_point": "0x1000",
            "basic_blocks": [
                {"id": "0x1000", "edges": [{"source": "0x1000", "target": "0x1004"}]},
                {
                    "id": "0x1004",
                    "edges": [
                        {"source": "0x1004", "target": "0x1008"},
                        {"source": "0x1004", "target": "0x101c"}
                    ]
                },
                {
                    "id": "0x1008",
                    "edges": [
                        {"source": "0x1008", "target": "0x100c"},
                        {"source": "0x1008", "target": "0x1010"}
                    ]
                },
                {"id": "0x100c", "edges": [{"source": "0x100c", "target": "0x1008"}]},
                {"id": "0x1010", "edges": [{"source": "0x1010", "target": "0x1004"}]},
                {"id": "0x101c", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        self.assertIsInstance(root, SequenceNode)
        outer_loop = root.children[1]
        self.assertIsInstance(outer_loop, LoopNode)
        self.assertEqual(outer_loop.header_block, "0x1004")
        
        # Outer loop body contains: Block(0x1004), SequenceNode([LoopNode(inner), Block(0x1010)])
        self.assertIsInstance(outer_loop.body, SequenceNode)
        self.assertEqual(outer_loop.body.children[0].node_id, "0x1004")
        
        outer_body_rest = outer_loop.body.children[1]
        self.assertIsInstance(outer_body_rest, SequenceNode)
        
        inner_loop = outer_body_rest.children[0]
        self.assertIsInstance(inner_loop, LoopNode)
        self.assertEqual(inner_loop.header_block, "0x1008")
        self.assertEqual(inner_loop.body.children[0].node_id, "0x1008")
        self.assertEqual(inner_loop.body.children[1].node_id, "0x100c")
        
        inner_exit = outer_body_rest.children[1]
        self.assertEqual(inner_exit.node_id, "0x1010")

    def test_recursion_loop_coexistence(self):
        """
        Verify that recursion alone does not trigger LoopNode.
        """
        func_data = {
            "name": "fact_recursion",
            "entry_point": "0x2000",
            "basic_blocks": [
                {
                    "id": "0x2000",
                    "edges": [
                        {"source": "0x2000", "target": "0x2004"},
                        {"source": "0x2000", "target": "0x2008"}
                    ]
                },
                {"id": "0x2004", "edges": []},
                {"id": "0x2008", "edges": []} # recursive call block in original code, no CFG edges to 0x2000
            ]
        }
        root = structure_function(func_data, self.logger)
        # Recursion is call-level, not CFG cycle, so it structures to IfElseNode
        self.assertIsInstance(root, IfElseNode)

    def test_ambiguous_cyclic_fallback(self):
        """
        Verify fallback to UnstructuredRegionNode for non-reducible cyclic graphs.
        """
        func_data = {
            "name": "irreducible_cycle",
            "entry_point": "0x1000",
            "basic_blocks": [
                {
                    "id": "0x1000",
                    "edges": [
                        {"source": "0x1000", "target": "0x1004"},
                        {"source": "0x1000", "target": "0x1008"}
                    ]
                },
                {"id": "0x1004", "edges": [{"source": "0x1004", "target": "0x1008"}]},
                {"id": "0x1008", "edges": [{"source": "0x1008", "target": "0x1004"}]}
            ]
        }
        root = structure_function(func_data, self.logger)
        self.assertIsInstance(root, UnstructuredRegionNode)

if __name__ == "__main__":
    unittest.main()
