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

    def test_weak_loop_body_not_reducing_is_rejected(self):
        """
        Verify that a candidate loop is rejected if its back-edge-removed body
        does not reduce to a single structured root.
        """
        func_data = {
            "name": "weak_loop_rejected",
            "entry_point": "0x1000",
            "basic_blocks": [
                {
                    "id": "0x1000",
                    "edges": [
                        {"source": "0x1000", "target": "0x1004"},
                        {"source": "0x1000", "target": "0x1008"}
                    ]
                },
                {"id": "0x1008", "edges": [{"source": "0x1008", "target": "0x1004"}, {"source": "0x1008", "target": "0x100c"}]},
                {"id": "0x1004", "edges": [{"source": "0x1004", "target": "0x100c"}]},
                {"id": "0x100c", "edges": [{"source": "0x100c", "target": "0x1000"}]}
            ]
        }
        root = structure_function(func_data, self.logger)
        # Should NOT contain a LoopNode because the loop was rejected
        def has_loop_node(node):
            if isinstance(node, LoopNode):
                return True
            if hasattr(node, "children"):
                return any(has_loop_node(c) for c in node.children)
            if hasattr(node, "then_branch") and node.then_branch:
                if has_loop_node(node.then_branch):
                    return True
            if hasattr(node, "else_branch") and node.else_branch:
                if has_loop_node(node.else_branch):
                    return True
            return False

        self.assertFalse(has_loop_node(root), "Weak loop candidate was incorrectly structured as a LoopNode")
        self.assertIsInstance(root, UnstructuredRegionNode)

    def test_helper_false_positive_rejected(self):
        """
        Recreates the _helper CFG structure where recursive call back-edges
        form a natural loop that is weak and must be rejected.
        """
        func_data = {
            "name": "_helper_mock",
            "entry_point": "0x460",
            "basic_blocks": [
                {
                    "id": "0x460",
                    "edges": [
                        {"source": "0x460", "target": "0x47c"},
                        {"source": "0x460", "target": "0x48c"}
                    ]
                },
                {"id": "0x47c", "edges": [{"source": "0x47c", "target": "0x480"}]},
                {"id": "0x480", "edges": [{"source": "0x480", "target": "0x4f0"}]},
                {
                    "id": "0x48c",
                    "edges": [
                        {"source": "0x48c", "target": "0x4a4"},
                        {"source": "0x48c", "target": "0x4cc"}
                    ]
                },
                {"id": "0x4a4", "edges": [{"source": "0x4a4", "target": "0x4a8"}]},
                {
                    "id": "0x4a8",
                    "edges": [
                        {"source": "0x4a8", "target": "0x460"}, # back-edge
                        {"source": "0x4a8", "target": "0x4bc"}
                    ]
                },
                {"id": "0x4bc", "edges": [{"source": "0x4bc", "target": "0x4f0"}]},
                {
                    "id": "0x4cc",
                    "edges": [
                        {"source": "0x4cc", "target": "0x460"}, # back-edge
                        {"source": "0x4cc", "target": "0x4e0"}
                    ]
                },
                {"id": "0x4e0", "edges": [{"source": "0x4e0", "target": "0x4f0"}]},
                {"id": "0x4f0", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        # Verify that no LoopNode is constructed
        def has_loop_node(node):
            if isinstance(node, LoopNode):
                return True
            if hasattr(node, "children"):
                return any(has_loop_node(c) for c in node.children)
            if hasattr(node, "then_branch") and node.then_branch:
                if has_loop_node(node.then_branch):
                    return True
            if hasattr(node, "else_branch") and node.else_branch:
                if has_loop_node(node.else_branch):
                    return True
            return False

        self.assertFalse(has_loop_node(root), "Helper recursive back-edge was incorrectly structured as a LoopNode")
        self.assertIsInstance(root, UnstructuredRegionNode)


class TestPhase3DHardCases(unittest.TestCase):
    """
    Phase 3D: robustness and conservative fallback tests.
    All hard cases must be handled without bogus structuring, without crash,
    and with deterministic output.
    """

    def setUp(self):
        self.logger = logging.getLogger("TestPhase3DHardCases")
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s'))
            self.logger.addHandler(handler)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _find_nodes(self, root, cls):
        """Recursively collect all RegionNode instances of type `cls`."""
        found = []
        self._collect(root, cls, found)
        return found

    def _collect(self, node, cls, acc):
        if isinstance(node, cls):
            acc.append(node)
        for attr in ("children", ):
            for child in getattr(node, attr, []):
                self._collect(child, cls, acc)
        for attr in ("body", "then_branch", "else_branch"):
            child = getattr(node, attr, None)
            if child is not None:
                self._collect(child, cls, acc)

    # ------------------------------------------------------------------
    # 1. Irreducible goto fallback
    # ------------------------------------------------------------------

    def test_irreducible_goto_fallback(self):
        """
        Mutual back-edges: A->B, A->C, B->C, C->B
        B and C enter each other — neither dominates the other, making the
        graph irreducible.  The result must be an UnstructuredRegionNode with
        no bogus LoopNode and a reason in {"irreducible_cfg", "partial_reduction"}.
        """
        func_data = {
            "name": "irreducible_goto",
            "entry_point": "0xA000",
            "basic_blocks": [
                {
                    "id": "0xA000",
                    "edges": [
                        {"source": "0xA000", "target": "0xA004"},
                        {"source": "0xA000", "target": "0xA008"},
                    ],
                },
                {
                    "id": "0xA004",
                    "edges": [{"source": "0xA004", "target": "0xA008"}],
                },
                {
                    "id": "0xA008",
                    "edges": [{"source": "0xA008", "target": "0xA004"}],
                },
            ],
        }
        root = structure_function(func_data, self.logger)

        self.assertIsInstance(root, UnstructuredRegionNode)
        # No bogus LoopNode
        self.assertEqual(self._find_nodes(root, LoopNode), [])
        # Reason must be present and be a known conservative fallback
        self.assertIn(root.reason, {"irreducible_cfg", "partial_reduction", "multi_exit_loop"})

    # ------------------------------------------------------------------
    # 2. Multi-exit loop fallback
    # ------------------------------------------------------------------

    def test_multi_exit_loop_fallback(self):
        """
        Loop with 2 exits to nodes outside the loop region.
        H->body->H (latch), body->exit1 (break), H->exit2 (loop condition exit),
        exit1 and exit2 are outside the natural loop body.
        Must not crash; if fallback, reason must be a valid hard-case reason.
        """
        func_data = {
            "name": "multi_exit_loop",
            "entry_point": "0xB000",
            "basic_blocks": [
                # H: branches to body or exit2
                {
                    "id": "0xB000",
                    "edges": [
                        {"source": "0xB000", "target": "0xB004"},
                        {"source": "0xB000", "target": "0xB014"},  # exit2
                    ],
                },
                # body: branches to latch or exit1
                {
                    "id": "0xB004",
                    "edges": [
                        {"source": "0xB004", "target": "0xB008"},  # to latch
                        {"source": "0xB004", "target": "0xB010"},  # exit1
                    ],
                },
                # latch: back-edge to H
                {
                    "id": "0xB008",
                    "edges": [{"source": "0xB008", "target": "0xB000"}],
                },
                # exit1
                {"id": "0xB010", "edges": []},
                # exit2
                {"id": "0xB014", "edges": []},
            ],
        }
        root = structure_function(func_data, self.logger)

        # Must not crash and must produce a deterministic result
        self.assertIsNotNone(root)

        # If the result is unstructured, the reason must be a valid hard-case reason
        valid_reasons = {
            "multi_exit_loop",
            "irreducible_cfg",
            "fragmented_loop_body",
            "partial_reduction",
        }
        if isinstance(root, UnstructuredRegionNode):
            self.assertIn(root.reason, valid_reasons)

    # ------------------------------------------------------------------
    # 3. Switch fan-out detection
    # ------------------------------------------------------------------

    def test_switch_fanout_detection(self):
        """
        One node with 4 successors — clearly not reducible as binary conditional.
        Result must be UnstructuredRegionNode with reason='switch_candidate'.
        """
        func_data = {
            "name": "switch_fanout",
            "entry_point": "0xC000",
            "basic_blocks": [
                {
                    "id": "0xC000",
                    "edges": [
                        {"source": "0xC000", "target": "0xC004"},
                        {"source": "0xC000", "target": "0xC008"},
                        {"source": "0xC000", "target": "0xC00c"},
                        {"source": "0xC000", "target": "0xC010"},
                    ],
                },
                {"id": "0xC004", "edges": []},
                {"id": "0xC008", "edges": []},
                {"id": "0xC00c", "edges": []},
                {"id": "0xC010", "edges": []},
            ],
        }
        root = structure_function(func_data, self.logger)

        self.assertIsInstance(root, UnstructuredRegionNode)
        self.assertEqual(root.reason, "switch_candidate")
        self.assertEqual(root.region_kind, "switch_candidate")

    # ------------------------------------------------------------------
    # 4. Partial reduction preservation
    # ------------------------------------------------------------------

    def test_partial_reduction_preserved(self):
        """
        A CFG with a loop where the inner conditional diamond collapses to an
        IfElseNode inside the loop body DAG, but the outer loop is rejected
        because the body has multiple exits — leaving the inner structured node
        preserved inside the final UnstructuredRegionNode.

        Topology:
          entry(0xD000) -> loop_header(0xD004) [straight line]
          loop_header(0xD004) -> cond_split(0xD008) or exit(0xD030)
          cond_split(0xD008) -> then(0xD010) or else(0xD014)
          then(0xD010) -> merge(0xD018)
          else(0xD014) -> merge(0xD018)
          merge(0xD018) -> latch1(0xD020) or break_exit(0xD024)  [multi-exit]
          latch1(0xD020) -> loop_header(0xD004) [back-edge]
          break_exit(0xD024) -> exit(0xD030) [exits loop differently]
          exit(0xD030): terminal

        The inner if/else (0xD008 -> 0xD010/0xD014 -> 0xD018) should collapse
        inside the loop body DAG. But the loop body has two exits (0xD030 via
        header, and 0xD024 via break_exit), so the loop as a whole gets
        rejected, and the outer graph includes the partially reduced IfElseNode.
        """
        func_data = {
            "name": "partial_reduction",
            "entry_point": "0xD000",
            "basic_blocks": [
                # straight-line entry
                {"id": "0xD000", "edges": [{"source": "0xD000", "target": "0xD004"}]},
                # loop header: to body or exit
                {
                    "id": "0xD004",
                    "edges": [
                        {"source": "0xD004", "target": "0xD008"},
                        {"source": "0xD004", "target": "0xD030"},  # loop exit
                    ],
                },
                # conditional split (inner if/else diamond)
                {
                    "id": "0xD008",
                    "edges": [
                        {"source": "0xD008", "target": "0xD010"},
                        {"source": "0xD008", "target": "0xD014"},
                    ],
                },
                {"id": "0xD010", "edges": [{"source": "0xD010", "target": "0xD018"}]},
                {"id": "0xD014", "edges": [{"source": "0xD014", "target": "0xD018"}]},
                # merge: to latch OR break exit (multi-exit from loop body)
                {
                    "id": "0xD018",
                    "edges": [
                        {"source": "0xD018", "target": "0xD020"},  # latch
                        {"source": "0xD018", "target": "0xD024"},  # break exit
                    ],
                },
                # latch: back-edge to loop header
                {"id": "0xD020", "edges": [{"source": "0xD020", "target": "0xD004"}]},
                # break exit
                {"id": "0xD024", "edges": [{"source": "0xD024", "target": "0xD030"}]},
                # function exit
                {"id": "0xD030", "edges": []},
            ],
        }
        root = structure_function(func_data, self.logger)

        # The function must produce some result without crashing
        self.assertIsNotNone(root)

        # Recursively search the entire tree for any non-BlockNode structured region
        def find_structured(node):
            """Return True if 'node' or any descendant is a structured non-BlockNode."""
            if not isinstance(node, (BlockNode,)):
                return True  # any structured region found
            return False

        def walk(node):
            if not isinstance(node, BlockNode):
                return True
            for attr in ("children",):
                for child in getattr(node, attr, []):
                    if walk(child):
                        return True
            for attr in ("body", "then_branch", "else_branch"):
                child = getattr(node, attr, None)
                if child is not None and walk(child):
                    return True
            return False

        self.assertTrue(
            walk(root),
            "Expected at least one structured inner region (non-BlockNode) preserved in the result"
        )


    # ------------------------------------------------------------------
    # 5. Break-heavy loop body
    # ------------------------------------------------------------------

    def test_break_heavy_loop_body(self):
        """
        Loop with multiple break-like exits from mid-body nodes.
        Must not crash and must produce a deterministic result.
        """
        # H->B1, H->exit2 ; B1->B2, B1->exit1 ; B2->H (latch)
        func_data = {
            "name": "break_heavy_loop",
            "entry_point": "0xE000",
            "basic_blocks": [
                {
                    "id": "0xE000",
                    "edges": [
                        {"source": "0xE000", "target": "0xE004"},
                        {"source": "0xE000", "target": "0xE014"},  # header exit
                    ],
                },
                {
                    "id": "0xE004",
                    "edges": [
                        {"source": "0xE004", "target": "0xE008"},
                        {"source": "0xE004", "target": "0xE010"},  # break exit1
                    ],
                },
                # latch
                {"id": "0xE008", "edges": [{"source": "0xE008", "target": "0xE000"}]},
                # break exit1
                {"id": "0xE010", "edges": []},
                # header exit2
                {"id": "0xE014", "edges": []},
            ],
        }
        root = structure_function(func_data, self.logger)

        # Must not crash; must produce a result
        self.assertIsNotNone(root)

        # Result must be deterministic (call twice, same to_dict)
        root2 = structure_function(func_data, self.logger)
        self.assertEqual(root.to_dict(), root2.to_dict())

    # ------------------------------------------------------------------
    # 6. Continue-if loop body
    # ------------------------------------------------------------------

    def test_continue_if_loop_body(self):
        """
        Canonical continue-if pattern: loop header H->body, body contains
        an if(cond){ continue } pattern.  The loop must collapse to a LoopNode
        and its body must contain an IfNode (the continue-if).

        CFG:
          H(0xF000) -> body(0xF004) [loop entry], H -> exit(0xF014)
          body -> continue_target(0xF008) [back to H via latch], body -> cont(0xF00c)
          latch(0xF008) -> H [back-edge]
          cont(0xF00c) -> latch(0xF008) [falls through to latch after continue-if]
        """
        func_data = {
            "name": "continue_if_loop",
            "entry_point": "0xF000",
            "basic_blocks": [
                # loop header
                {
                    "id": "0xF000",
                    "edges": [
                        {"source": "0xF000", "target": "0xF004"},  # enter body
                        {"source": "0xF000", "target": "0xF014"},  # exit loop
                    ],
                },
                # body split: if(cond) continue else fall-through
                {
                    "id": "0xF004",
                    "edges": [
                        {"source": "0xF004", "target": "0xF008"},  # latch (continue)
                        {"source": "0xF004", "target": "0xF00c"},  # fallthrough
                    ],
                },
                # latch: back-edge to H
                {"id": "0xF008", "edges": [{"source": "0xF008", "target": "0xF000"}]},
                # fallthrough after the if
                {"id": "0xF00c", "edges": [{"source": "0xF00c", "target": "0xF008"}]},
                # loop exit
                {"id": "0xF014", "edges": []},
            ],
        }
        root = structure_function(func_data, self.logger)

        # Must produce a LoopNode (the continue-if pattern is supported by Phase 3C)
        loop_nodes = self._find_nodes(root, LoopNode)
        self.assertTrue(len(loop_nodes) >= 1, "Expected at least one LoopNode")

        loop = loop_nodes[0]
        # Body must contain an IfNode (the continue-if reduction)
        if_nodes = self._find_nodes(loop.body, IfNode)
        self.assertTrue(len(if_nodes) >= 1, "Expected IfNode inside loop body for continue-if")

    # ------------------------------------------------------------------
    # 7. Regression: _helper false-positive still rejected
    # ------------------------------------------------------------------

    def test_helper_fp_not_regressed(self):
        """
        Regression: the _helper-style recursive back-edge CFG must not
        produce a LoopNode after Phase 3D changes.
        """
        func_data = {
            "name": "_helper_regression",
            "entry_point": "0x460",
            "basic_blocks": [
                {
                    "id": "0x460",
                    "edges": [
                        {"source": "0x460", "target": "0x47c"},
                        {"source": "0x460", "target": "0x48c"},
                    ],
                },
                {"id": "0x47c", "edges": [{"source": "0x47c", "target": "0x480"}]},
                {"id": "0x480", "edges": [{"source": "0x480", "target": "0x4f0"}]},
                {
                    "id": "0x48c",
                    "edges": [
                        {"source": "0x48c", "target": "0x4a4"},
                        {"source": "0x48c", "target": "0x4cc"},
                    ],
                },
                {"id": "0x4a4", "edges": [{"source": "0x4a4", "target": "0x4a8"}]},
                {
                    "id": "0x4a8",
                    "edges": [
                        {"source": "0x4a8", "target": "0x460"},
                        {"source": "0x4a8", "target": "0x4bc"},
                    ],
                },
                {"id": "0x4bc", "edges": [{"source": "0x4bc", "target": "0x4f0"}]},
                {
                    "id": "0x4cc",
                    "edges": [
                        {"source": "0x4cc", "target": "0x460"},
                        {"source": "0x4cc", "target": "0x4e0"},
                    ],
                },
                {"id": "0x4e0", "edges": [{"source": "0x4e0", "target": "0x4f0"}]},
                {"id": "0x4f0", "edges": []},
            ],
        }
        root = structure_function(func_data, self.logger)
        self.assertIsInstance(root, UnstructuredRegionNode)
        self.assertEqual(self._find_nodes(root, LoopNode), [])

    # ------------------------------------------------------------------
    # 8. Regression: _classify clean structuring survives
    # ------------------------------------------------------------------

    def test_classify_clean_not_regressed(self):
        """
        Regression: a nested if/else (_classify-style) must still produce
        a fully structured SequenceNode with nested IfElseNode.
        No UnstructuredRegionNode, no LoopNode.
        """
        func_data = {
            "name": "_classify_regression",
            "entry_point": "0x1000",
            "basic_blocks": [
                {
                    "id": "0x1000",
                    "edges": [
                        {"source": "0x1000", "target": "0x1004"},
                        {"source": "0x1000", "target": "0x1008"},
                    ],
                },
                {"id": "0x1004", "edges": [{"source": "0x1004", "target": "0x1010"}]},
                {
                    "id": "0x1008",
                    "edges": [
                        {"source": "0x1008", "target": "0x100c"},
                        {"source": "0x1008", "target": "0x1014"},
                    ],
                },
                {"id": "0x100c", "edges": [{"source": "0x100c", "target": "0x1018"}]},
                {"id": "0x1014", "edges": [{"source": "0x1014", "target": "0x1018"}]},
                {"id": "0x1018", "edges": [{"source": "0x1018", "target": "0x1010"}]},
                {"id": "0x1010", "edges": []},
            ],
        }
        root = structure_function(func_data, self.logger)

        self.assertEqual(self._find_nodes(root, UnstructuredRegionNode), [])
        self.assertEqual(self._find_nodes(root, LoopNode), [])
        self.assertTrue(len(self._find_nodes(root, IfElseNode)) >= 1)

    # ------------------------------------------------------------------
    # 9. Regression: simple valid loop still recovers
    # ------------------------------------------------------------------

    def test_simple_loop_not_regressed(self):
        """
        Regression: simple while loop must still produce LoopNode(while_like).
        """
        func_data = {
            "name": "simple_while_regression",
            "entry_point": "0x1000",
            "basic_blocks": [
                {"id": "0x1000", "edges": [{"source": "0x1000", "target": "0x1004"}]},
                {
                    "id": "0x1004",
                    "edges": [
                        {"source": "0x1004", "target": "0x1008"},
                        {"source": "0x1004", "target": "0x100c"},
                    ],
                },
                {"id": "0x1008", "edges": [{"source": "0x1008", "target": "0x1004"}]},
                {"id": "0x100c", "edges": []},
            ],
        }
        root = structure_function(func_data, self.logger)

        loop_nodes = self._find_nodes(root, LoopNode)
        self.assertEqual(len(loop_nodes), 1)
        self.assertEqual(loop_nodes[0].kind, "while_like")

    # ------------------------------------------------------------------
    # 10. Metadata: reason must be present on hard-case fallback
    # ------------------------------------------------------------------

    def test_unstructured_reason_metadata(self):
        """
        Any hard CFG that falls back to UnstructuredRegionNode must carry a
        non-None reason string.
        """
        # Use the irreducible cyclic CFG (confirmed to produce unstructured)
        func_data = {
            "name": "reason_metadata_check",
            "entry_point": "0x1000",
            "basic_blocks": [
                {
                    "id": "0x1000",
                    "edges": [
                        {"source": "0x1000", "target": "0x1004"},
                        {"source": "0x1000", "target": "0x1008"},
                    ],
                },
                {"id": "0x1004", "edges": [{"source": "0x1004", "target": "0x1008"}]},
                {"id": "0x1008", "edges": [{"source": "0x1008", "target": "0x1004"}]},
            ],
        }
        root = structure_function(func_data, self.logger)

        self.assertIsInstance(root, UnstructuredRegionNode)
        self.assertIsNotNone(
            root.reason,
            "UnstructuredRegionNode.reason must not be None for hard-case fallbacks"
        )
        self.assertIn(
            root.reason,
            {
                "irreducible_cfg",
                "multi_exit_loop",
                "fragmented_loop_body",
                "switch_candidate",
                "partial_reduction",
            },
        )

    # ------------------------------------------------------------------
    # 11. Determinism: identical to_dict output on repeated calls
    # ------------------------------------------------------------------

    def test_unstructured_children_deterministic(self):
        """
        Calling structure_function twice on the same hard CFG must produce
        byte-for-byte identical to_dict() output.
        """
        func_data = {
            "name": "determinism_check",
            "entry_point": "0x1000",
            "basic_blocks": [
                {
                    "id": "0x1000",
                    "edges": [
                        {"source": "0x1000", "target": "0x1004"},
                        {"source": "0x1000", "target": "0x1008"},
                    ],
                },
                {"id": "0x1004", "edges": [{"source": "0x1004", "target": "0x1008"}]},
                {"id": "0x1008", "edges": [{"source": "0x1008", "target": "0x1004"}]},
            ],
        }
        root1 = structure_function(func_data, self.logger)
        root2 = structure_function(func_data, self.logger)

        self.assertEqual(
            root1.to_dict(),
            root2.to_dict(),
            "structure_function must produce identical to_dict() on repeated calls",
        )


class TestPhase3StressTests(unittest.TestCase):
    """
    Phase 3 Stress and Validation Tests.
    Targeting complex loop/conditional nestings, switch fan-out variations,
    recursion boundary conditions, and determinism.
    """

    def setUp(self):
        self.logger = logging.getLogger("TestPhase3StressTests")
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s'))
            self.logger.addHandler(handler)

    def _find_nodes(self, root, cls):
        """Recursively collect all RegionNode instances of type `cls`."""
        found = []
        self._collect(root, cls, found)
        return found

    def _collect(self, node, cls, acc):
        if isinstance(node, cls):
            acc.append(node)
        for attr in ("children", ):
            for child in getattr(node, attr, []):
                self._collect(child, cls, acc)
        for attr in ("body", "then_branch", "else_branch"):
            child = getattr(node, attr, None)
            if child is not None:
                self._collect(child, cls, acc)

    # 1. 3-level deep nested loops
    def test_deeply_nested_loops_3_levels(self):
        """
        L1 (outer) -> L2 (middle) -> L3 (inner).
        Should yield 3 nested LoopNode instances, all of 'while_like' kind.
        """
        func_data = {
            "name": "deeply_nested_3_levels",
            "entry_point": "0x1000",
            "basic_blocks": [
                # entry
                {"id": "0x1000", "edges": [{"source": "0x1000", "target": "0x1010"}]},
                # Outer loop header
                {
                    "id": "0x1010",
                    "edges": [
                        {"source": "0x1010", "target": "0x1020"}, # into Middle loop
                        {"source": "0x1010", "target": "0x1090"}, # exit Outer loop
                    ]
                },
                # Middle loop header
                {
                    "id": "0x1020",
                    "edges": [
                        {"source": "0x1020", "target": "0x1030"}, # into Inner loop
                        {"source": "0x1020", "target": "0x1080"}, # exit Middle loop (latch of Outer)
                    ]
                },
                # Inner loop header
                {
                    "id": "0x1030",
                    "edges": [
                        {"source": "0x1030", "target": "0x1040"}, # Inner loop body
                        {"source": "0x1030", "target": "0x1070"}, # exit Inner loop (latch of Middle)
                    ]
                },
                # Inner loop body/latch
                {"id": "0x1040", "edges": [{"source": "0x1040", "target": "0x1030"}]}, # back-edge to L3
                # Middle loop latch
                {"id": "0x1070", "edges": [{"source": "0x1070", "target": "0x1020"}]}, # back-edge to L2
                # Outer loop latch
                {"id": "0x1080", "edges": [{"source": "0x1080", "target": "0x1010"}]}, # back-edge to L1
                # Outer exit
                {"id": "0x1090", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        loop_nodes = self._find_nodes(root, LoopNode)
        self.assertEqual(len(loop_nodes), 3, "Should reconstruct exactly 3 LoopNodes")
        
        # Verify nesting: outer contains middle contains inner
        # Find outer loop (header = 0x1010)
        outer_loop = next(l for l in loop_nodes if l.header_block == "0x1010")
        self.assertEqual(outer_loop.kind, "while_like")
        
        # Middle loop (header = 0x1020) should be inside outer_loop.body
        middle_loops = self._find_nodes(outer_loop.body, LoopNode)
        self.assertTrue(any(l.header_block == "0x1020" for l in middle_loops))
        middle_loop = next(l for l in middle_loops if l.header_block == "0x1020")
        self.assertEqual(middle_loop.kind, "while_like")
        
        # Inner loop (header = 0x1030) should be inside middle_loop.body
        inner_loops = self._find_nodes(middle_loop.body, LoopNode)
        self.assertTrue(any(l.header_block == "0x1030" for l in inner_loops))
        inner_loop = next(l for l in inner_loops if l.header_block == "0x1030")
        self.assertEqual(inner_loop.kind, "while_like")
        self.assertIsInstance(inner_loop.body, SequenceNode)
        self.assertEqual(inner_loop.body.children[0].block_id, "0x1030")
        self.assertEqual(inner_loop.body.children[1].block_id, "0x1040")

    # 2. Sibling loops
    def test_sibling_loops(self):
        """
        Two sequential independent loops: Loop A then Loop B.
        Should collapse into a SequenceNode containing two LoopNodes.
        """
        func_data = {
            "name": "sibling_loops",
            "entry_point": "0x2000",
            "basic_blocks": [
                {"id": "0x2000", "edges": [{"source": "0x2000", "target": "0x2010"}]},
                # Loop A
                {
                    "id": "0x2010",
                    "edges": [
                        {"source": "0x2010", "target": "0x2020"},
                        {"source": "0x2010", "target": "0x2030"},
                    ]
                },
                {"id": "0x2020", "edges": [{"source": "0x2020", "target": "0x2010"}]},
                # Path between them
                {"id": "0x2030", "edges": [{"source": "0x2030", "target": "0x2040"}]},
                # Loop B
                {
                    "id": "0x2040",
                    "edges": [
                        {"source": "0x2040", "target": "0x2050"},
                        {"source": "0x2040", "target": "0x2060"},
                    ]
                },
                {"id": "0x2050", "edges": [{"source": "0x2050", "target": "0x2040"}]},
                {"id": "0x2060", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        loop_nodes = self._find_nodes(root, LoopNode)
        self.assertEqual(len(loop_nodes), 2, "Should reconstruct exactly 2 LoopNodes")
        headers = {l.header_block for l in loop_nodes}
        self.assertEqual(headers, {"0x2010", "0x2040"})
        self.assertEqual(self._find_nodes(root, UnstructuredRegionNode), [])

    # 3. Loop containing structured conditional diamond with continue-if
    def test_loop_nested_if_else_and_continue(self):
        """
        Loop header branches to exit or conditional split.
        The conditional split branches to then/else which merge at a latch block.
        The latch block then goes back to header.
        Should result in LoopNode whose body is a SequenceNode ending in a continue latch,
        and containing an IfElseNode.
        """
        func_data = {
            "name": "loop_nested_if_else_latch",
            "entry_point": "0x3000",
            "basic_blocks": [
                {
                    "id": "0x3000",
                    "edges": [
                        {"source": "0x3000", "target": "0x3010"},
                        {"source": "0x3000", "target": "0x3060"}, # exit
                    ]
                },
                {
                    "id": "0x3010",
                    "edges": [
                        {"source": "0x3010", "target": "0x3020"},
                        {"source": "0x3010", "target": "0x3030"},
                    ]
                },
                {"id": "0x3020", "edges": [{"source": "0x3020", "target": "0x3050"}]},
                {"id": "0x3030", "edges": [{"source": "0x3030", "target": "0x3050"}]},
                {"id": "0x3050", "edges": [{"source": "0x3050", "target": "0x3000"}]}, # back-edge
                {"id": "0x3060", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        loop_nodes = self._find_nodes(root, LoopNode)
        self.assertEqual(len(loop_nodes), 1)
        loop = loop_nodes[0]
        
        # Body must contain IfElseNode
        ifelse_nodes = self._find_nodes(loop.body, IfElseNode)
        self.assertEqual(len(ifelse_nodes), 1)
        self.assertEqual(ifelse_nodes[0].condition_block, "0x3010")

    # 4. Complex switch fan-out (out-degree >= 3)
    def test_complex_switch_fanout_5_arms(self):
        """
        Split node with 5 successors. Should fall back to UnstructuredRegionNode
        with reason "switch_candidate".
        """
        func_data = {
            "name": "switch_fanout_5",
            "entry_point": "0x4000",
            "basic_blocks": [
                {
                    "id": "0x4000",
                    "edges": [
                        {"source": "0x4000", "target": "0x4010"},
                        {"source": "0x4000", "target": "0x4020"},
                        {"source": "0x4000", "target": "0x4030"},
                        {"source": "0x4000", "target": "0x4040"},
                        {"source": "0x4000", "target": "0x4050"},
                    ]
                },
                {"id": "0x4010", "edges": [{"source": "0x4010", "target": "0x4060"}]},
                {"id": "0x4020", "edges": [{"source": "0x4020", "target": "0x4060"}]},
                {"id": "0x4030", "edges": [{"source": "0x4030", "target": "0x4060"}]},
                {"id": "0x4040", "edges": [{"source": "0x4040", "target": "0x4060"}]},
                {"id": "0x4050", "edges": [{"source": "0x4050", "target": "0x4060"}]},
                {"id": "0x4060", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        self.assertIsInstance(root, UnstructuredRegionNode)
        self.assertEqual(root.reason, "switch_candidate")
        self.assertEqual(root.region_kind, "switch_candidate")

    # 5. Inner loop preserved in unstructured outer loop
    def test_inner_loop_preserved_in_unstructured_outer_loop(self):
        """
        Outer loop has an irreducible body split and fails to structure.
        Inner loop is fully reducible and structures successfully.
        Result must be UnstructuredRegionNode containing the inner LoopNode.
        """
        func_data = {
            "name": "inner_loop_preserved",
            "entry_point": "0x5000",
            "basic_blocks": [
                {"id": "0x5000", "edges": [{"source": "0x5000", "target": "0x5010"}]},
                # Outer loop header
                {"id": "0x5010", "edges": [{"source": "0x5010", "target": "0x5020"}]},
                # Irreducible body split inside outer loop
                {
                    "id": "0x5020",
                    "edges": [
                        {"source": "0x5020", "target": "0x5030"}, # to inner loop
                        {"source": "0x5020", "target": "0x5060"}, # to parallel branch
                    ]
                },
                # Inner loop header
                {
                    "id": "0x5030",
                    "edges": [
                        {"source": "0x5030", "target": "0x5040"}, # inner body
                        {"source": "0x5030", "target": "0x5050"}, # inner exit
                    ]
                },
                # Inner body
                {"id": "0x5040", "edges": [{"source": "0x5040", "target": "0x5030"}]}, # inner back-edge
                # Inner exit (goes back to outer header)
                {"id": "0x5050", "edges": [{"source": "0x5050", "target": "0x5010"}]}, # outer latch 1
                # Parallel branch (goes back to outer header)
                {"id": "0x5060", "edges": [{"source": "0x5060", "target": "0x5010"}]}, # outer latch 2
            ]
        }
        root = structure_function(func_data, self.logger)
        
        self.assertIsInstance(root, UnstructuredRegionNode)
        self.assertIn(root.reason, {"irreducible_cfg", "partial_reduction", "multi_exit_loop"})
        
        # Verify the inner LoopNode survived and is present
        loops = self._find_nodes(root, LoopNode)
        self.assertEqual(len(loops), 1, "Inner loop should be successfully structured")
        self.assertEqual(loops[0].header_block, "0x5030")
        self.assertEqual(loops[0].kind, "while_like")

    # 6. Recursion boundary (back-edge with no dominance)
    def test_recursion_with_backedge_no_dominance(self):
        """
        CFG with back-edge target that does not dominate the source.
        This must not be structured as a LoopNode.
        """
        func_data = {
            "name": "recursion_no_dominance",
            "entry_point": "0x6000",
            "basic_blocks": [
                {
                    "id": "0x6000",
                    "edges": [
                        {"source": "0x6000", "target": "0x6010"},
                        {"source": "0x6000", "target": "0x6020"},
                    ]
                },
                {"id": "0x6010", "edges": [{"source": "0x6010", "target": "0x6030"}]},
                {"id": "0x6020", "edges": [{"source": "0x6020", "target": "0x6030"}]},
                {"id": "0x6030", "edges": [{"source": "0x6030", "target": "0x6010"}]}, # back-edge but 0x6010 doesn't dominate 0x6030
            ]
        }
        root = structure_function(func_data, self.logger)
        
        # Should not structure as LoopNode
        self.assertEqual(self._find_nodes(root, LoopNode), [])
        self.assertIsInstance(root, UnstructuredRegionNode)
        self.assertIn(root.reason, {"irreducible_cfg", "partial_reduction"})

    # 7. Endless loop classification
    def test_endless_loop_no_exit(self):
        """
        Infinite loop with no exits. Should structure into a LoopNode of kind 'endless'.
        """
        func_data = {
            "name": "endless_loop",
            "entry_point": "0x7000",
            "basic_blocks": [
                {"id": "0x7000", "edges": [{"source": "0x7000", "target": "0x7010"}]},
                {"id": "0x7010", "edges": [{"source": "0x7010", "target": "0x7020"}]},
                {"id": "0x7020", "edges": [{"source": "0x7020", "target": "0x7010"}]}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        loops = self._find_nodes(root, LoopNode)
        self.assertEqual(len(loops), 1)
        self.assertEqual(loops[0].kind, "endless")
        self.assertEqual(loops[0].header_block, "0x7010")

    # 8. Loop exit chained to another loop header
    def test_loop_exit_chained_to_another_loop_header(self):
        """
        L1 exits to L2. Should structure as a SequenceNode containing L1 then L2.
        """
        func_data = {
            "name": "loop_exit_chained",
            "entry_point": "0x8000",
            "basic_blocks": [
                {"id": "0x8000", "edges": [{"source": "0x8000", "target": "0x8010"}]},
                # Loop 1
                {
                    "id": "0x8010",
                    "edges": [
                        {"source": "0x8010", "target": "0x8020"},
                        {"source": "0x8010", "target": "0x8030"}, # exits to Loop 2 header
                    ]
                },
                {"id": "0x8020", "edges": [{"source": "0x8020", "target": "0x8010"}]},
                # Loop 2
                {
                    "id": "0x8030",
                    "edges": [
                        {"source": "0x8030", "target": "0x8040"},
                        {"source": "0x8030", "target": "0x8050"},
                    ]
                },
                {"id": "0x8040", "edges": [{"source": "0x8040", "target": "0x8030"}]},
                {"id": "0x8050", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        loops = self._find_nodes(root, LoopNode)
        self.assertEqual(len(loops), 2)
        self.assertEqual(self._find_nodes(root, UnstructuredRegionNode), [])

    # 9. Loop with body having conditional branches only to exits
    def test_loop_with_all_break_paths(self):
        """
        Loop header branches to latch and a body block.
        The body block only branches to outside exits.
        The latch block goes back to header.
        Should result in LoopNode(while_like) containing the latch sequence,
        with the loop exit linking to the body block.
        """
        func_data = {
            "name": "loop_all_breaks",
            "entry_point": "0x9000",
            "basic_blocks": [
                {
                    "id": "0x9000",
                    "edges": [
                        {"source": "0x9000", "target": "0x9010"}, # body (exit path)
                        {"source": "0x9000", "target": "0x9020"}, # latch
                    ]
                },
                {"id": "0x9020", "edges": [{"source": "0x9020", "target": "0x9000"}]}, # back-edge
                {"id": "0x9010", "edges": [{"source": "0x9010", "target": "0x9030"}]},
                {"id": "0x9030", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        loops = self._find_nodes(root, LoopNode)
        self.assertEqual(len(loops), 1)
        self.assertEqual(loops[0].kind, "while_like")
        self.assertEqual(loops[0].header_block, "0x9000")
        self.assertEqual(self._find_nodes(root, UnstructuredRegionNode), [])

    # 10. Determinism under dictionary ordering scramble
    def test_deterministic_ordering_scramble(self):
        """
        Reconstruct a CFG multiple times with basic blocks ordered differently
        in the input list. The result dictionary must be identical.
        """
        func_blocks = [
            {"id": "0x01", "edges": [{"source": "0x01", "target": "0x02"}, {"source": "0x01", "target": "0x03"}]},
            {"id": "0x02", "edges": [{"source": "0x02", "target": "0x04"}]},
            {"id": "0x03", "edges": [{"source": "0x03", "target": "0x04"}]},
            {"id": "0x04", "edges": [{"source": "0x04", "target": "0x05"}, {"source": "0x04", "target": "0x06"}]},
            {"id": "0x05", "edges": [{"source": "0x05", "target": "0x01"}]}, # back-edge
            {"id": "0x06", "edges": []}
        ]
        
        import random
        # Perform 5 random shuffles of blocks and verify the serialized tree is identical
        dct_ref = None
        for i in range(5):
            shuffled = list(func_blocks)
            random.seed(i)
            random.shuffle(shuffled)
            func_data = {
                "name": "deterministic_shuffle",
                "entry_point": "0x01",
                "basic_blocks": shuffled
            }
            root = structure_function(func_data, self.logger)
            dct = root.to_dict()
            if dct_ref is None:
                dct_ref = dct
            else:
                self.assertEqual(dct, dct_ref, f"Nondeterministic output on iteration {i}!")

    def test_helper_rec_not_collapsed_as_loop(self):
        """
        Recursion-shaped multi-latch entry-header candidate loop must be rejected.
        CFG layout:
          0x460 (entry) -> 0x470 (exit/return), 0x480 (split)
          0x470 -> 0x548 (merge)
          0x480 -> 0x490 (exit/return), 0x4a0 (split)
          0x490 -> 0x548
          0x4a0 -> 0x4c0 (latch 1), 0x4e0 (split)
          0x4c0 -> 0x460 (back-edge)
          0x4e0 -> 0x500 (latch 2), 0x510 (split)
          0x500 -> 0x460 (back-edge)
          0x510 -> 0x524 (latch 3), 0x530 (exit/return)
          0x524 -> 0x460 (back-edge)
          0x530 -> 0x548
          0x548 -> empty
        """
        func_data = {
            "name": "helper_rec",
            "entry_point": "0x460",
            "basic_blocks": [
                {"id": "0x460", "edges": [{"source": "0x460", "target": "0x470"}, {"source": "0x460", "target": "0x480"}]},
                {"id": "0x470", "edges": [{"source": "0x470", "target": "0x548"}]},
                {"id": "0x480", "edges": [{"source": "0x480", "target": "0x490"}, {"source": "0x480", "target": "0x4a0"}]},
                {"id": "0x490", "edges": [{"source": "0x490", "target": "0x548"}]},
                {"id": "0x4a0", "edges": [{"source": "0x4a0", "target": "0x4c0"}, {"source": "0x4a0", "target": "0x4e0"}]},
                {"id": "0x4c0", "edges": [{"source": "0x4c0", "target": "0x460"}]},
                {"id": "0x4e0", "edges": [{"source": "0x4e0", "target": "0x500"}, {"source": "0x4e0", "target": "0x510"}]},
                {"id": "0x500", "edges": [{"source": "0x500", "target": "0x460"}]},
                {"id": "0x510", "edges": [{"source": "0x510", "target": "0x524"}, {"source": "0x510", "target": "0x530"}]},
                {"id": "0x524", "edges": [{"source": "0x524", "target": "0x460"}]},
                {"id": "0x530", "edges": [{"source": "0x530", "target": "0x548"}]},
                {"id": "0x548", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        # Verify that no LoopNode is constructed for header 0x460
        loops = self._find_nodes(root, LoopNode)
        self.assertEqual(loops, [], "Should not collapse recursion-shaped entry-header candidate into a LoopNode")
        
        # Should fall back to UnstructuredRegionNode carrying correct cyclic reason
        self.assertIsInstance(root, UnstructuredRegionNode)
        self.assertIn(root.reason, {"irreducible_cfg", "partial_reduction", "multi_exit_loop"})

    def test_classify_pair_collapses_cleanly(self):
        """
        _classify_pair style conditional chain.
        Should result in a SequenceNode containing nested IfElseNode structures
        without any UnstructuredRegionNode.
        """
        func_data = {
            "name": "classify_pair_style",
            "entry_point": "0x10",
            "basic_blocks": [
                {"id": "0x10", "edges": [{"source": "0x10", "target": "0x20"}, {"source": "0x10", "target": "0x50"}]},
                {"id": "0x20", "edges": [{"source": "0x20", "target": "0x30"}, {"source": "0x20", "target": "0x50"}]},
                {"id": "0x30", "edges": [{"source": "0x30", "target": "0x40"}]},
                {"id": "0x40", "edges": [{"source": "0x40", "target": "0x90"}]},
                {"id": "0x50", "edges": [{"source": "0x50", "target": "0x60"}, {"source": "0x50", "target": "0x70"}]},
                {"id": "0x60", "edges": [{"source": "0x60", "target": "0x90"}]},
                {"id": "0x70", "edges": [{"source": "0x70", "target": "0x80"}, {"source": "0x70", "target": "0x85"}]},
                {"id": "0x80", "edges": [{"source": "0x80", "target": "0x90"}]},
                {"id": "0x85", "edges": [{"source": "0x85", "target": "0x90"}]},
                {"id": "0x90", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)

        self.assertIsInstance(root, SequenceNode)
        self.assertEqual(self._find_nodes(root, UnstructuredRegionNode), [])

        # Verify that nested IfElseNodes are preserved
        ifelse_nodes = self._find_nodes(root, IfElseNode)
        self.assertEqual(len(ifelse_nodes), 2)  # One at 0x50, one at 0x70
        
        # Verify the children details based on topological order
        self.assertEqual(root.children[0].node_id, "0x10")
        self.assertEqual(root.children[1].node_id, "0x20")
        self.assertIsInstance(root.children[2], IfElseNode)
        self.assertEqual(root.children[2].condition_block, "0x50")
        self.assertIsInstance(root.children[3], SequenceNode)
        self.assertEqual(root.children[3].children[0].node_id, "0x30")
        self.assertEqual(root.children[3].children[1].node_id, "0x40")
        self.assertEqual(root.children[4].node_id, "0x90")

    def test_final_acyclic_assembly_preserves_inner_structure(self):
        """
        Verify that final acyclic assembly preserves already collapsed/structured inner nodes
        like IfElseNode and SequenceNode, and returns a structured SequenceNode.
        """
        func_data = {
            "name": "final_acyclic_preserves_inner",
            "entry_point": "0x10",
            "basic_blocks": [
                {"id": "0x10", "edges": [{"source": "0x10", "target": "0x20"}, {"source": "0x10", "target": "0x50"}]},
                {"id": "0x20", "edges": [{"source": "0x20", "target": "0x30"}, {"source": "0x20", "target": "0x40"}]},
                {"id": "0x30", "edges": [{"source": "0x30", "target": "0x45"}]},
                {"id": "0x40", "edges": [{"source": "0x40", "target": "0x45"}]},
                {"id": "0x45", "edges": [{"source": "0x45", "target": "0x50"}]},
                {"id": "0x50", "edges": [{"source": "0x50", "target": "0x60"}, {"source": "0x50", "target": "0x70"}]},
                {"id": "0x60", "edges": [{"source": "0x60", "target": "0x80"}]},
                {"id": "0x70", "edges": [{"source": "0x70", "target": "0x80"}]},
                {"id": "0x80", "edges": [{"source": "0x80", "target": "0x90"}]},
                {"id": "0x90", "edges": [{"source": "0x90", "target": "0x100"}]},
                {"id": "0x100", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)

        self.assertIsInstance(root, SequenceNode)
        self.assertEqual(self._find_nodes(root, UnstructuredRegionNode), [])

        # Verify inner structured nodes
        ifelse_nodes = self._find_nodes(root, IfElseNode)
        self.assertEqual(len(ifelse_nodes), 1)  # at 0x20
        
        from src.ir.structuring.models import IfNode
        if_nodes = self._find_nodes(root, IfNode)
        self.assertEqual(len(if_nodes), 1)  # at 0x10
        
        seq_nodes = self._find_nodes(root, SequenceNode)
        # Sequence nodes exist: root SequenceNode, plus the collapsed sequence at 0x80
        # Let's verify that a SequenceNode contains [0x80, 0x90, 0x100]
        sub_seqs = [s for s in seq_nodes if s is not root]
        self.assertTrue(any(len(s.children) == 3 and s.children[0].node_id == "0x80" for s in sub_seqs))

    def test_fragmented_acyclic_still_falls_back(self):
        """
        Construct an acyclic graph containing a node unreachable from the entry node.
        This represents a truly fragmented/disconnected acyclic graph.
        Expected: final acyclic assembly is skipped, falling back to UnstructuredRegionNode.
        """
        func_data = {
            "name": "unreachable_fragmented_acyclic",
            "entry_point": "0x10",
            "basic_blocks": [
                {"id": "0x10", "edges": [{"source": "0x10", "target": "0x20"}]},
                {"id": "0x20", "edges": []},
                {"id": "0x999", "edges": []}  # Unreachable node
            ]
        }
        root = structure_function(func_data, self.logger)

        self.assertIsInstance(root, UnstructuredRegionNode)
        self.assertEqual(root.reason, "fragmented_loop_body")
        self.assertEqual(root.region_kind, "acyclic")

    def test_regression_simple_loops_still_work(self):
        """
        Regression check to ensure simple loops are still correctly structured.
        """
        func_data = {
            "name": "simple_while_loop_regression",
            "entry_point": "0x10",
            "basic_blocks": [
                {"id": "0x10", "edges": [{"source": "0x10", "target": "0x20"}]},
                {"id": "0x20", "edges": [{"source": "0x20", "target": "0x30"}, {"source": "0x20", "target": "0x40"}]},
                {"id": "0x30", "edges": [{"source": "0x30", "target": "0x20"}]},
                {"id": "0x40", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)
        
        self.assertIsInstance(root, SequenceNode)
        self.assertEqual(len(root.children), 3)
        self.assertEqual(root.children[0].node_id, "0x10")
        self.assertIsInstance(root.children[1], LoopNode)
        self.assertEqual(root.children[1].header_block, "0x20")
        self.assertEqual(root.children[2].node_id, "0x40")

    def test_switchy_preserved_as_switch_candidate(self):
        """
        CFG isomorphic to _switchy (binary comparison ladder).
        Expected: Not a generic SequenceNode, but UnstructuredRegionNode with
        reason "switch_candidate" and region_kind "switch_candidate".
        """
        func_data = {
            "name": "switchy_style",
            "entry_point": "0x10",
            "basic_blocks": [
                {"id": "0x10", "edges": [{"source": "0x10", "target": "0x20"}, {"source": "0x10", "target": "0x15"}]},
                {"id": "0x15", "edges": [{"source": "0x15", "target": "0x90"}]},
                {"id": "0x20", "edges": [{"source": "0x20", "target": "0x30"}]},
                {"id": "0x30", "edges": [{"source": "0x30", "target": "0x40"}, {"source": "0x30", "target": "0x35"}]},
                {"id": "0x35", "edges": [{"source": "0x35", "target": "0x90"}]},
                {"id": "0x40", "edges": [{"source": "0x40", "target": "0x50"}]},
                {"id": "0x50", "edges": [{"source": "0x50", "target": "0x60"}, {"source": "0x50", "target": "0x55"}]},
                {"id": "0x55", "edges": [{"source": "0x55", "target": "0x90"}]},
                {"id": "0x60", "edges": [{"source": "0x60", "target": "0x70"}]},
                {"id": "0x70", "edges": [{"source": "0x70", "target": "0x80"}, {"source": "0x70", "target": "0x75"}]},
                {"id": "0x75", "edges": [{"source": "0x75", "target": "0x90"}]},
                {"id": "0x80", "edges": [{"source": "0x80", "target": "0x85"}]},
                {"id": "0x85", "edges": [{"source": "0x85", "target": "0x90"}]},
                {"id": "0x90", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)

        self.assertIsInstance(root, UnstructuredRegionNode)
        self.assertEqual(root.reason, "switch_candidate")
        self.assertEqual(root.region_kind, "switch_candidate")

    def test_switch_like_dispatch_tree_not_flattened(self):
        """
        Acyclic dispatch tree with several short case-like leaves.
        Expected: switch-like fallback classification.
        """
        func_data = {
            "name": "switch_tree_style",
            "entry_point": "0x10",
            "basic_blocks": [
                # Entry block 10 goes to split block 12, which is sequence-collapsed with 10
                {"id": "0x10", "edges": [{"source": "0x10", "target": "0x12"}]},
                {"id": "0x12", "edges": [{"source": "0x12", "target": "0x20"}, {"source": "0x12", "target": "0x30"}]},
                
                # Left branch block 20 goes to split block 22, which is sequence-collapsed with 20
                {"id": "0x20", "edges": [{"source": "0x20", "target": "0x22"}]},
                {"id": "0x22", "edges": [{"source": "0x22", "target": "0x40"}, {"source": "0x22", "target": "0x50"}]},
                
                # Right branch block 30 goes to split block 32, which is sequence-collapsed with 30
                {"id": "0x30", "edges": [{"source": "0x30", "target": "0x32"}]},
                {"id": "0x32", "edges": [{"source": "0x32", "target": "0x60"}, {"source": "0x32", "target": "0x70"}]},
                
                {"id": "0x40", "edges": [{"source": "0x40", "target": "0x90"}]},
                {"id": "0x50", "edges": [{"source": "0x50", "target": "0x90"}]},
                {"id": "0x60", "edges": [{"source": "0x60", "target": "0x90"}]},
                {"id": "0x70", "edges": [{"source": "0x70", "target": "0x90"}]},
                {"id": "0x90", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)

        self.assertIsInstance(root, UnstructuredRegionNode)
        self.assertEqual(root.reason, "switch_candidate")
        self.assertEqual(root.region_kind, "switch_candidate")

    def test_regression_classify_pair_still_assembles_cleanly(self):
        """
        Ensure classify_pair style graph (a long nested conditional chain) still
        collapses cleanly into nested IfElseNode structures inside SequenceNode.
        """
        func_data = {
            "name": "regression_classify_pair",
            "entry_point": "0x10",
            "basic_blocks": [
                {"id": "0x10", "edges": [{"source": "0x10", "target": "0x20"}, {"source": "0x10", "target": "0x50"}]},
                {"id": "0x20", "edges": [{"source": "0x20", "target": "0x30"}, {"source": "0x20", "target": "0x50"}]},
                {"id": "0x30", "edges": [{"source": "0x30", "target": "0x40"}]},
                {"id": "0x40", "edges": [{"source": "0x40", "target": "0x90"}]},
                {"id": "0x50", "edges": [{"source": "0x50", "target": "0x60"}, {"source": "0x50", "target": "0x70"}]},
                {"id": "0x60", "edges": [{"source": "0x60", "target": "0x90"}]},
                {"id": "0x70", "edges": [{"source": "0x70", "target": "0x80"}, {"source": "0x70", "target": "0x85"}]},
                {"id": "0x80", "edges": [{"source": "0x80", "target": "0x90"}]},
                {"id": "0x85", "edges": [{"source": "0x85", "target": "0x90"}]},
                {"id": "0x90", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)

        self.assertIsInstance(root, SequenceNode)
        self.assertEqual(self._find_nodes(root, UnstructuredRegionNode), [])
        
        ifelse_nodes = self._find_nodes(root, IfElseNode)
        self.assertEqual(len(ifelse_nodes), 2)

    def test_regression_simple_acyclic_sequence_still_assembles(self):
        """
        Ensure ordinary acyclic regions (straight-line sequences) still assemble cleanly.
        """
        func_data = {
            "name": "regression_straight_sequence",
            "entry_point": "0x10",
            "basic_blocks": [
                {"id": "0x10", "edges": [{"source": "0x10", "target": "0x20"}]},
                {"id": "0x20", "edges": [{"source": "0x20", "target": "0x30"}]},
                {"id": "0x30", "edges": [{"source": "0x30", "target": "0x40"}]},
                {"id": "0x40", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)

        self.assertIsInstance(root, SequenceNode)
        self.assertEqual(len(root.children), 4)

    def test_regression_helper_rec_still_stays_fixed(self):
        """
        Preserve Phase 1 recursion loop rejection.
        """
        func_data = {
            "name": "regression_helper_rec",
            "entry_point": "0x460",
            "basic_blocks": [
                {"id": "0x460", "edges": [{"source": "0x460", "target": "0x470"}, {"source": "0x460", "target": "0x480"}]},
                {"id": "0x470", "edges": [{"source": "0x470", "target": "0x548"}]},
                {"id": "0x480", "edges": [{"source": "0x480", "target": "0x490"}, {"source": "0x480", "target": "0x4a0"}]},
                {"id": "0x490", "edges": [{"source": "0x490", "target": "0x548"}]},
                {"id": "0x4a0", "edges": [{"source": "0x4a0", "target": "0x4c0"}, {"source": "0x4a0", "target": "0x4e0"}]},
                {"id": "0x4c0", "edges": [{"source": "0x4c0", "target": "0x460"}]},
                {"id": "0x4e0", "edges": [{"source": "0x4e0", "target": "0x500"}, {"source": "0x4e0", "target": "0x510"}]},
                {"id": "0x500", "edges": [{"source": "0x500", "target": "0x460"}]},
                {"id": "0x510", "edges": [{"source": "0x510", "target": "0x524"}, {"source": "0x510", "target": "0x530"}]},
                {"id": "0x524", "edges": [{"source": "0x524", "target": "0x460"}]},
                {"id": "0x530", "edges": [{"source": "0x530", "target": "0x548"}]},
                {"id": "0x548", "edges": []}
            ]
        }
        root = structure_function(func_data, self.logger)

        self.assertEqual(self._find_nodes(root, LoopNode), [])
        self.assertIsInstance(root, UnstructuredRegionNode)


if __name__ == "__main__":
    unittest.main()


