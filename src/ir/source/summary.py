# -*- coding: utf-8 -*-
"""
Reconstruction Artifact Summary Aggregation
"""

from __future__ import annotations
from typing import Any, Dict

def default_source_summary() -> dict:
    """Return default decompiler metrics structure."""
    return {
        "functions_total": 0,
        "functions_emitted": 0,
        "functions_structured": 0,
        "functions_partially_structured": 0,
        "functions_unstructured": 0,
        "instructions_total": 0,
        "instructions_lowered": 0,
        "instructions_commented": 0,
        "lowering_coverage_percent": 0.0,
        "condition_expressions_recovered": 0,
        "condition_adapters_inserted": 0,
        "cset_adapters_inserted": 0,
        "unsupported_instruction_kinds": {},
        "declarations_total": 0,
        "call_sites_total": 0,
        "call_arguments_recovered": 0,
        "return_sites_total": 0,
        "return_sites_with_value": 0,
    }

def finalize_source_summary(summary: dict) -> dict:
    """Calculate dependent stats (e.g. coverage) and clean up final summary dict."""
    total = summary.get("instructions_total", 0)
    lowered = summary.get("instructions_lowered", 0)
    if total > 0:
        summary["lowering_coverage_percent"] = round((lowered / total) * 100, 2)
    else:
        summary["lowering_coverage_percent"] = 0.0
    return summary
