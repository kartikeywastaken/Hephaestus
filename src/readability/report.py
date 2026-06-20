# -*- coding: utf-8 -*-
"""
Readability Report Generator
Builds readability_report.json (readability-1.0) and optionally readability_report.md.
"""

import json
from pathlib import Path
from typing import Dict, Any, List

def build_readability_report(
    sites: List[Dict[str, Any]],
    skipped_sites: List[Dict[str, Any]],
    quality_gate_status: str,
    safe_to_use_for_phase7: bool,
    clang_syntax_status: str,
    warnings: List[str],
    diagnostics: List[str],
    promote_symbols_enabled: bool = False,
    symbol_promotion_data: Dict[str, Any] = None,
    compile_shape_enabled: bool = False,
    compile_shape_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Compile readability data into the standard readability JSON format."""
    total = len(sites) + len(skipped_sites)
    recovered = len(sites)
    skipped = len(skipped_sites)
    
    rate = (recovered / total * 100.0) if total > 0 else 0.0
    
    cbz_recovered = sum(1 for s in sites if s.get("source") == "cbz")
    cbnz_recovered = sum(1 for s in sites if s.get("source") == "cbnz")
    tbz_recovered = sum(1 for s in sites if s.get("source") == "tbz")
    tbnz_recovered = sum(1 for s in sites if s.get("source") == "tbnz")
    cmp_branch_recovered = sum(1 for s in sites if s.get("source") in ("cmp_conditional_branch", "cmp_branch_direct", "cmp_branch_indirect"))
    
    unsafe_complex_conditions_skipped = sum(1 for s in skipped_sites if s.get("reason") in (
        "complex condition", "unsupported condition", "floating-point comparisons", "compound and/or expressions"
    ))
    
    global_status = "ok"
    if warnings or diagnostics or quality_gate_status in ("review", "missing", "ignored"):
        global_status = "warning"
    if clang_syntax_status == "failed":
        global_status = "failed"
        
    if compile_shape_enabled and promote_symbols_enabled:
        schema_version = "readability-1.2"
        phase = "7.2.1"
        mode = "static_predicate_symbol_promotion_compile_shape_hardening"
    else:
        compile_shape_enabled = False
        schema_version = "readability-1.1" if promote_symbols_enabled else "readability-1.0"
        phase = "7.2" if promote_symbols_enabled else "7.1"
        mode = "static_predicate_and_symbol_promotion" if promote_symbols_enabled else "static_predicate_recovery_only"
    
    summary = {
        "unknown_condition_sites_total": total,
        "predicates_recovered": recovered,
        "predicates_skipped": skipped,
        "predicate_recovery_rate_percent": round(rate, 2),
        "cbz_recovered": cbz_recovered,
        "cbnz_recovered": cbnz_recovered,
        "tbz_recovered": tbz_recovered,
        "tbnz_recovered": tbnz_recovered,
        "cmp_branch_recovered": cmp_branch_recovered,
        "unsafe_complex_conditions_skipped": unsafe_complex_conditions_skipped,
        "quality_gate_status": quality_gate_status,
        "safe_to_use_for_phase7": safe_to_use_for_phase7,
        "clang_syntax_status": clang_syntax_status,
    }
    
    # Extra inputs
    input_artifacts = {
        "recovered_c": "recovered.c",
        "source_reconstruction": "source_reconstruction.json",
        "evidence_index": "evidence_index.json",
        "trace_report": "trace_report.json",
        "quality_gate": "quality_gate.json",
        "layout_recovery": "layout_recovery.json",
        "type_recovery": "type_recovery.json",
    }
    
    report = {
        "schema_version": schema_version,
        "phase": phase,
        "status": global_status,
        "mode": mode,
        "note": "All Phase 7.2 names are synthetic readability names, not recovered original source names.",
        "input_artifacts": input_artifacts,
        "output_artifacts": {
            "recovered_readable_c": "recovered_readable.c"
        },
        "summary": summary,
        "sites": sites,
        "skipped_sites": skipped_sites,
        "diagnostics": diagnostics + warnings
    }
    
    if promote_symbols_enabled and symbol_promotion_data:
        report["symbol_promotion"] = {
            "pseudo_registers_seen": symbol_promotion_data.get("pseudo_registers_seen", 0),
            "pseudo_stack_slots_seen": symbol_promotion_data.get("pseudo_stack_slots_seen", 0),
            "symbols_promoted": symbol_promotion_data.get("symbols_promoted", 0),
            "register_aliases_created": symbol_promotion_data.get("register_aliases_created", 0),
            "stack_slots_promoted": symbol_promotion_data.get("stack_slots_promoted", 0),
            "parameters_promoted": symbol_promotion_data.get("parameters_promoted", 0),
            "temps_promoted": symbol_promotion_data.get("temps_promoted", 0),
            "function_symbols_promoted": symbol_promotion_data.get("function_symbols_promoted", 0),
            "promotion_skipped": symbol_promotion_data.get("promotion_skipped", 0)
        }
        report["promotions"] = symbol_promotion_data.get("promotions", [])
        report["skipped_promotions"] = symbol_promotion_data.get("skipped_promotions", [])
        
        # Add to summary block too
        summary["symbols_promoted"] = symbol_promotion_data.get("symbols_promoted", 0)
        summary["stack_slots_promoted"] = symbol_promotion_data.get("stack_slots_promoted", 0)
        summary["parameters_promoted"] = symbol_promotion_data.get("parameters_promoted", 0)
        summary["temps_promoted"] = symbol_promotion_data.get("temps_promoted", 0)
        summary["function_symbols_promoted"] = symbol_promotion_data.get("function_symbols_promoted", 0)
        summary["promotion_skipped"] = symbol_promotion_data.get("promotion_skipped", 0)
    else:
        report["symbol_promotion"] = {"enabled": False}
        report["promotions"] = []
        report["skipped_promotions"] = []
        summary["symbols_promoted"] = 0
        summary["stack_slots_promoted"] = 0
        summary["parameters_promoted"] = 0
        summary["temps_promoted"] = 0
        summary["function_symbols_promoted"] = 0
        summary["promotion_skipped"] = 0
        
    if compile_shape_enabled:
        cs = compile_shape_data or {}
        stats_dict = dict(cs.get("stats", {}))
        stats_dict.setdefault("main_signature_normalized", True)
        stats_dict.setdefault("main_forward_declarations_normalized", 0)
        stats_dict.setdefault("duplicate_main_definitions_renamed", 0)
        stats_dict.setdefault("main_abi_bridge_declarations_added", 0)
        stats_dict.setdefault("abi_scratch_declarations_added", 0)
        stats_dict.setdefault("abi_scratch_declarations_inherited", 0)
        report["compile_shape"] = stats_dict
        report["compile_shape_items"] = cs.get("items", [])
        
    return report

def write_readability_report_json(report: Dict[str, Any], out_dir: Path) -> Path:
    """Write readability report to readability_report.json."""
    path = out_dir / "readability_report.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return path

def generate_readability_report_md(report: Dict[str, Any], out_dir: Path) -> Path:
    """Generate human-readable Markdown report in readability_report.md."""
    path = out_dir / "readability_report.md"
    summary = report["summary"]
    
    md = []
    md.append(f"# Hephaestus Phase {report['phase']} Readability Report")
    md.append("")
    md.append(f"**Status**: `{report['status'].upper()}`")
    md.append(f"**Predicate Recovery Rate**: {summary['predicate_recovery_rate_percent']}%")
    md.append(f"**Symbols Promoted**: {summary.get('symbols_promoted', 0)}")
    md.append("")
    md.append(f"> [!NOTE]")
    md.append(f"> {report['note']}")
    md.append("")
    md.append("## Summary Statistics")
    md.append("")
    md.append("| Metric | Value |")
    md.append("| --- | --- |")
    md.append(f"| Total Candidate Sites | {summary['unknown_condition_sites_total']} |")
    md.append(f"| Predicates Recovered | {summary['predicates_recovered']} |")
    md.append(f"| Predicates Skipped | {summary['predicates_skipped']} |")
    md.append(f"| CBZ Recovered | {summary['cbz_recovered']} |")
    md.append(f"| CBNZ Recovered | {summary['cbnz_recovered']} |")
    md.append(f"| TBZ Recovered | {summary['tbz_recovered']} |")
    md.append(f"| TBNZ Recovered | {summary['tbnz_recovered']} |")
    md.append(f"| CMP/Branch Recovered | {summary['cmp_branch_recovered']} |")
    md.append(f"| Stack Slots Promoted | {summary.get('stack_slots_promoted', 0)} |")
    md.append(f"| Parameters Promoted | {summary.get('parameters_promoted', 0)} |")
    md.append(f"| Temporaries Promoted | {summary.get('temps_promoted', 0)} |")
    md.append(f"| Function Symbols Promoted | {summary.get('function_symbols_promoted', 0)} |")
    md.append(f"| Promotions Skipped | {summary.get('promotion_skipped', 0)} |")
    md.append(f"| Quality Gate Status | `{summary['quality_gate_status'].upper()}` |")
    md.append(f"| Clang Syntax Status | `{summary['clang_syntax_status'].upper()}` |")
    md.append("")
    
    if report.get("diagnostics"):
        md.append("## Warnings & Diagnostics")
        md.append("")
        for d in report["diagnostics"]:
            md.append(f"- ⚠️ {d}")
        md.append("")
        
    md.append("## Recovered Predicate Sites")
    md.append("")
    if report.get("sites"):
        md.append("| Line | Function | Source | Replacement Condition |")
        md.append("| --- | --- | --- | --- |")
        for s in report["sites"]:
            md.append(f"| {s['line_number']} | `{s['function']}` | `{s['source']}` | `{s['replacement_condition']}` |")
    else:
        md.append("*No sites recovered.*")
    md.append("")
    
    md.append("## Promoted Symbols")
    md.append("")
    promos = report.get("promotions", [])
    if promos:
        md.append("| Function | Old Name | New Name | Kind | Confidence |")
        md.append("| --- | --- | --- | --- | --- |")
        for p in promos:
            md.append(f"| `{p['function']}` | `{p['old_name']}` | `{p['new_name']}` | {p['kind']} | `{p['confidence']}` |")
    else:
        md.append("*No symbols promoted.*")
    md.append("")
    
    md.append("## Skipped Promotions")
    md.append("")
    skipped_promos = report.get("skipped_promotions", [])
    if skipped_promos:
        md.append("| Function | Old Name | Proposed New Name | Kind | Reason |")
        md.append("| --- | --- | --- | --- | --- |")
        for p in skipped_promos:
            md.append(f"| `{p['function']}` | `{p['old_name']}` | `{p['proposed_new_name']}` | {p['kind']} | {p['reason']} |")
    else:
        md.append("*No promotions skipped.*")
    md.append("")
    
    if "compile_shape" in report:
        cs = report["compile_shape"]
        md.append("## Compile-Shape Hardening")
        md.append("")
        md.append("| Hardening Metric | Value |")
        md.append("| --- | --- |")
        md.append(f"| Missing Predicate Declarations Added | {cs.get('missing_predicate_declarations_added', 0)} |")
        md.append(f"| Scratch Declarations Added | {cs.get('scratch_declarations_added', 0)} |")
        md.append(f"| Predicates Skipped (Undeclared) | {cs.get('predicates_skipped_due_to_undeclared_identifiers', 0)} |")
        md.append(f"| Forward Declarations Removed | {cs.get('forward_declarations_removed', 0)} |")
        md.append(f"| Forward Declaration Conflicts Resolved | {cs.get('forward_declaration_conflicts_resolved', 0)} |")
        md.append(f"| Function Symbol Promotions Skipped for Collision | {cs.get('function_symbol_promotions_skipped_for_collision', 0)} |")
        md.append("")
    
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
        
    return path
