# -*- coding: utf-8 -*-
"""
Phase 4D: Adversarial Tests for Final Semantic Artifact Merger

Tests cover:
  1. Missing required type_recovery fails clearly
  2. Malformed optional semantic artifact does not crash
  3. Malformed optional layout artifact does not crash
  4. Conflicting function identities do not merge
  5. Duplicate variables are not duplicated in final output
  6. Unknown variables produce uncertainty
  7. No new inference
  8. Layout candidates do not become structs
  9. No source or expression keys
  10. No confidence scoring keys created by 4D
  11. Pre-existing nested type confidence is tolerated
  12. Empty functions list works
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict, List

import pytest

from src.ir.types.phase4_semantics import (
    Phase4FunctionSemantics,
    Phase4SemanticsArtifact,
    build_phase4_semantics,
)
from src.ir.types.phase4_emitter import write_phase4_semantics_artifact


# ---------------------------------------------------------------------------
# Helpers (same factories as must-pass suite)
# ---------------------------------------------------------------------------

def _make_type_recovery(
    functions: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "schema_version": "4A.0.0",
        "provenance": {"phase": "4A"},
        "data": {"functions": functions or []},
    }


def _make_tr_function(
    name: str = "_main",
    entry_point: str = "0x1000",
    function_kind: str = "user",
    variables: List[Dict[str, Any]] = None,
    parameters: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "name": name,
        "entry_point": entry_point,
        "function_kind": function_kind,
        "signature": {
            "return_type": {"type": "unknown", "confidence": 0.2, "source": "fallback", "notes": []},
            "parameters": parameters or [],
            "variadic": False,
            "confidence": 0.2,
            "source": "fallback",
            "notes": [],
        },
        "variables": variables or [],
        "evidence": ["test"],
        "confidence": 0.2,
    }


def _make_semantic_recovery(
    functions: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "schema_version": "4B.0.0",
        "provenance": {"phase": "4B"},
        "data": {"functions": functions or []},
    }


def _make_sr_function(
    name: str = "_main",
    entry_point: str = "0x1000",
    total_constraints_applied: int = 0,
    variables: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "name": name,
        "entry_point": entry_point,
        "function_kind": "user",
        "refined_signature": {
            "return_type": {"type": "unknown", "confidence": 0.2},
            "parameters": [],
        },
        "variables": variables or [],
        "total_constraints_applied": total_constraints_applied,
        "evidence": [],
        "confidence": 0.2,
    }


def _make_layout_recovery(
    candidates: List[Dict[str, Any]] = None,
    unbound: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "schema_version": "4C.0.0",
        "provenance": {"phase": "4C"},
        "data": {
            "layout_candidates": candidates or [],
            "unbound_memory_accesses": unbound or [],
        },
    }


def _make_variable(
    name: str = "local_10",
    type_name: str = "unknown",
    confidence: float = 0.2,
) -> Dict[str, Any]:
    return {
        "name": name,
        "storage": "stack",
        "category": "local",
        "type": {"type": type_name, "confidence": confidence, "source": "fallback", "notes": []},
        "offset_bytes": -16,
        "size_bytes": 8,
        "source": "unified_ir",
        "confidence": confidence,
        "notes": [],
    }


def _serialize_artifact(artifact: Phase4SemanticsArtifact) -> str:
    """Serialize artifact to JSON string for content inspection."""
    return json.dumps(artifact.to_dict(), indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 1. Missing required type_recovery fails clearly
# ---------------------------------------------------------------------------

class TestMissingTypeRecoveryFails:
    def test_none_raises_value_error(self):
        with pytest.raises(ValueError, match="type_recovery"):
            build_phase4_semantics(None)

    def test_non_dict_raises_value_error(self):
        with pytest.raises(ValueError, match="type_recovery"):
            build_phase4_semantics("not a dict")

    def test_list_raises_value_error(self):
        with pytest.raises(ValueError, match="type_recovery"):
            build_phase4_semantics([1, 2, 3])

    def test_int_raises_value_error(self):
        with pytest.raises(ValueError, match="type_recovery"):
            build_phase4_semantics(42)


# ---------------------------------------------------------------------------
# 2. Malformed optional semantic artifact does not crash
# ---------------------------------------------------------------------------

class TestMalformedSemanticNoCrash:
    def test_semantic_is_string(self):
        tr = _make_type_recovery([_make_tr_function()])
        artifact = build_phase4_semantics(tr, semantic_recovery="garbage")
        assert len(artifact.functions) == 1

    def test_semantic_is_list(self):
        tr = _make_type_recovery([_make_tr_function()])
        artifact = build_phase4_semantics(tr, semantic_recovery=[1, 2])
        assert len(artifact.functions) == 1

    def test_semantic_is_empty_dict(self):
        tr = _make_type_recovery([_make_tr_function()])
        artifact = build_phase4_semantics(tr, semantic_recovery={})
        assert len(artifact.functions) == 1

    def test_semantic_has_bad_data_key(self):
        tr = _make_type_recovery([_make_tr_function()])
        artifact = build_phase4_semantics(tr, semantic_recovery={"data": "not_a_dict"})
        assert len(artifact.functions) == 1

    def test_semantic_missing_functions_key(self):
        tr = _make_type_recovery([_make_tr_function()])
        artifact = build_phase4_semantics(tr, semantic_recovery={"data": {"other": []}})
        assert len(artifact.functions) == 1


# ---------------------------------------------------------------------------
# 3. Malformed optional layout artifact does not crash
# ---------------------------------------------------------------------------

class TestMalformedLayoutNoCrash:
    def test_layout_is_string(self):
        tr = _make_type_recovery([_make_tr_function()])
        artifact = build_phase4_semantics(tr, layout_recovery="garbage")
        assert len(artifact.functions) == 1

    def test_layout_is_number(self):
        tr = _make_type_recovery([_make_tr_function()])
        artifact = build_phase4_semantics(tr, layout_recovery=42)
        assert len(artifact.functions) == 1

    def test_layout_missing_data_key(self):
        tr = _make_type_recovery([_make_tr_function()])
        artifact = build_phase4_semantics(tr, layout_recovery={"bad": True})
        assert len(artifact.functions) == 1

    def test_layout_has_non_list_candidates(self):
        tr = _make_type_recovery([_make_tr_function()])
        artifact = build_phase4_semantics(
            tr, layout_recovery={"data": {"layout_candidates": "bad"}}
        )
        fn = artifact.functions[0]
        assert fn.layout_candidates == []


# ---------------------------------------------------------------------------
# 4. Conflicting function identities do not merge
# ---------------------------------------------------------------------------

class TestConflictingIdentities:
    def test_same_name_different_entry_no_merge(self):
        tr = _make_type_recovery([
            _make_tr_function(name="_main", entry_point="0x1000"),
        ])
        sr = _make_semantic_recovery([
            _make_sr_function(name="_main", entry_point="0x2000",
                              total_constraints_applied=9),
        ])
        artifact = build_phase4_semantics(tr, sr)
        # The function at 0x1000 should NOT get constraints from 0x2000
        fn_1000 = [f for f in artifact.functions if f.entry_point == "0x1000"][0]
        assert fn_1000.constraints_summary["total_constraints_applied"] == 0

    def test_conflicting_semantic_preserved_separately(self):
        tr = _make_type_recovery([
            _make_tr_function(name="_main", entry_point="0x1000"),
        ])
        sr = _make_semantic_recovery([
            _make_sr_function(name="_main", entry_point="0x2000",
                              total_constraints_applied=9),
        ])
        artifact = build_phase4_semantics(tr, sr)
        # The semantic-only function should appear with uncertainty
        fn_2000_list = [f for f in artifact.functions if f.entry_point == "0x2000"]
        assert len(fn_2000_list) == 1
        fn_2000 = fn_2000_list[0]
        assert any("not in type recovery" in u.lower() for u in fn_2000.uncertainties)


# ---------------------------------------------------------------------------
# 5. Duplicate variables are not duplicated in final output
# ---------------------------------------------------------------------------

class TestDuplicateVariableDedup:
    def test_duplicate_vars_deduped(self):
        v1 = _make_variable("local_10")
        v2 = _make_variable("local_10")  # duplicate
        v3 = _make_variable("local_20")
        tr = _make_type_recovery([
            _make_tr_function(variables=[v1, v2, v3]),
        ])
        artifact = build_phase4_semantics(tr)
        fn = artifact.functions[0]
        var_names = [v["name"] for v in fn.variables]
        assert var_names == ["local_10", "local_20"]  # deduped, sorted


# ---------------------------------------------------------------------------
# 6. Unknown variables produce uncertainty
# ---------------------------------------------------------------------------

class TestUnknownVariableUncertainty:
    def test_unknown_type_variable_noted(self):
        tr = _make_type_recovery([
            _make_tr_function(variables=[_make_variable("local_10", "unknown")]),
        ])
        artifact = build_phase4_semantics(tr)
        fn = artifact.functions[0]
        assert any("unknown" in u.lower() for u in fn.uncertainties)


# ---------------------------------------------------------------------------
# 7. No new inference
# ---------------------------------------------------------------------------

class TestNoNewInference:
    def test_unknown_var_stays_unknown(self):
        tr = _make_type_recovery([
            _make_tr_function(variables=[_make_variable("local_10", "unknown")]),
        ])
        artifact = build_phase4_semantics(tr)
        fn = artifact.functions[0]
        # Variable type must still be "unknown" — no inference
        var = fn.variables[0]
        assert var["type"]["type"] == "unknown"

    def test_no_refined_variables_without_semantic(self):
        tr = _make_type_recovery([
            _make_tr_function(variables=[_make_variable()]),
        ])
        artifact = build_phase4_semantics(tr)
        fn = artifact.functions[0]
        assert fn.refined_variables == []


# ---------------------------------------------------------------------------
# 8. Layout candidates do not become structs
# ---------------------------------------------------------------------------

class TestNoStructs:
    def test_no_structs_key(self):
        tr = _make_type_recovery([_make_tr_function()])
        lr = _make_layout_recovery(candidates=[{
            "function_entry": "0x1000",
            "function_name": "_main",
            "base_id": "sp",
            "layout_kind": "record_like",
            "observed_offsets": [0, 8],
            "observed_sizes": [4, 8],
        }])
        artifact = build_phase4_semantics(tr, layout_recovery=lr)
        output = _serialize_artifact(artifact)
        assert '"structs"' not in output
        assert '"fields"' not in output


# ---------------------------------------------------------------------------
# 9. No source or expression keys
# ---------------------------------------------------------------------------

class TestNoSourceExpressionKeys:
    def test_forbidden_source_keys(self):
        tr = _make_type_recovery([
            _make_tr_function(variables=[_make_variable()]),
        ])
        sr = _make_semantic_recovery([_make_sr_function(total_constraints_applied=1)])
        lr = _make_layout_recovery(candidates=[{
            "function_entry": "0x1000",
            "function_name": "_main",
            "base_id": "sp",
            "layout_kind": "scalar",
        }])
        artifact = build_phase4_semantics(tr, sr, lr)
        output = _serialize_artifact(artifact)
        for forbidden in ("source_code", "c_source", "expressions", "statements"):
            assert f'"{forbidden}"' not in output


# ---------------------------------------------------------------------------
# 10. No confidence scoring keys created by 4D
# ---------------------------------------------------------------------------

class TestNoConfidenceScoringKeys:
    def test_no_4d_confidence_keys(self):
        tr = _make_type_recovery([_make_tr_function()])
        artifact = build_phase4_semantics(tr)
        d = artifact.to_dict()

        # Check top-level data keys
        top_keys = set(d.keys())
        for forbidden in ("overall_confidence", "risk", "similarity",
                          "source_similarity", "semantic_similarity"):
            assert forbidden not in top_keys

        # Check data-level keys
        data_keys = set(d["data"].keys())
        for forbidden in ("overall_confidence", "risk", "similarity",
                          "source_similarity", "semantic_similarity",
                          "confidence"):
            assert forbidden not in data_keys

        # Check summary keys
        summary_keys = set(d["data"]["summary"].keys())
        for forbidden in ("confidence", "overall_confidence", "risk",
                          "similarity"):
            assert forbidden not in summary_keys

        # Check function-level keys (Phase 4D-created)
        if d["data"]["functions"]:
            fn_keys = set(d["data"]["functions"][0].keys())
            for forbidden in ("confidence", "overall_confidence", "risk",
                              "similarity", "source_similarity",
                              "semantic_similarity"):
                assert forbidden not in fn_keys


# ---------------------------------------------------------------------------
# 11. Pre-existing nested type confidence is tolerated
# ---------------------------------------------------------------------------

class TestPreExistingConfidenceTolerated:
    def test_nested_type_confidence_preserved(self):
        var = _make_variable("local_10", "int32", confidence=0.6)
        tr = _make_type_recovery([
            _make_tr_function(variables=[var]),
        ])
        artifact = build_phase4_semantics(tr)
        fn = artifact.functions[0]
        # The original variable dict should still contain its nested confidence
        assert fn.variables[0]["type"]["confidence"] == 0.6

    def test_no_new_top_level_confidence_despite_nested(self):
        var = _make_variable("local_10", "int32", confidence=0.9)
        tr = _make_type_recovery([
            _make_tr_function(variables=[var]),
        ])
        artifact = build_phase4_semantics(tr)
        d = artifact.to_dict()
        fn_d = d["data"]["functions"][0]
        # No top-level confidence key on the function
        assert "confidence" not in fn_d


# ---------------------------------------------------------------------------
# 12. Empty functions list works
# ---------------------------------------------------------------------------

class TestEmptyFunctionsList:
    def test_empty_functions_produces_empty(self):
        tr = _make_type_recovery([])
        artifact = build_phase4_semantics(tr)
        assert len(artifact.functions) == 0
        assert artifact.summary["functions_total"] == 0

    def test_empty_functions_emittable(self):
        tr = _make_type_recovery([])
        artifact = build_phase4_semantics(tr)
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "phase4_semantics.json")
            write_phase4_semantics_artifact(artifact, out)
            with open(out) as f:
                payload = json.load(f)
            assert payload["data"]["functions"] == []
            assert payload["data"]["summary"]["functions_total"] == 0


# ---------------------------------------------------------------------------
# Extra adversarial: mixed scenarios
# ---------------------------------------------------------------------------

class TestMixedAdversarial:
    def test_non_dict_function_entries_skipped(self):
        tr = {"data": {"functions": ["not_a_dict", None, 42, _make_tr_function()]}}
        artifact = build_phase4_semantics(tr)
        assert len(artifact.functions) == 1

    def test_sr_with_non_dict_function_entries(self):
        tr = _make_type_recovery([_make_tr_function()])
        sr = {"data": {"functions": [None, "bad", _make_sr_function()]}}
        artifact = build_phase4_semantics(tr, sr)
        assert len(artifact.functions) >= 1

    def test_layout_with_non_dict_candidates(self):
        tr = _make_type_recovery([_make_tr_function()])
        lr = {"data": {"layout_candidates": [None, "bad", 42], "unbound_memory_accesses": []}}
        artifact = build_phase4_semantics(tr, layout_recovery=lr)
        fn = artifact.functions[0]
        assert fn.layout_candidates == []

    def test_large_function_count_no_crash(self):
        """Stress test: 100 functions from each artifact."""
        tr_funcs = [_make_tr_function(name=f"fn_{i}", entry_point=f"0x{i:x}")
                    for i in range(100)]
        sr_funcs = [_make_sr_function(name=f"fn_{i}", entry_point=f"0x{i:x}",
                                      total_constraints_applied=i % 5)
                    for i in range(100)]
        lr_cands = [{"function_entry": f"0x{i:x}", "function_name": f"fn_{i}",
                     "base_id": "sp", "layout_kind": "scalar",
                     "observed_offsets": [0], "observed_sizes": [4]}
                    for i in range(50)]
        tr = _make_type_recovery(tr_funcs)
        sr = _make_semantic_recovery(sr_funcs)
        lr = _make_layout_recovery(candidates=lr_cands)
        artifact = build_phase4_semantics(tr, sr, lr)
        assert artifact.summary["functions_total"] == 100
        assert artifact.summary["functions_with_layout_candidates"] == 50
