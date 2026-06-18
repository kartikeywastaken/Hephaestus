# -*- coding: utf-8 -*-
"""
Tests for Quality Gate Decision Rules
"""

from __future__ import annotations
from src.validation.quality_gate.rules import (
    evaluate_decision,
    extract_clang_diagnostic_counts,
    normalize_record
)

def get_base_params():
    return {
        "missing_artifacts": [],
        "validation_status": "ok",
        "validation_findings": [],
        "condition_expressions_recovered": 0,
        "trace_report_schema_valid": True,
        "evidence_index_schema_valid": True,
        "hash_check_failed": False,
        "summary": {
            "statements_total": 100,
            "evidence_backed_statements": 80,
            "unknown_statements": 2,
            "true_unsupported_statements": 0,
            "high_attention_lines": 0,
            "validation_errors": 0,
            "validation_warnings": 0,
            "syntax_adapter_statements": 0,
            "branch_evidence_statements": 0,
            "executable_lowered_statements": 50,
            "control_flow_scaffold_statements": 0,
            "has_tmp_stack_decls": False
        },
        "unattached_findings_count": 0,
        "scores": {
            "readability_readiness_score": 85.0,
            "risk_score": 0.0
        },
        "validation_checks": None
    }

def test_ready_status():
    params = get_base_params()
    res = evaluate_decision(**params)
    assert res["status"] == "ready"
    assert res["decision"]["safe_to_use_for_phase7"] is True
    assert res["decision"]["requires_review"] is False
    assert res["decision"]["blocked"] is False
    assert not res["blocking_issues"]
    assert not res["warnings"]

def test_blocked_by_missing_artifacts():
    params = get_base_params()
    params["missing_artifacts"] = ["recovered.c"]
    res = evaluate_decision(**params)
    assert res["status"] == "blocked"
    assert res["decision"]["safe_to_use_for_phase7"] is False
    assert res["decision"]["blocked"] is True
    assert any("recovered.c" in b.get("message", "") for b in res["blocking_issues"])

def test_validation_failed_non_blocking_review():
    params = get_base_params()
    params["validation_status"] = "failed"
    res = evaluate_decision(**params)
    # Failed status alone does not block now; triggers review.
    assert res["status"] == "review"
    assert res["decision"]["blocked"] is False
    assert res["decision"]["safe_to_use_for_phase7"] is True
    assert any(w.get("id") == "QG-VAL-FAILED-NON-BLOCKING" for w in res["warnings"])

def test_blocked_by_safety_category():
    params = get_base_params()
    # Finding in safety category with severity error blocks
    params["validation_findings"] = [{
        "category": "c_safety",
        "id": "VAL-C-001",
        "title": "Struct check failed",
        "severity": "error",
        "message": "Emitted structure layout detected"
    }]
    res = evaluate_decision(**params)
    assert res["status"] == "blocked"
    assert res["decision"]["blocked"] is True
    assert any(b.get("id") == "VAL-C-001" for b in res["blocking_issues"])

def test_blocked_by_condition_recovery():
    params = get_base_params()
    params["condition_expressions_recovered"] = 1
    res = evaluate_decision(**params)
    assert res["status"] == "blocked"
    assert res["decision"]["blocked"] is True

def test_blocked_by_schema_invalid():
    params = get_base_params()
    params["trace_report_schema_valid"] = False
    res = evaluate_decision(**params)
    assert res["status"] == "blocked"
    assert res["decision"]["blocked"] is True

def test_blocked_by_hash_mutation():
    params = get_base_params()
    params["hash_check_failed"] = True
    res = evaluate_decision(**params)
    assert res["status"] == "blocked"
    assert res["decision"]["blocked"] is True

def test_review_by_validation_warning():
    params = get_base_params()
    params["validation_status"] = "warning"
    res = evaluate_decision(**params)
    assert res["status"] == "review"
    assert res["decision"]["requires_review"] is True
    assert res["decision"]["safe_to_use_for_phase7"] is True

def test_review_by_unknown_ratio():
    params = get_base_params()
    params["summary"]["unknown_statements"] = 20 # 20/100 = 20% > 15%
    res = evaluate_decision(**params)
    assert res["status"] == "review"
    assert res["decision"]["requires_review"] is True

def test_review_by_unsupported_or_attention():
    params = get_base_params()
    params["summary"]["true_unsupported_statements"] = 1
    res = evaluate_decision(**params)
    assert res["status"] == "review"
    assert res["decision"]["requires_review"] is True

def test_review_by_low_readiness():
    params = get_base_params()
    params["scores"]["readability_readiness_score"] = 65.0
    res = evaluate_decision(**params)
    assert res["status"] == "review"
    assert res["decision"]["requires_review"] is True

def test_phase7_hints():
    params = get_base_params()
    params["summary"]["syntax_adapter_statements"] = 1
    params["summary"]["control_flow_scaffold_statements"] = 1
    params["summary"]["has_tmp_stack_decls"] = True
    res = evaluate_decision(**params)
    hints = res["phase7_hints"]
    assert hints["predicate_recovery_recommended"] is True
    assert hints["local_variable_recovery_recommended"] is True
    assert hints["loop_readability_recommended"] is True
    assert hints["expression_simplification_recommended"] is True


# ================= Phase 6.4 Tweak Specific Tests =================

def test_extract_clang_diagnostic_counts():
    # 1. Reads evidence
    f = {"category": "clang_syntax", "evidence": {"errors": 2, "warnings": 10}}
    errs, warns = extract_clang_diagnostic_counts(finding=f)
    assert errs == 2
    assert warns == 10

    # 2. Reads details
    f = {"category": "clang_syntax", "details": {"syntax_errors": "4", "clang_warnings": "23"}}
    errs, warns = extract_clang_diagnostic_counts(finding=f)
    assert errs == 4
    assert warns == 23

    # 3. Reads validation_checks.clang_syntax_ok.details
    checks = {"clang_syntax_ok": {"details": {"clang_errors": 0, "warnings": 5}}}
    errs, warns = extract_clang_diagnostic_counts(validation_checks=checks)
    assert errs == 0
    assert warns == 5

    # 4. Handles missing and unparsable fields
    f = {"category": "clang_syntax", "evidence": {"errors": "invalid", "warnings": None}}
    errs, warns = extract_clang_diagnostic_counts(finding=f)
    assert errs is None
    assert warns is None


def test_clang_warnings_only_review():
    params = get_base_params()
    params["validation_status"] = "warning"
    params["validation_findings"] = [{
        "id": "VAL-CLNG-003",
        "category": "clang_syntax",
        "severity": "warning",
        "evidence": {
            "errors": 0,
            "warnings": 23
        }
    }]
    res = evaluate_decision(**params)
    assert res["status"] == "review"
    assert res["decision"]["blocked"] is False
    assert res["decision"]["safe_to_use_for_phase7"] is True
    assert res["decision"]["requires_review"] is True
    
    # QG-CLANG-WARN in warnings, not blocking_issues
    assert any(w.get("id") == "QG-CLANG-WARN" for w in res["warnings"])
    assert not any(b.get("id") == "QG-CLANG-WARN" for b in res["blocking_issues"])
    
    # Standard warning dict format
    warn_rec = next(w for w in res["warnings"] if w.get("id") == "QG-CLANG-WARN")
    assert warn_rec["severity"] == "warning"
    assert warn_rec["category"] == "clang_syntax"
    assert warn_rec["evidence"]["warnings"] == 23


def test_clang_syntax_errors_blocked():
    params = get_base_params()
    params["validation_status"] = "failed"
    params["validation_findings"] = [{
        "id": "VAL-CLNG-001",
        "category": "clang_syntax",
        "severity": "error",
        "evidence": {
            "errors": 2,
            "warnings": 23
        }
    }]
    res = evaluate_decision(**params)
    assert res["status"] == "blocked"
    assert res["decision"]["blocked"] is True
    assert res["decision"]["safe_to_use_for_phase7"] is False
    
    # QG-CLANG-ERR in blocking_issues
    assert any(b.get("id") == "QG-CLANG-ERR" for b in res["blocking_issues"])
    
    # Standard blocker dict format
    block_rec = next(b for b in res["blocking_issues"] if b.get("id") == "QG-CLANG-ERR")
    assert block_rec["severity"] == "error"
    assert block_rec["category"] == "clang_syntax"
    assert block_rec["evidence"]["errors"] == 2


def test_clang_syntax_fallback():
    params = get_base_params()
    
    # Error severity fallback when counts missing
    params["validation_findings"] = [{
        "id": "VAL-CLNG-001",
        "category": "clang_syntax",
        "severity": "error"
    }]
    res = evaluate_decision(**params)
    assert res["status"] == "blocked"
    
    # Warning severity fallback when counts missing
    params["validation_findings"] = [{
        "id": "VAL-CLNG-003",
        "category": "clang_syntax",
        "severity": "warning"
    }]
    res = evaluate_decision(**params)
    assert res["status"] == "review"
    assert res["decision"]["blocked"] is False
