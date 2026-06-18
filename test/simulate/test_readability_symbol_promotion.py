# -*- coding: utf-8 -*-
"""
Unit Tests for Phase 7.2 Symbol Promotion mapping resolver
"""

import pytest
from src.readability.symbol_promotion import SymbolPromotionEngine

def test_symbol_promotion_basic():
    source_recon = {
        "data": {
            "functions": [
                {
                    "name": "_main",
                    "c_name": "main",
                    "entry_point": "0x100000548",
                    "parameters": [
                        {"name": "arg0", "index": 0},
                        {"name": "arg_1", "index": 1}
                    ]
                }
            ]
        }
    }
    
    # Positive offsets layout candidates
    phase4_sem = {
        "data": {
            "functions": [
                {
                    "name": "_main",
                    "layout_candidates": [
                        {
                            "base_id": "sp",
                            "observed_offsets": [16, 24]
                        }
                    ]
                }
            ]
        }
    }
    
    engine = SymbolPromotionEngine(
        source_recon=source_recon,
        type_recovery={},
        phase4_semantics=phase4_sem,
        layout_recovery={},
        promote_temps=False
    )
    
    c_input = """
int32_t main(int32_t arg0, char ** arg_1)
{
    u64 stack_m16 = 0;
    u64 stack_24 = 0;
    u64 tmp_x8 = 0;
    stack_m16 = arg0;
    stack_24 = tmp_x8;
    return 0;
}
"""
    
    rewritten, report = engine.run_symbol_promotion(c_input)
    
    # stack_m16 -> local_m16 (syntax-backed fallback because offset -16 not in sp observed offsets)
    # stack_24 -> local_24 (artifact-backed since 24 is in layout_candidates)
    # arg0 -> param_0 (parameter metadata exists)
    # arg_1 -> param_1 (parameter metadata exists)
    # tmp_x8 remains unchanged by default
    
    assert "local_m16" in rewritten
    assert "local_24" in rewritten
    assert "param_0" in rewritten
    assert "param_1" in rewritten
    assert "tmp_x8" in rewritten
    
    # Check details of promotions
    promos = report["promotions"]
    p_m16 = next(p for p in promos if p["old_name"] == "stack_m16")
    p_24 = next(p for p in promos if p["old_name"] == "stack_24")
    p_arg0 = next(p for p in promos if p["old_name"] == "arg0")
    
    assert p_m16["confidence"] == "syntax_backed"
    assert p_24["confidence"] == "artifact_backed"
    assert p_arg0["confidence"] == "artifact_backed"

def test_symbol_promotion_promote_temps():
    engine = SymbolPromotionEngine(
        source_recon={},
        type_recovery={},
        phase4_semantics={},
        layout_recovery={},
        promote_temps=True # enabled!
    )
    
    c_input = """
void test() {
    u64 tmp_x8 = 1;
    u64 tmp_sp = 2;
    tmp_x8 = tmp_sp;
}
"""
    rewritten, report = engine.run_symbol_promotion(c_input)
    assert "temp_x8" in rewritten
    assert "temp_sp" in rewritten
    assert "tmp_x8" not in rewritten
    assert report["temps_promoted"] == 2

def test_symbol_promotion_name_collisions():
    # Collision scenario: local_m16 already exists in function scope
    engine = SymbolPromotionEngine(
        source_recon={},
        type_recovery={},
        phase4_semantics={},
        layout_recovery={}
    )
    
    c_input = """
void test() {
    u64 stack_m16 = 0;
    u64 local_m16 = 5; // collision target
    stack_m16 = local_m16;
}
"""
    rewritten, report = engine.run_symbol_promotion(c_input)
    # Promotion should be skipped
    assert "stack_m16" in rewritten
    assert report["promotion_skipped"] == 1
    assert report["skipped_promotions"][0]["reason"] == "name collision"

def test_symbol_promotion_function_renaming():
    source_recon = {
        "data": {
            "functions": [
                {
                    "name": "_printf",
                    "c_name": "printf",
                    "entry_point": "0x100001ab8"
                }
            ]
        }
    }
    
    engine = SymbolPromotionEngine(
        source_recon=source_recon,
        type_recovery={},
        phase4_semantics={},
        layout_recovery={}
    )
    
    c_input = """
void call_0x100001ab8();
void main() {
    call_0x100001ab8();
}
"""
    rewritten, report = engine.run_symbol_promotion(c_input)
    assert "printf" in rewritten
    assert "call_0x100001ab8" not in rewritten
    assert report["function_symbols_promoted"] == 1
