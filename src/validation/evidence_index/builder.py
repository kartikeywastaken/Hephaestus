# -*- coding: utf-8 -*-
"""
Evidence Index Builder
"""

from __future__ import annotations
import json
import hashlib
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set

from src.validation.evidence_index.models import StatementEntry, GlobalStatementEntry, FunctionIndex
from src.validation.evidence_index.classifiers import classify_line, is_pure_comment
from src.validation.evidence_index.matcher import match_statement_to_provenance, normalize_text

def count_braces(line: str) -> Tuple[int, int]:
    """Count open and close braces outside comments."""
    cleaned = re.sub(r"/\*.*?\*/", "", line)
    cleaned = re.sub(r"//.*", "", cleaned)
    return cleaned.count("{"), cleaned.count("}")

def build_index_payload(out_dir: Path) -> Dict[str, Any]:
    """
    Read source reconstruction and C skeletons, segment lines,
    run classifiers/matchers, and compile the index dictionary.
    """
    recon_path = out_dir / "source_reconstruction.json"
    c_path = out_dir / "recovered.c"
    
    if not recon_path.exists():
        raise FileNotFoundError(f"Missing source_reconstruction.json at {recon_path}")
    if not c_path.exists():
        raise FileNotFoundError(f"Missing recovered.c at {c_path}")
        
    with open(recon_path, "r", encoding="utf-8") as f:
        reconstruction = json.load(f)
        
    with open(c_path, "r", encoding="utf-8") as f:
        c_content = f.read()
        
    unsupported_kinds = reconstruction.get("summary", {}).get("unsupported_instruction_kinds", {})
    if not isinstance(unsupported_kinds, dict):
        unsupported_kinds = {}
        
    # Build function lookup map
    # Some functions have c_name (e.g. main) and name (e.g. _main)
    functions_map: Dict[str, Dict[str, Any]] = {}
    funcs_list = reconstruction.get("data", {}).get("functions", [])
    if not funcs_list and "functions" in reconstruction:
        funcs_list = reconstruction.get("functions", [])
        
    for fn in funcs_list:
        c_name = fn.get("c_name") or fn.get("name")
        if c_name:
            functions_map[c_name] = fn
            
    c_lines = c_content.splitlines()
    
    global_entries: List[GlobalStatementEntry] = []
    function_indices: List[FunctionIndex] = []
    function_indices_map: Dict[str, FunctionIndex] = {}
    
    current_fn_c_name: Optional[str] = None
    current_fn_info: Optional[Dict[str, Any]] = None
    brace_depth = 0
    entered_body = False
    
    global_stmt_count = 0
    func_stmt_count = 0
    current_block_id: Optional[str] = None
    
    # Summary category counts
    category_counts = {
        "executable_lowered": 0,
        "true_unsupported": 0,
        "comment_lowered": 0,
        "branch_evidence": 0,
        "syntax_adapter": 0,
        "helper": 0,
        "declaration": 0,
        "call": 0,
        "return": 0,
        "control_flow_scaffold": 0,
        "function_signature": 0,
        "empty_function_scaffold": 0,
        "unknown": 0
    }
    
    evidence_backed_count = 0
    non_evidence_backed_count = 0
    
    for idx, raw_line in enumerate(c_lines):
        line_num = idx + 1
        stripped = raw_line.strip()
        
        if not stripped:
            # Skip blank lines
            continue
            
        normalized = normalize_text(raw_line)
        h = hashlib.sha256()
        h.update(normalized.encode("utf-8"))
        text_hash = f"sha256:{h.hexdigest()}"
        
        # Check if this line starts a function definition
        if current_fn_c_name is None:
            for c_name, fn_info in functions_map.items():
                # Signature regex pattern (type followed by name and parens, no ending semicolon)
                pattern = r"^\s*[a-zA-Z0-9_ *&]+\s+" + re.escape(c_name) + r"\s*\([^;]*\)\s*$"
                if re.match(pattern, stripped):
                    current_fn_c_name = c_name
                    current_fn_info = fn_info
                    brace_depth = 0
                    entered_body = False
                    current_block_id = None
                    break
                    
        # Process the statement line
        if current_fn_c_name is None:
            # Global Statement
            global_stmt_count += 1
            stmt_id = f"global_{global_stmt_count:06d}"
            
            category, subcategory = classify_line(raw_line, unsupported_kinds)
            # Matcher fallback for global elements
            confidence = "generated_scaffold"
            if category == "helper" or category == "declaration":
                confidence = "generated_scaffold"
            elif category == "comment_lowered":
                confidence = "commentary_only"
                
            evidence_sources = ["classifier_fallback"]
            if category == "helper":
                evidence_sources = ["source_emitter.generated_helper"]
            elif category == "declaration":
                evidence_sources = ["source_emitter.generated_prototype"]
                
            entry = GlobalStatementEntry(
                statement_id=stmt_id,
                line_number=line_num,
                text_hash=text_hash,
                statement_text=stripped,
                category=category,
                subcategory=subcategory,
                confidence=confidence,
                evidence_sources=evidence_sources
            )
            global_entries.append(entry)
            category_counts[category] = category_counts.get(category, 0) + 1
            non_evidence_backed_count += 1
            
        else:
            # Function Statement
            func_stmt_count += 1
            stmt_id = f"stmt_{func_stmt_count:06d}"
            
            # Segment block IDs from comment lines
            block_match = re.search(r"block\s+(0x[0-9a-fA-F]+)", stripped)
            if block_match:
                current_block_id = block_match.group(1)
                
            # Classify line
            category, subcategory = classify_line(raw_line, unsupported_kinds)
            
            # Override for signature line itself
            is_sig = False
            # Check if it is the function signature line
            pattern = r"^\s*[a-zA-Z0-9_ *&]+\s+" + re.escape(current_fn_c_name) + r"\s*\([^;]*\)\s*$"
            if re.match(pattern, stripped):
                category = "function_signature"
                subcategory = None
                is_sig = True
                
            # Track brace depth
            opens, closes = count_braces(raw_line)
            if opens > 0:
                entered_body = True
            brace_depth += (opens - closes)
            
            # Evidence Matching
            lowered_stmts = current_fn_info.get("lowered_statements", [])
            # Also fall back to lowered_blocks if statements list is empty
            if not lowered_stmts and "lowered_blocks" in current_fn_info:
                lowered_stmts = []
                for b_stmts in current_fn_info["lowered_blocks"].values():
                    if isinstance(b_stmts, list):
                        lowered_stmts.extend(b_stmts)
                        
            # Execute match logic
            if is_sig:
                confidence = "generated_scaffold"
                provenance = {
                    "block_id": None,
                    "instruction_address": None,
                    "instruction_mnemonic": None,
                    "raw_instruction": None,
                    "evidence_sources": ["classifier_fallback"]
                }
                notes = []
            else:
                confidence, provenance, notes = match_statement_to_provenance(
                    raw_line, category, lowered_stmts, current_block_id
                )
                
            # Count evidence status
            if confidence == "evidence_backed":
                evidence_backed_count += 1
            else:
                non_evidence_backed_count += 1
                
            # Build statement entry
            entry = StatementEntry(
                statement_id=stmt_id,
                line_number=line_num,
                text_hash=text_hash,
                statement_text=stripped,
                category=category,
                subcategory=subcategory,
                confidence=confidence,
                function=current_fn_info.get("name"),
                block_id=provenance.get("block_id"),
                instruction_address=provenance.get("instruction_address"),
                instruction_mnemonic=provenance.get("instruction_mnemonic"),
                raw_instruction=provenance.get("raw_instruction"),
                evidence_sources=provenance.get("evidence_sources"),
                notes=notes
            )
            
            # Add to function index
            if current_fn_c_name not in function_indices_map:
                fn_idx = FunctionIndex(
                    name=current_fn_info.get("name", current_fn_c_name),
                    c_name=current_fn_c_name,
                    entry_point=current_fn_info.get("entry_point")
                )
                function_indices.append(fn_idx)
                function_indices_map[current_fn_c_name] = fn_idx
                
            function_indices_map[current_fn_c_name].statements.append(entry)
            category_counts[category] = category_counts.get(category, 0) + 1
            
            # Check if function context ends
            if entered_body and brace_depth <= 0:
                current_fn_c_name = None
                current_fn_info = None
                entered_body = False
                brace_depth = 0
                current_block_id = None
                
    statements_total = global_stmt_count + func_stmt_count
    
    # Map counts to required keys
    summary = {
        "functions_total": len(function_indices),
        "statements_total": statements_total,
        "statements_with_instruction_evidence": evidence_backed_count,
        "statements_without_instruction_evidence": non_evidence_backed_count,
        "executable_lowered_statements": category_counts["executable_lowered"],
        "true_unsupported_statements": category_counts["true_unsupported"],
        "comment_lowered_statements": category_counts["comment_lowered"],
        "branch_evidence_comments": category_counts["branch_evidence"],
        "syntax_adapter_statements": category_counts["syntax_adapter"],
        "helper_statements": category_counts["helper"],
        "declaration_statements": category_counts["declaration"],
        "call_statements": category_counts["call"],
        "return_statements": category_counts["return"],
        "control_flow_scaffold_statements": category_counts["control_flow_scaffold"],
        "function_signature_statements": category_counts["function_signature"],
        "empty_function_scaffold_statements": category_counts["empty_function_scaffold"],
        "unknown_statement_category": category_counts["unknown"]
    }
    
    # Build complete index dict
    from datetime import datetime, timezone
    payload = {
        "schema_version": "evidence-index-1.0",
        "phase": "6.2",
        "source_schema_version": reconstruction.get("schema_version", "5.7.2"),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),

        "input_artifacts": {
            "source_reconstruction": "source_reconstruction.json",
            "recovered_c": "recovered.c",
            "unified_ir": "unified_ir.json" if (out_dir / "unified_ir.json").exists() else None,
            "phase4_semantics": "phase4_semantics.json" if (out_dir / "phase4_semantics.json").exists() else None
        },
        "summary": summary,
        "functions": [f.to_dict() for f in function_indices],
        "global_statements": [g.to_dict() for g in global_entries],
        "diagnostics": []
    }
    return payload
