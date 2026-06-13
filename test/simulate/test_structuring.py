# -*- coding: utf-8 -*-
"""
Phase 3A: CFG Structuring & Control Flow Analysis Unit Tests
"""

import unittest
import logging
from src.ir.structuring.analysis import analyze_function

class TestCFGStructuringAnalysis(unittest.TestCase):

    def setUp(self):
        self.logger = logging.getLogger("TestCFGStructuringAnalysis")
        self.logger.setLevel(logging.DEBUG)
        # Ensure we have a stream handler to print logs if tests fail
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

if __name__ == "__main__":
    unittest.main()
