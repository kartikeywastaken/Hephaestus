# -*- coding: utf-8 -*-
"""
Phase 3B: Conditional Region Detection
"""

import logging
from typing import Dict, List, Set, Optional, Tuple
from src.ir.structuring.models import RegionNode, IfNode, IfElseNode, SequenceNode
from src.ir.structuring.reducers import ReductionGraph

def extract_branch_region(graph: ReductionGraph, start: str, merge: Optional[str]) -> Set[str]:
    """
    Finds all nodes reachable from 'start' in the current graph without crossing 'merge'.
    """
    visited = set()
    queue = [start]
    while queue:
        curr = queue.pop(0)
        if curr == merge:
            continue
        if curr in visited:
            continue
        visited.add(curr)
        
        for succ in graph.successors.get(curr, []):
            if succ != merge:
                queue.append(succ)
    return visited

def validate_branch_region(graph: ReductionGraph, region: Set[str], split: str, merge: Optional[str]) -> bool:
    """
    Validates that a candidate branch region has a single entry from 'split' and
    exits only to 'merge' (or exits the function directly).
    """
    if not region:
        return False
        
    for node_id in region:
        # Avoid premature structuring if the region still contains active split nodes.
        # Active split nodes should be structured first from the inside out.
        if len(graph.successors.get(node_id, [])) > 1:
            return False

        # 1. Check predecessors of node_id
        for pred in graph.predecessors.get(node_id, []):
            if pred not in region and pred != split:
                # Node has an entry from outside the region that is not the split node
                return False
                
        # 2. Check successors of node_id
        for succ in graph.successors.get(node_id, []):
            if succ not in region and succ != merge:
                # Node exits the region to a node other than the merge node
                return False
                
    return True

def build_branch_node(graph: ReductionGraph, region: Set[str], start: str) -> RegionNode:
    """
    Sorts a branch region topologically and wraps it in a SequenceNode if it has
    multiple nodes, or returns the single RegionNode.
    """
    sorted_nodes = []
    visited = set()
    
    def dfs_sort(node_id):
        if node_id in visited:
            return
        visited.add(node_id)
        for succ in graph.successors.get(node_id, []):
            if succ in region:
                dfs_sort(succ)
        sorted_nodes.insert(0, node_id)
        
    dfs_sort(start)
    
    # Retrieve actual RegionNodes
    nodes_list = [graph.nodes[nid] for nid in sorted_nodes]
    if len(nodes_list) == 1:
        return nodes_list[0]
    else:
        return SequenceNode(nodes_list)

def try_conditional_reduction(graph: ReductionGraph, ipdom: Dict[str, Optional[str]], logger: logging.Logger) -> bool:
    """
    Finds and collapses a single conditional region (if or if-else) in the graph.
    Returns True if a conditional region was collapsed, False otherwise.
    """
    # Sort split nodes deterministically
    split_nodes = []
    for node_id, node in graph.nodes.items():
        succs = graph.successors.get(node_id, [])
        if len(succs) == 2:
            split_nodes.append(node_id)
            
    split_nodes.sort()
    
    for s in split_nodes:
        succs = graph.successors[s]
        a, b = succs[0], succs[1]
        
        # Merge node using immediate post-dominator info
        m = ipdom.get(s)
        
        logger.debug(f"Checking conditional split at {s} with merge candidate {m}")
        
        # Case 1: Simple If (a == m)
        if a == m:
            else_region = extract_branch_region(graph, b, m)
            if validate_branch_region(graph, else_region, s, m):
                then_branch = build_branch_node(graph, else_region, b)
                new_node = IfNode(condition_block=s, then_branch=then_branch, merge_block=m)
                
                old_ids = [s] + list(else_region)
                new_succs = [m] if m is not None else []
                new_preds = list(graph.predecessors.get(s, []))
                
                graph.replace_nodes(old_ids, new_node, new_succs, new_preds)
                logger.info(f"Detected if region at {s} with merge node {m}")
                return True
                
        # Case 2: Simple If (b == m)
        if b == m:
            then_region = extract_branch_region(graph, a, m)
            if validate_branch_region(graph, then_region, s, m):
                then_branch = build_branch_node(graph, then_region, a)
                new_node = IfNode(condition_block=s, then_branch=then_branch, merge_block=m)
                
                old_ids = [s] + list(then_region)
                new_succs = [m] if m is not None else []
                new_preds = list(graph.predecessors.get(s, []))
                
                graph.replace_nodes(old_ids, new_node, new_succs, new_preds)
                logger.info(f"Detected if region at {s} with merge node {m}")
                return True
                
        # Case 3: If/Else (a != m and b != m)
        if a != m and b != m:
            then_region = extract_branch_region(graph, a, m)
            else_region = extract_branch_region(graph, b, m)
            
            if (validate_branch_region(graph, then_region, s, m) and
                validate_branch_region(graph, else_region, s, m) and
                then_region.isdisjoint(else_region)):
                
                then_branch = build_branch_node(graph, then_region, a)
                else_branch = build_branch_node(graph, else_region, b)
                new_node = IfElseNode(condition_block=s, then_branch=then_branch, else_branch=else_branch, merge_block=m)
                
                old_ids = [s] + list(then_region) + list(else_region)
                new_succs = [m] if m is not None else []
                new_preds = list(graph.predecessors.get(s, []))
                
                graph.replace_nodes(old_ids, new_node, new_succs, new_preds)
                logger.info(f"Detected if/else region at {s} with merge node {m}")
                return True
                
    return False
