# -*- coding: utf-8 -*-
"""
Phase 4B.1: Conservative Operand-to-Variable Binding

Provides the binding layer between low-level instruction operands
(register, memory, immediate, symbol, unknown) and Phase 4A named
variables.

Binding pipeline
----------------
instruction operand
    ↓
stack slot / register temporary
    ↓
Phase 4A variable
    ↓
type constraint

Core Principle
--------------
Do not fabricate bindings. Missing bindings are acceptable. Guessed
bindings are not.

Rules
-----
- Explicit variable operands (kind="variable") bind at confidence 1.0
  if the name exists in the Phase 4A index.
- Memory operands bind to a stack variable only when Phase 4A provides
  a verified offset_bytes field and the match is unambiguous.
- Register bindings are only maintained within one basic block.
- Register bindings are never propagated across basic blocks.
- ABI argument register bindings only fire when the register is already
  locally bound to a Phase 4A variable.
- Unknown registers, raw text, and unverified offsets never produce
  constraints.

This module does NOT:
- Reconstruct expressions or statements
- Emit C source code
- Infer struct layouts
- Lower Phase 4A confidence
- Create new variables not in the Phase 4A record
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional, Set

from src.ir.types.models import RecoveredFunctionSemantics, RecoveredVariable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Binding kinds
# ---------------------------------------------------------------------------

BINDING_EXPLICIT_VARIABLE = "explicit_variable"
BINDING_STACK_SLOT        = "stack_slot"
BINDING_REGISTER_TEMP     = "register_temp"
BINDING_ABI_ARG_REGISTER  = "abi_argument_register"
BINDING_UNKNOWN           = "unknown"


# ---------------------------------------------------------------------------
# ARM64 ABI argument register order (canonical x-form)
# ---------------------------------------------------------------------------

# ARM64 integer/pointer ABI registers in argument order
_ARM64_ARG_REGISTERS = ["x0", "x1", "x2", "x3", "x4", "x5", "x6", "x7"]

# Registers used as base pointer for stack frames on ARM64
_STACK_BASE_REGISTERS = frozenset({"sp", "xsp", "x28", "fp", "x29"})


# ---------------------------------------------------------------------------
# VariableBinding
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VariableBinding:
    """
    A conservative binding between an instruction operand and a Phase 4A variable.

    Attributes
    ----------
    variable_name : Name of the matched Phase 4A variable or parameter.
    binding_kind  : How the binding was established (see BINDING_* constants).
    source        : Short provenance tag (e.g. "instruction_operand", "stack_slot").
    confidence    : 0.0–1.0 — how certain this binding is.
    evidence_note : Human-readable description for ``semantic_recovery.json``.
    """
    variable_name: str
    binding_kind: str
    source: str
    confidence: float
    evidence_note: str


# ---------------------------------------------------------------------------
# Register name normalizer
# ---------------------------------------------------------------------------

def normalize_register_name(reg: str) -> str:
    """
    Normalize an ARM64 register alias to its canonical x-form.

    Normalization rules (conservative):
    - w0 → x0, w1 → x1, …, w30 → x30
    - sp, xsp → sp  (kept as-is; treated as frame base)
    - fp, x29 → x29 (frame pointer)
    - lr, x30 → x30 (link register)
    - All other names are returned lowercased.

    This function is architecture-aware only for ARM64. It does NOT
    normalize x86 registers or any other architecture.

    Parameters
    ----------
    reg : Register name string (case-insensitive input).

    Returns
    -------
    str
        Normalized lowercase register name.
    """
    if not reg:
        return reg
    r = reg.strip().lower()

    # Handle w0–w30 → x0–x30
    if r.startswith("w") and len(r) >= 2:
        suffix = r[1:]
        try:
            n = int(suffix)
            if 0 <= n <= 30:
                return f"x{n}"
        except ValueError:
            pass

    # Normalize aliases
    if r == "xsp":
        return "sp"
    if r == "fp":
        return "x29"
    if r == "lr":
        return "x30"

    return r


# ---------------------------------------------------------------------------
# BindingContext
# ---------------------------------------------------------------------------

class BindingContext:
    """
    Per-function binding context, with per-basic-block register scope.

    Responsibilities
    ----------------
    1. Build a Phase 4A variable index by name.
    2. Build a conservative stack-variable offset index (requires
       verified ``offset_bytes`` on the Phase 4A variable record).
    3. Track temporary register bindings *within a single basic block*.
    4. Expose lookup helpers for use by the constraint propagator.

    Register binding rules
    ----------------------
    - ``remember_register`` is called when a load-like instruction moves
      a known variable into a register.
    - ``bind_register`` looks up whether a register is currently bound.
    - ``clear_register`` removes a binding when a register is clobbered.
    - ``clear_all_registers`` is called at basic-block boundaries.

    Never propagate register state across basic blocks.
    """

    def __init__(self, phase4a_record: RecoveredFunctionSemantics) -> None:
        # Primary variable index by name
        self._var_by_name: Dict[str, RecoveredVariable] = {}
        # All known names (variables + parameters) for fast membership tests
        self._all_known: Set[str] = set()
        # Stack variable index: verified offset_bytes → variable
        # Only includes variables where offset_bytes is an integer (not None).
        self._var_by_offset: Dict[int, RecoveredVariable] = {}
        # Current register bindings (cleared per basic block)
        self._reg_bindings: Dict[str, VariableBinding] = {}

        self._build_index(phase4a_record)

    # ------------------------------------------------------------------
    # Index construction
    # ------------------------------------------------------------------

    def _build_index(self, record: RecoveredFunctionSemantics) -> None:
        """Build variable and offset lookup tables from the Phase 4A record."""
        # Variables
        for var in record.variables:
            if var.name:
                self._var_by_name[var.name] = var
                self._all_known.add(var.name)

                # Stack offset index (only verified integer offsets)
                if isinstance(var.offset_bytes, int):
                    existing = self._var_by_offset.get(var.offset_bytes)
                    if existing is not None:
                        # Ambiguous offset — remove from index; cannot bind safely
                        logger.debug(
                            "Duplicate stack offset %d for variables %r and %r; "
                            "removed from binding index.",
                            var.offset_bytes, existing.name, var.name,
                        )
                        del self._var_by_offset[var.offset_bytes]
                    else:
                        self._var_by_offset[var.offset_bytes] = var

        # Parameters (added to name set; they rarely have stack offsets)
        for param in record.signature.parameters:
            if param.name:
                self._all_known.add(param.name)

    # ------------------------------------------------------------------
    # Core lookup helpers
    # ------------------------------------------------------------------

    @property
    def all_known_names(self) -> Set[str]:
        """All Phase 4A variable and parameter names."""
        return self._all_known

    def bind_operand(self, operand: dict) -> Optional[VariableBinding]:
        """
        Attempt to bind a single instruction operand dict to a Phase 4A variable.

        Supported operand kinds:
        - ``"variable"`` (explicit) → bind_explicit
        - ``"memory"``              → bind_stack_slot
        - ``"register"``            → bind_register (current block state)
        - All others                → None (not bindable conservatively)

        Parameters
        ----------
        operand : A canonical instruction operand dict.

        Returns
        -------
        VariableBinding or None
            A binding if one can be established conservatively, else None.
        """
        if not isinstance(operand, dict):
            return None

        kind = operand.get("kind", "")

        if kind == "variable":
            return self._bind_explicit(operand)
        elif kind == "memory":
            return self._bind_memory(operand)
        elif kind == "register":
            reg = operand.get("value", "")
            if reg:
                return self.bind_register(normalize_register_name(str(reg)))
        return None

    def bind_register(self, register_name: str) -> Optional[VariableBinding]:
        """
        Look up a current block-local register binding.

        Parameters
        ----------
        register_name : Normalized register name (e.g. "x0", "sp").

        Returns
        -------
        VariableBinding or None
        """
        norm = normalize_register_name(register_name)
        return self._reg_bindings.get(norm)

    def remember_register(
        self,
        register_name: str,
        binding: VariableBinding,
    ) -> None:
        """
        Record that a register now holds a known variable value.

        Only called when a load-like instruction moves a bound variable
        into a register. Overwrites any previous binding for this register.

        Parameters
        ----------
        register_name : Register to bind (will be normalized).
        binding       : The VariableBinding this register now carries.
        """
        norm = normalize_register_name(register_name)
        self._reg_bindings[norm] = binding
        logger.debug(
            "Bound register %s → %s (%s)",
            norm, binding.variable_name, binding.binding_kind,
        )

    def clear_register(self, register_name: str) -> None:
        """
        Remove a register binding (register clobbered by non-variable write).

        Parameters
        ----------
        register_name : Register name to clear (will be normalized).
        """
        norm = normalize_register_name(register_name)
        if norm in self._reg_bindings:
            logger.debug("Cleared register binding: %s", norm)
            del self._reg_bindings[norm]

    def clear_all_registers(self) -> None:
        """
        Clear all register bindings.

        Must be called at the start AND end of every basic block to
        ensure register state is never propagated across blocks.
        """
        if self._reg_bindings:
            logger.debug(
                "Clearing all register bindings (%d entries).", len(self._reg_bindings)
            )
            self._reg_bindings.clear()

    # ------------------------------------------------------------------
    # ABI argument register helpers
    # ------------------------------------------------------------------

    def abi_register_for_arg(self, arg_index: int) -> Optional[str]:
        """
        Return the ARM64 ABI argument register for the given 0-based index.

        Parameters
        ----------
        arg_index : 0-based argument position.

        Returns
        -------
        str or None
            Canonical register name (e.g. "x0"), or None if out of range.
        """
        if 0 <= arg_index < len(_ARM64_ARG_REGISTERS):
            return _ARM64_ARG_REGISTERS[arg_index]
        return None

    # ------------------------------------------------------------------
    # Private binding helpers
    # ------------------------------------------------------------------

    def _bind_explicit(self, operand: dict) -> Optional[VariableBinding]:
        """
        Bind an operand with ``kind == "variable"`` to the Phase 4A index.

        Requires ``operand["name"]`` to match a known variable name exactly.
        Never creates new variables.
        """
        name = operand.get("name", "")
        if not name or name not in self._all_known:
            return None
        return VariableBinding(
            variable_name=name,
            binding_kind=BINDING_EXPLICIT_VARIABLE,
            source="instruction_operand",
            confidence=1.0,
            evidence_note=f"Operand explicitly names Phase 4A variable {name}",
        )

    def _bind_memory(self, operand: dict) -> Optional[VariableBinding]:
        """
        Conservatively bind a memory operand to a Phase 4A stack variable.

        Binding requires:
        1. ``base`` register is a known stack frame base (sp, fp/x29).
        2. ``offset`` is an integer.
        3. Phase 4A index has exactly one variable with a matching
           ``offset_bytes`` (unambiguous match).
        4. ``size_bytes`` is compatible with the variable's ``size_bytes``
           if both are known.

        ARM64 caveat: Ghidra/Radare2 may emit sp-relative offsets that do
        not directly correspond to Phase 4A's ``offset_bytes`` naming
        convention. We therefore only bind when Phase 4A's record includes
        verified integer offsets AND the match is unambiguous.
        """
        base = operand.get("base", "")
        if not base:
            return None

        base_norm = normalize_register_name(str(base)).lower()
        if base_norm not in _STACK_BASE_REGISTERS:
            # Non-frame-base memory accesses are not bindable conservatively
            logger.debug(
                "_bind_memory: non-stack base register %r; skipping.", base_norm
            )
            return None

        raw_offset = operand.get("offset")
        if raw_offset is None:
            return None
        try:
            offset_int = int(raw_offset)
        except (TypeError, ValueError):
            return None

        # Check for verified offset match in the Phase 4A index
        matched_var = self._var_by_offset.get(offset_int)
        if matched_var is None:
            # Try negative convention: Ghidra often uses negative offsets,
            # but sp-relative offsets in disassembly are positive.
            # Attempt both signs conservatively.
            matched_var = self._var_by_offset.get(-offset_int)
            if matched_var is None:
                logger.debug(
                    "_bind_memory: no Phase 4A variable at offset %d (or %d); skip.",
                    offset_int, -offset_int,
                )
                return None

        # Size compatibility check (only if both sides are known)
        op_size = operand.get("size_bytes")
        var_size = matched_var.size_bytes
        if op_size is not None and var_size is not None:
            try:
                if int(op_size) != int(var_size):
                    logger.debug(
                        "_bind_memory: size mismatch for %s (var=%d, op=%d); skip.",
                        matched_var.name, var_size, op_size,
                    )
                    return None
            except (TypeError, ValueError):
                pass  # Can't compare; proceed conservatively

        return VariableBinding(
            variable_name=matched_var.name,
            binding_kind=BINDING_STACK_SLOT,
            source="stack_slot",
            confidence=0.85,
            evidence_note=(
                f"{matched_var.name} bound from stack slot "
                f"[{base_norm} + {offset_int:#x}]"
            ),
        )
