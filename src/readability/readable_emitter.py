# -*- coding: utf-8 -*-
"""
Readable C Emitter
Writes recovered_readable.c by replacing HEPHAESTUS_UNKNOWN_COND wrappers with recovered predicates.
"""

import re
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("readability.emitter")

# Match: if/while ( HEPHAESTUS_UNKNOWN_COND ( "..." ) )
SITE_REGEX = re.compile(r'\b(if|while)\s*\(\s*HEPHAESTUS_UNKNOWN_COND\("((?:\\.|[^"\\])*)"\)\s*\)')

DISCLAIMER_HEADER = """/*
 * Hephaestus recovered_readable.c
 * Phase 7.1 static predicate recovery.
 * Best-effort human-readable approximation.
 * No semantic equivalence is claimed.
 * See readability_report.json for inferred predicates and skipped sites.
 */
"""

def extract_candidate_sites(recovered_c: str) -> List[Dict[str, Any]]:
    """
    Scans recovered_c and extracts all candidate HEPHAESTUS_UNKNOWN_COND wrapper sites.
    Does not modify content.
    """
    candidates = []
    lines = recovered_c.splitlines()
    
    # Simple regex to guess current function name
    func_regex = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_* ]+\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*\{?')
    current_function = "unknown"
    
    for idx, line in enumerate(lines):
        line_num = idx + 1
        
        # Keep track of the current function name
        func_match = func_regex.match(line)
        if func_match:
            current_function = func_match.group(1)
            # ignore standard keywords
            if current_function in ("if", "while", "for", "switch", "return"):
                current_function = "unknown"
                
        for match in SITE_REGEX.finditer(line):
            kind = match.group(1)
            adapter_raw = match.group(2)
            candidates.append({
                "line_number": line_num,
                "kind": kind,
                "original_condition": match.group(0),
                "adapter_raw": adapter_raw,
                "function": current_function,
                "full_line": line
            })
            
    return candidates

def emit_readable_c(
    recovered_c: str, 
    recovered_sites: Dict[int, Tuple[str, str]]
) -> str:
    """
    Generates recovered_readable.c contents.
    Args:
        recovered_c: contents of recovered.c
        recovered_sites: dict mapping line_number (1-indexed) -> (replacement_expr, source_name)
    """
    lines = recovered_c.splitlines(keepends=True)
    new_lines = []
    
    for idx, line in enumerate(lines):
        line_num = idx + 1
        if line_num not in recovered_sites:
            new_lines.append(line)
            continue
            
        replacement_expr, source_name = recovered_sites[line_num]
        
        # Remove line endings first to handle replacement cleanly
        line_no_ending = line.rstrip('\r\n')
        ending = line[len(line_no_ending):]
        
        m = SITE_REGEX.search(line_no_ending)
        if not m:
            new_lines.append(line)
            continue
            
        kind = m.group(1)
        matched_str = m.group(0)
        
        # Build replaced condition part
        replacement_part = f"{kind} ({replacement_expr})"
        left_str = line_no_ending[:m.start()]
        right_str = line_no_ending[m.end():]
        
        # Inject the uncertainty comment
        comment_text = f"/* inferred from {source_name}; uncertain */"
        
        if '{' in right_str:
            left_brace, right_brace = right_str.split('{', 1)
            if right_brace.strip():
                new_right = f"{left_brace}{{ {comment_text} {right_brace}"
            else:
                new_right = f"{left_brace}{{ {comment_text}"
        else:
            new_right = f"{right_str} {comment_text}"
            
        new_line = left_str + replacement_part + new_right + ending
        new_lines.append(new_line)
        
    return DISCLAIMER_HEADER + "".join(new_lines)
