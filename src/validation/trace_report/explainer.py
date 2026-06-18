# -*- coding: utf-8 -*-
"""
Trace Report Explanations & Attention Levels
"""

from __future__ import annotations
from typing import List, Dict, Any

def get_statement_explanation(category: str, confidence: str) -> str:
    """Return deterministic explanation string for a statement category & confidence."""
    if category == "executable_lowered":
        if confidence == "evidence_backed":
            return "Executable lowered statement backed by instruction evidence."
        else:
            return "Executable lowered statement without detailed instruction provenance in the current artifacts."
    elif category == "true_unsupported":
        return "Instruction was not lowered and is preserved as an unsupported statement/comment."
    elif category == "comment_lowered":
        return "Recognized instruction or event preserved as conservative commentary rather than executable C semantics."
    elif category == "branch_evidence":
        return "Control-flow evidence preserved as a comment; no executable condition was recovered."
    elif category == "syntax_adapter":
        return "Syntax adapter emitted to keep recovered C compilable without inventing semantics."
    elif category == "helper":
        return "Generated helper used by syntax adapters; not recovered source logic."
    elif category == "declaration":
        return "Generated pseudo declaration for recovered temporaries, stack slots, helpers, or typedefs."
    elif category == "call":
        return "Call statement or indirect-call evidence derived from call-site recovery/lowering."
    elif category == "return":
        return "Return statement/comment derived from ABI return recovery or conservative fallback."
    elif category == "control_flow_scaffold":
        return "Generated control-flow scaffold preserving structured regions without inventing high-level conditions."
    elif category == "function_signature":
        return "Generated function signature derived from recovered symbol/type metadata."
    elif category == "empty_function_scaffold":
        return "Generated empty-function scaffold for a function with no recovered body evidence."
    else:
        return "Statement could not be classified by the Phase 6.3 trace builder."

def compute_attention_level(category: str, confidence: str, findings: List[Dict[str, Any]]) -> str:
    """
    Compute attention level for a statement.
    Priority: error > warning > info > none
    """
    # 1. Error if any validation finding with severity 'error' or 'failed' is attached
    for f in findings:
        sev = f.get("severity", "").lower()
        if sev in ("error", "failed"):
            return "error"
            
    # 2. Warning check
    # Check attached findings for warnings
    for f in findings:
        sev = f.get("severity", "").lower()
        if sev == "warning":
            return "warning"
            
    # Check category/confidence rules for warning
    if category == "unknown" or confidence == "unknown" or category == "true_unsupported":
        return "warning"
        
    # 3. Info check
    if category in ("comment_lowered", "branch_evidence", "syntax_adapter"):
        return "info"
        
    # 4. None
    return "none"
