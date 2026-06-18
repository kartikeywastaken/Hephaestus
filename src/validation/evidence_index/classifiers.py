# -*- coding: utf-8 -*-
"""
Evidence Index Statement Classifiers
"""

from __future__ import annotations
import re
from typing import Dict, Any, Tuple, Optional

def is_pure_comment(line: str) -> bool:
    """Check if a line is a pure comment (starts and ends with comment markers)."""
    s = line.strip()
    if not s:
        return False
    if s.startswith("/*") and s.endswith("*/"):
        return True
    if s.startswith("//"):
        return True
    return False

def classify_line(line: str, unsupported_instruction_kinds: Dict[str, int]) -> Tuple[str, Optional[str]]:
    """
    Classify a line of C code into exactly one primary category and subcategory.
    Returns (primary_category, subcategory).
    
    Category Precedence:
    1. helper
    2. declaration
    3. function_signature
    4. empty_function_scaffold
    5. syntax_adapter
    6. true_unsupported
    7. branch_evidence
    8. call
    9. return
    10. control_flow_scaffold
    11. comment_lowered
    12. executable_lowered
    13. unknown
    """
    s = line.strip()
    
    # 1. helper definitions
    if s.startswith("static int HEPHAESTUS_UNKNOWN_COND") or s.startswith("static u64 HEPHAESTUS_CSET"):
        return "helper", "helper_definition"
        
    # 2. declaration
    # Typedefs
    if s.startswith("typedef "):
        return "declaration", "typedef"
    # Function prototypes (ends with ; and has ( and does not start with return or assignments)
    if s.endswith(";") and "(" in s and ")" in s and not ("=" in s or "return" in s or "call_" in s):
        # e.g., "int32_t main(int32_t argc, char ** argv);" or "u64 call_0x...();"
        return "declaration", "prototype"
    # Local variable declarations, e.g. "u64 tmp_sp = 0;"
    # Matches u64/u32/etc. with assignment to 0
    if s.endswith(";") and "=" in s:
        # e.g. "u64 tmp_x8 = 0;"
        decl_match = re.match(r"^(u8|u16|u32|u64|i8|i16|i32|i64|uint8_t|uint16_t|uint32_t|uint64_t|int8_t|int16_t|int32_t|int64_t|void\s*\*|char\s*\*\s*\*)\s+(tmp_|stack_|var_)[a-zA-Z0-9_]+\s*=", s)
        if decl_match:
            return "declaration", "local_declaration"
            
    # 3. function_signature (this is set during parsing when a function definition starts, handled in builder)
    
    # 4. empty_function_scaffold
    if "TODO: body reconstruction pending" in s or "empty function" in s:
        return "empty_function_scaffold", None
        
    # 5. syntax_adapter
    if "HEPHAESTUS_UNKNOWN_COND(" in s:
        if s.startswith("if ") or s.startswith("while "):
            return "syntax_adapter", "control_flow_condition"
        return "syntax_adapter", "unknown_condition"
    if "HEPHAESTUS_CSET(" in s:
        return "syntax_adapter", "cset"
        
    # 6. true_unsupported & comment_lowered (distinguished via unsupported_instruction_kinds)
    if "unsupported" in s.lower():
        # Attempt to extract mnemonic
        mnemonic = None
        m1 = re.search(r"unsupported\s+instruction:\s*([a-zA-Z0-9_]+)", s, re.IGNORECASE)
        if m1:
            mnemonic = m1.group(1).lower()
        else:
            m2 = re.search(r"unsupported\s+([a-zA-Z0-9_]+)", s, re.IGNORECASE)
            if m2:
                mnemonic = m2.group(1).lower()
                
        # Verify mnemonic against unsupported_instruction_kinds summary
        is_true = False
        matched_kind = None
        if mnemonic and mnemonic in unsupported_instruction_kinds:
            is_true = True
            matched_kind = mnemonic
        else:
            # Check if any of the keys exists in the line text
            for kind in unsupported_instruction_kinds.keys():
                if kind.lower() in s.lower():
                    is_true = True
                    matched_kind = kind.lower()
                    break
                    
        if is_true:
            return "true_unsupported", matched_kind
        else:
            return "comment_lowered", "unsupported_comment_fallback"
            
    # 7. branch_evidence
    if is_pure_comment(s):
        # e.g. "/* branch to 0x100000578 */" or "/* tbz tmp_w8 bit 0 -> 0x10000065c */"
        has_branch_term = re.search(r"\b(cbz|cbnz|tbz|tbnz|b\.[a-z]+|conditional branch|branch to|branch)\b", s, re.IGNORECASE)
        has_target = "->" in s or "0x" in s or "block " in s
        if has_branch_term and has_target:
            return "branch_evidence", None
            
    # 8. call
    if "call_0x" in s:
        return "call", "direct_call"
    if "indirect call" in s.lower() or "blr " in s.lower():
        return "call", "indirect_call_comment"
        
    # 9. return
    if s.startswith("return ") or s.startswith("return;"):
        return "return", "return_statement"
    if is_pure_comment(s) and "return" in s.lower():
        return "return", "return_comment"
        
    # 10. control_flow_scaffold
    if s.startswith("if (") or s.startswith("while (") or s.startswith("} else") or s.startswith("else") or s == "{" or s == "}":
        return "control_flow_scaffold", None
        
    # 11. comment_lowered
    if is_pure_comment(s):
        return "comment_lowered", None
        
    # 12. executable_lowered
    if s.endswith(";"):
        return "executable_lowered", None
        
    # 13. unknown
    return "unknown", None
