# -*- coding: utf-8 -*-
"""
Phase 3B: Structured Region Node Models
"""

from typing import List, Optional

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
    """
    def __init__(self, children: List[RegionNode]):
        self.children = children

    @property
    def node_id(self) -> str:
        return self.children[0].node_id if self.children else "empty_unstructured"

    def to_dict(self) -> dict:
        return {
            "type": "unstructured",
            "children": [c.to_dict() for c in self.children]
        }
