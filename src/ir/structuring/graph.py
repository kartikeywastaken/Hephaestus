# -*- coding: utf-8 -*-
"""
Phase 3A: CFG Graph Representation & Normalization
"""

from typing import Dict, Any, List, Set, Optional
from src.ir.assembler import normalize_addr

class CFG:
    """
    Representation of a function's Control Flow Graph normalized for analysis.
    """
    def __init__(self, function_data: Dict[str, Any]):
        self.entry_node: str = normalize_addr(function_data.get("entry_point", ""))
        self.nodes: Set[str] = set()
        self.successors: Dict[str, List[str]] = {}
        self.predecessors: Dict[str, List[str]] = {}
        self.exit_nodes: Set[str] = set()
        self.basic_blocks: Dict[str, Dict[str, Any]] = {}

        self._build_cfg(function_data)

    def _build_cfg(self, function_data: Dict[str, Any]):
        bbs = function_data.get("basic_blocks", [])
        
        # 1. Normalize all nodes
        for bb in bbs:
            bb_id = normalize_addr(bb.get("id"))
            if bb_id:
                self.nodes.add(bb_id)
                self.basic_blocks[bb_id] = bb
                self.successors[bb_id] = []
                self.predecessors[bb_id] = []

        # Ensure entry node is in nodes
        if self.entry_node and self.entry_node not in self.nodes:
            self.nodes.add(self.entry_node)
            self.successors[self.entry_node] = []
            self.predecessors[self.entry_node] = []

        # 2. Normalize and trace edges
        for bb in bbs:
            bb_id = normalize_addr(bb.get("id"))
            if not bb_id:
                continue
            
            # Edges are nested inside basic_blocks
            edges = bb.get("edges", [])
            for edge in edges:
                src = normalize_addr(edge.get("source"))
                dst = normalize_addr(edge.get("target"))
                
                if src and dst:
                    self.nodes.add(src)
                    self.nodes.add(dst)
                    
                    self.successors.setdefault(src, [])
                    self.predecessors.setdefault(dst, [])
                    
                    if dst not in self.successors[src]:
                        self.successors[src].append(dst)
                    if src not in self.predecessors[dst]:
                        self.predecessors[dst].append(src)

        # 3. Identify exit nodes (nodes with 0 successors)
        for node in self.nodes:
            if not self.successors.get(node):
                self.exit_nodes.add(node)
