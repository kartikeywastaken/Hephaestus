# -*- coding: utf-8 -*-
"""
Phase 3A: Post-Dominators Solver
"""

from typing import Dict, Set, Optional, List
import logging
from src.ir.structuring.graph import CFG

def compute_post_dominators(cfg: CFG, logger: logging.Logger) -> Dict[str, Set[str]]:
    """
    Computes the post-dominator sets for each node in the CFG using a synthetic exit node
    and the iterative solver on the reversed CFG.
    """
    # Nodes list including a virtual EXIT node
    exit_node_id = "EXIT"
    all_nodes = set(cfg.nodes) | {exit_node_id}
    
    # In the reversed CFG:
    # - The entry node is EXIT.
    # - The predecessors of node 'n' are its successors in the forward CFG.
    # - For exit nodes in the forward CFG, they transition to EXIT, so in the reversed CFG,
    #   EXIT transitions to them. This means the predecessor of the exit nodes in the reversed CFG is EXIT.
    
    rev_preds: Dict[str, List[str]] = {}
    for node in cfg.nodes:
        # successors in forward CFG are predecessors in reversed CFG
        successors = cfg.successors.get(node, [])
        if not successors:
            # Forward exit node: in forward CFG it has an edge to EXIT,
            # so in reversed CFG, EXIT is its predecessor (comes before it).
            rev_preds[node] = [exit_node_id]
        else:
            rev_preds[node] = list(successors)
            
    # For EXIT itself, in reversed CFG, it is the entry, so it has no predecessors in reversed CFG.
    rev_preds[exit_node_id] = []

    # Initialize post-dominators
    pdom = {n: set(all_nodes) for n in all_nodes}
    pdom[exit_node_id] = {exit_node_id}

    changed = True
    iterations = 0
    while changed:
        changed = False
        iterations += 1
        for node in all_nodes:
            if node == exit_node_id:
                continue
            
            preds = rev_preds.get(node, [])
            if not preds:
                new_pdom = {node}
            else:
                new_pdom = set(pdom[preds[0]])
                for p in preds[1:]:
                    new_pdom.intersection_update(pdom[p])
                new_pdom.add(node)
            
            if new_pdom != pdom[node]:
                pdom[node] = new_pdom
                changed = True

    logger.info(f"Computed post-dominators in {iterations} iterations")
    
    # Filter out the virtual EXIT node from the final sets for cleaner output,
    # but we keep it or handle it for immediate post-dominator computation.
    # Let's return a dictionary containing only the original cfg nodes,
    # but keep the virtual EXIT in the sets or filter it?
    # If we filter it, the user doesn't see "EXIT". Let's keep a internal version with EXIT
    # for immediate post-dominators computation, but return the filtered version or the full version?
    # Actually, returning the full version or filtered version: if we return the full version,
    # the caller knows about EXIT. Let's return the full version but also allow filtering.
    # Actually, let's keep EXIT in the sets returned by compute_post_dominators, so that
    # compute_immediate_post_dominators can use it.
    return pdom

def compute_immediate_post_dominators(cfg: CFG, pdom: Dict[str, Set[str]], logger: logging.Logger) -> Dict[str, Optional[str]]:
    """
    Computes the immediate post-dominator (ipdom) for each node based on the post-dominator sets.
    """
    ipdom: Dict[str, Optional[str]] = {}
    exit_node_id = "EXIT"
    
    for node in cfg.nodes:
        # strict post-dominators
        strict_pdoms = pdom.get(node, set()) - {node}
        curr_ipdom = None
        for p in strict_pdoms:
            is_ipdom = True
            for other in strict_pdoms:
                if other == p:
                    continue
                # If 'other' is post-dominated by 'p' (i.e. 'p' is in 'pdom[other]'),
                # then 'p' is further away from 'node' than 'other'.
                # So 'p' cannot be the immediate post-dominator.
                if p in pdom.get(other, set()):
                    is_ipdom = False
                    break
            if is_ipdom:
                curr_ipdom = p
                break
        
        # If the immediate post-dominator is the virtual EXIT node, map it to None
        if curr_ipdom == exit_node_id:
            curr_ipdom = None
            
        ipdom[node] = curr_ipdom
        if curr_ipdom:
            logger.debug(f"Immediate post-dominator of {node} is {curr_ipdom}")
            
    return ipdom
