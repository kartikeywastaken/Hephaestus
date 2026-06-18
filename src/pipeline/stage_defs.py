# -*- coding: utf-8 -*-
"""
Central Pipeline Stage and Outputs Definitions
"""

PIPELINE_STAGES = [
    "extract",
    "analyze_cfg",
    "recover_semantics",
    "refine_semantics",
    "recover_layouts",
    "finalize_semantics",
    "reconstruct_source",
]

OPTIONAL_PIPELINE_STAGES = [
    "build_evidence_index",
    "validate",
    "build_trace_report",
    "quality_gate",
    "build_readable",
]

STAGE_OUTPUTS = {
    "extract": [
        "unified_ir.json",
        "ghidra_extraction.json",
        "radare2_extraction.json",
    ],
    "analyze_cfg": [
        "structuring_analysis.json",
        "structuring_regions.json",
    ],
    "recover_semantics": [
        "type_recovery.json",
    ],
    "refine_semantics": [
        "semantic_recovery.json",
    ],
    "recover_layouts": [
        "layout_recovery.json",
    ],
    "finalize_semantics": [
        "phase4_semantics.json",
    ],
    "reconstruct_source": [
        "source_reconstruction.json",
        "recovered.c",
    ],
    "build_evidence_index": [
        "evidence_index.json",
    ],
    "validate": [
        "validation_report.json",
    ],
    "build_trace_report": [
        "trace_report.json",
        "trace_report.md",
    ],
    "quality_gate": [
        "quality_gate.json",
        "quality_gate.md",
    ],
    "build_readable": [
        "recovered_readable.c",
        "readability_report.json",
        "readability_report.md",
    ],
}

