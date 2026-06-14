# -*- coding: utf-8 -*-
"""
Phase 4C: Conservative Data Layout Recovery Engine

Walks the Unified IR instruction stream to collect MemoryAccessFacts from
structured memory operands, groups them by (function_entry, base_id), and
classifies each group as a conservative LayoutCandidate.

Core rules
----------
- Only structured memory operands (kind == "memory") with a non-empty
  ``base`` field produce MemoryAccessFacts.
- Raw register/immediate/symbol/unknown operands are never interpreted as
  memory accesses.
- Cross-block register binding is explicitly forbidden; base_id is taken
  directly from the memory operand's ``base`` field only.
- Unbound memory accesses (no known stack variable at that offset, or non-stack
  base) are captured in ``unbound_memory_accesses`` and never silently dropped.
- No structs are emitted. No field names are emitted. No C source is emitted.
- Confidence scoring is out of scope for Phase 4C.
- Output is deterministic: sorted by (function_entry, function_name, base_id,
  offset, instr_address).

Classification heuristics (conservative)
-----------------------------------------
- ``scalar``      : exactly one distinct offset, exactly one distinct size.
- ``array_like``  : two or more accesses, offsets form a regular stride pattern
                    (all gaps between sorted offsets are equal and > 0),
                    and only one distinct size value is observed.
- ``record_like`` : two or more distinct offsets that are NOT a regular stride,
                    OR multiple distinct sizes observed.
- ``pointer_like``: exactly one offset, size == 8 or size == 4 (pointer-width),
                    and there is evidence of a load followed by another dereference
                    (currently: size == pointer-width at a single offset).
- ``unknown``     : anything else.

These rules are CONSERVATIVE. We prefer false-negative (unknown) over
false-positive (wrong classification).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, FrozenSet, Iterator, List, Optional, Set, Tuple

from src.ir.types.bindings import normalize_register_name
from src.ir.types.layouts import (
    ACCESS_LOAD,
    ACCESS_STORE,
    LAYOUT_ARRAY_LIKE,
    LAYOUT_POINTER_LIKE,
    LAYOUT_RECORD_LIKE,
    LAYOUT_SCALAR,
    LAYOUT_UNKNOWN,
    LayoutCandidate,
    MemoryAccessFact,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Opcode sets
# ---------------------------------------------------------------------------

_LOAD_OPCODES = frozenset({
    "ldr", "ldrb", "ldrh", "ldrsb", "ldrsh", "ldrsw",
    "ldr.w", "load",
})
_STORE_OPCODES = frozenset({
    "str", "strb", "strh", "str.w", "store",
})

# Pointer widths considered for pointer_like classification (64-bit only, conservative)
_POINTER_WIDTHS: FrozenSet[int] = frozenset({8})

# Minimum stride for array_like detection (prevent stride-0 false positives)
_MIN_STRIDE = 1


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _access_kind_for_opcode(opcode: str) -> Optional[str]:
    """Return ACCESS_LOAD, ACCESS_STORE, or None for non-memory opcodes."""
    o = opcode.strip().lower()
    if o in _LOAD_OPCODES:
        return ACCESS_LOAD
    if o in _STORE_OPCODES:
        return ACCESS_STORE
    return None


def _iter_memory_operands(operands: Any) -> Iterator[dict]:
    """Yield memory operand dicts from an operand list."""
    if not isinstance(operands, list):
        return
    for op in operands:
        if isinstance(op, dict) and op.get("kind") == "memory":
            base = op.get("base", "")
            if base:
                yield op


def _safe_int(value: Any) -> Optional[int]:
    """Convert value to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Fact collection
# ---------------------------------------------------------------------------

def collect_memory_access_facts(unified_ir: Dict[str, Any]) -> List[MemoryAccessFact]:
    """
    Walk the Unified IR and collect one MemoryAccessFact per structured
    memory operand found in load/store instructions.

    Parameters
    ----------
    unified_ir : The Unified IR dict (Phase 2 output).

    Returns
    -------
    list[MemoryAccessFact]
        Sorted by (function_entry, function_name, block_id, instr_address,
        base_id, offset).  Stable for determinism.
    """
    if not isinstance(unified_ir, dict):
        return []

    ir_functions = []
    try:
        ir_functions = unified_ir["data"]["functions"]
    except (KeyError, TypeError):
        ir_functions = unified_ir.get("functions", [])

    if not isinstance(ir_functions, list):
        return []

    facts: List[MemoryAccessFact] = []

    for fn in ir_functions:
        if not isinstance(fn, dict):
            continue

        from src.ir.utils.addressing import normalize_address
        fn_entry = normalize_address(fn.get("entry_point")) or "unknown"
        fn_name = str(fn.get("name", "unknown_function"))

        for block in fn.get("basic_blocks", []):
            if not isinstance(block, dict):
                continue

            block_id = normalize_address(block.get("id") or block.get("start")) or "unknown_block"

            for instr in block.get("instructions", []):
                if not isinstance(instr, dict):
                    continue

                opcode_raw = instr.get("opcode") or instr.get("mnemonic") or ""
                if not opcode_raw:
                    continue

                access_kind = _access_kind_for_opcode(str(opcode_raw))
                if access_kind is None:
                    continue  # Not a memory instruction we care about

                instr_addr = normalize_address(instr.get("address")) or "?"
                size_bytes = _safe_int(instr.get("size_bytes"))

                operands = instr.get("operands", [])
                for mem_op in _iter_memory_operands(operands):
                    base_raw = str(mem_op.get("base", ""))
                    if not base_raw:
                        continue

                    base_id = normalize_register_name(base_raw)
                    offset = _safe_int(mem_op.get("offset"))
                    # Prefer operand-level size_bytes when present
                    op_size = _safe_int(mem_op.get("size_bytes")) or size_bytes

                    fact = MemoryAccessFact(
                        function_entry=fn_entry,
                        function_name=fn_name,
                        block_id=block_id,
                        instr_address=instr_addr,
                        base_id=base_id,
                        offset=offset,
                        size_bytes=op_size,
                        access_kind=access_kind,
                    )
                    facts.append(fact)
                    logger.debug(
                        "Collected MemoryAccessFact: fn=%s base=%s offset=%s size=%s kind=%s",
                        fn_name, base_id, offset, op_size, access_kind,
                    )

    # Deterministic sort
    facts.sort(key=lambda f: (
        f.function_entry,
        f.function_name,
        f.block_id,
        f.instr_address,
        f.base_id,
        f.offset if f.offset is not None else 0,
    ))
    return facts


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def _classify_access_kind(
    offsets: List[int],
    sizes: List[int],
) -> str:
    """
    Classify a group of accesses sharing the same (function_entry, base_id).

    Parameters
    ----------
    offsets : Sorted list of distinct integer offsets (may be empty).
    sizes   : Sorted list of distinct size_bytes values (may be empty).

    Returns
    -------
    str
        One of the LAYOUT_* constants.
    """
    n_offsets = len(offsets)
    n_sizes = len(sizes)

    # Degenerate: no useful data
    if n_offsets == 0:
        return LAYOUT_UNKNOWN

    # Single offset
    if n_offsets == 1:
        off = offsets[0]
        if n_sizes == 1 and sizes[0] in _POINTER_WIDTHS:
            # One access at one offset with pointer-width size → pointer_like
            return LAYOUT_POINTER_LIKE
        if n_sizes <= 1:
            return LAYOUT_SCALAR
        # Multiple sizes at the same offset → ambiguous; keep unknown
        return LAYOUT_UNKNOWN

    # Multiple offsets
    if n_offsets >= 2:
        # Check for regular stride (array_like)
        gaps = [offsets[i] - offsets[i - 1] for i in range(1, n_offsets)]
        all_same_stride = (len(set(gaps)) == 1 and gaps[0] >= _MIN_STRIDE)

        if all_same_stride and n_sizes == 1:
            return LAYOUT_ARRAY_LIKE

        # Non-regular stride or multiple sizes → record_like
        return LAYOUT_RECORD_LIKE

    return LAYOUT_UNKNOWN


# ---------------------------------------------------------------------------
# Grouping and candidate building
# ---------------------------------------------------------------------------

def build_layout_candidates(
    facts: List[MemoryAccessFact],
) -> Tuple[List[LayoutCandidate], List[MemoryAccessFact]]:
    """
    Group MemoryAccessFacts by (function_entry, base_id) and build conservative
    LayoutCandidate objects.

    Facts whose ``offset`` is None are treated as unbound and excluded from
    candidate construction but returned separately.

    Parameters
    ----------
    facts : All collected MemoryAccessFacts.

    Returns
    -------
    tuple[list[LayoutCandidate], list[MemoryAccessFact]]
        (layout_candidates, unbound_facts)

        ``layout_candidates`` is sorted by (function_entry, function_name, base_id).
        ``unbound_facts`` contains facts with offset == None.
    """
    # Separate bound vs unbound
    bound: List[MemoryAccessFact] = []
    unbound: List[MemoryAccessFact] = []
    for fact in facts:
        if fact.offset is not None:
            bound.append(fact)
        else:
            unbound.append(fact)

    # Group bound facts by (function_entry, base_id)
    groups: Dict[Tuple[str, str], List[MemoryAccessFact]] = {}
    for fact in bound:
        key = (fact.function_entry, fact.base_id)
        groups.setdefault(key, []).append(fact)

    candidates: List[LayoutCandidate] = []

    for (fn_entry, base_id), group_facts in sorted(groups.items()):
        # Use the name from the first fact (all share the same function_entry)
        fn_name = group_facts[0].function_name

        # Collect distinct offsets and sizes
        offsets_set: Set[int] = set()
        sizes_set: Set[int] = set()
        instr_addrs: Set[str] = set()

        for f in group_facts:
            offsets_set.add(f.offset)  # type: ignore[arg-type]  # None already excluded
            if f.size_bytes is not None:
                sizes_set.add(f.size_bytes)
            instr_addrs.add(f.instr_address)

        sorted_offsets = sorted(offsets_set)
        sorted_sizes = sorted(sizes_set)

        min_off = sorted_offsets[0] if sorted_offsets else None
        max_off = sorted_offsets[-1] if sorted_offsets else None

        layout_kind = _classify_access_kind(sorted_offsets, sorted_sizes)

        # Build evidence note
        note = (
            f"{len(group_facts)} memory access(es) observed at base {base_id!r} "
            f"in function {fn_name!r}; "
            f"offsets={sorted_offsets}; sizes={sorted_sizes}; "
            f"classification={layout_kind}"
        )

        candidate = LayoutCandidate(
            function_entry=fn_entry,
            function_name=fn_name,
            base_id=base_id,
            layout_kind=layout_kind,
            observed_offsets=sorted_offsets,
            min_offset=min_off,
            max_offset=max_off,
            observed_sizes=sorted_sizes,
            access_count=len(group_facts),
            evidence_notes=[note],
            source_instrs=sorted(instr_addrs),
        )
        candidates.append(candidate)
        logger.debug(
            "LayoutCandidate: fn=%s base=%s kind=%s offsets=%s",
            fn_name, base_id, layout_kind, sorted_offsets,
        )

    # Sort deterministically
    candidates.sort(key=lambda c: (c.function_entry, c.function_name, c.base_id))
    return candidates, unbound


# ---------------------------------------------------------------------------
# High-level engine entry point
# ---------------------------------------------------------------------------

class LayoutRecoveryEngine:
    """
    Phase 4C layout recovery engine.

    Usage
    -----
    engine = LayoutRecoveryEngine()
    candidates, unbound = engine.recover(unified_ir)
    """

    def recover(
        self,
        unified_ir: Dict[str, Any],
    ) -> Tuple[List[LayoutCandidate], List[MemoryAccessFact]]:
        """
        Run Phase 4C layout recovery on a Unified IR dict.

        Parameters
        ----------
        unified_ir : The Unified IR dict (Phase 2 output).

        Returns
        -------
        tuple[list[LayoutCandidate], list[MemoryAccessFact]]
            (layout_candidates, unbound_memory_accesses)
        """
        facts = collect_memory_access_facts(unified_ir)
        candidates, unbound = build_layout_candidates(facts)

        logger.info(
            "Phase 4C: collected %d facts → %d layout candidates, %d unbound.",
            len(facts), len(candidates), len(unbound),
        )
        return candidates, unbound
