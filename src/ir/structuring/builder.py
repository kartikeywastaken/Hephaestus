# -*- coding: utf-8 -*-
"""
Phase 3B/3D: Orchestration of Structuring Passes
"""

import logging
from typing import Dict, Any, List, Optional
from src.ir.structuring.analysis import analyze_function
from src.ir.structuring.models import RegionNode, BlockNode, UnstructuredRegionNode
from src.ir.structuring.reducers import ReductionGraph, run_sequence_reductions
from src.ir.structuring.conditionals import try_conditional_reduction
from src.ir.structuring.fallbacks import classify_unstructured_region

def try_final_acyclic_assembly(graph: ReductionGraph, entry_node_id: str, logger: logging.Logger, function_name: str) -> Optional[RegionNode]:
    """
    Attempt to assemble the remaining reduced graph if it is acyclic and cleanly entry-rooted.
    """
    from src.ir.structuring.fallbacks import _remaining_back_edges, detect_switch_fanout
    from src.ir.structuring.models import SequenceNode

    logger.info(
        "Attempting final acyclic assembly for function %s with %d residual nodes",
        function_name,
        len(graph.nodes),
    )

    # 1. Check if the graph is acyclic (no back-edges)
    back_edges = _remaining_back_edges(graph)
    if back_edges:
        logger.info(
            "Final acyclic assembly skipped for function %s: residual graph contains cycles/back-edges",
            function_name,
        )
        return None

    # 2. Check if it is a switch candidate (out-degree >= 3)
    if detect_switch_fanout(graph, logger) is not None:
        logger.info(
            "Final acyclic assembly skipped for function %s: residual graph contains switch-like fan-out",
            function_name,
        )
        return None

    # 3. Perform a stable entry-rooted DFS traversal to get topological ordering of remaining nodes
    remaining_ids = sorted(list(graph.nodes.keys()))
    visited = set()
    sorted_nodes = []

    def dfs_sort(node_id):
        if node_id in visited:
            return
        visited.add(node_id)
        # Sort successors to ensure deterministic order
        for succ in sorted(graph.successors.get(node_id, [])):
            if succ in graph.nodes:
                dfs_sort(succ)
        sorted_nodes.insert(0, graph.nodes[node_id])

    # Start sorting from entry
    if entry_node_id in graph.nodes:
        dfs_sort(entry_node_id)
    else:
        logger.info(
            "Final acyclic assembly skipped for function %s: entry node not in residual graph",
            function_name,
        )
        return None

    # 4. Check if the entry node can reach all remaining nodes (no disconnected components)
    if len(visited) < len(graph.nodes):
        logger.info(
            "Final acyclic assembly skipped for function %s: residual graph contains unreachable nodes from entry",
            function_name,
        )
        return None

    # 5. Assemble ordered nodes
    if len(sorted_nodes) == 1:
        logger.info(
            "Final acyclic assembly succeeded for function %s: single residual root returned",
            function_name,
        )
        return sorted_nodes[0]
    
    logger.info(
        "Final acyclic assembly succeeded for function %s: collapsed %d residual nodes into SequenceNode",
        function_name,
        len(sorted_nodes),
    )
    return SequenceNode(sorted_nodes)

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
        from src.ir.structuring.fallbacks import detect_switch_like_region
        if detect_switch_like_region(graph, logger):
            logger.info(
                "Detected switch-like residual region in function %s; preserving as switch_candidate fallback",
                func_name,
            )
            logger.info(
                "Skipping final acyclic assembly for function %s because residual graph is switch-like",
                func_name,
            )
            root_node = None
        else:
            root_node = try_final_acyclic_assembly(graph, graph.entry_node_id, logger, func_name)
            
        if root_node is None:
            # Perform a stable entry-rooted DFS ordering on remaining nodes
            visited = set()
            sorted_nodes = []

            def dfs_sort(node_id):
                if node_id in visited:
                    return
                visited.add(node_id)
                # Sort successors to ensure deterministic order
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

            # Phase 3D: classify why the graph remained unstructured, then wrap
            reason, region_kind = classify_unstructured_region(graph, logger)
            logger.info(
                "Wrapping function %s in UnstructuredRegionNode(reason='%s', region_kind='%s')",
                func_name,
                reason,
                region_kind,
            )
            for nid, node in sorted(graph.nodes.items()):
                if not isinstance(node, BlockNode):
                    logger.info(
                        f"Preserving {type(node).__name__} inside fallback region "
                        f"rooted at {nid}"
                    )

            root_node = UnstructuredRegionNode(
                sorted_nodes,
                reason=reason,
                region_kind=region_kind,
            )

    logger.info(f"Structured function {func_name} into root node type {type(root_node).__name__}")
    return root_node
