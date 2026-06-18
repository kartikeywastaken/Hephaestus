# -*- coding: utf-8 -*-
"""
Evidence Index Statement Matcher
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Optional, Tuple

def normalize_text(text: str) -> str:
    """Normalize text by stripping ends and collapsing internal whitespace runs."""
    return re.sub(r"\s+", " ", text.strip())

def match_statement_to_provenance(
    line: str,
    category: str,
    lowered_statements: List[Dict[str, Any]],
    current_block_id: Optional[str] = None
) -> Tuple[str, Dict[str, Any], List[str]]:
    """
    Attempt to match a statement line to decompiler provenance.
    Returns (confidence, matched_provenance, notes).
    
    Provenance dict contains:
      - block_id
      - instruction_address
      - instruction_mnemonic
      - raw_instruction
      - evidence_sources
    """
    normalized_line = normalize_text(line)
    
    matched_stmt: Optional[Dict[str, Any]] = None
    
    # 1. Exact normalized line match
    for stmt in lowered_statements:
        if normalize_text(stmt.get("text", "")) == normalized_line:
            matched_stmt = stmt
            break
            
    # 2. Try raw instruction string match
    if not matched_stmt:
        for stmt in lowered_statements:
            instr = stmt.get("source_instruction")
            if instr and isinstance(instr, dict):
                raw = instr.get("raw")
                if raw and raw in line:
                    matched_stmt = stmt
                    break
                    
    # 3. Try instruction address match
    if not matched_stmt:
        # e.g., "0x100000abc" in line
        addresses = re.findall(r"0x[0-9a-fA-F]+", line)
        for addr in addresses:
            for stmt in lowered_statements:
                stmt_addr = stmt.get("address")
                if stmt_addr and stmt_addr.lower() == addr.lower():
                    matched_stmt = stmt
                    break
                instr = stmt.get("source_instruction")
                if instr and isinstance(instr, dict):
                    ins_addr = instr.get("address")
                    if ins_addr and ins_addr.lower() == addr.lower():
                        matched_stmt = stmt
                        break
            if matched_stmt:
                break
                
    # 4. Try block ID matching or extraction
    block_id = current_block_id
    block_match = re.search(r"block\s+(0x[0-9a-fA-F]+)", line)
    if block_match:
        block_id = block_match.group(1)
        
    provenance: Dict[str, Any] = {
        "block_id": block_id,
        "instruction_address": None,
        "instruction_mnemonic": None,
        "raw_instruction": None,
        "evidence_sources": []
    }
    notes: List[str] = []
    
    if matched_stmt:
        provenance["instruction_address"] = matched_stmt.get("address")
        instr = matched_stmt.get("source_instruction")
        if instr and isinstance(instr, dict):
            provenance["instruction_mnemonic"] = instr.get("mnemonic")
            provenance["raw_instruction"] = instr.get("raw")
            if not provenance["block_id"]:
                provenance["block_id"] = instr.get("block_id")
            provenance["instruction_address"] = instr.get("address") or provenance["instruction_address"]
            
        provenance["evidence_sources"] = [
            "source_reconstruction.lowered_blocks",
            "unified_ir.basic_blocks.instructions"
        ]
        return "evidence_backed", provenance, notes
        
    # Classifier Fallback
    provenance["evidence_sources"] = ["classifier_fallback"]
    
    if category == "syntax_adapter":
        confidence = "syntax_adapter"
    elif category in ("declaration", "helper", "function_signature", "control_flow_scaffold", "empty_function_scaffold"):
        confidence = "generated_scaffold"
    elif category in ("comment_lowered", "branch_evidence"):
        confidence = "commentary_only"
    elif category == "call" and ("blr" in line.lower() or "indirect call" in line.lower()):
        confidence = "commentary_only"
    elif category == "return" and ("return value" in line.lower() or "ret" in line.lower() or "/*" in line):
        confidence = "commentary_only"
    elif category == "executable_lowered":
        confidence = "unknown"
        notes.append("VAL-IDX-001 executable lowered statement lacks instruction provenance")
    else:
        confidence = "unknown"
        
    return confidence, provenance, notes
