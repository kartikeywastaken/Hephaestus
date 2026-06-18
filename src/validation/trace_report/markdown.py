# -*- coding: utf-8 -*-
"""
Trace Report Human-Readable Markdown Generator
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List

def write_trace_markdown(payload: Dict[str, Any], out_dir: Path) -> Path:
    """Generate and write trace_report.md human-readable summary."""
    md_file = out_dir / "trace_report.md"
    
    summary = payload.get("summary", {})
    cat_summary = payload.get("category_summary", {})
    conf_summary = payload.get("confidence_summary", {})
    status = payload.get("status", "unknown")
    
    lines: List[str] = []
    lines.append("# Hephaestus Trace Report")
    lines.append("")
    lines.append("This report details statement-level evidence traceability and validation explainability to assist in manual audits. It details the categorization of emitted statements, correlates validation findings to specific lines, and flags elements needing high attention.")
    lines.append("")
    lines.append("> [!NOTE]")
    lines.append("> Trace reports improve **explainability and auditability**, not semantic correctness. This report does not prove semantic equivalence to the original binary target behavior.")
    lines.append("")
    
    # Section: Summary
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("| :--- | :--- |")
    lines.append(f"| Functions Total | {summary.get('functions_total', 0)} |")
    lines.append(f"| Statements Total | {summary.get('statements_total', 0)} |")
    lines.append(f"| Evidence-Backed Statements | {summary.get('evidence_backed_statements', 0)} |")
    lines.append(f"| Generated Scaffold Statements | {summary.get('generated_scaffold_statements', 0)} |")
    lines.append(f"| Syntax Adapter Statements | {summary.get('syntax_adapter_statements', 0)} |")
    lines.append(f"| Commentary-Only Statements | {summary.get('commentary_only_statements', 0)} |")
    lines.append(f"| Unknown Confidence Statements | {summary.get('unknown_confidence_statements', 0)} |")
    lines.append(f"| High-Attention Lines | **{summary.get('high_attention_lines', 0)}** |")
    lines.append("")
    
    # Section: Validation Status
    lines.append("## Validation Status")
    lines.append("")
    lines.append(f"Overall Validation Handoff Status: **{status.upper()}**")
    lines.append("")
    lines.append("| Check Summary | Value |")
    lines.append("| :--- | :--- |")
    lines.append(f"| Validation Findings Total | {summary.get('validation_findings_total', 0)} |")
    lines.append(f"| Validation Errors | {summary.get('validation_errors', 0)} |")
    lines.append(f"| Validation Warnings | {summary.get('validation_warnings', 0)} |")
    lines.append("")
    
    # Section: Category Summary
    lines.append("## Category Summary")
    lines.append("")
    lines.append("| Statement Category | Count |")
    lines.append("| :--- | :--- |")
    for cat, count in sorted(cat_summary.items()):
        lines.append(f"| {cat} | {count} |")
    lines.append("")
    
    # Section: Confidence Summary
    lines.append("## Confidence Summary")
    lines.append("")
    lines.append("| Confidence Tier | Count |")
    lines.append("| :--- | :--- |")
    for conf, count in sorted(conf_summary.items()):
        lines.append(f"| {conf} | {count} |")
    lines.append("")
    
    # Section: High Attention Lines
    lines.append("## High Attention Lines")
    lines.append("")
    
    # Collect all high attention statements
    attention_statements: List[Dict[str, Any]] = []
    
    # Global statements
    for s in payload.get("global_statements", []):
        if s.get("attention_level") != "none":
            s_copy = s.copy()
            s_copy["func"] = "global"
            attention_statements.append(s_copy)
            
    # Function statements
    for fn in payload.get("functions", []):
        for s in fn.get("statements", []):
            if s.get("attention_level") != "none":
                s_copy = s.copy()
                s_copy["func"] = fn.get("c_name")
                attention_statements.append(s_copy)
                
    # Sort: error > warning > info
    severity_order = {"error": 0, "warning": 1, "info": 2}
    attention_statements.sort(key=lambda x: severity_order.get(x.get("attention_level", "info"), 99))
    
    if not attention_statements:
        lines.append("No high attention lines detected in the trace report.")
    else:
        # Cap list to top 50
        capped = attention_statements[:50]
        lines.append(f"Showing top {len(capped)} of {len(attention_statements)} high-attention lines. (Full statement details are in [trace_report.json](file:///./trace_report.json)).")
        lines.append("")
        lines.append("| Line | Level | Function | Category | Statement | Finding / Explanation |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        
        for s in capped:
            line_no = s.get("line_number", 0)
            level = s.get("attention_level", "").upper()
            func = s.get("func", "")
            cat = s.get("category", "")
            text = s.get("statement_text", "")
            
            # Format findings or explanation
            findings = s.get("validation_findings", [])
            if findings:
                finding_desc = "; ".join(f"[{f.get('id')}] {f.get('title')}" for f in findings)
            else:
                finding_desc = s.get("short_explanation", "")
                
            # Clean up pipes in text to avoid breaking MD tables
            clean_text = text.replace("|", "\\|")
            clean_desc = finding_desc.replace("|", "\\|")
            
            lines.append(f"| {line_no} | {level} | {func} | {cat} | `{clean_text}` | {clean_desc} |")
            
    lines.append("")
    
    # Section: Function Summaries
    lines.append("## Function Summaries")
    lines.append("")
    lines.append("| Function | Entry Point | Statements | Attention Items | Top Categories |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")
    
    for fn in payload.get("functions", []):
        name = fn.get("c_name", "unknown")
        entry = fn.get("entry_point") or "N/A"
        total_s = fn.get("statements_total", 0)
        att_items = len(fn.get("attention_items", []))
        
        # Format top category summary
        f_cat_sum = fn.get("category_summary", {})
        top_cats = sorted(f_cat_sum.items(), key=lambda x: x[1], reverse=True)[:2]
        top_cats_str = ", ".join(f"{k} ({v})" for k, v in top_cats) or "None"
        
        lines.append(f"| {name} | {entry} | {total_s} | {att_items} | {top_cats_str} |")
        
    lines.append("")
    
    # Section: Notes and Limitations
    lines.append("## Notes and Limitations")
    lines.append("")
    lines.append("- For complete line-by-line classification, normalized statement hashes, and attached validation findings, inspect [trace_report.json](file:///./trace_report.json).")
    lines.append("- Unattached validation findings (if any) are recorded at the top level of the JSON payload.")
    lines.append("")
    
    with open(md_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    return md_file
