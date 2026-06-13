# -*- coding: utf-8 -*-
"""
Phase 3B/3D: Structured Region Node Models
"""

from typing import List, Optional

# ---------------------------------------------------------------------------
# Fallback reason constants (Phase 3D)
# These are diagnostic metadata only — they do not affect reduction behaviour.
# ---------------------------------------------------------------------------
REASON_IRREDUCIBLE_CFG      = "irreducible_cfg"
REASON_MULTI_EXIT_LOOP      = "multi_exit_loop"
REASON_FRAGMENTED_LOOP_BODY = "fragmented_loop_body"
REASON_SWITCH_CANDIDATE     = "switch_candidate"
REASON_PARTIAL_REDUCTION    = "partial_reduction"

REGION_KIND_CYCLIC           = "cyclic"
REGION_KIND_ACYCLIC          = "acyclic"
REGION_KIND_SWITCH_CANDIDATE = "switch_candidate"

class RegionNode:
    """
    Abstract base class representing a structured control-flow region.
    """
    @property
    def node_id(self) -> str:
        raise NotImplementedError

    def to_dict(self) -> dict:
        raise NotImplementedError

class BlockNode(RegionNode):
    """
    Wraps a raw basic block ID.
    """
    def __init__(self, block_id: str):
        self.block_id = block_id

    @property
    def node_id(self) -> str:
        return self.block_id

    def to_dict(self) -> dict:
        return {
            "type": "block",
            "id": self.block_id
        }

class SequenceNode(RegionNode):
    """
    Groups sequential nodes.
    """
    def __init__(self, children: List[RegionNode]):
        self.children = children

    @property
    def node_id(self) -> str:
        return self.children[0].node_id if self.children else "empty_sequence"

    def to_dict(self) -> dict:
        return {
            "type": "sequence",
            "children": [c.to_dict() for c in self.children]
        }

class IfNode(RegionNode):
    """
    Groups a single-branch conditional node.
    """
    def __init__(self, condition_block: str, then_branch: RegionNode, merge_block: Optional[str]):
        self.condition_block = condition_block
        self.then_branch = then_branch
        self.merge_block = merge_block

    @property
    def node_id(self) -> str:
        return self.condition_block

    def to_dict(self) -> dict:
        return {
            "type": "if",
            "condition_block": self.condition_block,
            "then_branch": self.then_branch.to_dict(),
            "merge_block": self.merge_block
        }

class IfElseNode(RegionNode):
    """
    Groups a double-branch conditional node.
    """
    def __init__(self, condition_block: str, then_branch: RegionNode, else_branch: RegionNode, merge_block: Optional[str]):
        self.condition_block = condition_block
        self.then_branch = then_branch
        self.else_branch = else_branch
        self.merge_block = merge_block

    @property
    def node_id(self) -> str:
        return self.condition_block

    def to_dict(self) -> dict:
        return {
            "type": "if_else",
            "condition_block": self.condition_block,
            "then_branch": self.then_branch.to_dict(),
            "else_branch": self.else_branch.to_dict(),
            "merge_block": self.merge_block
        }

class UnstructuredRegionNode(RegionNode):
    """
    Explicit fallback wrapper for partially structured or irreducible graphs.

    Parameters
    ----------
    children     : The ordered list of remaining RegionNodes.
    reason       : Diagnostic classification string (Phase 3D), e.g.
                   REASON_IRREDUCIBLE_CFG.  Does not affect graph semantics.
    region_kind  : Broad shape descriptor, e.g. REGION_KIND_CYCLIC.  Same.
    """
    def __init__(
        self,
        children: List[RegionNode],
        reason: Optional[str] = None,
        region_kind: Optional[str] = None,
    ):
        self.children = children
        self.reason = reason
        self.region_kind = region_kind

    @property
    def node_id(self) -> str:
        return self.children[0].node_id if self.children else "empty_unstructured"

    def to_dict(self) -> dict:
        d: dict = {
            "type": "unstructured",
            "children": [c.to_dict() for c in self.children],
        }
        if self.reason is not None:
            d["reason"] = self.reason
        if self.region_kind is not None:
            d["region_kind"] = self.region_kind
        return d

class LoopNode(RegionNode):
    """
    Groups a structured loop region associated with a loop header.
    """
    def __init__(self, kind: str, header_block: str, body: RegionNode, exit_blocks: List[str]):
        self.kind = kind
        self.header_block = header_block
        self.body = body
        self.exit_blocks = exit_blocks

    @property
    def node_id(self) -> str:
        return self.header_block

    def to_dict(self) -> dict:
        return {
            "type": "loop",
            "kind": self.kind,
            "header_block": self.header_block,
            "body": self.body.to_dict(),
            "exit_blocks": sorted(self.exit_blocks)
        }

