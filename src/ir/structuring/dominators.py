# -*- coding: utf-8 -*-
"""
Phase 3A: Dominators Solver
"""

from typing import Dict, Set, Optional
import logging
from src.ir.structuring.graph import CFG

def compute_dominators(cfg: CFG, logger: logging.Logger, func_name: str = "unknown") -> Dict[str, Set[str]]:
    """
    Computes the dominator sets for each node in the CFG using the iterative algorithm.
    """
    all_nodes = set(cfg.nodes)
    dom = {n: set(all_nodes) for n in cfg.nodes}
    
    entry = cfg.entry_node
    if entry in dom:
        dom[entry] = {entry}

    changed = True
    iterations = 0
    while changed:
        changed = False
        iterations += 1
        for node in cfg.nodes:
            if node == entry:
                continue
            preds = cfg.predecessors.get(node, [])
            if not preds:
                new_dom = {node}
            else:
                new_dom = set(dom[preds[0]])
                for p in preds[1:]:
                    new_dom.intersection_update(dom[p])
                new_dom.add(node)
            
            if new_dom != dom[node]:
                dom[node] = new_dom
                changed = True
    
    logger.info(f"Computed dominators for {func_name} in {iterations} iterations")
    return dom

def compute_immediate_dominators(cfg: CFG, dom: Dict[str, Set[str]], logger: logging.Logger, func_name: str = "unknown") -> Dict[str, Optional[str]]:
    """
    Computes the immediate dominator (idom) for each node based on the dominator sets.
    """
    idom: Dict[str, Optional[str]] = {}
    for node in cfg.nodes:
        if node == cfg.entry_node:
            idom[node] = None
            logger.debug(f"Immediate dominator of {node} is None in {func_name}")
            continue
        
        # strict dominators
        strict_doms = dom[node] - {node}
        curr_idom = None
        for d in strict_doms:
            is_idom = True
            for other in strict_doms:
                if other == d:
                    continue
                if other not in dom[d]:
                    is_idom = False
                    break
            if is_idom:
                curr_idom = d
                break
        
        idom[node] = curr_idom
        logger.debug(f"Immediate dominator of {node} is {curr_idom} in {func_name}")
            
    return idom
