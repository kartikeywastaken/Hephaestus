# -*- coding: utf-8 -*-
"""
Tests for C Safety Validation Checks
"""

from __future__ import annotations
import tempfile
from pathlib import Path
from src.validation.models import ValidationArtifacts
from src.validation.report import new_report
from src.validation.c_safety import check_c_safety

def test_check_c_safety_clean():
    report = new_report("artifacts", strict=False)
    # A valid recovered.c body without violations
    c_content = """
    #include "hephaestus.h"
    /* Here is a comment with -> and struct inside comments. */
    /* Also raw ARM leak in comment: [x9, x10, LSL #0x2] */
    /* if (tmp_x0 == 0) - this is a comment and is allowed */
    static int HEPHAESTUS_UNKNOWN_COND(const char* cond) { return 0; }
    
    u64 fn_0x1000() {
        u64 x = 0;
        if (HEPHAESTUS_UNKNOWN_COND("eq")) {
            x = 10;
        }
        return x;
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
    check_c_safety(artifacts, report)
    
    assert report["checks"]["recovered_c_nonempty"]["status"] == "ok"
    assert report["checks"]["no_phantom_0x5f5e"]["status"] == "ok"
    assert report["checks"]["no_struct_fabrication"]["status"] == "ok"
    assert report["checks"]["no_arrow_fields_executable"]["status"] == "ok"
    assert report["checks"]["no_empty_conditions"]["status"] == "ok"
    assert report["checks"]["no_executable_tmp_conditions"]["status"] == "ok"
    assert report["checks"]["no_raw_arm_indexed_leak_executable"]["status"] == "ok"
    assert report["checks"]["no_fake_flag_variables"]["status"] == "ok"
    assert len(report["findings"]) == 0

def test_check_c_safety_violations():
    report = new_report("artifacts", strict=False)
    # A recovered.c body containing structural violations
    c_content = """
    struct MyStruct { int a; }; // struct fabrication
    
    void foo() {
        MyStruct* s;
        s->a = 10; // arrow access
        
        if (0x5f5e) { // phantom address
            return;
        }
        
        if () { // empty condition
            return;
        }
        
        if (tmp_w8 == 0) { // fake executable condition
            return;
        }
        
        while (stack_val > 0) { // fake stack condition
            return;
        }
        
        tmp_flags_z = 1; // fake flag variable
        
        // raw ARM indexed memory syntax leak
        u64 val = [x9, x10, LSL #2];
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
    check_c_safety(artifacts, report)
    
    assert report["checks"]["no_phantom_0x5f5e"]["status"] == "failed"
    assert report["checks"]["no_struct_fabrication"]["status"] == "failed"
    assert report["checks"]["no_arrow_fields_executable"]["status"] == "failed"
    assert report["checks"]["no_empty_conditions"]["status"] == "failed"
    assert report["checks"]["no_executable_tmp_conditions"]["status"] == "failed"
    assert report["checks"]["no_raw_arm_indexed_leak_executable"]["status"] == "failed"
    assert report["checks"]["no_fake_flag_variables"]["status"] == "failed"
    
    finding_ids = [f["id"] for f in report["findings"]]
    assert "VAL-CSAF-002" in finding_ids # Phantom 0x5f5e
    assert "VAL-CSAF-003" in finding_ids # struct
    assert "VAL-CSAF-004" in finding_ids # arrow ->
    assert "VAL-CSAF-005" in finding_ids # empty cond
    assert "VAL-CSAF-006" in finding_ids # tmp_/arg/stack_ condition
    assert "VAL-CSAF-007" in finding_ids # raw ARM leak
    assert "VAL-CSAF-008" in finding_ids # flag variable
