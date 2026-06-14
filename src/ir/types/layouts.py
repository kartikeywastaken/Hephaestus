# -*- coding: utf-8 -*-
"""
Phase 4C: Conservative Data Layout Recovery — Data Models

Defines the canonical model classes used by the Phase 4C layout recovery
backbone.  All models support deterministic to_dict() serialization.

Design rules
------------
- No structs are emitted.
- No field names are emitted.
- No C source code is emitted.
- Confidence scoring is out of scope for Phase 4C.
- Unbound memory accesses are explicitly captured in ``unbound_memory_accesses``.
- Every claim must be backed by real instruction evidence from the Unified IR.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Layout classification constants
# ---------------------------------------------------------------------------

LAYOUT_SCALAR       = "scalar"
LAYOUT_ARRAY_LIKE   = "array_like"
LAYOUT_RECORD_LIKE  = "record_like"
LAYOUT_POINTER_LIKE = "pointer_like"
LAYOUT_UNKNOWN      = "unknown"

_VALID_LAYOUT_KINDS = frozenset({
    LAYOUT_SCALAR,
    LAYOUT_ARRAY_LIKE,
    LAYOUT_RECORD_LIKE,
    LAYOUT_POINTER_LIKE,
    LAYOUT_UNKNOWN,
})

# Access kind constants
ACCESS_LOAD  = "load"
ACCESS_STORE = "store"


# ---------------------------------------------------------------------------
# MemoryAccessFact
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MemoryAccessFact:
    """
    A single observed memory access collected from the Unified IR.

    Attributes
    ----------
    function_entry : Entry point address of the containing function.
    function_name  : Name of the containing function.
    block_id       : Identifier of the basic block.
    instr_address  : Address of the instruction.
    base_id        : Normalized base register / global symbol string.
    offset         : Integer byte offset from the base, or None if unknown.
    size_bytes     : Width of the access in bytes, or None if unknown.
    access_kind    : ``"load"`` or ``"store"``.
    """
    function_entry: str
    function_name: str
    block_id: str
    instr_address: str
    base_id: str
    offset: Optional[int]
    size_bytes: Optional[int]
    access_kind: str  # ACCESS_LOAD | ACCESS_STORE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function_entry": self.function_entry,
            "function_name": self.function_name,
            "block_id": self.block_id,
            "instr_address": self.instr_address,
            "base_id": self.base_id,
            "offset": self.offset,
            "size_bytes": self.size_bytes,
            "access_kind": self.access_kind,
        }


# ---------------------------------------------------------------------------
# LayoutCandidate
# ---------------------------------------------------------------------------

@dataclass
class LayoutCandidate:
    """
    A conservative layout candidate inferred from a group of MemoryAccessFacts
    that share the same (function_entry, base_id).

    Attributes
    ----------
    function_entry   : Entry point of the owning function.
    function_name    : Name of the owning function.
    base_id          : Normalized base for this layout group (e.g. "sp", "x19").
    layout_kind      : One of the LAYOUT_* constants.
    observed_offsets : Sorted list of distinct integer byte offsets observed.
    min_offset       : Smallest observed offset (or None).
    max_offset       : Largest observed offset (or None).
    observed_sizes   : Sorted list of distinct size_bytes values seen.
    access_count     : Total number of MemoryAccessFacts in this group.
    evidence_notes   : Human-readable notes describing the basis for the claim.
    source_instrs    : Sorted list of instruction addresses that contributed.
    """
    function_entry: str
    function_name: str
    base_id: str
    layout_kind: str
    observed_offsets: List[int] = field(default_factory=list)
    min_offset: Optional[int] = None
    max_offset: Optional[int] = None
    observed_sizes: List[int] = field(default_factory=list)
    access_count: int = 0
    evidence_notes: List[str] = field(default_factory=list)
    source_instrs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function_entry": self.function_entry,
            "function_name": self.function_name,
            "base_id": self.base_id,
            "layout_kind": self.layout_kind,
            "observed_offsets": list(self.observed_offsets),
            "min_offset": self.min_offset,
            "max_offset": self.max_offset,
            "observed_sizes": list(self.observed_sizes),
            "access_count": self.access_count,
            "evidence_notes": list(self.evidence_notes),
            "source_instrs": list(self.source_instrs),
        }
