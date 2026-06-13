# -*- coding: utf-8 -*-
"""
Phase 3D: Hard-Case Classification Helpers

This module is *pure classification only* — it never modifies the reduction
graph.  It is called by builder.py after all structuring passes have reached
fixpoint on a function that did not collapse to a single root node.

Detection order (decreasing specificity):
  1. detect_switch_fanout      — BlockNode with >= 3 successors
  2. detect_multi_exit_loop    — cyclic region with >= 2 exits outside the loop
  3. detect_cyclic_hard_region — any remaining back-edge (generic cyclic hard)
  4. detect_fragmented         — no back-edges but multiple roots remain
  5. fallback: ("partial_reduction", "acyclic")
"""

import logging
from typing import Dict, List, Optional, Set, Tuple

from src.ir.structuring.models import (
    BlockNode,
    RegionNode,
    REASON_FRAGMENTED_LOOP_BODY,
    REASON_IRREDUCIBLE_CFG,
    REASON_MULTI_EXIT_LOOP,
    REASON_PARTIAL_REDUCTION,
    REASON_SWITCH_CANDIDATE,
    REGION_KIND_ACYCLIC,
    REGION_KIND_CYCLIC,
    REGION_KIND_SWITCH_CANDIDATE,
)
from src.ir.structuring.reducers import ReductionGraph


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _remaining_back_edges(graph: ReductionGraph) -> List[Tuple[str, str]]:
    """
    Detect back-edges in the remaining reduced graph using a lightweight DFS
    colouring (grey/black) from the entry node.

    Returns a list of (tail, head) pairs where head is an ancestor of tail
    in the DFS spanning tree — i.e. a back-edge.
    """
    WHITE, GREY, BLACK = 0, 1, 2
    colour: Dict[str, int] = {nid: WHITE for nid in graph.nodes}
    back_edges: List[Tuple[str, str]] = []

    def _dfs(u: str) -> None:
        colour[u] = GREY
        for v in sorted(graph.successors.get(u, [])):
            if v not in graph.nodes:
                continue
            if colour[v] == GREY:
                back_edges.append((u, v))
            elif colour[v] == WHITE:
                _dfs(v)
        colour[u] = BLACK

    # Start from entry; then sweep any unreachable nodes for completeness.
    if graph.entry_node_id in graph.nodes:
        _dfs(graph.entry_node_id)
    for nid in sorted(graph.nodes):
        if colour.get(nid, WHITE) == WHITE:
            _dfs(nid)

    return back_edges


def _candidate_loop_body(graph: ReductionGraph, head: str, tail: str) -> Set[str]:
    """
    Build the natural loop body for back-edge (tail -> head) by walking
    predecessors backwards from tail up to head (inclusive).
    """
    body: Set[str] = {head}
    worklist = [tail]
    body.add(tail)
    while worklist:
        n = worklist.pop()
        if n == head:
            continue
        for p in graph.predecessors.get(n, []):
            if p in graph.nodes and p not in body:
                body.add(p)
                worklist.append(p)
    return body


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

def detect_switch_fanout(
    graph: ReductionGraph, logger: logging.Logger
) -> Optional[Tuple[str, str]]:
    """
    Classify the remaining graph as switch-like when any *BlockNode* has
    out-degree >= 3.  This conservative rule fires before any branch-reduction
    has had a chance to collapse these nodes, meaning they are genuinely
    unreduced high-arity branches — not normal binary if/else.

    Returns ("switch_candidate", "switch_candidate") or None.
    """
    for nid in sorted(graph.nodes):
        node = graph.nodes[nid]
        if isinstance(node, BlockNode):
            succs = graph.successors.get(nid, [])
            if len(succs) >= 3:
                logger.info(
                    f"Detected switch-like fan-out at node {nid} "
                    f"(out-degree={len(succs)})"
                )
                return (REASON_SWITCH_CANDIDATE, REGION_KIND_SWITCH_CANDIDATE)
    return None


def detect_multi_exit_loop(
    graph: ReductionGraph, logger: logging.Logger
) -> Optional[Tuple[str, str]]:
    """
    Classify the remaining graph as a multi-exit loop when:
    - at least one back-edge (cycle) exists
    - at least one candidate natural loop has >= 2 exit targets that are
      *outside* the accepted loop region

    Returns ("multi_exit_loop", "cyclic") or None.
    """
    back_edges = _remaining_back_edges(graph)
    if not back_edges:
        return None

    # Group by header (back-edge target)
    header_to_tails: Dict[str, List[str]] = {}
    for tail, head in back_edges:
        header_to_tails.setdefault(head, []).append(tail)

    for head, tails in sorted(header_to_tails.items()):
        # Build natural loop body for this header
        body: Set[str] = {head}
        for tail in tails:
            body |= _candidate_loop_body(graph, head, tail)

        # Count distinct exit targets outside the loop body
        exit_targets: Set[str] = set()
        for nid in body:
            for succ in graph.successors.get(nid, []):
                if succ not in body:
                    exit_targets.add(succ)

        if len(exit_targets) >= 2:
            logger.info(
                f"Classified remaining cyclic region as multi_exit_loop "
                f"(header={head}, exits={sorted(exit_targets)})"
            )
            return (REASON_MULTI_EXIT_LOOP, REGION_KIND_CYCLIC)

    return None


def detect_cyclic_hard_region(
    graph: ReductionGraph, logger: logging.Logger
) -> Optional[Tuple[str, str]]:
    """
    Generic cyclic-hard-region fallback: any remaining back-edge that did not
    qualify as multi_exit_loop.

    Returns ("irreducible_cfg", "cyclic") or None.
    """
    back_edges = _remaining_back_edges(graph)
    if back_edges:
        logger.info(
            f"Classified remaining reduced graph as irreducible_cfg "
            f"(back-edges: {back_edges})"
        )
        return (REASON_IRREDUCIBLE_CFG, REGION_KIND_CYCLIC)
    return None


def detect_fragmented(
    graph: ReductionGraph, logger: logging.Logger
) -> Optional[Tuple[str, str]]:
    """
    Fragmented acyclic fallback: no back-edges remain but multiple nodes were
    not collapsed.

    Returns ("fragmented_loop_body", "acyclic") or None.
    """
    back_edges = _remaining_back_edges(graph)
    if not back_edges and len(graph.nodes) > 1:
        logger.info(
            f"Classified remaining reduced graph as fragmented_loop_body "
            f"({len(graph.nodes)} residual nodes, no back-edges)"
        )
        return (REASON_FRAGMENTED_LOOP_BODY, REGION_KIND_ACYCLIC)
    return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def classify_unstructured_region(
    graph: ReductionGraph, logger: logging.Logger
) -> Tuple[str, str]:
    """
    Inspect the final reduced graph and classify why it remained unstructured.

    Detection order (decreasing specificity):
      1. switch fan-out
      2. multi-exit loop
      3. generic cyclic hard region
      4. fragmented acyclic
      5. partial_reduction catch-all

    Returns (reason, region_kind) — both are string constants from models.py.
    """
    result = detect_switch_fanout(graph, logger)
    if result:
        return result

    result = detect_multi_exit_loop(graph, logger)
    if result:
        return result

    result = detect_cyclic_hard_region(graph, logger)
    if result:
        return result

    result = detect_fragmented(graph, logger)
    if result:
        return result

    logger.info(
        f"Falling back to partial_reduction classification "
        f"({len(graph.nodes)} residual nodes)"
    )
    return (REASON_PARTIAL_REDUCTION, REGION_KIND_ACYCLIC)
