# -*- coding: utf-8 -*-
"""
Trace Report Builder Core Logic
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.validation.trace_report.models import TraceStatement, TraceFunction
from src.validation.trace_report.explainer import get_statement_explanation, compute_attention_level

def build_trace_report_payload(
    out_dir: Path,
    require_validation: bool = False,
    require_evidence_index: bool = True
) -> Dict[str, Any]:
    """
    Load evidence_index.json and optional validation_report.json,
    correlate findings, calculate summaries and attention items, and compile the trace report dict.
    """
    ev_path = out_dir / "evidence_index.json"
    val_path = out_dir / "validation_report.json"

    # 1. Load evidence_index
    if not ev_path.exists():
        if require_evidence_index:
            raise FileNotFoundError(f"Required evidence_index.json missing at {ev_path}")
        else:
            # Fallback degraded mode
            evidence_index = {"summary": {}, "functions": [], "global_statements": []}
    else:
        with open(ev_path, "r", encoding="utf-8") as f:
            evidence_index = json.load(f)

    # 2. Load validation_report
    validation_report = None
    if val_path.exists():
        with open(val_path, "r", encoding="utf-8") as f:
            validation_report = json.load(f)
    elif require_validation:
        raise FileNotFoundError(f"Required validation_report.json missing at {val_path}")

    findings: List[Dict[str, Any]] = []
    if validation_report and isinstance(validation_report, dict):
        findings = validation_report.get("findings", [])

    # 3. Initialize models
    global_statements: List[TraceStatement] = []
    functions: List[TraceFunction] = []

    # Map statements for easy lookup
    statement_lookup: Dict[str, TraceStatement] = {}
    line_lookup: Dict[int, TraceStatement] = {}

    # Initialize Global Statements
    for idx, gs_dict in enumerate(evidence_index.get("global_statements", [])):
        stmt_id = gs_dict.get("statement_id", f"global_{idx+1:06d}")
        line_num = gs_dict.get("line_number", 0)
        cat = gs_dict.get("category", "unknown")
        sub = gs_dict.get("subcategory")
        conf = gs_dict.get("confidence", "unknown")
        text = gs_dict.get("statement_text", "")
        
        # Build evidence dict
        evidence_dict = {
            "block_id": None,
            "instruction_address": None,
            "instruction_mnemonic": None,
            "raw_instruction": None,
            "evidence_sources": gs_dict.get("evidence_sources", [])
        }

        ts = TraceStatement(
            statement_id=stmt_id,
            line_number=line_num,
            category=cat,
            subcategory=sub,
            confidence=conf,
            statement_text=text,
            short_explanation=get_statement_explanation(cat, conf),
            evidence=evidence_dict,
            notes=gs_dict.get("notes", [])
        )
        global_statements.append(ts)
        statement_lookup[stmt_id] = ts
        if line_num > 0:
            line_lookup[line_num] = ts

    # Initialize Functions and Function Statements
    for fn_dict in evidence_index.get("functions", []):
        func_name = fn_dict.get("name", "unknown")
        c_name = fn_dict.get("c_name", "unknown")
        entry = fn_dict.get("entry_point")
        
        tf = TraceFunction(
            name=func_name,
            c_name=c_name,
            entry_point=entry
        )
        
        for idx, s_dict in enumerate(fn_dict.get("statements", [])):
            stmt_id = s_dict.get("statement_id", f"stmt_{idx+1:06d}")
            line_num = s_dict.get("line_number", 0)
            cat = s_dict.get("category", "unknown")
            sub = s_dict.get("subcategory")
            conf = s_dict.get("confidence", "unknown")
            text = s_dict.get("statement_text", "")
            
            evidence_dict = {
                "block_id": s_dict.get("block_id"),
                "instruction_address": s_dict.get("instruction_address"),
                "instruction_mnemonic": s_dict.get("instruction_mnemonic"),
                "raw_instruction": s_dict.get("raw_instruction"),
                "evidence_sources": s_dict.get("evidence_sources", [])
            }

            ts = TraceStatement(
                statement_id=stmt_id,
                line_number=line_num,
                category=cat,
                subcategory=sub,
                confidence=conf,
                statement_text=text,
                short_explanation=get_statement_explanation(cat, conf),
                evidence=evidence_dict,
                notes=s_dict.get("notes", [])
            )
            tf.statements.append(ts)
            statement_lookup[stmt_id] = ts
            if line_num > 0:
                line_lookup[line_num] = ts
                
        functions.append(tf)

    # 4. Attach Validation Findings to Statements
    unattached_findings: List[Dict[str, Any]] = []
    
    # We will build finding-to-line matching logic
    for f in findings:
        loc = f.get("location", {})
        if not isinstance(loc, dict):
            loc = {}

        stmt_matched = None

        # Priority 1: line number exact
        line = loc.get("line")
        if line is not None:
            try:
                line_val = int(line)
                if line_val in line_lookup:
                    stmt_matched = line_lookup[line_val]
            except (ValueError, TypeError):
                pass

        # Priority 2: statement_id exact
        if stmt_matched is None:
            fid = f.get("statement_id") or loc.get("statement_id")
            if fid in statement_lookup:
                stmt_matched = statement_lookup[fid]

        # Priority 3: function + block_id
        if stmt_matched is None:
            func_name = loc.get("function")
            block_id = loc.get("block_id")
            if func_name and block_id:
                for fn in functions:
                    if fn.name == func_name or fn.c_name == func_name:
                        for s in fn.statements:
                            if s.evidence.get("block_id") == block_id:
                                stmt_matched = s
                                break
                        if stmt_matched:
                            break

        # Priority 4: function + instruction address
        if stmt_matched is None:
            func_name = loc.get("function")
            addr = loc.get("address")
            if func_name and addr:
                for fn in functions:
                    if fn.name == func_name or fn.c_name == func_name:
                        for s in fn.statements:
                            if s.evidence.get("instruction_address") == addr:
                                stmt_matched = s
                                break
                        if stmt_matched:
                            break

        # Priority 5: category fallback (if has function, match to signature line)
        if stmt_matched is None:
            func_name = loc.get("function")
            if func_name:
                for fn in functions:
                    if fn.name == func_name or fn.c_name == func_name:
                        for s in fn.statements:
                            if s.category == "function_signature":
                                stmt_matched = s
                                break
                        if stmt_matched:
                            break

        if stmt_matched:
            stmt_matched.validation_findings.append(f)
        else:
            unattached_findings.append(f)

    # 5. Post-Process Models: compute attention levels & build aggregates
    global_stmt_count = len(global_statements)
    func_stmt_count = 0
    evidence_backed_count = 0
    generated_scaffold_count = 0
    syntax_adapter_count = 0
    commentary_only_count = 0
    unknown_confidence_count = 0
    high_attention_lines = 0

    category_summary = {
        "executable_lowered": 0, "true_unsupported": 0, "comment_lowered": 0,
        "branch_evidence": 0, "syntax_adapter": 0, "helper": 0,
        "declaration": 0, "call": 0, "return": 0, "control_flow_scaffold": 0,
        "function_signature": 0, "empty_function_scaffold": 0, "unknown": 0
    }
    
    confidence_summary = {
        "evidence_backed": 0, "generated_scaffold": 0, "syntax_adapter": 0,
        "commentary_only": 0, "unknown": 0
    }

    # Helper function to process TraceStatements
    def process_statement(s: TraceStatement) -> None:
        nonlocal evidence_backed_count, generated_scaffold_count, syntax_adapter_count
        nonlocal commentary_only_count, unknown_confidence_count, high_attention_lines
        
        # Calculate attention level
        s.attention_level = compute_attention_level(s.category, s.confidence, s.validation_findings)
        if s.attention_level in ("warning", "error"):
            high_attention_lines += 1

        # Accumulate category counts
        category_summary[s.category] = category_summary.get(s.category, 0) + 1

        # Accumulate confidence counts
        confidence_summary[s.confidence] = confidence_summary.get(s.confidence, 0) + 1
        if s.confidence == "evidence_backed":
            evidence_backed_count += 1
        elif s.confidence == "generated_scaffold":
            generated_scaffold_count += 1
        elif s.confidence == "syntax_adapter":
            syntax_adapter_count += 1
        elif s.confidence == "commentary_only":
            commentary_only_count += 1
        else:
            unknown_confidence_count += 1

    # Process Global Statements
    for gs in global_statements:
        process_statement(gs)

    # Process Functions
    for fn in functions:
        fn_statements_count = len(fn.statements)
        func_stmt_count += fn_statements_count
        fn.statements_total = fn_statements_count
        
        # Build local aggregates for this function
        fn_cat_sum: Dict[str, int] = {}
        fn_conf_sum: Dict[str, int] = {}
        fn_attention_items: List[Dict[str, Any]] = []

        for s in fn.statements:
            process_statement(s)
            
            # Local category/confidence summaries
            fn_cat_sum[s.category] = fn_cat_sum.get(s.category, 0) + 1
            fn_conf_sum[s.confidence] = fn_conf_sum.get(s.confidence, 0) + 1
            
            if s.attention_level != "none":
                fn_attention_items.append(s.to_dict())

        fn.category_summary = fn_cat_sum
        fn.confidence_summary = fn_conf_sum
        fn.attention_items = fn_attention_items

    statements_total = global_stmt_count + func_stmt_count

    # Group validation findings by category
    findings_by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for f in findings:
        cat = f.get("category", "unknown")
        if cat not in findings_by_cat:
            findings_by_cat[cat] = []
        findings_by_cat[cat].append(f)

    # Validation errors/warnings totals
    val_errors = sum(1 for f in findings if f.get("severity", "").lower() in ("error", "failed"))
    val_warnings = sum(1 for f in findings if f.get("severity", "").lower() == "warning")

    # Determine status
    if val_errors > 0:
        status = "failed"
    elif val_warnings > 0 or category_summary.get("unknown", 0) > 0 or confidence_summary.get("unknown", 0) > 0:
        status = "warning"
    else:
        status = "ok"

    summary = {
        "functions_total": len(functions),
        "statements_total": statements_total,
        "evidence_backed_statements": evidence_backed_count,
        "generated_scaffold_statements": generated_scaffold_count,
        "syntax_adapter_statements": syntax_adapter_count,
        "commentary_only_statements": commentary_only_count,
        "unknown_confidence_statements": unknown_confidence_count,
        "validation_findings_total": len(findings),
        "validation_errors": val_errors,
        "validation_warnings": val_warnings,
        "high_attention_lines": high_attention_lines
    }

    payload = {
        "schema_version": "trace-report-1.0",
        "phase": "6.3",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "input_artifacts": {
            "source_reconstruction": "source_reconstruction.json" if (out_dir / "source_reconstruction.json").exists() else None,
            "recovered_c": "recovered.c" if (out_dir / "recovered.c").exists() else None,
            "evidence_index": "evidence_index.json" if ev_path.exists() else None,
            "validation_report": "validation_report.json" if val_path.exists() else None
        },
        "status": status,
        "summary": summary,
        "category_summary": category_summary,
        "confidence_summary": confidence_summary,
        "functions": [fn.to_dict() for fn in functions],
        "global_statements": [gs.to_dict() for gs in global_statements],
        "validation_findings_by_category": findings_by_cat,
        "unattached_validation_findings": unattached_findings,
        "diagnostics": []
    }
    return payload
