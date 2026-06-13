# -*- coding: utf-8 -*-
"""
Phase 3C: Loop Detection, Validation, and Collapsing
"""

import logging
from typing import Dict, List, Set, Optional, Tuple
from src.ir.structuring.models import RegionNode, LoopNode, SequenceNode, UnstructuredRegionNode
from src.ir.structuring.reducers import ReductionGraph, run_sequence_reductions
from src.ir.structuring.conditionals import try_conditional_reduction
from src.ir.structuring.postdominators import compute_post_dominators, compute_immediate_post_dominators

class ReducedCFG:
    """
    Mock CFG wrapper expected by the dominators solver.
    Provides .entry_node, .nodes, .predecessors.
    """
    def __init__(self, entry_node: str, nodes: Set[str], predecessors: Dict[str, List[str]]):
        self.entry_node = entry_node
        self.nodes = nodes
        self.predecessors = predecessors


class SubGraphCFG:
    """
    Adapter wrapping a loop-body subgraph for use with the postdominators solver.
    Provides .nodes (set), .successors (dict), .predecessors (dict) matching
    the CFG interface expected by compute_post_dominators / compute_immediate_post_dominators.
    """
    def __init__(self, nodes: Set[str], successors: Dict[str, List[str]], predecessors: Dict[str, List[str]]):
        self.nodes = set(nodes)
        self.successors = {k: list(v) for k, v in successors.items()}
        self.predecessors = {k: list(v) for k, v in predecessors.items()}


def compute_subgraph_ipdom(
    nodes: Set[str],
    successors: Dict[str, List[str]],
    predecessors: Dict[str, List[str]],
    logger: logging.Logger,
) -> Dict[str, Optional[str]]:
    """
    Computes the immediate post-dominator map for a loop-body subgraph DAG.

    Nodes with successors that exit the subgraph (i.e., nodes outside `nodes`)
    are treated as DAG exit nodes by the postdominators solver's synthetic EXIT
    mechanism (zero in-subgraph successors after filtering).
    """
    # Build a SubGraphCFG whose successor lists only include in-body nodes;
    # this makes the postdominators solver treat dangling exits as function exits.
    filtered_succs: Dict[str, List[str]] = {
        nid: [s for s in successors.get(nid, []) if s in nodes]
        for nid in nodes
    }
    filtered_preds: Dict[str, List[str]] = {
        nid: [p for p in predecessors.get(nid, []) if p in nodes]
        for nid in nodes
    }
    cfg_adapter = SubGraphCFG(nodes, filtered_succs, filtered_preds)
    pdom = compute_post_dominators(cfg_adapter, logger)
    ipdom = compute_immediate_post_dominators(cfg_adapter, pdom, logger)
    # Filter to original nodes only (drop any synthetic EXIT entries)
    return {nid: v for nid, v in ipdom.items() if nid in nodes}


def try_conditional_reduction_body(
    graph: ReductionGraph,
    sub_ipdom: Dict[str, Optional[str]],
    logger: logging.Logger,
    latch_sinks: Optional[Set[str]] = None,
) -> bool:
    """
    A loop-body-specific variant of try_conditional_reduction that considers any
    RegionNode (not just BlockNode) as a potential split node, since sequence
    reductions inside the loop body collapse chains of BlockNodes into SequenceNodes
    that can still branch to two successors.

    Guard: when sub_ipdom[s] is None, we only accept the reduction if exactly one
    of the two arms is a pure latch sink (path leads exclusively through actual latch
    nodes which have no in-body successors) and the other arm is NOT a latch sink.
    In that case, the non-latch arm becomes the implicit merge node for a "continue-if"
    (if cond: continue else: fallthrough) reduction.

    If BOTH arms are pure sinks (whether latch or otherwise), the split is rejected
    to avoid the dual-exit false positive seen in _helper (recursion-as-loop pattern).

    Parameters
    ----------
    latch_sinks : set of node IDs that are latch nodes in the current subgraph
                  (they are back-edge sources whose back-edge has been removed,
                  so they have 0 in-body successors).
    """
    from src.ir.structuring.models import RegionNode, IfNode, IfElseNode, SequenceNode
    from src.ir.structuring.conditionals import (
        extract_branch_region,
        validate_branch_region,
        build_branch_node,
    )

    if latch_sinks is None:
        latch_sinks = set()

    def _is_latch_only_region(region: Set[str]) -> bool:
        """Returns True if every node in 'region' is a latch sink (no in-body successors)
        AND the region contains at least one actual latch node."""
        has_latch = False
        for nid in region:
            if len(graph.successors.get(nid, [])) > 0:
                return False
            if nid in latch_sinks:
                has_latch = True
        return has_latch

    split_nodes = []
    for node_id, node in graph.nodes.items():
        if isinstance(node, RegionNode):
            succs = graph.successors.get(node_id, [])
            if len(succs) == 2:
                split_nodes.append(node_id)
    split_nodes.sort()

    for s in split_nodes:
        succs = graph.successors[s]
        a, b = succs[0], succs[1]
        m = sub_ipdom.get(s)

        logger.debug(f"[body] Checking conditional split at {s} with merge candidate {m}")

        # Guard for m=None: handle the "continue-if" pattern.
        # This occurs when one arm is a pure latch-only sink (loop continue) and
        # the other arm continues the loop body (non-latch sink or internal node).
        # In this case, we set the merge to the non-latch arm if it exists in the graph.
        if m is None:
            a_region = extract_branch_region(graph, a, None)
            b_region = extract_branch_region(graph, b, None)
            a_is_sink = all(len(graph.successors.get(nid, [])) == 0 for nid in a_region)
            b_is_sink = all(len(graph.successors.get(nid, [])) == 0 for nid in b_region)

            if a_is_sink and b_is_sink:
                # Both arms exit the loop body. Check if one is a latch-only sink.
                a_is_latch = _is_latch_only_region(a_region)
                b_is_latch = _is_latch_only_region(b_region)

                if a_is_latch and not b_is_latch and b in graph.nodes:
                    # "if (cond) { continue; }" pattern — arm a goes to latch,
                    # arm b is the merge/fallthrough. Treat b as the merge.
                    then_region = a_region
                    if validate_branch_region(graph, then_region, s, b):
                        then_branch = build_branch_node(graph, then_region, a)
                        new_node = IfNode(condition_block=s, then_branch=then_branch, merge_block=b)
                        old_ids = [s] + list(then_region)
                        new_succs = [b]
                        new_preds = list(graph.predecessors.get(s, []))
                        graph.replace_nodes(old_ids, new_node, new_succs, new_preds)
                        logger.info(f"[body] Detected continue-if region at {s} with implicit merge {b}")
                        return True
                elif b_is_latch and not a_is_latch and a in graph.nodes:
                    # "if (cond) { fallthrough } else { continue; }" pattern
                    else_region = b_region
                    if validate_branch_region(graph, else_region, s, a):
                        else_branch = build_branch_node(graph, else_region, b)
                        new_node = IfNode(condition_block=s, then_branch=else_branch, merge_block=a)
                        old_ids = [s] + list(else_region)
                        new_succs = [a]
                        new_preds = list(graph.predecessors.get(s, []))
                        graph.replace_nodes(old_ids, new_node, new_succs, new_preds)
                        logger.info(f"[body] Detected continue-if region at {s} with implicit merge {a}")
                        return True
                else:
                    # Both or neither are latch sinks — not reducible as structured if
                    logger.debug(f"[body] Skipping dual-sink m=None split at {s} (not structured)")
                    continue

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
                logger.info(f"[body] Detected if region at {s} with merge node {m}")
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
                logger.info(f"[body] Detected if region at {s} with merge node {m}")
                return True

        # Case 3: If/Else (a != m and b != m)
        if a != m and b != m:
            then_region = extract_branch_region(graph, a, m)
            else_region = extract_branch_region(graph, b, m)
            if (validate_branch_region(graph, then_region, s, m)
                    and validate_branch_region(graph, else_region, s, m)
                    and then_region.isdisjoint(else_region)):
                then_branch = build_branch_node(graph, then_region, a)
                else_branch = build_branch_node(graph, else_region, b)
                new_node = IfElseNode(
                    condition_block=s,
                    then_branch=then_branch,
                    else_branch=else_branch,
                    merge_block=m,
                )
                old_ids = [s] + list(then_region) + list(else_region)
                new_succs = [m] if m is not None else []
                new_preds = list(graph.predecessors.get(s, []))
                graph.replace_nodes(old_ids, new_node, new_succs, new_preds)
                logger.info(f"[body] Detected if/else region at {s} with merge node {m}")
                return True

    return False

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

        # Compute a fresh immediate-post-dominator map on the loop-body subgraph DAG.
        # Using the outer function's ipdom clipped to body_set loses valid intra-body
        # merge points for conditionals whose outer ipdom falls at a loop-exit node
        # (outside body_set).  A fresh computation on the DAG finds the correct
        # intra-body merge blocks so that conditional reductions inside the loop work.
        sub_ipdom = compute_subgraph_ipdom(
            nodes=set(sub_graph.nodes.keys()),
            successors=sub_graph.successors,
            predecessors=sub_graph.predecessors,
            logger=logger,
        )
        logger.debug(f"Loop body sub_ipdom for header {h}: {sub_ipdom}")

        # Track which original latch IDs still exist as standalone nodes in the subgraph
        # (they are DAG sinks after back-edge removal). These are used by
        # try_conditional_reduction_body to detect "continue-if" patterns.
        original_latch_ids: Set[str] = set(latches)

        # Run sequence and conditional reductions on this DAG to fixpoint.
        # After each conditional collapse, node IDs change (SequenceNodes get new IDs),
        # so we recompute sub_ipdom from the current subgraph state to expose
        # newly visible intra-body merge points for subsequent passes.
        # Use the loop-body-specific reducer that handles RegionNode splits
        # (SequenceNodes that inherited 2 successors after sequence reduction).
        while True:
            run_sequence_reductions(sub_graph, logger)
            # Recompute ipdom on the current (possibly reduced) subgraph state
            sub_ipdom = compute_subgraph_ipdom(
                nodes=set(sub_graph.nodes.keys()),
                successors=sub_graph.successors,
                predecessors=sub_graph.predecessors,
                logger=logger,
            )
            # Latch sinks are original latch IDs still present as keys in the subgraph
            current_latch_sinks = original_latch_ids & set(sub_graph.nodes.keys())
            # First try standard BlockNode-only reduction, then body-specific RegionNode reduction
            collapsed_cond = try_conditional_reduction(sub_graph, sub_ipdom, logger)
            if not collapsed_cond:
                collapsed_cond = try_conditional_reduction_body(
                    sub_graph, sub_ipdom, logger, latch_sinks=current_latch_sinks
                )
            if collapsed_cond:
                continue
            else:
                break


        # Extract structured loop body node
        remaining_ids = sorted(list(sub_graph.nodes.keys()))
        if len(sub_graph.nodes) != 1:
            logger.info(
                f"Rejecting loop candidate at header {h}: loop body did not reduce to a single structured root"
            )
            continue

        body_node = sub_graph.nodes[remaining_ids[0]]

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
