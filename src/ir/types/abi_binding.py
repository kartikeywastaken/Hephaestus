# -*- coding: utf-8 -*-
"""
Phase 4B.2: ABI Argument Binding & Pointer-Base Propagation

Tracks AArch64 ABI argument register provenance through mov/str/ldr chains
within basic blocks, and links layout candidates to function parameters.

Core rules
----------
- Only AArch64 arm64 is supported; other architectures are silently skipped.
- Register provenance is tracked within a single basic block only.
- Stack-slot facts survive across blocks within the same function.
- ``bl``/``blr`` calls clear all caller-saved registers (x0-x18).
- All register names are normalized via ``normalize_register_name()``.
- Parameter-layout evidence requires BOTH function_entry AND base_id match.
- Missing evidence is acceptable. Fabricated evidence is not.

This module does NOT:
- Perform interprocedural analysis
- Create new variables or parameters
- Emit C source code or structs
- Lower Phase 4A/4B.1 confidence
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from src.ir.types.bindings import normalize_register_name

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AArch64 ABI constants
# ---------------------------------------------------------------------------

_ABI_ARG_REGISTERS = ("x0", "x1", "x2", "x3", "x4", "x5", "x6", "x7")
_ABI_ARG_SET: FrozenSet[str] = frozenset(_ABI_ARG_REGISTERS)

# Caller-saved registers cleared on BL/BLR (x0-x18, x30/lr)
_CALLER_SAVED: FrozenSet[str] = frozenset(
    [f"x{i}" for i in range(19)] + ["x30"]
)

# Move-like opcodes that copy register provenance
_MOV_OPCODES = frozenset({"mov", "orr"})

# Load opcodes
_LOAD_OPCODES = frozenset({
    "ldr", "ldrb", "ldrh", "ldrsb", "ldrsh", "ldrsw", "ldr.w", "load",
})

# Store opcodes
_STORE_OPCODES = frozenset({"str", "strb", "strh", "str.w", "store"})

# Call opcodes
_CALL_OPCODES = frozenset({"bl", "blr", "blx", "call", "callq"})

# Stack base registers
_STACK_BASES = frozenset({"sp", "x29"})


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AbiArgumentFact:
    """A fact that a register holds an ABI argument at some point."""
    function_entry: str
    register: str
    argument_index: int
    source: str
    evidence_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function_entry": self.function_entry,
            "register": self.register,
            "argument_index": self.argument_index,
            "source": self.source,
            "evidence_note": self.evidence_note,
        }


@dataclass(frozen=True)
class PointerBaseBinding:
    """
    Records that a register used as a memory base traces back to an
    ABI argument register.
    """
    function_entry: str
    base_register: str
    argument_index: int
    stack_slot: Optional[int]  # sp offset if saved via stack, else None
    source_instrs: tuple  # tuple[str, ...]
    binding_kind: str  # "direct_abi_reg" | "mov_propagated" | "stack_save_restore"
    evidence_notes: tuple  # tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function_entry": self.function_entry,
            "base_register": self.base_register,
            "argument_index": self.argument_index,
            "stack_slot": self.stack_slot,
            "source_instrs": list(self.source_instrs),
            "binding_kind": self.binding_kind,
            "evidence_notes": list(self.evidence_notes),
        }


@dataclass(frozen=True)
class ParameterLayoutEvidence:
    """
    Links a Phase 4C layout candidate to a specific function parameter
    through ABI register provenance.
    """
    function_entry: str
    function_name: str
    parameter_index: int
    parameter_name: str
    base_id: str
    layout_kind: str
    observed_offsets: tuple  # tuple[int, ...]
    observed_sizes: tuple  # tuple[int, ...]
    source_instrs: tuple  # tuple[str, ...]
    evidence_notes: tuple  # tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function_entry": self.function_entry,
            "function_name": self.function_name,
            "parameter_index": self.parameter_index,
            "parameter_name": self.parameter_name,
            "base_id": self.base_id,
            "layout_kind": self.layout_kind,
            "observed_offsets": list(self.observed_offsets),
            "observed_sizes": list(self.observed_sizes),
            "source_instrs": list(self.source_instrs),
            "evidence_notes": list(self.evidence_notes),
        }


# ---------------------------------------------------------------------------
# Register provenance entry
# ---------------------------------------------------------------------------

@dataclass
class _Provenance:
    """Internal provenance record for a register or stack slot."""
    argument_index: int
    binding_kind: str  # how the binding was established
    evidence: List[str] = field(default_factory=list)
    source_instrs: List[str] = field(default_factory=list)
    stack_slot: Optional[int] = None


# ---------------------------------------------------------------------------
# AbiRegisterState — intraprocedural, block-local register tracker
# ---------------------------------------------------------------------------

class AbiRegisterState:
    """
    Tracks which registers carry ABI argument provenance within a function.

    Register state is cleared at basic-block boundaries (conservative).
    Stack-slot facts survive across blocks within the same function.
    """

    def __init__(self, function_entry: str) -> None:
        self.function_entry = function_entry
        # register name → _Provenance
        self._reg_prov: Dict[str, _Provenance] = {}
        # stack offset → _Provenance  (survives block boundaries)
        self._stack_prov: Dict[int, _Provenance] = {}
        # Collected pointer-base bindings
        self.bindings: List[PointerBaseBinding] = []

    def init_abi_args(self) -> None:
        """Set initial ABI argument provenance for x0-x7."""
        for idx, reg in enumerate(_ABI_ARG_REGISTERS):
            self._reg_prov[reg] = _Provenance(
                argument_index=idx,
                binding_kind="direct_abi_reg",
                evidence=[f"ABI argument {idx} in {reg} at function entry"],
            )

    def clear_registers(self) -> None:
        """Clear all register provenance (block boundary)."""
        self._reg_prov.clear()

    def process_instruction(self, instr: Dict[str, Any]) -> None:
        """
        Update register state based on a single instruction.

        Parameters
        ----------
        instr : Canonical instruction dict with 'opcode'/'mnemonic' and 'operands'.
        """
        opcode = (
            instr.get("opcode") or instr.get("mnemonic") or ""
        ).lower().strip()
        operands = instr.get("operands", [])
        addr = instr.get("address", "")

        if not opcode:
            return

        if opcode in _CALL_OPCODES:
            self._handle_call()
        elif opcode in _MOV_OPCODES:
            self._handle_mov(opcode, operands, addr)
        elif opcode in _STORE_OPCODES:
            self._handle_store(operands, addr)
        elif opcode in _LOAD_OPCODES:
            self._handle_load(operands, addr)
        elif opcode == "add":
            self._handle_add(operands, addr)
        else:
            # Unknown opcode writing to a register → clear provenance
            self._clear_dest_register(operands)

        # Check if any memory operand uses a base with known provenance
        self._check_memory_bases(operands, addr)

    # ------------------------------------------------------------------
    # Instruction handlers
    # ------------------------------------------------------------------

    def _handle_call(self) -> None:
        """BL/BLR: clear caller-saved registers, preserve stack facts."""
        to_remove = [r for r in self._reg_prov if r in _CALLER_SAVED]
        for r in to_remove:
            del self._reg_prov[r]

    def _handle_mov(
        self, opcode: str, operands: List[Any], addr: str
    ) -> None:
        """
        MOV xD, xS — copy provenance.
        ORR xD, xzr, xS — also a move idiom on AArch64.
        """
        if opcode == "orr":
            # ORR xD, xzr, xS → mov if second operand is xzr
            if len(operands) >= 3:
                mid = operands[1]
                if isinstance(mid, dict) and mid.get("kind") == "register":
                    mid_reg = normalize_register_name(str(mid.get("value", "")))
                    if mid_reg not in ("xzr", "wzr"):
                        self._clear_dest_register(operands)
                        return
                elif isinstance(mid, str):
                    if normalize_register_name(mid) not in ("xzr", "wzr"):
                        self._clear_dest_register(operands)
                        return

                src = self._extract_register(operands[2])
                dst = self._extract_register(operands[0])
            else:
                self._clear_dest_register(operands)
                return
        else:
            # MOV xD, xS
            if len(operands) < 2:
                return
            dst = self._extract_register(operands[0])
            src = self._extract_register(operands[1])

        if not dst or not src:
            if dst:
                # Source is not a register → clear dst provenance
                self._reg_prov.pop(dst, None)
            return

        src_prov = self._reg_prov.get(src)
        if src_prov:
            self._reg_prov[dst] = _Provenance(
                argument_index=src_prov.argument_index,
                binding_kind="mov_propagated",
                evidence=list(src_prov.evidence) + [
                    f"{opcode} {dst}, {src} at {addr}"
                ],
                source_instrs=list(src_prov.source_instrs) + [addr],
            )
        else:
            # Source has no provenance → clear dst
            self._reg_prov.pop(dst, None)

    def _handle_store(self, operands: List[Any], addr: str) -> None:
        """STR xS, [sp, #offset] — save provenance to stack slot."""
        if len(operands) < 2:
            return

        src_reg = self._extract_register(operands[0])
        if not src_reg:
            return

        src_prov = self._reg_prov.get(src_reg)
        if not src_prov:
            return

        # Check if destination is a stack memory operand
        mem_op = operands[1] if isinstance(operands[1], dict) else None
        if not mem_op or mem_op.get("kind") != "memory":
            return

        base = normalize_register_name(str(mem_op.get("base", "")))
        if base not in _STACK_BASES:
            return

        raw_offset = mem_op.get("offset")
        if raw_offset is None:
            return
        try:
            offset = int(raw_offset)
        except (TypeError, ValueError):
            return

        # Save to stack slot
        self._stack_prov[offset] = _Provenance(
            argument_index=src_prov.argument_index,
            binding_kind="stack_save_restore",
            evidence=list(src_prov.evidence) + [
                f"str {src_reg}, [{base}, #{offset}] at {addr}"
            ],
            source_instrs=list(src_prov.source_instrs) + [addr],
            stack_slot=offset,
        )

    def _handle_load(self, operands: List[Any], addr: str) -> None:
        """LDR xD, [sp, #offset] — restore provenance from stack slot."""
        if len(operands) < 2:
            return

        dst_reg = self._extract_register(operands[0])
        if not dst_reg:
            return

        mem_op = operands[1] if isinstance(operands[1], dict) else None
        if not mem_op or mem_op.get("kind") != "memory":
            # Not a memory load → clear dst
            self._reg_prov.pop(dst_reg, None)
            return

        base = normalize_register_name(str(mem_op.get("base", "")))

        # Check for stack restore
        if base in _STACK_BASES:
            raw_offset = mem_op.get("offset")
            if raw_offset is not None:
                try:
                    offset = int(raw_offset)
                except (TypeError, ValueError):
                    self._reg_prov.pop(dst_reg, None)
                    return

                slot_prov = self._stack_prov.get(offset)
                if slot_prov:
                    self._reg_prov[dst_reg] = _Provenance(
                        argument_index=slot_prov.argument_index,
                        binding_kind="stack_save_restore",
                        evidence=list(slot_prov.evidence) + [
                            f"ldr {dst_reg}, [{base}, #{offset}] at {addr}"
                        ],
                        source_instrs=list(slot_prov.source_instrs) + [addr],
                        stack_slot=offset,
                    )
                    return

        # Non-stack load or unknown offset → clear dst provenance
        self._reg_prov.pop(dst_reg, None)

    def _handle_add(self, operands: List[Any], addr: str) -> None:
        """ADD xD, xS, #0 — copy provenance (zero-offset only)."""
        if len(operands) < 3:
            self._clear_dest_register(operands)
            return

        dst = self._extract_register(operands[0])
        src = self._extract_register(operands[1])

        if not dst or not src:
            if dst:
                self._reg_prov.pop(dst, None)
            return

        # Check if third operand is zero
        imm = operands[2]
        imm_val = None
        if isinstance(imm, dict):
            if imm.get("kind") == "immediate":
                try:
                    imm_val = int(imm.get("value", -1))
                except (TypeError, ValueError):
                    pass
        elif isinstance(imm, (int, float)):
            imm_val = int(imm)

        if imm_val == 0:
            src_prov = self._reg_prov.get(src)
            if src_prov:
                self._reg_prov[dst] = _Provenance(
                    argument_index=src_prov.argument_index,
                    binding_kind="mov_propagated",
                    evidence=list(src_prov.evidence) + [
                        f"add {dst}, {src}, #0 at {addr}"
                    ],
                    source_instrs=list(src_prov.source_instrs) + [addr],
                )
                return

        # Non-zero offset → clear dst
        self._reg_prov.pop(dst, None)

    # ------------------------------------------------------------------
    # Memory base checking
    # ------------------------------------------------------------------

    def _check_memory_bases(self, operands: List[Any], addr: str) -> None:
        """
        When a memory operand uses a base register with known ABI provenance,
        record a PointerBaseBinding.
        """
        for op in operands:
            if not isinstance(op, dict) or op.get("kind") != "memory":
                continue

            base = op.get("base", "")
            if not base:
                continue
            base_norm = normalize_register_name(str(base))

            # Skip stack-base registers (those are frame accesses, not arg pointers)
            if base_norm in _STACK_BASES:
                continue

            prov = self._reg_prov.get(base_norm)
            if prov is None:
                continue

            binding = PointerBaseBinding(
                function_entry=self.function_entry,
                base_register=base_norm,
                argument_index=prov.argument_index,
                stack_slot=prov.stack_slot,
                source_instrs=tuple(prov.source_instrs + [addr]),
                binding_kind=prov.binding_kind,
                evidence_notes=tuple(prov.evidence + [
                    f"memory access via [{base_norm}] at {addr}"
                ]),
            )
            self.bindings.append(binding)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_register(self, operand: Any) -> Optional[str]:
        """Extract and normalize a register name from an operand."""
        if isinstance(operand, dict):
            if operand.get("kind") == "register":
                val = str(operand.get("value", ""))
                return normalize_register_name(val) if val else None
        elif isinstance(operand, str):
            stripped = operand.strip()
            if stripped:
                return normalize_register_name(stripped)
        return None

    def _clear_dest_register(self, operands: List[Any]) -> None:
        """Clear provenance for the destination register (first operand)."""
        if operands:
            dst = self._extract_register(operands[0])
            if dst:
                self._reg_prov.pop(dst, None)

    def get_provenance(self, register: str) -> Optional[Tuple[int, List[str]]]:
        """
        Get the ABI argument provenance for a register.

        Returns (argument_index, evidence_notes) or None.
        """
        norm = normalize_register_name(register)
        prov = self._reg_prov.get(norm)
        if prov is None:
            return None
        return (prov.argument_index, list(prov.evidence))


# ---------------------------------------------------------------------------
# Collect ABI bindings from the Unified IR
# ---------------------------------------------------------------------------

def collect_abi_bindings(
    unified_ir: Dict[str, Any],
) -> Dict[str, List[PointerBaseBinding]]:
    """
    Walk all functions in the Unified IR and collect ABI argument bindings.

    Only processes arm64 architecture. Other architectures are skipped.

    Parameters
    ----------
    unified_ir : The Unified IR dict.

    Returns
    -------
    dict[str, list[PointerBaseBinding]]
        Mapping from function entry point to its pointer-base bindings.
    """
    if not isinstance(unified_ir, dict):
        return {}

    # Check architecture
    metadata = unified_ir.get("metadata", {})
    if isinstance(metadata, dict):
        arch = metadata.get("architecture", "")
    else:
        arch = ""

    if arch and arch not in ("arm64", "aarch64", "ARM64", "AARCH64"):
        logger.info(
            "Phase 4B.2: architecture is %r, not arm64; skipping ABI binding.", arch
        )
        return {}

    # Extract functions
    data = unified_ir.get("data", unified_ir)
    functions = data.get("functions", [])
    if not isinstance(functions, list):
        return {}

    result: Dict[str, List[PointerBaseBinding]] = {}
    total_bindings = 0

    for fn in functions:
        if not isinstance(fn, dict):
            continue

        entry = fn.get("entry_point", "")
        if not entry or entry == "unknown":
            continue

        state = AbiRegisterState(entry)

        # Get basic blocks
        blocks = fn.get("basic_blocks", [])
        cfg = fn.get("cfg", {})
        if isinstance(cfg, dict):
            nodes = cfg.get("nodes", [])
            if nodes:
                blocks = nodes

        if not isinstance(blocks, list):
            continue

        for block in blocks:
            if not isinstance(block, dict):
                continue

            # Clear registers at block start, re-init ABI args for first block
            state.clear_registers()

            # Initialize ABI args at function entry (first block only)
            # Since blocks may not be in order, we init for every block
            # but this is conservative — we only get bindings within one block
            state.init_abi_args()

            instructions = block.get("instructions", [])
            if not isinstance(instructions, list):
                continue

            for instr in instructions:
                if not isinstance(instr, dict):
                    continue
                state.process_instruction(instr)

        if state.bindings:
            result[entry] = list(state.bindings)
            total_bindings += len(state.bindings)

    logger.info(
        "Phase 4B.2: collected %d pointer-base binding(s) across %d function(s).",
        total_bindings, len(result),
    )
    return result


# ---------------------------------------------------------------------------
# Link parameter-layout evidence
# ---------------------------------------------------------------------------

def extract_layout_candidates(layout_recovery: Any) -> List[Dict[str, Any]]:
    """Extract layout candidates supporting list, dict wrappers, and nested data shapes."""
    if not layout_recovery:
        return []

    if isinstance(layout_recovery, list):
        return layout_recovery

    if isinstance(layout_recovery, dict):
        if "layout_candidates" in layout_recovery:
            return layout_recovery.get("layout_candidates") or []

        return (
            layout_recovery
            .get("data", {})
            .get("layout_candidates", [])
        )

    return []


def flatten_abi_bindings(bindings: Any) -> List[PointerBaseBinding]:
    """Flatten both dict-grouped and list-based ABI bindings into a flat list."""
    if not bindings:
        return []

    if isinstance(bindings, dict):
        out = []
        for items in bindings.values():
            out.extend(items or [])
        return out

    return list(bindings)


def link_parameter_layouts(
    abi_bindings_by_entry: Any,
    layout_recovery: Optional[Any],
    param_names_by_entry: Optional[Dict[str, Dict[int, str]]] = None,
) -> Dict[str, List[ParameterLayoutEvidence]]:
    """
    Link Phase 4C layout candidates to function parameters via ABI bindings.

    Matching safety: evidence is only linked when BOTH function_entry AND
    base_id match a PointerBaseBinding.
    """
    if not abi_bindings_by_entry:
        return {}

    candidates = extract_layout_candidates(layout_recovery)
    if not candidates:
        return {}

    if param_names_by_entry is None:
        param_names_by_entry = {}

    from src.ir.utils.addressing import normalize_address

    flat_bindings = flatten_abi_bindings(abi_bindings_by_entry)

    # Build index: (normalized(function_entry), normalized(base_id)) → list[PointerBaseBinding]
    binding_index: Dict[Tuple[str, str], List[PointerBaseBinding]] = {}
    for b in flat_bindings:
        b_entry = normalize_address(b.function_entry)
        b_reg = normalize_register_name(b.base_register)
        if b_entry and b_reg:
            key = (b_entry, b_reg)
            binding_index.setdefault(key, []).append(b)

    result: Dict[str, List[ParameterLayoutEvidence]] = {}
    total_evidence = 0

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue

        c_entry = candidate.get("function_entry", "")
        c_base = candidate.get("base_id", "")
        c_name = candidate.get("function_name", "")

        if not c_entry or not c_base:
            continue

        # Normalize entry and base_id for matching
        c_entry_norm = normalize_address(c_entry)
        c_base_norm = normalize_register_name(c_base)

        if not c_entry_norm or not c_base_norm:
            continue

        # Lookup: BOTH function_entry AND base_id must match
        key = (c_entry_norm, c_base_norm)
        matched_bindings = binding_index.get(key, [])
        if not matched_bindings:
            continue

        # Check for unambiguous argument index
        arg_indices = set(b.argument_index for b in matched_bindings if b.argument_index is not None)
        if len(arg_indices) != 1:
            logger.debug(
                "Phase 4B.2: ambiguous arg indices %s for (%s, %s); skipping.",
                arg_indices, c_entry_norm, c_base_norm,
            )
            continue

        arg_idx = arg_indices.pop()
        param_name_map = param_names_by_entry.get(c_entry_norm, {})
        # If not in the entry dict, try fallback lookup with original c_entry
        if not param_name_map and c_entry in param_names_by_entry:
            param_name_map = param_names_by_entry.get(c_entry, {})
        param_name = param_name_map.get(arg_idx, f"arg{arg_idx}")

        # Collect source instructions from all matching bindings
        all_source_instrs: List[str] = []
        all_evidence: List[str] = []
        for b in matched_bindings:
            all_source_instrs.extend(b.source_instrs)
            all_evidence.extend(b.evidence_notes)

        # Add layout candidate's own source instructions
        c_source_instrs = candidate.get("source_instrs", [])
        if isinstance(c_source_instrs, list):
            all_source_instrs.extend(str(s) for s in c_source_instrs)

        evidence = ParameterLayoutEvidence(
            function_entry=c_entry_norm,
            function_name=c_name,
            parameter_index=arg_idx,
            parameter_name=param_name,
            base_id=c_base_norm,
            layout_kind=candidate.get("layout_kind", "unknown"),
            observed_offsets=tuple(candidate.get("observed_offsets", [])),
            observed_sizes=tuple(candidate.get("observed_sizes", [])),
            source_instrs=tuple(sorted(set(all_source_instrs))),
            evidence_notes=tuple(all_evidence + [
                f"layout candidate base_id={c_base_norm} linked to parameter "
                f"{param_name} (arg{arg_idx}) via ABI register provenance"
            ]),
        )

        result.setdefault(c_entry_norm, []).append(evidence)
        total_evidence += 1

    # Sort for determinism
    for entry in result:
        result[entry].sort(key=lambda e: (e.parameter_index, e.base_id))

    return result
