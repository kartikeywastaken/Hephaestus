# -*- coding: utf-8 -*-
"""
Tests for Static Validation of Evidence Index
"""

from __future__ import annotations
import json
import tempfile
from pathlib import Path
from src.validation.models import ValidationArtifacts
from src.validation.report import new_report, finalize_report
from src.validation.checks import check_evidence_index

def test_check_evidence_index_missing_default():
    report = new_report("dummy", strict=False)
    artifacts = ValidationArtifacts(
        out_dir=Path("dummy"),
        source_reconstruction={"schema_version": "5.7.2"},
        recovered_c="int main() { return 0; }",
        pipeline_manifest=None,
        unified_ir=None,
        phase4_semantics=None,
        missing=["evidence_index.json"],
        evidence_index=None
    )
    
    check_evidence_index(artifacts, report, require_evidence_index=False)
    finalize_report(report)
    
    assert report["status"] == "ok"
    assert report["checks"]["evidence_index_present"]["status"] == "ok"
    assert report["checks"]["evidence_index_schema_valid"]["status"] == "skipped"

def test_check_evidence_index_missing_strict():
    report = new_report("dummy", strict=True)
    artifacts = ValidationArtifacts(
        out_dir=Path("dummy"),
        source_reconstruction={"schema_version": "5.7.2"},
        recovered_c="int main() { return 0; }",
        pipeline_manifest=None,
        unified_ir=None,
        phase4_semantics=None,
        missing=["evidence_index.json"],
        evidence_index=None
    )
    
    check_evidence_index(artifacts, report, require_evidence_index=False)
    finalize_report(report)
    
    # In strict mode, missing evidence index is a warning, so status is warning, not failed
    assert report["status"] == "warning"
    assert report["checks"]["evidence_index_present"]["status"] == "warning"

def test_check_evidence_index_missing_required():
    report = new_report("dummy", strict=False)
    artifacts = ValidationArtifacts(
        out_dir=Path("dummy"),
        source_reconstruction={"schema_version": "5.7.2"},
        recovered_c="int main() { return 0; }",
        pipeline_manifest=None,
        unified_ir=None,
        phase4_semantics=None,
        missing=["evidence_index.json"],
        evidence_index=None
    )
    
    check_evidence_index(artifacts, report, require_evidence_index=True)
    finalize_report(report)
    
    assert report["status"] == "failed"
    assert report["checks"]["evidence_index_present"]["status"] == "failed"

def test_check_evidence_index_invalid_schema():
    report = new_report("dummy", strict=False)
    artifacts = ValidationArtifacts(
        out_dir=Path("dummy"),
        source_reconstruction={"schema_version": "5.7.2"},
        recovered_c="int main() { return 0; }",
        pipeline_manifest=None,
        unified_ir=None,
        phase4_semantics=None,
        missing=[],
        evidence_index={"schema_version": "invalid-schema-version"}
    )
    
    check_evidence_index(artifacts, report, require_evidence_index=False)
    finalize_report(report)
    
    assert report["status"] == "failed"
    assert report["checks"]["evidence_index_schema_valid"]["status"] == "failed"
    assert report["checks"]["evidence_index_summary_valid"]["status"] == "skipped"

def test_check_evidence_index_valid():
    report = new_report("dummy", strict=False)
    
    index_data = {
        "schema_version": "evidence-index-1.0",
        "summary": {
            "statements_total": 10,
            "statements_with_instruction_evidence": 8,
            "statements_without_instruction_evidence": 2,
            "executable_lowered_statements": 8,
            "true_unsupported_statements": 1,
            "comment_lowered_statements": 1,
            "branch_evidence_comments": 0,
            "syntax_adapter_statements": 0,
            "helper_statements": 0,
            "declaration_statements": 0,
            "call_statements": 0,
            "return_statements": 0,
            "control_flow_scaffold_statements": 0,
            "function_signature_statements": 0,
            "empty_function_scaffold_statements": 0,
            "unknown_statement_category": 0
        }
    }
    
    recon_data = {
        "schema_version": "5.7.2",
        "summary": {
            "unsupported_instruction_kinds": {"invalid": 1}
        }
    }
    
    artifacts = ValidationArtifacts(
        out_dir=Path("dummy"),
        source_reconstruction=recon_data,
        recovered_c="int main() { return 0; }",
        pipeline_manifest=None,
        unified_ir=None,
        phase4_semantics=None,
        missing=[],
        evidence_index=index_data
    )
    
    check_evidence_index(artifacts, report, require_evidence_index=False)
    finalize_report(report)
    
    assert report["status"] == "ok"
    assert report["checks"]["evidence_index_present"]["status"] == "ok"
    assert report["checks"]["evidence_index_schema_valid"]["status"] == "ok"
    assert report["checks"]["evidence_index_summary_valid"]["status"] == "ok"
    assert report["checks"]["evidence_index_unsupported_accounting"]["status"] == "ok"
    assert report["checks"]["evidence_index_unknown_categories"]["status"] == "ok"

def test_check_evidence_index_summary_mismatch():
    report = new_report("dummy", strict=False)
    
    index_data = {
        "schema_version": "evidence-index-1.0",
        "summary": {
            "statements_total": 10, # Does not match sum (9)
            "statements_with_instruction_evidence": 8,
            "statements_without_instruction_evidence": 2,
            "executable_lowered_statements": 7,
            "true_unsupported_statements": 1,
            "comment_lowered_statements": 1,
            "branch_evidence_comments": 0,
            "syntax_adapter_statements": 0,
            "helper_statements": 0,
            "declaration_statements": 0,
            "call_statements": 0,
            "return_statements": 0,
            "control_flow_scaffold_statements": 0,
            "function_signature_statements": 0,
            "empty_function_scaffold_statements": 0,
            "unknown_statement_category": 0
        }
    }
    
    artifacts = ValidationArtifacts(
        out_dir=Path("dummy"),
        source_reconstruction={"summary": {"unsupported_instruction_kinds": {}}},
        recovered_c="int main() { return 0; }",
        pipeline_manifest=None,
        unified_ir=None,
        phase4_semantics=None,
        missing=[],
        evidence_index=index_data
    )
    
    check_evidence_index(artifacts, report, require_evidence_index=False)
    finalize_report(report)
    
    assert report["status"] == "failed"
    assert report["checks"]["evidence_index_summary_valid"]["status"] == "failed"

def test_check_evidence_index_unsupported_mismatch():
    report = new_report("dummy", strict=False)
    
    index_data = {
        "schema_version": "evidence-index-1.0",
        "summary": {
            "statements_total": 10,
            "statements_with_instruction_evidence": 8,
            "statements_without_instruction_evidence": 2,
            "executable_lowered_statements": 8,
            "true_unsupported_statements": 2, # Expected 1
            "comment_lowered_statements": 0,
            "branch_evidence_comments": 0,
            "syntax_adapter_statements": 0,
            "helper_statements": 0,
            "declaration_statements": 0,
            "call_statements": 0,
            "return_statements": 0,
            "control_flow_scaffold_statements": 0,
            "function_signature_statements": 0,
            "empty_function_scaffold_statements": 0,
            "unknown_statement_category": 0
        }
    }
    
    recon_data = {
        "schema_version": "5.7.2",
        "summary": {
            "unsupported_instruction_kinds": {"invalid": 1}
        }
    }
    
    artifacts = ValidationArtifacts(
        out_dir=Path("dummy"),
        source_reconstruction=recon_data,
        recovered_c="int main() { return 0; }",
        pipeline_manifest=None,
        unified_ir=None,
        phase4_semantics=None,
        missing=[],
        evidence_index=index_data
    )
    
    check_evidence_index(artifacts, report, require_evidence_index=False)
    finalize_report(report)
    
    assert report["status"] == "failed"
    assert report["checks"]["evidence_index_unsupported_accounting"]["status"] == "failed"

def test_check_evidence_index_unknown_category():
    report = new_report("dummy", strict=False)
    
    index_data = {
        "schema_version": "evidence-index-1.0",
        "summary": {
            "statements_total": 10,
            "statements_with_instruction_evidence": 8,
            "statements_without_instruction_evidence": 2,
            "executable_lowered_statements": 8,
            "true_unsupported_statements": 0,
            "comment_lowered_statements": 1,
            "branch_evidence_comments": 0,
            "syntax_adapter_statements": 0,
            "helper_statements": 0,
            "declaration_statements": 0,
            "call_statements": 0,
            "return_statements": 0,
            "control_flow_scaffold_statements": 0,
            "function_signature_statements": 0,
            "empty_function_scaffold_statements": 0,
            "unknown_statement_category": 1
        }
    }
    
    artifacts = ValidationArtifacts(
        out_dir=Path("dummy"),
        source_reconstruction={"summary": {"unsupported_instruction_kinds": {}}},
        recovered_c="int main() { return 0; }",
        pipeline_manifest=None,
        unified_ir=None,
        phase4_semantics=None,
        missing=[],
        evidence_index=index_data
    )
    
    check_evidence_index(artifacts, report, require_evidence_index=False)
    finalize_report(report)
    
    # In default mode, unknown category is warning
    assert report["status"] == "warning"
    assert report["checks"]["evidence_index_unknown_categories"]["status"] == "warning"
