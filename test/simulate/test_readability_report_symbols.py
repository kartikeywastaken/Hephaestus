# -*- coding: utf-8 -*-
"""
Unit Tests for readability-1.1 report schema and details
"""

import pytest
from src.readability.report import build_readability_report

def test_report_builder_symbols_enabled():
    sites = [{"site_id": "pred_000001", "function": "main", "line_number": 12, "source": "cbz", "status": "recovered"}]
    skipped_sites = []
    
    symbol_promotion_data = {
        "pseudo_registers_seen": 5,
        "pseudo_stack_slots_seen": 3,
        "symbols_promoted": 4,
        "register_aliases_created": 0,
        "stack_slots_promoted": 3,
        "parameters_promoted": 1,
        "temps_promoted": 0,
        "function_symbols_promoted": 0,
        "promotion_skipped": 1,
        "promotions": [
            {
                "promotion_id": "sym_000001",
                "function": "main",
                "old_name": "stack_m16",
                "new_name": "local_m16",
                "kind": "stack_slot",
                "type": "u64",
                "source": "phase4_layout_stack_slot",
                "status": "promoted",
                "confidence": "artifact_backed",
                "evidence": {"offset": -16, "base": "fp", "layout_candidate": None}
            }
        ],
        "skipped_promotions": [
            {
                "promotion_id": "sym_000002",
                "function": "main",
                "old_name": "stack_m24",
                "proposed_new_name": "local_m24",
                "kind": "stack_slot",
                "reason": "name collision",
                "confidence": "syntax_backed",
                "evidence": {"offset": -24, "base": "fp"}
            }
        ]
    }
    
    report = build_readability_report(
        sites=sites,
        skipped_sites=skipped_sites,
        quality_gate_status="ok",
        safe_to_use_for_phase7=True,
        clang_syntax_status="ok",
        warnings=[],
        diagnostics=[],
        promote_symbols_enabled=True,
        symbol_promotion_data=symbol_promotion_data
    )
    
    assert report["schema_version"] == "readability-1.1"
    assert report["phase"] == "7.2"
    assert report["mode"] == "static_predicate_and_symbol_promotion"
    assert "symbol_promotion" in report
    
    # Check counts inside summary
    summary = report["summary"]
    assert summary["symbols_promoted"] == 4
    assert summary["stack_slots_promoted"] == 3
    assert summary["parameters_promoted"] == 1
    assert summary["temps_promoted"] == 0
    assert summary["promotion_skipped"] == 1
    
    # Check list items
    assert len(report["promotions"]) == 1
    assert len(report["skipped_promotions"]) == 1
    assert report["promotions"][0]["old_name"] == "stack_m16"
    assert report["skipped_promotions"][0]["reason"] == "name collision"

def test_report_builder_symbols_disabled():
    report = build_readability_report(
        sites=[],
        skipped_sites=[],
        quality_gate_status="ok",
        safe_to_use_for_phase7=True,
        clang_syntax_status="ok",
        warnings=[],
        diagnostics=[],
        promote_symbols_enabled=False
    )
    
    assert report["schema_version"] == "readability-1.0"
    assert report["phase"] == "7.1"
    assert report["mode"] == "static_predicate_recovery_only"
    assert report["symbol_promotion"] == {"enabled": False}
    assert report["promotions"] == []
    assert report["skipped_promotions"] == []
    assert report["summary"]["symbols_promoted"] == 0
