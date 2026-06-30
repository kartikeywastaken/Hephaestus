# -*- coding: utf-8 -*-
"""
Predicate Recovery Logic
Translates parsed branch/compare evidence into C boolean expressions.
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple, List
from src.readability.models import BRANCH_MAP, UNSIGNED_BRANCHES

logger = logging.getLogger("readability.recovery")

NEGATION_MAP = {
    "==": "!=",
    "!=": "==",
    "<": ">=",
    "<=": ">",
    ">": "<=",
    ">=": "<",
}

def map_operand(op: str) -> str:
    """Format register and immediate operand values to C-style pseudo names."""
    op = op.strip()
    if not op:
        return ""
    if op.startswith("#"):
        op = op[1:]
        
    lower_op = op.lower()
    if lower_op in ("wzr", "xzr"):
        return "0"
    if lower_op == "sp":
        return "tmp_sp"
    if lower_op in ("fp", "x29"):
        return "tmp_fp"
    if lower_op in ("lr", "x30"):
        return "tmp_lr"
        
    # Standard ARM64 registers
    if re.match(r'^[wx][0-9]+$', lower_op):
        return f"tmp_{lower_op}"
        
    # Attempt parsing as integer
    try:
        val = int(op, 0)
        return str(val)
    except ValueError:
        pass
        
    if lower_op.startswith("tmp_"):
        return lower_op
        
    return op

def parse_compare_instruction(inst: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """
    Parses a compare (cmp) or subtract and update flags (subs) instruction to extract operands.
    Returns (operand1, operand2) if successful, None otherwise.
    """
    mnemonic = inst.get("mnemonic", "").strip().lower()
    raw = inst.get("raw", "").strip().lower()
    
    if mnemonic not in ("cmp", "subs"):
        return None
        
    raw_clean = re.sub(r'\s+', ' ', raw)
    
    # Try parsing cmp
    if mnemonic == "cmp":
        # cmp reg, #imm
        m = re.match(r'^cmp\s+([a-z0-9]+)\s*,\s*#?(-?(?:0x[0-9a-f]+|[0-9]+))$', raw_clean)
        if m:
            return m.group(1), m.group(2)
        # cmp reg, reg
        m = re.match(r'^cmp\s+([a-z0-9]+)\s*,\s*([a-z0-9]+)$', raw_clean)
        if m:
            return m.group(1), m.group(2)
            
    elif mnemonic == "subs":
        # subs dest, src, #imm
        m = re.match(r'^subs\s+[a-z0-9]+\s*,\s*([a-z0-9]+)\s*,\s*#?(-?(?:0x[0-9a-f]+|[0-9]+))$', raw_clean)
        if m:
            return m.group(1), m.group(2)
        # subs dest, src, reg
        m = re.match(r'^subs\s+[a-z0-9]+\s*,\s*([a-z0-9]+)\s*,\s*([a-z0-9]+)$', raw_clean)
        if m:
            return m.group(1), m.group(2)
            
    # Fallback to operands structured list if available
    operands = inst.get("operands", [])
    if mnemonic == "cmp" and len(operands) >= 2:
        val1 = operands[0].get("value")
        val2 = operands[1].get("value")
        if val1 and val2 is not None:
            if isinstance(val2, int):
                val2 = hex(val2)
            return str(val1), str(val2)
    elif mnemonic == "subs" and len(operands) >= 4:
        val1 = operands[1].get("value")
        val2 = operands[3].get("value")
        if val1 and val2 is not None:
            if isinstance(val2, int):
                val2 = hex(val2)
            return str(val1), str(val2)
            
    return None

def recover_predicate(site: Dict[str, Any], inst_lookup: Dict[str, Dict[str, Any]]) -> Tuple[str, Optional[str], Optional[str], List[str]]:
    """
    Recover relational C expression for a parsed condition site.
    Returns:
        status: "recovered" or "skipped"
        replacement_condition: generated condition string (or None)
        reason: skipped reason string (or None)
        notes: list of uncertainty/diagnostics notes
    """
    site_type = site.get("type")
    polarity = site.get("polarity")
    
    if polarity == "unclear":
        return "skipped", None, "ambiguous branch polarity", []
        
    notes = []
    # If assumed direct, add warning note
    if polarity == "assumed_direct":
        notes.append("Predicate polarity inferred from adapter text; uncertain.")
    else:
        notes.append("Predicate inferred from local compare/branch evidence.")
    notes.append("No semantic equivalence is claimed.")
    
    # 1. cbz / cbnz
    if site_type in ("cbz", "cbnz"):
        reg = site.get("register")
        is_cbnz = (site_type == "cbnz")
        cond = "!=" if is_cbnz else "=="
        if polarity == "inverted":
            cond = "==" if cond == "!=" else "!="
        mapped_reg = map_operand(reg)
        expr = f"{mapped_reg} {cond} 0"
        return "recovered", expr, None, notes
        
    # 2. tbz / tbnz
    elif site_type in ("tbz", "tbnz"):
        reg = site.get("register")
        bit = site.get("bit")
        is_tbnz = (site_type == "tbnz")
        
        mapped_reg = map_operand(reg)
        is_64 = mapped_reg.startswith("tmp_x") or mapped_reg in ("tmp_fp", "tmp_lr", "tmp_sp")
        suffix = "ull" if is_64 else "u"
        
        cond = "!=" if is_tbnz else "=="
        if polarity == "inverted":
            cond = "==" if cond == "!=" else "!="
            
        expr = f"({mapped_reg} & (1{suffix} << {bit})) {cond} 0"
        return "recovered", expr, None, notes
        
    # 3. cmp_branch_direct
    elif site_type == "cmp_branch_direct":
        op1 = site.get("operand1")
        op2 = site.get("operand2")
        branch_cond = site.get("branch_cond")
        
        if branch_cond not in BRANCH_MAP:
            return "skipped", None, "unsupported branch condition", []
            
        mapped_op = BRANCH_MAP[branch_cond]
        if polarity == "inverted":
            mapped_op = NEGATION_MAP[mapped_op]
            
        if branch_cond in UNSIGNED_BRANCHES:
            notes.append("unsigned branch condition; signedness approximate")
            
        expr = f"{map_operand(op1)} {mapped_op} {map_operand(op2)}"
        return "recovered", expr, None, notes
        
    # 4. cmp_branch_indirect
    elif site_type == "cmp_branch_indirect":
        comp_addr = site.get("comp_address")
        branch_cond = site.get("branch_cond")
        
        # Standardize compare address to match keys (usually hex strings)
        lookup_addr = comp_addr
        # if comp_addr doesn't start with 0x and lookup table keys do, prepend
        # Let's handle both
        if not lookup_addr.startswith("0x"):
            # try finding it as is, or with prefix
            if lookup_addr not in inst_lookup:
                lookup_addr = f"0x{lookup_addr}"
        else:
            if lookup_addr not in inst_lookup:
                # try without prefix
                lookup_addr = lookup_addr[2:]
                if lookup_addr not in inst_lookup:
                    lookup_addr = comp_addr # restore
                    
        inst = inst_lookup.get(lookup_addr)
        if not inst:
            return "skipped", None, "missing compare producer", []
            
        ops = parse_compare_instruction(inst)
        if not ops:
            return "skipped", None, "missing compare producer", []
            
        op1, op2 = ops
        
        if branch_cond not in BRANCH_MAP:
            return "skipped", None, "unsupported branch condition", []
            
        mapped_op = BRANCH_MAP[branch_cond]
        if polarity == "inverted":
            mapped_op = NEGATION_MAP[mapped_op]
            
        if branch_cond in UNSIGNED_BRANCHES:
            notes.append("unsigned branch condition; signedness approximate")
            
        expr = f"{map_operand(op1)} {mapped_op} {map_operand(op2)}"
        return "recovered", expr, None, notes
        
    return "skipped", None, "unsupported evidence format", []
