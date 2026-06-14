# -*- coding: utf-8 -*-
"""
Phase 4B.1: Instruction-Level Constraint Propagation

Walks real instruction evidence from the Unified IR basic-block structure and
emits TypeConstraints for variables that can be bound to Phase 4A records via
the conservative BindingContext layer.

Binding pipeline (Phase 4B.1)
------------------------------
instruction operand
    ↓
BindingContext.bind_operand()
    ↓ explicit_variable | stack_slot | register_temp
Phase 4A variable
    ↓
TypeConstraint

Core rules
----------
- A TypeConstraint is ONLY emitted when a VariableBinding is established.
- Register bindings are scoped to one basic block; cleared at block boundaries.
- ABI argument register bindings only fire for registers already bound to
  a Phase 4A variable in the current block.
- Unknown registers, raw text, and unverified stack offsets never produce
  constraints.
- ``printf`` and other variadic functions only have their first fixed
  argument constraint emitted.
- Every code path is guarded against missing/malformed fields.

This module does NOT:
- Reconstruct expressions, statements, C source, or structs.
- Create new variables.
- Lower Phase 4A confidence.
- Propagate register bindings across basic blocks.
"""

from __future__ import annotations

import logging
from typing import Iterator, List, Optional, Set

from src.ir.types.bindings import (
    BindingContext,
    VariableBinding,
    BINDING_REGISTER_TEMP,
    _ARM64_ARG_REGISTERS,
    normalize_register_name,
)
from src.ir.types.constraints import (
    ConstraintKind,
    ConstraintSet,
    ConstraintSource,
    TypeConstraint,
)
from src.ir.types.models import RecoveredFunctionSemantics
from src.ir.types.signatures import get_known_signature

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Opcode sets (lowercased)
# ---------------------------------------------------------------------------

_CALL_OPCODES = frozenset({"call", "bl", "blx", "blr", "callq"})

# Load-like opcodes where the destination register is written from memory
_LOAD_OPCODES = frozenset({
    "ldr", "ldrb", "ldrh", "ldrsb", "ldrsh", "ldrsw",
    "ldr.w", "load",
})

# Store-like opcodes (source → memory; may update register bindings)
_STORE_OPCODES = frozenset({"str", "strb", "strh", "str.w", "store"})

# Arithmetic opcodes
_ARITH_OPCODES = frozenset({"add", "sub", "mul", "imul", "sdiv", "udiv", "idiv"})

# Move-like opcodes (may propagate register bindings)
_MOV_OPCODES = frozenset({"mov", "movz", "movk", "movn", "orr"})

# Comparison opcodes
_CMP_OPCODES = frozenset({"cmp", "test", "subs", "cbz", "cbnz", "tst", "cmn"})


# ---------------------------------------------------------------------------
# Instruction iterator (preserved for backward-compat + test usage)
# ---------------------------------------------------------------------------

def iter_instructions(func_ir: dict) -> Iterator[dict]:
    """
    Yield all instruction dicts from ``basic_blocks[*].instructions``.

    Skips blocks that are not dicts or instruction entries that are not dicts.
    Never raises — all failures are logged at debug level.

    Parameters
    ----------
    func_ir : A single function dict from the Unified IR.
    """
    if not isinstance(func_ir, dict):
        return
    for block in func_ir.get("basic_blocks", []):
        if not isinstance(block, dict):
            logger.debug("iter_instructions: skipping non-dict block: %r", block)
            continue
        for instr in block.get("instructions", []):
            if isinstance(instr, dict):
                yield instr
            else:
                logger.debug(
                    "iter_instructions: skipping non-dict instruction: %r", instr
                )


# ---------------------------------------------------------------------------
# Operand helpers
# ---------------------------------------------------------------------------

def _get_symbol_operand(operands: list) -> str:
    """Return the name of the first ``symbol`` operand, or empty string."""
    for op in operands:
        if not isinstance(op, dict):
            continue
        if op.get("kind") == "symbol":
            name = op.get("name", "")
            if name:
                return name
    return ""


def _get_dest_register(operands: list) -> Optional[str]:
    """
    Return the normalized name of the first register operand (the destination),
    or None if not found.

    On ARM64, the destination is conventionally the first operand.
    """
    for op in operands:
        if not isinstance(op, dict):
            continue
        if op.get("kind") == "register":
            val = op.get("value", "")
            if val:
                return normalize_register_name(str(val))
    return None


def _get_all_register_operands(operands: list) -> List[str]:
    """Return normalized names of all register operands."""
    result = []
    for op in operands:
        if not isinstance(op, dict):
            continue
        if op.get("kind") == "register":
            val = op.get("value", "")
            if val:
                result.append(normalize_register_name(str(val)))
    return result


# ---------------------------------------------------------------------------
# Instruction processor
# ---------------------------------------------------------------------------

def _process_instruction(
    instr: dict,
    context: BindingContext,
    cset: ConstraintSet,
) -> None:
    """
    Process a single instruction within its basic block context.

    Side effects:
    - May update register bindings in ``context``
    - May add TypeConstraints to ``cset``

    Parameters
    ----------
    instr   : A validated instruction dict from the Unified IR.
    context : The current BindingContext (block-scoped).
    cset    : The ConstraintSet being built for this function.
    """
    opcode_raw = instr.get("opcode") or instr.get("mnemonic") or ""
    if not opcode_raw:
        logger.debug("_process_instruction: no opcode, skipping: %r", instr)
        return

    opcode = opcode_raw.strip().lower()
    operands = instr.get("operands", [])
    if not isinstance(operands, list):
        return

    addr = instr.get("address", "?")
    size_bytes = instr.get("size_bytes")

    # -----------------------------------------------------------------------
    # Load-like instructions
    # -----------------------------------------------------------------------
    if opcode in _LOAD_OPCODES:
        _handle_load(opcode, operands, addr, size_bytes, context, cset)

    # -----------------------------------------------------------------------
    # Store-like instructions
    # -----------------------------------------------------------------------
    elif opcode in _STORE_OPCODES:
        _handle_store(opcode, operands, addr, size_bytes, context, cset)

    # -----------------------------------------------------------------------
    # Move-like instructions (may propagate register binding)
    # -----------------------------------------------------------------------
    elif opcode in _MOV_OPCODES:
        _handle_mov(opcode, operands, addr, context, cset)

    # -----------------------------------------------------------------------
    # Arithmetic instructions
    # -----------------------------------------------------------------------
    elif opcode in _ARITH_OPCODES:
        _handle_arith(opcode, operands, addr, context, cset)

    # -----------------------------------------------------------------------
    # Comparison instructions
    # -----------------------------------------------------------------------
    elif opcode in _CMP_OPCODES:
        _handle_cmp(opcode, operands, addr, context, cset)

    # -----------------------------------------------------------------------
    # Call instructions
    # -----------------------------------------------------------------------
    elif opcode in _CALL_OPCODES:
        _handle_call(opcode, operands, addr, context, cset)
        # Always clear all register bindings after a call
        context.clear_all_registers()

    else:
        # Unknown/other instruction: if it writes to a bound register, clear it
        dest_reg = _get_dest_register(operands)
        if dest_reg and context.bind_register(dest_reg) is not None:
            logger.debug(
                "Unknown opcode %r clobbers bound register %s; clearing.", opcode, dest_reg
            )
            context.clear_register(dest_reg)


# ---------------------------------------------------------------------------
# Per-opcode-class handlers
# ---------------------------------------------------------------------------

def _handle_load(
    opcode: str,
    operands: list,
    addr: str,
    size_bytes,
    context: BindingContext,
    cset: ConstraintSet,
) -> None:
    """
    Handle a load-like instruction.

    If the source memory operand binds to a Phase 4A variable, remember
    the destination register as carrying that variable, and emit a SIZE
    constraint.

    ldr x8, [sp, #0x10]   →   remember x8 → local_10; emit SIZE(local_10)
    """
    if not operands:
        return

    # Destination is the first register operand
    dest_reg = _get_dest_register(operands)

    # Source binding: try all non-first operands as the source memory
    source_binding: Optional[VariableBinding] = None
    for op in operands[1:] if len(operands) > 1 else operands:
        b = context.bind_operand(op)
        if b is not None:
            source_binding = b
            break
    # Also check the first operand if it's a memory operand and we only
    # have one operand (some IR representations)
    if source_binding is None and len(operands) == 1:
        source_binding = context.bind_operand(operands[0])

    if source_binding is None:
        # Clear destination register binding if it had one (load from unknown)
        if dest_reg:
            context.clear_register(dest_reg)
        return

    # Create a register-temp binding for the destination register
    if dest_reg:
        reg_binding = VariableBinding(
            variable_name=source_binding.variable_name,
            binding_kind=BINDING_REGISTER_TEMP,
            source=f"register_temp_from_load",
            confidence=source_binding.confidence * 0.9,
            evidence_note=(
                f"{source_binding.variable_name} bound through register "
                f"{dest_reg} from {opcode} at {addr}"
            ),
        )
        context.remember_register(dest_reg, reg_binding)

    # Emit SIZE constraint if size_bytes is known
    if size_bytes is not None:
        cset.add(TypeConstraint(
            kind=ConstraintKind.SIZE,
            lhs=source_binding.variable_name,
            rhs=str(size_bytes),
            source_priority=ConstraintSource.IR_MEMORY,
            evidence_note=(
                f"{source_binding.variable_name} {source_binding.evidence_note}, "
                f"loaded by {opcode} at {addr} with size_bytes={size_bytes}"
            ),
        ))


def _handle_store(
    opcode: str,
    operands: list,
    addr: str,
    size_bytes,
    context: BindingContext,
    cset: ConstraintSet,
) -> None:
    """
    Handle a store-like instruction.

    If the destination memory operand binds to a Phase 4A variable, and
    the source register is bound, emit a SIZE constraint. If the source
    is a direct binding (explicit variable or stack slot), also emit SIZE.

    str w8, [sp, #0x10]   →   if x8 → local_10 or sp+0x10 → local_10: emit SIZE
    """
    if not operands:
        return

    # For stores: source is typically first operand, dest memory is second
    # Try to bind the destination memory operand
    dest_binding: Optional[VariableBinding] = None
    for op in operands:
        if isinstance(op, dict) and op.get("kind") == "memory":
            dest_binding = context.bind_operand(op)
            break

    # Also try source-register binding (the value being stored)
    src_binding: Optional[VariableBinding] = None
    if operands:
        first_op = operands[0]
        if isinstance(first_op, dict) and first_op.get("kind") == "register":
            reg_name = normalize_register_name(first_op.get("value", ""))
            src_binding = context.bind_register(reg_name)

    # Use whichever binding we have (destination memory takes priority)
    binding = dest_binding or src_binding
    if binding is None:
        return

    if size_bytes is not None:
        cset.add(TypeConstraint(
            kind=ConstraintKind.SIZE,
            lhs=binding.variable_name,
            rhs=str(size_bytes),
            source_priority=ConstraintSource.IR_MEMORY,
            evidence_note=(
                f"{binding.variable_name} {binding.evidence_note}, "
                f"stored by {opcode} at {addr} with size_bytes={size_bytes}"
            ),
        ))


def _handle_mov(
    opcode: str,
    operands: list,
    addr: str,
    context: BindingContext,
    cset: ConstraintSet,
) -> None:
    """
    Handle a move-like instruction.

    Propagate register bindings: if the source is a bound register,
    the destination register inherits the same binding.

    mov x0, x8  →  if x8 → local_10, then x0 → local_10
    """
    if len(operands) < 2:
        dest_reg = _get_dest_register(operands)
        if dest_reg:
            context.clear_register(dest_reg)
        return

    dest_reg = _get_dest_register(operands)
    if not dest_reg:
        return

    # Try binding the source (second operand)
    src_op = operands[1] if len(operands) > 1 else None
    if src_op is None:
        context.clear_register(dest_reg)
        return

    src_binding = context.bind_operand(src_op)
    if src_binding is not None:
        # Propagate the binding to the destination register
        new_binding = VariableBinding(
            variable_name=src_binding.variable_name,
            binding_kind=BINDING_REGISTER_TEMP,
            source="register_temp_from_mov",
            confidence=src_binding.confidence * 0.85,
            evidence_note=(
                f"{src_binding.variable_name} propagated from "
                f"{src_binding.evidence_note} via {opcode} at {addr}"
            ),
        )
        context.remember_register(dest_reg, new_binding)
    else:
        # Source is not bound → clear destination
        context.clear_register(dest_reg)


def _handle_arith(
    opcode: str,
    operands: list,
    addr: str,
    context: BindingContext,
    cset: ConstraintSet,
) -> None:
    """
    Handle arithmetic instructions.

    If any source operand is a bound register or explicit variable, emit
    a SIGN constraint for the bound variable.

    add w8, w8, #1  →  if x8 → local_10: SIGN(local_10)
    """
    # Check all operands for register or explicit variable bindings
    bound: Optional[VariableBinding] = None
    for op in operands:
        if not isinstance(op, dict):
            continue
        b = context.bind_operand(op)
        if b is not None:
            bound = b
            break

    if bound is None:
        # Also check register operands explicitly
        for reg in _get_all_register_operands(operands):
            b = context.bind_register(reg)
            if b is not None:
                bound = b
                break

    if bound is None:
        return

    cset.add(TypeConstraint(
        kind=ConstraintKind.SIGN,
        lhs=bound.variable_name,
        rhs="int32",
        source_priority=ConstraintSource.IR_ARITHMETIC,
        evidence_note=(
            f"{bound.variable_name} bound from {bound.evidence_note}, "
            f"used by {opcode} at {addr}"
        ),
    ))

    # Update destination register binding (arithmetic produces the same variable)
    dest_reg = _get_dest_register(operands)
    if dest_reg and bound is not None:
        new_binding = VariableBinding(
            variable_name=bound.variable_name,
            binding_kind=BINDING_REGISTER_TEMP,
            source="register_temp_from_arith",
            confidence=bound.confidence * 0.8,
            evidence_note=(
                f"{bound.variable_name} result of {opcode} at {addr}"
            ),
        )
        context.remember_register(dest_reg, new_binding)


def _handle_cmp(
    opcode: str,
    operands: list,
    addr: str,
    context: BindingContext,
    cset: ConstraintSet,
) -> None:
    """
    Handle comparison instructions.

    If any operand is a bound register or explicit variable, emit a weak
    SUBTYPE constraint.

    cmp w8, #0  →  if x8 → local_10: SUBTYPE(local_10)
    """
    bound: Optional[VariableBinding] = None
    for op in operands:
        if not isinstance(op, dict):
            continue
        b = context.bind_operand(op)
        if b is not None:
            bound = b
            break
    if bound is None:
        for reg in _get_all_register_operands(operands):
            b = context.bind_register(reg)
            if b is not None:
                bound = b
                break
    if bound is None:
        return

    cset.add(TypeConstraint(
        kind=ConstraintKind.SUBTYPE,
        lhs=bound.variable_name,
        rhs="int32",
        source_priority=ConstraintSource.IR_COMPARISON,
        evidence_note=(
            f"{bound.variable_name} bound from {bound.evidence_note}, "
            f"used in comparison {opcode} at {addr}"
        ),
    ))


def _handle_call(
    opcode: str,
    operands: list,
    addr: str,
    context: BindingContext,
    cset: ConstraintSet,
) -> None:
    """
    Handle call instructions.

    For each fixed parameter of a known callee:
    1. Map argument index to ABI register (x0, x1, ...).
    2. Check if that register is currently bound to a Phase 4A variable.
    3. If yes, emit CALL_ARG constraint.
    4. For variadic functions (e.g. printf), only the first argument is
       constrained.

    Register bindings are cleared by the caller after this returns.
    """
    callee_name = _get_symbol_operand(operands)
    if not callee_name:
        return

    known_sig = get_known_signature(callee_name)
    if known_sig is None:
        return

    for idx, param in enumerate(known_sig.params):
        # Variadic: only first fixed argument
        if known_sig.variadic and idx >= 1:
            break

        abi_reg = context.abi_register_for_arg(idx)
        if abi_reg is None:
            continue

        bound = context.bind_register(abi_reg)
        if bound is None:
            continue

        cset.add(TypeConstraint(
            kind=ConstraintKind.CALL_ARG,
            lhs=bound.variable_name,
            rhs=param.type_name,
            source_priority=ConstraintSource.IR_CALL_SITE,
            evidence_note=(
                f"{bound.variable_name} passed through ABI argument register "
                f"{abi_reg} to {callee_name} at {addr}; "
                f"expected type {param.type_name}"
            ),
        ))


# ---------------------------------------------------------------------------
# Main constraint collector (Phase 4B.1 — per-block scoped)
# ---------------------------------------------------------------------------

def collect_constraints(
    func_ir: dict,
    phase4a_record: RecoveredFunctionSemantics,
) -> ConstraintSet:
    """
    Walk the instruction stream of a single function, block by block, and
    emit TypeConstraints using the conservative BindingContext.

    Register bindings are scoped to one basic block — they are cleared at
    the start and end of every block. They are never propagated across blocks.

    Parameters
    ----------
    func_ir        : The function dict from the Unified IR (may be ``{}``).
    phase4a_record : The Phase 4A recovery record for the same function.

    Returns
    -------
    ConstraintSet
        A deduplicated set of constraints.  May be empty if no real
        instruction evidence is available or bindings cannot be established.
    """
    cset = ConstraintSet()

    if not isinstance(func_ir, dict):
        return cset

    context = BindingContext(phase4a_record)

    for block in func_ir.get("basic_blocks", []):
        if not isinstance(block, dict):
            logger.debug("collect_constraints: skipping non-dict block: %r", block)
            continue

        # Clear register state at start of each block
        context.clear_all_registers()

        instructions = block.get("instructions", [])
        if not isinstance(instructions, list):
            continue

        for instr in instructions:
            if not isinstance(instr, dict):
                continue
            try:
                _process_instruction(instr, context, cset)
            except Exception as exc:
                logger.warning(
                    "collect_constraints: exception processing instruction %r: %s",
                    instr.get("address", "?"), exc,
                )

        # Clear register state at end of each block (defensive double-clear)
        context.clear_all_registers()

    return cset
