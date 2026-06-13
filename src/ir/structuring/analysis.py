# -*- coding: utf-8 -*-
"""
Phase 3A: Per-Function Control-Flow Analysis Report
"""

from typing import Dict, Any, List, Set, Optional
import logging

from src.ir.structuring.graph import CFG
from src.ir.structuring.dominators import (
    compute_dominators,
    compute_immediate_dominators,
)
from src.ir.structuring.postdominators import (
    compute_post_dominators,
    compute_immediate_post_dominators,
)

def analyze_function(function_data: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    """
    Computes and returns a structured control-flow analysis report for the function.
    """
    func_name = function_data.get("name", "unknown")
    
    # 1. Normalize CFG
    cfg = CFG(function_data)
    
    # Reconstruct normalized edge list for reporting and sorting
    edges: List[Dict[str, str]] = []
    for src in sorted(cfg.successors.keys()):
        for dst in sorted(cfg.successors[src]):
            edges.append({"source": src, "target": dst})
            
    node_count = len(cfg.nodes)
    edge_count = len(edges)
    logger.info(f"Function {func_name} normalized CFG: {node_count} nodes, {edge_count} edges")
    
    # 2. Compute Dominators
    dom = compute_dominators(cfg, logger, func_name=func_name)
    idom = compute_immediate_dominators(cfg, dom, logger, func_name=func_name)
    
    # 3. Compute Post-Dominators (using virtual EXIT node)
    pdom = compute_post_dominators(cfg, logger)
    ipdom = compute_immediate_post_dominators(cfg, pdom, logger)
    
    # Log post-dominator convergence and immediate post-dominator assignments
    # Note: compute_post_dominators already logs convergence.
    # We log immediate post-dominator assignments here for consistency.
    for node in sorted(cfg.nodes):
        val = ipdom.get(node)
        logger.debug(f"Immediate post-dominator assignment: {node} -> {val} for {func_name}")
        
    # 4. Detect Back-Edges
    back_edges: List[Dict[str, Any]] = []
    for edge in edges:
        u = edge["source"]
        v = edge["target"]
        # Back-edge is an edge u -> v where v dominates u
        if v in dom.get(u, set()):
            back_edges.append({
                "source": u,
                "destination": v,
                "candidate_loop_header": v,
                "candidate_latch": u
            })
            logger.info(f"Detected back edge {u} -> {v} in {func_name}")
            
    # Sort back edges for deterministic output
    back_edges.sort(key=lambda x: (x["source"], x["destination"]))
    
    # Prepare serializable forms of dom/pdom mapping (remove EXIT from pdom, convert to sorted lists)
    report_dom: Dict[str, List[str]] = {
        node: sorted(list(nodes)) for node, nodes in dom.items()
    }
    
    report_pdom: Dict[str, List[str]] = {}
    for node in cfg.nodes:
        # Filter out the virtual EXIT node from the reported post-dominators set
        filtered = pdom.get(node, set()) - {"EXIT"}
        report_pdom[node] = sorted(list(filtered))
        
    # Standardize predecessors / successors into sorted lists
    report_preds: Dict[str, List[str]] = {
        node: sorted(cfg.predecessors.get(node, [])) for node in sorted(cfg.nodes)
    }
    report_succs: Dict[str, List[str]] = {
        node: sorted(cfg.successors.get(node, [])) for node in sorted(cfg.nodes)
    }
    
    return {
        "function_name": func_name,
        "entry_node": cfg.entry_node,
        "exit_nodes": sorted(list(cfg.exit_nodes)),
        "nodes": sorted(list(cfg.nodes)),
        "edges": edges,
        "predecessor_map": report_preds,
        "successor_map": report_succs,
        "dominator_sets": report_dom,
        "immediate_dominators": idom,
        "post_dominator_sets": report_pdom,
        "immediate_post_dominators": ipdom,
        "detected_back_edges": back_edges,
    }
