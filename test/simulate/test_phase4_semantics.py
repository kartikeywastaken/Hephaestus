# -*- coding: utf-8 -*-
"""
Phase 4D: Final Phase 4 Semantic Artifact Merger — Must-Pass Tests

Tests cover:
  1. Type-only input succeeds
  2. Type + semantic merge succeeds
  3. Type + layout merge succeeds
  4. Full 4A + 4B + 4C merge succeeds
  5. Function matching prefers entry point
  6. Name fallback works only when entry point is missing
  7. Unmatched semantic function is preserved with uncertainty
  8. Unmatched layout candidate is preserved only if identity is clear
  9. Summary counts are correct
  10. Deterministic output
"""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from typing import Any, Dict, List

import pytest

from src.ir.types.phase4_semantics import (
    SCHEMA_VERSION,
    Phase4FunctionSemantics,
    Phase4SemanticsArtifact,
    build_phase4_semantics,
)
from src.ir.types.phase4_emitter import write_phase4_semantics_artifact


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_type_recovery(
    functions: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a minimal type_recovery.json dict."""
    return {
        "schema_version": "4A.0.0",
        "provenance": {"phase": "4A"},
        "data": {
            "functions": functions or [],
        },
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
    """Build a minimal semantic_recovery.json dict."""
    return {
        "schema_version": "4B.0.0",
        "provenance": {"phase": "4B"},
        "data": {
            "functions": functions or [],
        },
    }


def _make_sr_function(
    name: str = "_main",
    entry_point: str = "0x1000",
    function_kind: str = "user",
    total_constraints_applied: int = 0,
    variables: List[Dict[str, Any]] = None,
    refined_signature: Dict[str, Any] = None,
) -> Dict[str, Any]:
    return {
        "name": name,
        "entry_point": entry_point,
        "function_kind": function_kind,
        "refined_signature": refined_signature or {
            "return_type": {"type": "unknown", "confidence": 0.2},
            "parameters": [],
        },
        "variables": variables or [],
        "total_constraints_applied": total_constraints_applied,
        "evidence": ["test"],
        "confidence": 0.2,
    }


def _make_layout_recovery(
    candidates: List[Dict[str, Any]] = None,
    unbound: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a minimal layout_recovery.json dict."""
    return {
        "schema_version": "4C.0.0",
        "provenance": {"phase": "4C"},
        "data": {
            "layout_candidates": candidates or [],
            "unbound_memory_accesses": unbound or [],
        },
    }


def _make_layout_candidate(
    fn_entry: str = "0x1000",
    fn_name: str = "_main",
    base_id: str = "sp",
    layout_kind: str = "scalar",
) -> Dict[str, Any]:
    return {
        "function_entry": fn_entry,
        "function_name": fn_name,
        "base_id": base_id,
        "layout_kind": layout_kind,
        "observed_offsets": [-16],
        "min_offset": -16,
        "max_offset": -16,
        "observed_sizes": [8],
        "access_count": 1,
        "evidence_notes": ["test note"],
        "source_instrs": ["0x1004"],
    }


def _make_unbound_access(
    fn_entry: str = "0x1000",
    fn_name: str = "_main",
) -> Dict[str, Any]:
    return {
        "function_entry": fn_entry,
        "function_name": fn_name,
        "block_id": "bb0",
        "instr_address": "0x1000",
        "base_id": "sp",
        "offset": None,
        "size_bytes": 8,
        "access_kind": "load",
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


def _make_refined_variable(
    name: str = "local_10",
    type_name: str = "int32",
    constraints_applied: int = 1,
) -> Dict[str, Any]:
    return {
        "name": name,
        "refined_type": {"type": type_name, "confidence": 0.6, "source": "constraint", "notes": []},
        "constraints_applied": constraints_applied,
        "phase4a_type": "unknown",
    }


# ---------------------------------------------------------------------------
# 1. Type-only input succeeds
# ---------------------------------------------------------------------------

class TestTypeOnlyInput:
    def test_type_only_produces_artifact(self):
        tr = _make_type_recovery([_make_tr_function()])
        artifact = build_phase4_semantics(tr)
        assert artifact.schema_version == SCHEMA_VERSION
        assert len(artifact.functions) == 1

    def test_type_only_has_empty_refined_fields(self):
        tr = _make_type_recovery([_make_tr_function()])
        artifact = build_phase4_semantics(tr)
        fn = artifact.functions[0]
        assert fn.refined_signature == {}
        assert fn.refined_variables == []
        assert fn.refined_parameters == []

    def test_type_only_has_empty_layout_fields(self):
        tr = _make_type_recovery([_make_tr_function()])
        artifact = build_phase4_semantics(tr)
        fn = artifact.functions[0]
        assert fn.layout_candidates == []
        assert fn.unbound_memory_accesses == []

    def test_type_only_has_uncertainties(self):
        tr = _make_type_recovery([_make_tr_function()])
        artifact = build_phase4_semantics(tr)
        fn = artifact.functions[0]
        assert any("semantic" in u.lower() for u in fn.uncertainties)
        assert any("layout" in u.lower() for u in fn.uncertainties)

    def test_type_only_emitter(self):
        tr = _make_type_recovery([_make_tr_function()])
        artifact = build_phase4_semantics(tr)
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "phase4_semantics.json")
            write_phase4_semantics_artifact(artifact, out)
            with open(out, "r") as f:
                payload = json.load(f)
            assert payload["schema_version"] == SCHEMA_VERSION
            assert payload["provenance"]["phase"] == "4D"
            assert len(payload["data"]["functions"]) == 1


# ---------------------------------------------------------------------------
# 2. Type + semantic merge succeeds
# ---------------------------------------------------------------------------

class TestTypeSemanticMerge:
    def test_merge_with_matching_function(self):
        tr = _make_type_recovery([
            _make_tr_function(variables=[_make_variable()]),
        ])
        sr = _make_semantic_recovery([
            _make_sr_function(
                total_constraints_applied=2,
                variables=[_make_refined_variable()],
            ),
        ])
        artifact = build_phase4_semantics(tr, sr)
        fn = artifact.functions[0]
        assert len(fn.variables) == 1
        assert len(fn.refined_variables) == 1
        assert fn.constraints_summary["total_constraints_applied"] == 2

    def test_known_facts_mention_refinement(self):
        tr = _make_type_recovery([
            _make_tr_function(variables=[_make_variable()]),
        ])
        sr = _make_semantic_recovery([
            _make_sr_function(
                total_constraints_applied=2,
                variables=[_make_refined_variable()],
            ),
        ])
        artifact = build_phase4_semantics(tr, sr)
        fn = artifact.functions[0]
        assert any("constraint" in f.lower() for f in fn.known_facts)

    def test_recovered_variables_preserved(self):
        tr = _make_type_recovery([
            _make_tr_function(variables=[_make_variable("local_10"), _make_variable("local_20")]),
        ])
        sr = _make_semantic_recovery([
            _make_sr_function(variables=[_make_refined_variable("local_10")]),
        ])
        artifact = build_phase4_semantics(tr, sr)
        fn = artifact.functions[0]
        assert len(fn.variables) == 2
        var_names = {v["name"] for v in fn.variables}
        assert var_names == {"local_10", "local_20"}


# ---------------------------------------------------------------------------
# 3. Type + layout merge succeeds
# ---------------------------------------------------------------------------

class TestTypeLayoutMerge:
    def test_merge_with_matching_layout(self):
        tr = _make_type_recovery([_make_tr_function()])
        lr = _make_layout_recovery(
            candidates=[_make_layout_candidate()],
            unbound=[_make_unbound_access()],
        )
        artifact = build_phase4_semantics(tr, layout_recovery=lr)
        fn = artifact.functions[0]
        assert len(fn.layout_candidates) == 1
        assert len(fn.unbound_memory_accesses) == 1

    def test_known_facts_mention_layout(self):
        tr = _make_type_recovery([_make_tr_function()])
        lr = _make_layout_recovery(candidates=[_make_layout_candidate()])
        artifact = build_phase4_semantics(tr, layout_recovery=lr)
        fn = artifact.functions[0]
        assert any("layout" in f.lower() for f in fn.known_facts)


# ---------------------------------------------------------------------------
# 4. Full 4A + 4B + 4C merge succeeds
# ---------------------------------------------------------------------------

class TestFullMerge:
    def test_all_three_artifacts_merged(self):
        tr = _make_type_recovery([
            _make_tr_function(variables=[_make_variable()]),
        ])
        sr = _make_semantic_recovery([
            _make_sr_function(
                total_constraints_applied=3,
                variables=[_make_refined_variable()],
            ),
        ])
        lr = _make_layout_recovery(
            candidates=[_make_layout_candidate()],
            unbound=[_make_unbound_access()],
        )
        artifact = build_phase4_semantics(tr, sr, lr)
        fn = artifact.functions[0]

        # Type data
        assert len(fn.variables) == 1
        # Semantic data
        assert len(fn.refined_variables) == 1
        assert fn.constraints_summary["total_constraints_applied"] == 3
        # Layout data
        assert len(fn.layout_candidates) == 1
        assert len(fn.unbound_memory_accesses) == 1

    def test_summary_counts_correct(self):
        tr = _make_type_recovery([
            _make_tr_function(variables=[_make_variable()]),
        ])
        sr = _make_semantic_recovery([
            _make_sr_function(
                total_constraints_applied=3,
                variables=[_make_refined_variable()],
            ),
        ])
        lr = _make_layout_recovery(
            candidates=[_make_layout_candidate()],
        )
        artifact = build_phase4_semantics(tr, sr, lr)
        s = artifact.summary
        assert s["functions_total"] == 1
        assert s["functions_with_refinement"] == 1
        assert s["functions_with_layout_candidates"] == 1
        assert s["total_layout_candidates"] == 1
        assert s["total_constraints_applied"] == 3


# ---------------------------------------------------------------------------
# 5. Function matching prefers entry point
# ---------------------------------------------------------------------------

class TestFunctionMatchingPreference:
    def test_entry_point_wins_over_name(self):
        """Two functions share the same name but different entry points → no merge."""
        tr = _make_type_recovery([
            _make_tr_function(name="fn_a", entry_point="0x1000"),
            _make_tr_function(name="fn_a", entry_point="0x2000"),
        ])
        sr = _make_semantic_recovery([
            _make_sr_function(name="fn_a", entry_point="0x1000",
                              total_constraints_applied=5),
        ])
        artifact = build_phase4_semantics(tr, sr)
        # Should have 2 functions
        assert len(artifact.functions) == 2
        # Only the one at 0x1000 should have constraints
        fn_1000 = [f for f in artifact.functions if f.entry_point == "0x1000"][0]
        fn_2000 = [f for f in artifact.functions if f.entry_point == "0x2000"][0]
        assert fn_1000.constraints_summary["total_constraints_applied"] == 5
        assert fn_2000.constraints_summary["total_constraints_applied"] == 0


# ---------------------------------------------------------------------------
# 6. Name fallback works only when entry point is missing
# ---------------------------------------------------------------------------

class TestNameFallback:
    def test_name_fallback_when_no_entry(self):
        tr = _make_type_recovery([
            _make_tr_function(name="my_func", entry_point="0x3000"),
        ])
        sr = _make_semantic_recovery([
            _make_sr_function(name="my_func", entry_point="unknown",
                              total_constraints_applied=7),
        ])
        artifact = build_phase4_semantics(tr, sr)
        fn = artifact.functions[0]
        assert fn.constraints_summary["total_constraints_applied"] == 7


# ---------------------------------------------------------------------------
# 7. Unmatched semantic function is preserved with uncertainty
# ---------------------------------------------------------------------------

class TestUnmatchedSemanticFunction:
    def test_unmatched_sr_function_has_uncertainty(self):
        tr = _make_type_recovery([
            _make_tr_function(name="fn_a", entry_point="0x1000"),
        ])
        sr = _make_semantic_recovery([
            _make_sr_function(name="fn_a", entry_point="0x1000"),
            _make_sr_function(name="fn_b", entry_point="0x2000",
                              total_constraints_applied=1),
        ])
        artifact = build_phase4_semantics(tr, sr)
        # fn_b should appear with uncertainty
        fn_b_list = [f for f in artifact.functions if f.name == "fn_b"]
        assert len(fn_b_list) == 1
        fn_b = fn_b_list[0]
        assert any("not in type recovery" in u.lower() for u in fn_b.uncertainties)


# ---------------------------------------------------------------------------
# 8. Unmatched layout candidate is preserved only if identity is clear
# ---------------------------------------------------------------------------

class TestUnmatchedLayoutCandidate:
    def test_layout_for_known_function_attached(self):
        tr = _make_type_recovery([
            _make_tr_function(name="fn_a", entry_point="0x1000"),
        ])
        lr = _make_layout_recovery(candidates=[
            _make_layout_candidate(fn_entry="0x1000", fn_name="fn_a"),
        ])
        artifact = build_phase4_semantics(tr, layout_recovery=lr)
        fn = artifact.functions[0]
        assert len(fn.layout_candidates) == 1

    def test_layout_for_unknown_function_not_attached(self):
        tr = _make_type_recovery([
            _make_tr_function(name="fn_a", entry_point="0x1000"),
        ])
        lr = _make_layout_recovery(candidates=[
            _make_layout_candidate(fn_entry="0x9999", fn_name="fn_z"),
        ])
        artifact = build_phase4_semantics(tr, layout_recovery=lr)
        fn = artifact.functions[0]
        assert len(fn.layout_candidates) == 0


# ---------------------------------------------------------------------------
# 9. Summary counts are correct
# ---------------------------------------------------------------------------

class TestSummaryCounts:
    def test_summary_fields_present(self):
        tr = _make_type_recovery([])
        artifact = build_phase4_semantics(tr)
        s = artifact.summary
        required = {
            "functions_total", "functions_with_refinement",
            "functions_with_layout_candidates",
            "total_layout_candidates", "total_unbound_memory_accesses",
            "total_constraints_applied",
        }
        assert required.issubset(set(s.keys()))

    def test_empty_functions_summary(self):
        tr = _make_type_recovery([])
        artifact = build_phase4_semantics(tr)
        s = artifact.summary
        assert s["functions_total"] == 0
        assert s["functions_with_refinement"] == 0
        assert s["total_constraints_applied"] == 0

    def test_multi_function_summary(self):
        tr = _make_type_recovery([
            _make_tr_function(name="a", entry_point="0x1000"),
            _make_tr_function(name="b", entry_point="0x2000"),
        ])
        sr = _make_semantic_recovery([
            _make_sr_function(name="a", entry_point="0x1000",
                              total_constraints_applied=2),
        ])
        lr = _make_layout_recovery(candidates=[
            _make_layout_candidate(fn_entry="0x1000", fn_name="a"),
            _make_layout_candidate(fn_entry="0x2000", fn_name="b"),
        ])
        artifact = build_phase4_semantics(tr, sr, lr)
        s = artifact.summary
        assert s["functions_total"] == 2
        assert s["functions_with_refinement"] == 1
        assert s["functions_with_layout_candidates"] == 2
        assert s["total_layout_candidates"] == 2
        assert s["total_constraints_applied"] == 2


# ---------------------------------------------------------------------------
# 10. Deterministic output
# ---------------------------------------------------------------------------

class TestDeterministicOutput:
    def test_same_input_same_output(self):
        tr = _make_type_recovery([
            _make_tr_function(name="b", entry_point="0x2000",
                              variables=[_make_variable("var_b")]),
            _make_tr_function(name="a", entry_point="0x1000",
                              variables=[_make_variable("var_a")]),
        ])
        sr = _make_semantic_recovery([
            _make_sr_function(name="a", entry_point="0x1000",
                              total_constraints_applied=1,
                              variables=[_make_refined_variable("var_a")]),
        ])
        lr = _make_layout_recovery(candidates=[
            _make_layout_candidate(fn_entry="0x2000", fn_name="b"),
        ])

        a1 = build_phase4_semantics(tr, sr, lr)
        a2 = build_phase4_semantics(deepcopy(tr), deepcopy(sr), deepcopy(lr))

        assert a1.to_dict() == a2.to_dict()

    def test_emitter_output_deterministic(self):
        tr = _make_type_recovery([_make_tr_function()])
        artifact = build_phase4_semantics(tr)
        with tempfile.TemporaryDirectory() as tmpdir:
            p1 = os.path.join(tmpdir, "out1.json")
            p2 = os.path.join(tmpdir, "out2.json")
            write_phase4_semantics_artifact(artifact, p1)
            write_phase4_semantics_artifact(artifact, p2)
            with open(p1) as f1, open(p2) as f2:
                assert f1.read() == f2.read()
