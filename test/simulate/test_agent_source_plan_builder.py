# -*- coding: utf-8 -*-
"""
Test: Phase 11 plan builder.

Tests:
  - plan loads accepted suggestions
  - plan disables human-approval suggestions by default
  - --allow-human-suggestions enables them
  - plan entries include basis/evidence/confidence
  - suggestions with no basis are disabled
  - suggestions with forbidden phrases are skipped
  - empty suggestions list returns empty plan
"""

from __future__ import annotations
import pytest
from types import SimpleNamespace

from src.agent_source.plan_builder import build_source_plan


def _make_arts(suggestions: list[dict] | None = None, missing_required: list | None = None):
    """Build a minimal mock Phase11Artifacts object."""
    arts = SimpleNamespace()
    if suggestions is not None:
        arts.agent_suggestions = {"suggestions": suggestions}
    else:
        arts.agent_suggestions = None
    arts.missing_required = missing_required or []
    arts.missing_optional = []
    arts.warnings = []
    arts.recovered_readable_c = ""
    arts.recovered_c = ""
    arts.agent_debate_report = None
    arts.behavior_model = None
    arts.source_reconstruction = None
    return arts


class TestBuildSourcePlanEmpty:
    def test_no_suggestions_field_returns_empty(self):
        arts = _make_arts(suggestions=None)
        entries, diag = build_source_plan(arts)
        assert entries == []
        assert any("agent_suggestions" in d for d in diag)

    def test_empty_suggestions_list(self):
        arts = _make_arts(suggestions=[])
        entries, diag = build_source_plan(arts)
        assert entries == []

    def test_non_dict_suggestion_skipped(self):
        arts = _make_arts(suggestions=["not a dict"])
        entries, diag = build_source_plan(arts)
        assert entries == []
        assert any("skipped" in d.lower() for d in diag)


class TestBuildSourcePlanHumanApproval:
    def _human_suggestion(self):
        return {
            "kind": "rename_variable",
            "function": "test_fn",
            "target": "var_1",
            "replacement": "index",
            "basis": ["static_evidence: var_1 observed as counter"],
            "confidence": "medium",
            "evidence_level": "static_evidence",
            "requires_human_approval": True,
        }

    def test_human_approval_suggestion_disabled_by_default(self):
        arts = _make_arts(suggestions=[self._human_suggestion()])
        entries, diag = build_source_plan(arts, allow_human_suggestions=False)
        assert len(entries) == 1
        assert entries[0]["enabled"] is False
        assert "human" in entries[0]["reason_disabled"].lower()

    def test_human_approval_enabled_when_flag_set(self):
        arts = _make_arts(suggestions=[self._human_suggestion()])
        entries, diag = build_source_plan(arts, allow_human_suggestions=True)
        assert len(entries) == 1
        assert entries[0]["enabled"] is True

    def test_non_human_suggestion_enabled_by_default(self):
        sugg = {
            "kind": "add_comment",
            "function": "foo",
            "target": "foo",
            "basis": ["static_evidence: function observed as iterator"],
            "confidence": "high",
            "evidence_level": "static_evidence",
            "requires_human_approval": False,
        }
        arts = _make_arts(suggestions=[sugg])
        entries, diag = build_source_plan(arts)
        assert len(entries) == 1
        assert entries[0]["enabled"] is True


class TestBuildSourcePlanFields:
    def _base_suggestion(self):
        return {
            "kind": "rename_variable",
            "function": "process_input",
            "target": "var_4h",
            "replacement": "count",
            "basis": ["dynamic_observed: var_4h incremented in loop"],
            "confidence": "medium",
            "evidence_level": "dynamic_observed",
            "requires_human_approval": False,
        }

    def test_plan_entry_has_all_required_fields(self):
        arts = _make_arts(suggestions=[self._base_suggestion()])
        entries, diag = build_source_plan(arts)
        assert len(entries) == 1
        entry = entries[0]
        assert "kind" in entry
        assert "function" in entry
        assert "target" in entry
        assert "replacement" in entry
        assert "basis" in entry
        assert "confidence" in entry
        assert "evidence_level" in entry
        assert "requires_human_approval" in entry
        assert "enabled" in entry
        assert "reason_disabled" in entry

    def test_basis_includes_source_reference(self):
        arts = _make_arts(suggestions=[self._base_suggestion()])
        entries, _ = build_source_plan(arts)
        assert len(entries) == 1
        basis = entries[0]["basis"]
        # The source reference string should be in the basis
        assert any("agent_suggestions.json" in b for b in basis)

    def test_confidence_preserved(self):
        arts = _make_arts(suggestions=[self._base_suggestion()])
        entries, _ = build_source_plan(arts)
        assert entries[0]["confidence"] == "medium"

    def test_evidence_level_preserved(self):
        arts = _make_arts(suggestions=[self._base_suggestion()])
        entries, _ = build_source_plan(arts)
        assert entries[0]["evidence_level"] == "dynamic_observed"

    def test_invalid_confidence_normalized(self):
        sugg = {**self._base_suggestion(), "confidence": "very_high"}
        arts = _make_arts(suggestions=[sugg])
        entries, _ = build_source_plan(arts)
        assert entries[0]["confidence"] == "unknown"

    def test_invalid_evidence_level_normalized(self):
        sugg = {**self._base_suggestion(), "evidence_level": "guessed"}
        arts = _make_arts(suggestions=[sugg])
        entries, _ = build_source_plan(arts)
        assert entries[0]["evidence_level"] == "pattern_inferred"


class TestBuildSourcePlanDisabling:
    def test_no_basis_disables_suggestion(self):
        sugg = {
            "kind": "rename_variable",
            "function": "foo",
            "target": "var_1",
            "replacement": "index",
            "basis": [],
            "confidence": "low",
            "evidence_level": "hypothesis",
            "requires_human_approval": False,
        }
        arts = _make_arts(suggestions=[sugg])
        entries, diag = build_source_plan(arts)
        assert len(entries) == 1
        assert entries[0]["enabled"] is False
        assert entries[0]["reason_disabled"] is not None

    def test_forbidden_phrase_in_suggestion_skipped(self):
        sugg = {
            "kind": "rename_variable",
            "function": "foo",
            "target": "var_1",
            "replacement": "index",
            "basis": ["semantically equivalent to original"],
            "confidence": "high",
            "evidence_level": "static_evidence",
            "requires_human_approval": False,
        }
        arts = _make_arts(suggestions=[sugg])
        entries, diag = build_source_plan(arts)
        # The suggestion should be skipped entirely (not added to entries at all)
        # because it contains a forbidden phrase in its basis
        # (basis is the field with the offending phrase)
        assert len(entries) == 0 or (
            len(entries) == 1 and not entries[0]["enabled"]
        )
