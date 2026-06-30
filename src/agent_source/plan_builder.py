# -*- coding: utf-8 -*-
"""
Phase 11 — Agent-Assisted Source Generation: plan builder.

Reads agent_suggestions.json and builds a transformation plan
(agent_source_plan.json) that specifies what the generator is
allowed and not allowed to do.

Default policy:
  Suggestions requiring human approval are DISABLED unless
  allow_human_suggestions=True is explicitly passed.

Each plan entry contains:
  kind, function, target, replacement, basis, confidence,
  evidence_level, requires_human_approval, enabled, reason_disabled
"""

from __future__ import annotations

import logging
from typing import Any

from src.agent_source.models import (
    ALLOWED_TRANSFORMATION_KINDS,
    DISALLOWED_TRANSFORMATION_REASONS,
    FORBIDDEN_SOURCE_PHRASES,
)

logger = logging.getLogger("agent_source.plan_builder")

# ── Allowed evidence levels ───────────────────────────────────────────────────

ALLOWED_EVIDENCE_LEVELS = frozenset({
    "static_evidence",
    "dynamic_observed",
    "static_dynamic_fused",
    "pattern_inferred",
    "hypothesis",
    "unsupported",
})

ALLOWED_CONFIDENCE_LEVELS = frozenset({"high", "medium", "low", "unknown"})

# Classification of suggestion kinds for target selection.
# Source-transform kinds trigger LLM generation.
# Metadata-only kinds are recorded in the plan but do NOT trigger generation.

SOURCE_TRANSFORM_KINDS: frozenset[str] = frozenset({
    "rename_variable",
    "rename_function",
    "add_function_comment",
    "add_readability_comment",
    "source_rewrite",
    "condition_refinement",
    "loop_refinement",
    "type_refinement",
    "body_reconstruction",
})

METADATA_ONLY_KINDS: frozenset[str] = frozenset({
    "name",
    "comment",
    "role",
    "hypothesis",
    "preserve_signature",
    "preserve_control_flow",
    "preserve_fallback_markers",
    "add_warning_header",
})


def _scan_forbidden(value: Any) -> list[str]:
    """Recursively scan for forbidden phrases in any string value."""
    found = []
    if isinstance(value, str):
        low = value.lower()
        for phrase in FORBIDDEN_SOURCE_PHRASES:
            if phrase in low:
                found.append(phrase)
    elif isinstance(value, dict):
        for v in value.values():
            found.extend(_scan_forbidden(v))
    elif isinstance(value, list):
        for item in value:
            found.extend(_scan_forbidden(item))
    return found


def _safe_str(value: Any, default: str = "") -> str:
    if isinstance(value, str):
        return value.strip()
    return default


def _safe_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    return []


def build_source_plan(
    arts: Any,  # Phase11Artifacts
    allow_human_suggestions: bool = False,
) -> tuple[list[dict], list[str]]:
    """
    Build the transformation plan from agent_suggestions.json.

    Parameters
    ----------
    arts:
        Phase11Artifacts instance (must have agent_suggestions loaded).
    allow_human_suggestions:
        If True, suggestions marked requires_human_approval=True are enabled.
        Default False.

    Returns
    -------
    (plan_entries, diagnostics)
    """
    diagnostics: list[str] = []
    plan_entries: list[dict] = []

    if arts.agent_suggestions is None:
        diagnostics.append("agent_suggestions.json missing — plan will be empty")
        return plan_entries, diagnostics

    suggestions = arts.agent_suggestions.get("suggestions", [])
    if not isinstance(suggestions, list):
        diagnostics.append("agent_suggestions.json has no 'suggestions' list")
        return plan_entries, diagnostics

    for i, suggestion in enumerate(suggestions):
        if not isinstance(suggestion, dict):
            diagnostics.append(f"suggestion[{i}] is not a dict — skipped")
            continue

        # Check for forbidden phrases in the suggestion itself
        forbidden_found = _scan_forbidden(suggestion)
        if forbidden_found:
            diagnostics.append(
                f"suggestion[{i}] contains forbidden phrases {forbidden_found} — skipped"
            )
            continue

        kind = _safe_str(suggestion.get("kind"), "unknown")
        fn_name = _safe_str(
            suggestion.get("function") or suggestion.get("function_name"), "unknown"
        )
        target = _safe_str(suggestion.get("target") or suggestion.get("name"), "")
        replacement = _safe_str(
            suggestion.get("replacement") or suggestion.get("suggested_name") or
            suggestion.get("value"), ""
        )
        basis = _safe_list(suggestion.get("basis") or suggestion.get("evidence") or [])
        confidence = _safe_str(suggestion.get("confidence"), "unknown")
        evidence_level = _safe_str(suggestion.get("evidence_level"), "static_evidence")
        requires_human = bool(suggestion.get("requires_human_approval", False))

        # Validate vocabulary
        if confidence not in ALLOWED_CONFIDENCE_LEVELS:
            confidence = "unknown"
        if evidence_level not in ALLOWED_EVIDENCE_LEVELS:
            evidence_level = "pattern_inferred"

        # Map suggestion kinds to allowed transformation kinds
        entry_kind = _map_suggestion_kind(kind)

        # Determine if enabled
        enabled = True
        reason_disabled = None

        if requires_human and not allow_human_suggestions:
            enabled = False
            reason_disabled = "requires --allow-human-suggestions"

        # Check if kind is in allowed transformations
        if entry_kind not in ALLOWED_TRANSFORMATION_KINDS:
            enabled = False
            reason_disabled = f"transformation kind '{entry_kind}' not in allowed list"

        # If no basis, disable — must cite evidence
        if enabled and not basis:
            enabled = False
            reason_disabled = "no evidence basis provided"
            diagnostics.append(
                f"suggestion[{i}] kind='{kind}' function='{fn_name}' disabled: no evidence basis"
            )

        # Add source reference to basis
        basis_with_source = list(basis)
        if f"agent_suggestions.json suggestions[{i}]" not in basis_with_source:
            basis_with_source.append(f"agent_suggestions.json suggestions[{i}]")

        entry: dict = {
            "kind": entry_kind,
            "function": fn_name,
            "target": target,
            "replacement": replacement,
            "basis": basis_with_source,
            "confidence": confidence,
            "evidence_level": evidence_level,
            "requires_human_approval": requires_human,
            "enabled": enabled,
            "reason_disabled": reason_disabled,
        }
        plan_entries.append(entry)

    enabled_count = sum(1 for e in plan_entries if e["enabled"])
    disabled_count = len(plan_entries) - enabled_count
    logger.info(
        "[plan_builder] %d plan entries: %d enabled, %d disabled",
        len(plan_entries), enabled_count, disabled_count,
    )

    return plan_entries, diagnostics


def get_approved_transforms_for_function(
    plan_entries: list[dict],
    fn_name: str,
) -> list[dict]:
    """Return enabled plan entries for the given function."""
    return [
        e for e in plan_entries
        if e.get("enabled") and (
            e.get("function") == fn_name
            or e.get("function") in ("*", "all", "")
        )
    ]


def get_forbidden_transforms() -> list[str]:
    """Return the standard list of disallowed transformation descriptions."""
    return list(DISALLOWED_TRANSFORMATION_REASONS)


def _map_suggestion_kind(kind: str) -> str:
    """Map agent suggestion kind to allowed transformation kind."""
    kind_lower = kind.lower()
    mapping = {
        "rename_variable": "rename_variable",
        "rename_local": "rename_variable",
        "rename_function": "rename_function",
        "add_comment": "add_function_comment",
        "function_comment": "add_function_comment",
        "readability_improvement": "add_readability_comment",
        "comment_only": "add_readability_comment",
        "add_readability_comment": "add_readability_comment",
        "add_function_comment": "add_function_comment",
        "preserve_signature": "preserve_signature",
        "preserve_control_flow": "preserve_control_flow",
        "preserve_fallback": "preserve_fallback_markers",
    }
    return mapping.get(kind_lower, kind_lower)


def has_source_transforms(plan_entries: list[dict], fn_name: str) -> bool:
    """Return True if fn_name has at least one enabled source-transform entry."""
    for e in plan_entries:
        if not e.get("enabled"):
            continue
        efn = e.get("function", "")
        if efn not in (fn_name, "*", "all", ""):
            continue
        kind = e.get("kind", "")
        if kind in SOURCE_TRANSFORM_KINDS:
            return True
    return False
