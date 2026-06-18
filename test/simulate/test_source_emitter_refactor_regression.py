# -*- coding: utf-8 -*-
"""
Source emitter and summary refactor regression tests.
"""

from __future__ import annotations
import json
import tempfile
from pathlib import Path

from src.ir.source.models import (
    ReconstructedFunction,
    SourceReconstructionArtifact,
)
from src.ir.source.c_emitter import emit_recovered_c

def test_source_summary_metrics():
    # Verify standard metrics keys exist and have default types/values
    artifact = SourceReconstructionArtifact()
    summary = artifact.summary
    
    expected_metrics = [
        "functions_total",
        "instructions_total",
        "instructions_lowered",
        "instructions_commented",
        "lowering_coverage_percent",
        "condition_expressions_recovered",
        "condition_adapters_inserted",
        "cset_adapters_inserted",
        "unsupported_instruction_kinds",
        "declarations_total",
    ]
    
    for metric in expected_metrics:
        assert metric in summary

def test_main_signature_and_helpers_emission():
    # Construct an artifact containing a main function and a normal user function
    artifact = SourceReconstructionArtifact()
    
    # 1. Main function
    main_fn = ReconstructedFunction(
        name="main",
        c_name="main",
        canonical_name="main",
        entry_point="0x1000",
        return_type="i32",
        parameters=[
            {"name": "argc", "type": "i32"},
            {"name": "argv", "type": "pointer"}
        ],
        lowered_blocks={},
        lowered_statements=[],
        structured_regions=None
    )
    
    # 2. User function using HEPHAESTUS_CSET helper
    user_fn = ReconstructedFunction(
        name="user_func",
        c_name="user_func",
        canonical_name="user_func",
        entry_point="0x2000",
        return_type="void",
        parameters=[],
        lowered_blocks={
            "0x2000": [
                {"address": "0x2000", "kind": "binary_op", "text": "tmp_w8 = HEPHAESTUS_CSET(\"eq\");"}
            ]
        },
        lowered_statements=[],
        structured_regions=None
    )
    
    artifact.functions = [main_fn, user_fn]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        c_path = Path(tmpdir) / "recovered.c"
        emit_recovered_c(artifact, str(c_path))
        
        c_content = c_path.read_text(encoding="utf-8")
        
        # Verify main signature remains int32_t main(int32_t argc, char ** argv)
        assert "int32_t main(int32_t argc, char ** argv)" in c_content
        
        # Verify HEPHAESTUS_CSET helper is emitted
        assert "HEPHAESTUS_CSET" in c_content
        assert "static u64 HEPHAESTUS_CSET" in c_content
        
        # Verify HEPHAESTUS_UNKNOWN_COND is NOT emitted (since it wasn't used)
        assert "HEPHAESTUS_UNKNOWN_COND" not in c_content
        
        # Verify reserved helper functions (HEPHAESTUS_CSET) are not declared as call target helpers
        assert "u64 HEPHAESTUS_CSET();" not in c_content
