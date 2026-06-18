# -*- coding: utf-8 -*-
"""
Quality Gate Builder Core Logic
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List

from src.validation.quality_gate.scoring import compute_scores
from src.validation.quality_gate.rules import evaluate_decision

def build_quality_gate_payload(
    out_dir: Path,
    strict: bool = False,
    hash_check_failed: bool = False
) -> Dict[str, Any]:
    """
    Load all artifacts, analyze metrics, compute scores, run rules, and return the report dict.
    """
    required_files = {
        "source_reconstruction": "source_reconstruction.json",
        "recovered_c": "recovered.c",
        "validation_report": "validation_report.json",
        "evidence_index": "evidence_index.json",
        "trace_report": "trace_report.json"
    }
    
    missing_artifacts = []
    for key, name in required_files.items():
        if not (out_dir / name).exists():
            missing_artifacts.append(name)
            
    # Default values in case we are blocked early due to missing files
    summary = {
        "functions_total": 0,
        "statements_total": 0,
        "evidence_backed_statements": 0,
        "unknown_statements": 0,
        "true_unsupported_statements": 0,
        "comment_lowered_statements": 0,
        "syntax_adapter_statements": 0,
        "validation_errors": 0,
        "validation_warnings": 0,
        "high_attention_lines": 0,
        "branch_evidence_statements": 0,
        "control_flow_scaffold_statements": 0,
        "executable_lowered_statements": 0,
        "has_tmp_stack_decls": False
    }
    
    validation_status = "unknown"
    validation_findings = []
    condition_expressions_recovered = 0
    trace_report_schema_valid = True
    evidence_index_schema_valid = True
    unattached_findings_count = 0
    validation_checks = {}
    
    # 1. Parse files if present
    if "source_reconstruction.json" not in missing_artifacts:
        try:
            with open(out_dir / "source_reconstruction.json", "r", encoding="utf-8") as f:
                recon_data = json.load(f)
            recon_summary = recon_data.get("summary", {})
            condition_expressions_recovered = recon_summary.get("condition_expressions_recovered", 0)
        except Exception:
            missing_artifacts.append("source_reconstruction.json")
            
    if "evidence_index.json" not in missing_artifacts:
        try:
            with open(out_dir / "evidence_index.json", "r", encoding="utf-8") as f:
                ev_data = json.load(f)
            if ev_data.get("schema_version") != "evidence-index-1.0":
                evidence_index_schema_valid = False
        except Exception:
            evidence_index_schema_valid = False
            
    if "validation_report.json" not in missing_artifacts:
        try:
            with open(out_dir / "validation_report.json", "r", encoding="utf-8") as f:
                val_data = json.load(f)
            validation_status = val_data.get("status", "unknown")
            validation_findings = val_data.get("findings", [])
            validation_checks = val_data.get("checks", {})
            val_summary = val_data.get("summary", {})
            summary["validation_errors"] = val_summary.get("errors", 0)
            summary["validation_warnings"] = val_summary.get("warnings", 0)
        except Exception:
            validation_status = "failed"
            
    if "trace_report.json" not in missing_artifacts:
        try:
            with open(out_dir / "trace_report.json", "r", encoding="utf-8") as f:
                trace_data = json.load(f)
            if trace_data.get("schema_version") != "trace-report-1.0":
                trace_report_schema_valid = False
                
            tr_summary = trace_data.get("summary", {})
            summary["functions_total"] = tr_summary.get("functions_total", 0)
            summary["statements_total"] = tr_summary.get("statements_total", 0)
            summary["evidence_backed_statements"] = tr_summary.get("evidence_backed_statements", 0)
            summary["high_attention_lines"] = tr_summary.get("high_attention_lines", 0)
            summary["generated_scaffold_statements"] = tr_summary.get("generated_scaffold_statements", 0)
            summary["commentary_only_statements"] = tr_summary.get("commentary_only_statements", 0)
            
            # Extract category & confidence details from trace report
            cat_summary = trace_data.get("category_summary", {})
            summary["true_unsupported_statements"] = cat_summary.get("true_unsupported", 0)
            summary["comment_lowered_statements"] = cat_summary.get("comment_lowered", 0)
            summary["syntax_adapter_statements"] = cat_summary.get("syntax_adapter", 0)
            summary["branch_evidence_statements"] = cat_summary.get("branch_evidence", 0)
            summary["control_flow_scaffold_statements"] = cat_summary.get("control_flow_scaffold", 0)
            summary["executable_lowered_statements"] = cat_summary.get("executable_lowered", 0)
            
            # Count unknown statements: statements with category == "unknown" OR confidence == "unknown"
            unknown_statements = 0
            has_tmp_stack_decls = False
            for gs in trace_data.get("global_statements", []):
                if gs.get("category") == "unknown" or gs.get("confidence") == "unknown":
                    unknown_statements += 1
                if gs.get("category") == "declaration":
                    txt = gs.get("statement_text", "")
                    if "tmp_" in txt or "stack_" in txt:
                        has_tmp_stack_decls = True
            for fn in trace_data.get("functions", []):
                for s in fn.get("statements", []):
                    if s.get("category") == "unknown" or s.get("confidence") == "unknown":
                        unknown_statements += 1
                    if s.get("category") == "declaration":
                        txt = s.get("statement_text", "")
                        if "tmp_" in txt or "stack_" in txt:
                            has_tmp_stack_decls = True
                            
            summary["unknown_statements"] = unknown_statements
            summary["has_tmp_stack_decls"] = has_tmp_stack_decls
            
            unattached_findings_count = len(trace_data.get("unattached_validation_findings", []))
        except Exception:
            trace_report_schema_valid = False

    # 2. Compute scores
    scores = compute_scores(summary, validation_status, unattached_findings_count)
    
    # 3. Evaluate rules
    decision_payload = evaluate_decision(
        missing_artifacts=missing_artifacts,
        validation_status=validation_status,
        validation_findings=validation_findings,
        condition_expressions_recovered=condition_expressions_recovered,
        trace_report_schema_valid=trace_report_schema_valid,
        evidence_index_schema_valid=evidence_index_schema_valid,
        hash_check_failed=hash_check_failed,
        summary=summary,
        unattached_findings_count=unattached_findings_count,
        scores=scores,
        validation_checks=validation_checks
    )
    
    # Clean up internal keys in summary for the final JSON payload
    clean_summary = {
        "functions_total": summary["functions_total"],
        "statements_total": summary["statements_total"],
        "evidence_backed_statements": summary["evidence_backed_statements"],
        "unknown_statements": summary["unknown_statements"],
        "true_unsupported_statements": summary["true_unsupported_statements"],
        "comment_lowered_statements": summary["comment_lowered_statements"],
        "syntax_adapter_statements": summary["syntax_adapter_statements"],
        "validation_errors": summary["validation_errors"],
        "validation_warnings": summary["validation_warnings"],
        "high_attention_lines": summary["high_attention_lines"]
    }
    
    payload = {
        "schema_version": "quality-gate-1.0",
        "phase": "6.4",
        "status": decision_payload["status"],
        "decision": decision_payload["decision"],
        "input_artifacts": {
            "source_reconstruction": "source_reconstruction.json" if "source_reconstruction.json" not in missing_artifacts else None,
            "recovered_c": "recovered.c" if "recovered.c" not in missing_artifacts else None,
            "validation_report": "validation_report.json" if "validation_report.json" not in missing_artifacts else None,
            "evidence_index": "evidence_index.json" if "evidence_index.json" not in missing_artifacts else None,
            "trace_report": "trace_report.json" if "trace_report.json" not in missing_artifacts else None
        },
        "scores": scores,
        "thresholds": {
            "min_readiness_score": 70.0,
            "max_risk_score": 40.0,
            "max_unknown_statement_ratio": 0.15,
            "max_validation_errors": 0
        },
        "summary": clean_summary,
        "blocking_issues": decision_payload["blocking_issues"],
        "warnings": decision_payload["warnings"],
        "recommendations": decision_payload["recommendations"],
        "phase7_hints": decision_payload["phase7_hints"],
        "diagnostics": []
    }
    
    return payload
