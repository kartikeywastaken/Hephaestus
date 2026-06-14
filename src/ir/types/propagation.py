# -*- coding: utf-8 -*-
"""
Phase 4B: Instruction-Level Constraint Propagation

Walks real instruction evidence from the Unified IR basic-block structure and
emits TypeConstraints for variables that have concrete extractor-provided
variable/stack-slot mappings.

Core rules (Amendment 5)
------------------------
- Constraints are ONLY emitted for operands with ``kind == "variable"`` whose
  ``name`` is present in the Phase 4A known variable/parameter index.
- Register operands (``kind == "register"``) never produce variable constraints.
- Unknown operands (``kind == "unknown"``) never produce variable constraints.
- Call-site constraints use the built-in known signature database.
- Every code path is guarded against missing/malformed fields — skip with debug.

This module does NOT reconstruct expressions, statements, C source, or structs.
"""

from __future__ import annotations

import logging
from typing import Dict, Iterator, Set

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
_ARITH_OPCODES = frozenset({"add", "sub", "mul", "imul", "sdiv", "udiv", "idiv"})
_MEMORY_OPCODES = frozenset({
    "load", "store", "ldr", "str", "mov",
    "ldrb", "strb", "ldrh", "strh", "ldrsb", "ldrsh",
    "ldr.w", "str.w",
})
_CMP_OPCODES = frozenset({"cmp", "test", "subs", "cbz", "cbnz", "tst", "cmn"})


# ---------------------------------------------------------------------------
# Instruction iterator
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
                logger.debug("iter_instructions: skipping non-dict instruction: %r", instr)


# ---------------------------------------------------------------------------
# Operand helpers
# ---------------------------------------------------------------------------

def _get_variable_operands(operands: list, known: Set[str]) -> list:
    """
    Return operand dicts with kind=="variable" whose name is in ``known``.

    This is the Amendment 5 gate: only concrete variable mappings from the
    extractor trigger constraints.
    """
    result = []
    for op in operands:
        if not isinstance(op, dict):
            continue
        if op.get("kind") == "variable":
            name = op.get("name", "")
            if name and name in known:
                result.append(op)
    return result


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


# ---------------------------------------------------------------------------
# Main constraint collector
# ---------------------------------------------------------------------------

def collect_constraints(
    func_ir: dict,
    phase4a_record: RecoveredFunctionSemantics,
) -> ConstraintSet:
    """
    Walk the instruction stream of a single function and emit TypeConstraints.

    Parameters
    ----------
    func_ir        : The function dict from the Unified IR (may be empty ``{}``).
    phase4a_record : The Phase 4A recovery record for the same function.

    Returns
    -------
    ConstraintSet
        A deduplicated set of constraints.  May be empty if no real instruction
        evidence is available.
    """
    cset = ConstraintSet()

    # Build the known variable/parameter index (Amendment 5)
    known_vars: Set[str] = {v.name for v in phase4a_record.variables if v.name}
    known_params: Set[str] = {
        p.name for p in phase4a_record.signature.parameters if p.name
    }
    all_known: Set[str] = known_vars | known_params

    for instr in iter_instructions(func_ir):
        opcode_raw = instr.get("opcode") or instr.get("mnemonic") or ""
        if not opcode_raw:
            logger.debug("collect_constraints: skipping instruction with no opcode: %r", instr)
            continue

        opcode = opcode_raw.strip().lower()
        operands = instr.get("operands", [])
        if not isinstance(operands, list):
            logger.debug("collect_constraints: non-list operands in %r; skipping", instr)
            continue

        size_bytes = instr.get("size_bytes")

        # ---------------------------------------------------------------
        # Call-site constraints
        # ---------------------------------------------------------------
        if opcode in _CALL_OPCODES:
            callee_name = _get_symbol_operand(operands)
            if not callee_name:
                continue
            known_sig = get_known_signature(callee_name)
            if known_sig is None:
                continue
            # Emit CALL_ARG constraints for each known fixed parameter
            for idx, param in enumerate(known_sig.params):
                if known_sig.variadic and idx >= 1:
                    # For variadic functions (e.g. printf), only emit constraint
                    # for the first (format) argument; skip variadic slots.
                    break
                # We don't know which variable maps to which call argument
                # unless the extractor provided variable operands.
                # Look for a variable operand at the matching position.
                var_ops = _get_variable_operands(operands, all_known)
                if idx < len(var_ops):
                    var_name = var_ops[idx].get("name", "")
                    if var_name:
                        cset.add(TypeConstraint(
                            kind=ConstraintKind.CALL_ARG,
                            lhs=var_name,
                            rhs=param.type_name,
                            source_priority=ConstraintSource.IR_CALL_SITE,
                            evidence_note=(
                                f"passed as arg {idx} to {callee_name}; "
                                f"expected type {param.type_name}"
                            ),
                        ))

        # ---------------------------------------------------------------
        # Arithmetic constraints (SIGN)
        # ---------------------------------------------------------------
        elif opcode in _ARITH_OPCODES:
            for op in _get_variable_operands(operands, all_known):
                var_name = op.get("name", "")
                if var_name:
                    cset.add(TypeConstraint(
                        kind=ConstraintKind.SIGN,
                        lhs=var_name,
                        rhs="int32",
                        source_priority=ConstraintSource.IR_ARITHMETIC,
                        evidence_note=f"used in arithmetic opcode '{opcode}'",
                    ))

        # ---------------------------------------------------------------
        # Memory constraints (SIZE)
        # ---------------------------------------------------------------
        elif opcode in _MEMORY_OPCODES:
            if size_bytes is not None:
                for op in _get_variable_operands(operands, all_known):
                    var_name = op.get("name", "")
                    if var_name:
                        cset.add(TypeConstraint(
                            kind=ConstraintKind.SIZE,
                            lhs=var_name,
                            rhs=str(size_bytes),
                            source_priority=ConstraintSource.IR_MEMORY,
                            evidence_note=(
                                f"memory opcode '{opcode}' with size_bytes={size_bytes}"
                            ),
                        ))

        # ---------------------------------------------------------------
        # Comparison constraints (SUBTYPE — weak)
        # ---------------------------------------------------------------
        elif opcode in _CMP_OPCODES:
            for op in _get_variable_operands(operands, all_known):
                var_name = op.get("name", "")
                if var_name:
                    cset.add(TypeConstraint(
                        kind=ConstraintKind.SUBTYPE,
                        lhs=var_name,
                        rhs="int32",
                        source_priority=ConstraintSource.IR_COMPARISON,
                        evidence_note=f"used in comparison opcode '{opcode}'",
                    ))

    return cset
