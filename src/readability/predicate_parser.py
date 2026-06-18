# -*- coding: utf-8 -*-
"""
Regex-based Predicate Parser for HEPHAESTUS_UNKNOWN_COND Strings
"""

import re
from typing import Dict, Any, Optional

def unescape_c_string(s: str) -> str:
    """Basic unescaping for C-style string content inside double quotes."""
    res = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            char = s[i+1]
            if char == 'n':
                res.append('\n')
            elif char == 't':
                res.append('\t')
            elif char == '\\':
                res.append('\\')
            elif char == '"':
                res.append('"')
            elif char == "'":
                res.append("'")
            else:
                res.append(char)
            i += 2
        else:
            res.append(s[i])
            i += 1
    return "".join(res)

def parse_adapter_polarity(adapter_str: str) -> str:
    """
    Determine the polarity of the adapter condition.
    Returns:
        "inverted": if explicit inversion markers exist
        "direct": if explicit direct markers exist
        "unclear": if "polarity" is mentioned but is ambiguous
        "assumed_direct": if no polarity or inversion words are mentioned at all
    """
    lower_str = adapter_str.lower()
    
    # Check explicit inversion markers first
    inversion_markers = [
        "loop polarity inverted",
        "branch polarity inverted",
        "condition polarity inverted",
        "polarity inverted",
        "inverted"
    ]
    for marker in inversion_markers:
        if marker in lower_str:
            return "inverted"
            
    # Check explicit direct markers
    direct_markers = [
        "polarity direct",
        "direct"
    ]
    for marker in direct_markers:
        if marker in lower_str:
            return "direct"
            
    # If "polarity" is in the string but wasn't matched above, it's unclear
    if "polarity" in lower_str:
        return "unclear"
        
    # Default case when no polarity language exists
    return "assumed_direct"

def parse_adapter_string(adapter_raw: str) -> Optional[Dict[str, Any]]:
    """
    Parses a HEPHAESTUS_UNKNOWN_COND unescaped adapter string.
    Returns a dict with parsed information, or None if completely unsupported format.
    """
    # Exclude condition unknown fallbacks
    if "condition unknown" in adapter_raw:
        return None
        
    # Detect branch polarity
    polarity = parse_adapter_polarity(adapter_raw)
    
    # Let's search for cbz/cbnz/tbz/tbnz
    cbz_match = re.search(r'\bcbz\s+([a-zA-Z0-9]+)\b', adapter_raw)
    cbnz_match = re.search(r'\bcbnz\s+([a-zA-Z0-9]+)\b', adapter_raw)
    tbz_match = re.search(r'\btbz\s+([a-zA-Z0-9]+)\s*,\s*#?([0-9]+)\b', adapter_raw)
    tbnz_match = re.search(r'\btbnz\s+([a-zA-Z0-9]+)\s*,\s*#?([0-9]+)\b', adapter_raw)
    
    if cbz_match:
        return {
            "type": "cbz",
            "register": cbz_match.group(1),
            "polarity": polarity,
            "raw_evidence": adapter_raw
        }
    elif cbnz_match:
        return {
            "type": "cbnz",
            "register": cbnz_match.group(1),
            "polarity": polarity,
            "raw_evidence": adapter_raw
        }
    elif tbz_match:
        return {
            "type": "tbz",
            "register": tbz_match.group(1),
            "bit": int(tbz_match.group(2)),
            "polarity": polarity,
            "raw_evidence": adapter_raw
        }
    elif tbnz_match:
        return {
            "type": "tbnz",
            "register": tbnz_match.group(1),
            "bit": int(tbnz_match.group(2)),
            "polarity": polarity,
            "raw_evidence": adapter_raw
        }
        
    # Check for cmp + conditional branch
    # Example: "cmp w8, w9; b.lt" or "cmp x0,#0 + b.ne"
    cmp_match = re.search(r'\bcmp\s+([a-zA-Z0-9]+)\s*,\s*(#?[a-zA-Z0-9]+)\b', adapter_raw)
    branch_match = re.search(r'\b(b\.[a-z]+)\b', adapter_raw)
    
    if cmp_match and branch_match:
        return {
            "type": "cmp_branch_direct",
            "operand1": cmp_match.group(1),
            "operand2": cmp_match.group(2),
            "branch_cond": branch_match.group(1),
            "polarity": polarity,
            "raw_evidence": adapter_raw
        }
        
    # Check for branch condition with "after cmp/subs at 0x..."
    # Example: "b.ge at 0x100000670 after subs at 0x10000066c"
    after_match = re.search(r'\bafter\s+(subs|cmp)\s+at\s+(0x[0-9a-fA-F]+|[0-9a-fA-F]+)\b', adapter_raw)
    if branch_match and after_match:
        return {
            "type": "cmp_branch_indirect",
            "comp_mnemonic": after_match.group(1),
            "comp_address": after_match.group(2),
            "branch_cond": branch_match.group(1),
            "polarity": polarity,
            "raw_evidence": adapter_raw
        }
        
    return None
