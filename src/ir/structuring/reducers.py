# -*- coding: utf-8 -*-
"""
Phase 3B: Region Reduction Engine
"""

import logging
from typing import Dict, List, Set, Optional
from src.ir.structuring.models import RegionNode, BlockNode, SequenceNode

class ReductionGraph:
    """
    Graph representation operating on structured RegionNode vertices.
    """
    def __init__(self, entry_node_id: str, nodes: Dict[str, RegionNode], successors: Dict[str, List[str]], predecessors: Dict[str, List[str]]):
        self.entry_node_id = entry_node_id
        self.nodes = nodes
        self.successors = {k: list(v) for k, v in successors.items()}
        self.predecessors = {k: list(v) for k, v in predecessors.items()}

    def replace_nodes(self, old_node_ids: List[str], new_node: RegionNode, new_successors: List[str], new_predecessors: List[str]):
        new_id = new_node.node_id
        
        # 1. Update predecessor connections of successors of the collapsed region
        for old_id in old_node_ids:
            for s in self.successors.get(old_id, []):
                if s not in old_node_ids:
                    preds = self.predecessors.get(s, [])
                    # Replace old_id with new_id in predecessor list
                    new_preds = []
                    for p in preds:
                        if p in old_node_ids:
                            if new_id not in new_preds:
                                new_preds.append(new_id)
                        else:
                            new_preds.append(p)
                    self.predecessors[s] = new_preds

        # 2. Update successor connections of predecessors of the collapsed region
        for old_id in old_node_ids:
            for p in self.predecessors.get(old_id, []):
                if p not in old_node_ids:
                    succs = self.successors.get(p, [])
                    # Replace old_id with new_id in successor list
                    new_succs = []
                    for s in succs:
                        if s in old_node_ids:
                            if new_id not in new_succs:
                                new_succs.append(new_id)
                        else:
                            new_succs.append(s)
                    self.successors[p] = new_succs

        # 3. Remove old nodes
        for old_id in old_node_ids:
            self.nodes.pop(old_id, None)
            self.successors.pop(old_id, None)
            self.predecessors.pop(old_id, None)

        # 4. Insert new node
        self.nodes[new_id] = new_node
        self.successors[new_id] = list(new_successors)
        self.predecessors[new_id] = list(new_predecessors)

        # 5. Update entry node if it was collapsed
        if self.entry_node_id in old_node_ids:
            self.entry_node_id = new_id

def run_sequence_reductions(graph: ReductionGraph, logger: logging.Logger) -> bool:
    """
    Finds and collapses all eligible sequence edges in the graph to fixpoint.
    """
    collapsed_any = False
    while True:
        candidate = None
        # Sort nodes deterministically
        for u_id in sorted(graph.nodes.keys()):
            succs = graph.successors.get(u_id, [])
            if len(succs) == 1:
                v_id = succs[0]
                preds = graph.predecessors.get(v_id, [])
                if len(preds) == 1 and preds[0] == u_id and v_id != graph.entry_node_id:
                    # u_id -> v_id sequence candidate found
                    candidate = (u_id, v_id)
                    break
        
        if not candidate:
            break
            
        u_id, v_id = candidate
        u_node = graph.nodes[u_id]
        v_node = graph.nodes[v_id]
        
        children = []
        if isinstance(u_node, SequenceNode):
            children.extend(u_node.children)
        else:
            children.append(u_node)
            
        # Do not flatten v_node to preserve already structured subregions
        children.append(v_node)
            
        new_node = SequenceNode(children)
        new_succs = list(graph.successors.get(v_id, []))
        new_preds = list(graph.predecessors.get(u_id, []))
        
        graph.replace_nodes([u_id, v_id], new_node, new_succs, new_preds)
        
        # Log sequence reduction
        collapsed_ids = [c.node_id for c in children]
        logger.debug(f"Collapsed sequence region: {collapsed_ids}")
        collapsed_any = True
        
    return collapsed_any
