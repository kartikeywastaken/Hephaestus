# -*- coding: utf-8 -*-
"""
Phase 3B: Orchestration of Structuring Passes
"""

import logging
from typing import Dict, Any, List
from src.ir.structuring.analysis import analyze_function
from src.ir.structuring.models import RegionNode, BlockNode, UnstructuredRegionNode
from src.ir.structuring.reducers import ReductionGraph, run_sequence_reductions
from src.ir.structuring.conditionals import try_conditional_reduction

def structure_function(function_data: Dict[str, Any], logger: logging.Logger) -> RegionNode:
    """
    Orchestrates the structuring passes for a single function and returns
    its structured control-flow RegionNode.
    """
    func_name = function_data.get("name", "unknown")
    
    # 1. Run Phase 3A analysis to get initial graphs and ipdom maps
    report = analyze_function(function_data, logger)
    
    # 2. Wrap basic blocks in BlockNode objects
    nodes = {nid: BlockNode(nid) for nid in report["nodes"]}
    
    # 3. Initialize the ReductionGraph
    graph = ReductionGraph(
        entry_node_id=report["entry_node"],
        nodes=nodes,
        successors=report["successor_map"],
        predecessors=report["predecessor_map"]
    )
    
    ipdom = report["immediate_post_dominators"]
    
    # 4. Orchestrate reduction loop with sequence + conditional + loop restart rule
    from src.ir.structuring.loops import try_loop_reduction
    reductions = 0
    while True:
        # Step A: Reduce sequences to fixpoint
        run_sequence_reductions(graph, logger)
        
        # Step B: Detect and collapse one conditional region
        collapsed_conditional = try_conditional_reduction(graph, ipdom, logger)
        if collapsed_conditional:
            reductions += 1
            # Restart sequence reductions after a conditional collapse
            continue
            
        # Step C: Detect and collapse one loop region
        collapsed_loop = try_loop_reduction(graph, ipdom, logger)
        if collapsed_loop:
            reductions += 1
            # Restart sequence and conditional passes after a loop collapse
            continue
            
        break
            
    # 5. Fallback wrapping for partially structured graphs
    remaining_ids = sorted(list(graph.nodes.keys()))
    if len(graph.nodes) == 1:
        root_node = graph.nodes[remaining_ids[0]]
    else:
        # Perform a stable topological sort on remaining nodes
        visited = set()
        sorted_nodes = []
        
        def dfs_sort(node_id):
            if node_id in visited:
                return
            visited.add(node_id)
            # Sort successors to ensure deterministic topological sort
            for succ in sorted(graph.successors.get(node_id, [])):
                if succ in graph.nodes:
                    dfs_sort(succ)
            sorted_nodes.insert(0, graph.nodes[node_id])
            
        # Start sorting from entry if still present in graph
        if graph.entry_node_id in graph.nodes:
            dfs_sort(graph.entry_node_id)
            
        for nid in remaining_ids:
            if nid not in visited:
                dfs_sort(nid)
                
        root_node = UnstructuredRegionNode(sorted_nodes)
        
    logger.info(f"Structured function {func_name} into root node type {type(root_node).__name__}")
    return root_node
