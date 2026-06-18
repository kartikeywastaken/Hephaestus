# -*- coding: utf-8 -*-
"""
Tests for Helper Consistency Checks
"""

from __future__ import annotations
import tempfile
from pathlib import Path
from src.validation.models import ValidationArtifacts
from src.validation.report import new_report
from src.validation.helpers import check_helpers

def test_check_helpers_valid():
    report = new_report("artifacts", strict=True)
    # definition exists and helper is used in execution
    c_content = """
    static int HEPHAESTUS_UNKNOWN_COND(const char* c) { return 0; }
    static u64 HEPHAESTUS_CSET(const char* c) { return 0; }
    
    void foo() {
        if (HEPHAESTUS_UNKNOWN_COND("eq")) {
            u64 val = HEPHAESTUS_CSET("ne");
        }
    }
    """
    recon = {
        "summary": {
            "unknown_condition_helpers_emitted": 1,
            "cset_helper_emitted": 1
        }
    }
    artifacts = ValidationArtifacts(
        out_dir=Path("artifacts"),
        source_reconstruction=recon,
        recovered_c=c_content,
        pipeline_manifest=None,
        unified_ir=None,
        phase4_semantics=None,
        missing=[]
    )
    check_helpers(artifacts, report)
    
    assert report["checks"]["unknown_cond_helper_consistent"]["status"] == "ok"
    assert report["checks"]["cset_helper_consistent"]["status"] == "ok"
    assert report["checks"]["reserved_helpers_not_declared_as_call_helpers"]["status"] == "ok"
    assert len(report["findings"]) == 0

def test_check_helpers_definition_missing_but_used():
    report = new_report("artifacts", strict=True)
    # Used but no definitions present
    c_content = """
    void foo() {
        if (HEPHAESTUS_UNKNOWN_COND("eq")) {
            u64 val = HEPHAESTUS_CSET("ne");
        }
    }
    """
    artifacts = ValidationArtifacts(
        out_dir=Path("artifacts"),
        source_reconstruction=None,
        recovered_c=c_content,
        pipeline_manifest=None,
        unified_ir=None,
        phase4_semantics=None,
        missing=[]
    )
    check_helpers(artifacts, report)
    
    assert report["checks"]["unknown_cond_helper_consistent"]["status"] == "failed"
    assert report["checks"]["cset_helper_consistent"]["status"] == "failed"
    
    finding_ids = [f["id"] for f in report["findings"]]
    assert "VAL-HELP-001" in finding_ids
    assert "VAL-HELP-002" in finding_ids

def test_check_helpers_definition_without_usage_is_allowed():
    report = new_report("artifacts", strict=True)
    # definitions present but NOT used (definition count itself is not counted as usage)
    c_content = """
    static int HEPHAESTUS_UNKNOWN_COND(const char* c) { return 0; }
    static u64 HEPHAESTUS_CSET(const char* c) { return 0; }
    """
    recon = {
        "summary": {
            "unknown_condition_helpers_emitted": 1,
            "cset_helper_emitted": 1
        }
    }
    artifacts = ValidationArtifacts(
        out_dir=Path("artifacts"),
        source_reconstruction=recon,
        recovered_c=c_content,
        pipeline_manifest=None,
        unified_ir=None,
        phase4_semantics=None,
        missing=[]
    )
    check_helpers(artifacts, report)
    
    assert report["checks"]["unknown_cond_helper_consistent"]["status"] == "ok"
    assert report["checks"]["cset_helper_consistent"]["status"] == "ok"

def test_check_helpers_forbidden_call_prefix():
    report = new_report("artifacts", strict=True)
    c_content = """
    u64 call_HEPHAESTUS_CSET(); // Forbidden call_ prefix
    """
    artifacts = ValidationArtifacts(
        out_dir=Path("artifacts"),
        source_reconstruction=None,
        recovered_c=c_content,
        pipeline_manifest=None,
        unified_ir=None,
        phase4_semantics=None,
        missing=[]
    )
    check_helpers(artifacts, report)
    
    assert report["checks"]["reserved_helpers_not_declared_as_call_helpers"]["status"] == "failed"
    assert "VAL-HELP-003" in [f["id"] for f in report["findings"]]
