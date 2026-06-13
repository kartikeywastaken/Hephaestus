# -*- coding: utf-8 -*-
"""
Phase 3C: Loop Detection, Validation, and Collapsing
"""

import logging
from typing import Dict, List, Set, Optional, Tuple
from src.ir.structuring.models import RegionNode, LoopNode, SequenceNode, UnstructuredRegionNode
from src.ir.structuring.reducers import ReductionGraph, run_sequence_reductions
from src.ir.structuring.conditionals import try_conditional_reduction

class ReducedCFG:
    """
    Mock CFG wrapper expected by Phase 3A dominators solver.
    """
    def __init__(self, entry_node: str, nodes: Set[str], predecessors: Dict[str, List[str]]):
        self.entry_node = entry_node
        self.nodes = nodes
        self.predecessors = predecessors

def try_loop_reduction(graph: ReductionGraph, ipdom: Dict[str, Optional[str]], logger: logging.Logger) -> bool:
    """
    Detects, validates, and collapses one loop region in the ReductionGraph.
    Returns True if a loop was collapsed, False otherwise.
    """
    # 1. Dynamically compute dominators on the current reduced graph
    from src.ir.structuring.dominators import compute_dominators
    reduced_cfg = ReducedCFG(
        entry_node=graph.entry_node_id,
        nodes=set(graph.nodes.keys()),
        predecessors=graph.predecessors
    )
    # compute dominators with logger to fixpoint
    reduced_dom = compute_dominators(reduced_cfg, logger, func_name="reduced_graph")

    # 2. Detect back-edges: u -> h where h dominates u in the reduced graph
    back_edges: List[Tuple[str, str]] = []
    for u in sorted(graph.nodes.keys()):
        for h in sorted(graph.successors.get(u, [])):
            if h in reduced_dom.get(u, set()):
                back_edges.append((u, h))
                logger.debug(f"Detected back-edge candidate: {u} -> {h}")

    if not back_edges:
        return False

    # Group latches by header
    header_to_latches: Dict[str, List[str]] = {}
    for u, h in back_edges:
        header_to_latches.setdefault(h, []).append(u)

    # Sort headers to ensure deterministic loop recovery order (inside-out)
    # We prioritize headers that are dominated by other headers (inner loops first)
    # Or simply sort by headers' normalized address (stable order)
    headers = sorted(list(header_to_latches.keys()))
    
    # Sort headers so that if h1 dominates h2, h2 (the inner loop) is processed first
    headers_copy = list(headers)
    def get_inner_priority(h):
        # Count how many other headers dominate h
        count = 0
        for other in headers_copy:
            if other != h and other in reduced_dom.get(h, set()):
                count += 1
        return count

    # Sort in descending order of dominator counts (inner loop has more dominators)
    logger.debug(f"reduced_dom: {reduced_dom}")
    for h in headers:
        logger.debug(f"header {h} priority: {get_inner_priority(h)}, dominated by: {[other for other in headers if other != h and other in reduced_dom.get(h, set())]}")
    logger.debug(f"headers before sort: {headers}")
    headers.sort(key=get_inner_priority, reverse=True)
    logger.debug(f"headers after sort: {headers}")

    for h in headers:
        latches = sorted(header_to_latches[h])
        logger.info(f"Processing candidate loop header {h} with latches {latches}")

        # 3. Construct natural loop body: predecessor walking
        body_set = {h}
        worklist = list(latches)
        for latch in latches:
            body_set.add(latch)
            
        while worklist:
            n = worklist.pop()
            for p in graph.predecessors.get(n, []):
                if p not in body_set:
                    body_set.add(p)
                    worklist.append(p)

        logger.debug(f"Natural loop for header {h} contains {len(body_set)} nodes: {sorted(list(body_set))}")

        # 4. Dominance Guard: ensure all candidate body vertices are dominated by header h
        is_reducible = True
        for node_id in body_set:
            if h not in reduced_dom.get(node_id, set()):
                logger.warning(f"Loop body node {node_id} is not dominated by header {h}. Rejecting loop structuring.")
                is_reducible = False
                break

        if not is_reducible:
            continue

        # 5. Extract loop exit blocks
        exit_blocks = set()
        for x in body_set:
            for y in graph.successors.get(x, []):
                if y not in body_set:
                    exit_blocks.add(y)

        # 6. Classify loop kind (heuristic)
        kind = "endless"
        h_succs = graph.successors.get(h, [])
        if len(h_succs) == 2:
            outside_succs = [s for s in h_succs if s not in body_set]
            if len(outside_succs) == 1:
                kind = "while_like"

        # 7. Collapse Loop Body (induced subgraph copy DAG reduction)
        # Extract induced subgraph
        sub_nodes = {nid: graph.nodes[nid] for nid in body_set}
        sub_successors = {}
        sub_predecessors = {}
        for nid in body_set:
            sub_successors[nid] = [s for s in graph.successors.get(nid, []) if s in body_set]
            sub_predecessors[nid] = [p for p in graph.predecessors.get(nid, []) if p in body_set]

        # Temporarily remove back-edges to break cycles (DAG conversion)
        for latch in latches:
            if h in sub_successors.get(latch, []):
                sub_successors[latch].remove(h)
            if latch in sub_predecessors.get(h, []):
                sub_predecessors[h].remove(latch)

        # Initialize sub reduction graph
        sub_graph = ReductionGraph(
            entry_node_id=h,
            nodes=sub_nodes,
            successors=sub_successors,
            predecessors=sub_predecessors
        )

        # Restrict ipdom mapping to the loop body set (nodes outside act as exit None)
        sub_ipdom = {}
        for nid in body_set:
            m_outer = ipdom.get(nid)
            if m_outer in body_set:
                sub_ipdom[nid] = m_outer
            else:
                sub_ipdom[nid] = None

        # Run sequence and conditional reductions on this DAG to fixpoint
        while True:
            run_sequence_reductions(sub_graph, logger)
            collapsed_cond = try_conditional_reduction(sub_graph, sub_ipdom, logger)
            if collapsed_cond:
                continue
            else:
                break

        # Extract structured loop body node
        remaining_ids = sorted(list(sub_graph.nodes.keys()))
        if len(sub_graph.nodes) == 1:
            body_node = sub_graph.nodes[remaining_ids[0]]
        else:
            # Fallback wrapping if loop body doesn't collapse to 1 node
            visited_sub = set()
            sorted_sub = []
            
            def dfs_sort_sub(node_id):
                if node_id in visited_sub:
                    return
                visited_sub.add(node_id)
                for succ in sorted(sub_graph.successors.get(node_id, [])):
                    if succ in sub_graph.nodes:
                        dfs_sort_sub(succ)
                sorted_sub.insert(0, sub_graph.nodes[node_id])

            if sub_graph.entry_node_id in sub_graph.nodes:
                dfs_sort_sub(sub_graph.entry_node_id)

            for nid in remaining_ids:
                if nid not in visited_sub:
                    dfs_sort_sub(nid)

            body_node = UnstructuredRegionNode(sorted_sub)

        # 8. Collapse Loop in Main ReductionGraph
        new_node = LoopNode(
            kind=kind,
            header_block=h,
            body=body_node,
            exit_blocks=sorted(list(exit_blocks))
        )
        
        # Rewiring Rules:
        old_ids = list(body_set)
        new_succs = sorted(list(exit_blocks))
        new_preds = [p for p in graph.predecessors.get(h, []) if p not in body_set]

        graph.replace_nodes(old_ids, new_node, new_succs, new_preds)
        logger.info(f"Collapsed loop region at header {h} into LoopNode(kind='{kind}')")
        return True

    return False
