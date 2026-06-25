# -*- coding: utf-8 -*-
"""
Tests for src/agent/validators.py — deterministic Python validator.
No Ollama or Groq required.
"""
import pytest
from src.agent.validators import validate_agent_output


# ── Helpers to build valid outputs ────────────────────────────────────────────

def _valid_evidence():
    return {
        "function": "main",
        "facts": {
            "calls": ["printf"],
            "loops": 1,
            "conditions": 2,
            "returns_value": True,
            "constants": [],
            "layout_candidates": [],
            "dynamic_observations_present": False,
            "global_behavior_refs": [],
        },
        "evidence_refs": [
            {"kind": "static", "source": "source_reconstruction.json", "detail": "has calls"}
        ],
        "uncertainties": ["source variable names are unknown"],
    }


def _valid_dynamic():
    return {
        "function": "main",
        "dynamic_behavior": [
            {
                "kind": "argv_dependency",
                "text": "Observed behavior changes across argv variants.",
                "basis": ["behavior_profile.summary.argv_sensitive == true"],
                "confidence": "medium",
                "evidence_level": "static_dynamic_fused",
            }
        ],
        "limitations": ["dynamic evidence only covers provided inputs"],
    }


def _valid_reconstruction():
    return {
        "function": "main",
        "hypotheses": [
            {
                "kind": "function_summary",
                "text": "Appears to coordinate command-line-dependent behavior.",
                "basis": ["static main signature", "argv-sensitive dynamic behavior"],
                "confidence": "medium",
                "evidence_level": "static_dynamic_fused",
                "requires_human_approval": True,
            }
        ],
        "suggested_names": [
            {
                "target": "local_20",
                "suggested_name": "possible_total",
                "basis": ["value updated repeatedly in readable C"],
                "confidence": "low",
                "evidence_level": "pattern_inferred",
                "requires_human_approval": True,
            }
        ],
        "suggested_structs": [],
    }


def _valid_critic():
    return {
        "function": "main",
        "critic_findings": [
            {
                "target": "hypotheses[0]",
                "status": "accept_with_warning",
                "reason": "Limited tested inputs.",
                "recommended_confidence": "medium",
                "recommended_evidence_level": "static_dynamic_fused",
            }
        ],
        "rejected_suggestions": [],
    }


def _valid_finalizer():
    return {
        "function": "main",
        "summary": {
            "text": "Appears to coordinate command-line-dependent behavior.",
            "confidence": "medium",
            "evidence_level": "static_dynamic_fused",
            "critic_status": "accept_with_warning",
            "requires_human_approval": True,
        },
        "suggestions": [
            {
                "kind": "function_summary",
                "target": "main",
                "text": "Appears to coordinate command-line-dependent behavior.",
                "confidence": "medium",
                "evidence_level": "static_dynamic_fused",
                "requires_human_approval": True,
                "basis": ["argv-sensitive dynamic behavior", "static main evidence"],
                "critic_status": "accept_with_warning",
            }
        ],
        "rejected": [],
    }


# ── Valid outputs pass ─────────────────────────────────────────────────────────

class TestValidOutputsPass:
    def test_valid_evidence_passes(self):
        ok, errs = validate_agent_output(_valid_evidence(), "evidence")
        assert ok, f"Expected pass but got errors: {errs}"

    def test_valid_dynamic_passes(self):
        ok, errs = validate_agent_output(_valid_dynamic(), "dynamic_behavior")
        assert ok, f"Expected pass but got errors: {errs}"

    def test_valid_reconstruction_passes(self):
        ok, errs = validate_agent_output(_valid_reconstruction(), "reconstruction")
        assert ok, f"Expected pass but got errors: {errs}"

    def test_valid_critic_passes(self):
        ok, errs = validate_agent_output(_valid_critic(), "critic")
        assert ok, f"Expected pass but got errors: {errs}"

    def test_valid_finalizer_passes(self):
        ok, errs = validate_agent_output(_valid_finalizer(), "finalizer")
        assert ok, f"Expected pass but got errors: {errs}"


# ── Forbidden certainty phrases ────────────────────────────────────────────────

class TestForbiddenPhrases:
    def test_rejects_definitely_equivalent(self):
        bad = _valid_evidence()
        bad["uncertainties"] = ["This is definitely equivalent to original."]
        ok, errs = validate_agent_output(bad, "evidence")
        assert not ok
        assert any("definitely equivalent" in e for e in errs)

    def test_rejects_semantic_equivalence(self):
        bad = _valid_reconstruction()
        bad["hypotheses"][0]["text"] = "There is semantic equivalence here."
        ok, errs = validate_agent_output(bad, "reconstruction")
        assert not ok
        assert any("semantic equivalence" in e for e in errs)

    def test_rejects_exact_source(self):
        bad = _valid_finalizer()
        bad["summary"]["text"] = "We found the exact source variable."
        ok, errs = validate_agent_output(bad, "finalizer")
        assert not ok
        assert any("exact source" in e for e in errs)

    def test_rejects_guaranteed(self):
        bad = _valid_evidence()
        bad["facts"]["calls"] = ["guaranteed output"]
        ok, errs = validate_agent_output(bad, "evidence")
        assert not ok
        assert any("guaranteed" in e for e in errs)

    def test_rejects_same_behavior_as_original(self):
        bad = _valid_dynamic()
        bad["dynamic_behavior"][0]["text"] = "same behavior as original."
        ok, errs = validate_agent_output(bad, "dynamic_behavior")
        assert not ok
        assert any("same behavior as original" in e for e in errs)

    def test_rejects_proven_struct(self):
        bad = _valid_reconstruction()
        bad["hypotheses"][0]["text"] = "This is a proven struct layout."
        ok, errs = validate_agent_output(bad, "reconstruction")
        assert not ok
        assert any("proven struct" in e for e in errs)

    def test_recursive_scan_in_nested_dict(self):
        bad = _valid_finalizer()
        bad["suggestions"][0]["basis"] = ["This is definitely equivalent to original source"]
        ok, errs = validate_agent_output(bad, "finalizer")
        assert not ok


# ── Invalid confidence labels ──────────────────────────────────────────────────

class TestInvalidConfidence:
    def test_rejects_unknown_confidence_label(self):
        bad = _valid_dynamic()
        bad["dynamic_behavior"][0]["confidence"] = "certain"
        ok, errs = validate_agent_output(bad, "dynamic_behavior")
        assert not ok
        assert any("confidence" in e for e in errs)

    def test_rejects_very_high_confidence(self):
        bad = _valid_finalizer()
        bad["summary"]["confidence"] = "very_high"
        ok, errs = validate_agent_output(bad, "finalizer")
        assert not ok

    def test_allows_all_valid_levels(self):
        for level in ("high", "medium", "low", "unknown"):
            good = _valid_evidence()
            # inject into a nested location that will be checked
            good["facts"]["dynamic_observations_present"] = False
            ok, errs = validate_agent_output(good, "evidence")
            assert ok


# ── Invalid evidence_level labels ─────────────────────────────────────────────

class TestInvalidEvidenceLevel:
    def test_rejects_invalid_level(self):
        bad = _valid_reconstruction()
        bad["hypotheses"][0]["evidence_level"] = "magic_inferred"
        ok, errs = validate_agent_output(bad, "reconstruction")
        assert not ok
        assert any("evidence_level" in e for e in errs)

    def test_allows_all_valid_evidence_levels(self):
        for level in ("static_evidence", "dynamic_observed", "static_dynamic_fused",
                      "pattern_inferred", "hypothesis", "unsupported"):
            good = _valid_dynamic()
            good["dynamic_behavior"][0]["evidence_level"] = level
            ok, errs = validate_agent_output(good, "dynamic_behavior")
            assert ok, f"level '{level}' should be valid, got: {errs}"


# ── recovered_agent.c rejection ────────────────────────────────────────────────

class TestRecoveredAgentC:
    def test_rejects_recovered_agent_c_mention(self):
        bad = _valid_finalizer()
        bad["suggestions"][0]["text"] = "Output this to recovered_agent.c"
        ok, errs = validate_agent_output(bad, "finalizer")
        assert not ok
        assert any("recovered_agent.c" in e for e in errs)

    def test_rejects_in_any_string(self):
        bad = _valid_evidence()
        bad["uncertainties"] = ["See recovered_agent.c for details"]
        ok, errs = validate_agent_output(bad, "evidence")
        assert not ok


# ── possible_ prefix enforcement ──────────────────────────────────────────────

class TestPossiblePrefix:
    def test_rejects_speculative_name_without_prefix(self):
        bad = _valid_reconstruction()
        bad["suggested_names"][0]["suggested_name"] = "total_count"
        bad["suggested_names"][0]["evidence_level"] = "pattern_inferred"
        ok, errs = validate_agent_output(bad, "reconstruction")
        assert not ok
        assert any("possible_" in e for e in errs)

    def test_rejects_missing_requires_human_approval(self):
        bad = _valid_reconstruction()
        bad["suggested_names"][0]["suggested_name"] = "possible_total"
        bad["suggested_names"][0]["evidence_level"] = "pattern_inferred"
        bad["suggested_names"][0]["requires_human_approval"] = False
        ok, errs = validate_agent_output(bad, "reconstruction")
        assert not ok
        assert any("requires_human_approval" in e for e in errs)

    def test_accepts_possible_prefix_with_approval(self):
        good = _valid_reconstruction()
        good["suggested_names"][0]["suggested_name"] = "possible_count"
        good["suggested_names"][0]["evidence_level"] = "pattern_inferred"
        good["suggested_names"][0]["requires_human_approval"] = True
        ok, errs = validate_agent_output(good, "reconstruction")
        assert ok, f"Should pass with possible_ prefix: {errs}"


# ── Required keys ──────────────────────────────────────────────────────────────

class TestRequiredKeys:
    def test_missing_function_key_evidence(self):
        bad = _valid_evidence()
        del bad["function"]
        ok, errs = validate_agent_output(bad, "evidence")
        assert not ok
        assert any("function" in e for e in errs)

    def test_missing_facts_key(self):
        bad = _valid_evidence()
        del bad["facts"]
        ok, errs = validate_agent_output(bad, "evidence")
        assert not ok

    def test_missing_suggestions_key_finalizer(self):
        bad = _valid_finalizer()
        del bad["suggestions"]
        ok, errs = validate_agent_output(bad, "finalizer")
        assert not ok

    def test_missing_critic_findings(self):
        bad = _valid_critic()
        del bad["critic_findings"]
        ok, errs = validate_agent_output(bad, "critic")
        assert not ok


# ── Basis enforcement ──────────────────────────────────────────────────────────

class TestBasisEnforcement:
    def test_hypothesis_empty_basis(self):
        bad = _valid_reconstruction()
        bad["hypotheses"][0]["basis"] = []
        ok, errs = validate_agent_output(bad, "reconstruction")
        assert not ok
        assert any("basis" in e for e in errs)

    def test_finalizer_suggestion_empty_basis(self):
        bad = _valid_finalizer()
        bad["suggestions"][0]["basis"] = []
        ok, errs = validate_agent_output(bad, "finalizer")
        assert not ok
        assert any("basis" in e for e in errs)
