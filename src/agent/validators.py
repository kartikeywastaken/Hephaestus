# -*- coding: utf-8 -*-
"""
Phase 10 — Deterministic Python Validator.

Validates agent outputs BEFORE they are passed to the Finalizer.
No LLM involvement. This is authoritative.

Checks:
  - Required keys present
  - confidence values in ALLOWED_CONFIDENCE_LEVELS
  - evidence_level values in ALLOWED_EVIDENCE_LEVELS
  - No forbidden certainty phrases (recursive scan of all strings)
  - No C code blocks (pattern detection in suggestion texts)
  - No recovered_agent.c mention
  - Speculative suggested_names use possible_ prefix
  - Speculative suggestions have requires_human_approval = True
  - Every hypothesis has basis list
  - Critic rejected items are excluded from final suggestions (checked in debate.py)
"""

from __future__ import annotations

import re
from typing import Any

from src.agent.models import (
    ALLOWED_CONFIDENCE_LEVELS,
    ALLOWED_EVIDENCE_LEVELS,
    FORBIDDEN_CERTAINTY_PHRASES,
)

# Heuristic C code detection: looks for semicolon-terminated statement patterns
# or multi-char sequences that suggest an emitted C body.
_C_CODE_PATTERN = re.compile(
    r"(?:int|void|char|return|if\s*\(|for\s*\(|while\s*\(|#include|#define)\s+\w",
    re.IGNORECASE,
)


# ── Public entry point ────────────────────────────────────────────────────────

def validate_agent_output(
    output: dict,
    agent_kind: str,
) -> tuple[bool, list[str]]:
    """
    Validate the output dict from a named agent.

    Parameters
    ----------
    output:
        Parsed agent response dict.
    agent_kind:
        One of: "evidence", "dynamic_behavior", "reconstruction", "critic", "finalizer"

    Returns
    -------
    (ok: bool, errors: list[str])
      ok=True means validation passed (warnings may still be non-empty).
    """
    errors: list[str] = []

    # 1 — Required keys by agent type
    _check_required_keys(output, agent_kind, errors)

    # 2 — Confidence + evidence level labels
    _check_labels_recursive(output, errors)

    # 3 — Forbidden certainty phrases (recursive scan)
    _check_forbidden_phrases(output, errors)

    # 4 — No C code in suggestion texts
    _check_no_c_code(output, errors)

    # 5 — No recovered_agent.c mention
    _check_no_recovered_agent_c(output, errors)

    # 6 — Agent-specific structural checks
    if agent_kind == "reconstruction":
        _check_reconstruction_names(output, errors)
    elif agent_kind == "finalizer":
        _check_finalizer_suggestions(output, errors)

    return len(errors) == 0, errors


# ── Required keys ─────────────────────────────────────────────────────────────

_REQUIRED_KEYS: dict[str, list[str]] = {
    "evidence": ["function", "facts", "evidence_refs", "uncertainties"],
    "dynamic_behavior": ["function", "dynamic_behavior", "limitations"],
    "reconstruction": ["function", "hypotheses", "suggested_names"],
    "critic": ["function", "critic_findings"],
    "finalizer": ["function", "summary", "suggestions"],
}


def _check_required_keys(output: dict, agent_kind: str, errors: list[str]) -> None:
    required = _REQUIRED_KEYS.get(agent_kind, [])
    for key in required:
        if key not in output:
            errors.append(f"[{agent_kind}] missing required key: '{key}'")


# ── Label checks ──────────────────────────────────────────────────────────────

def _check_labels_recursive(obj: Any, errors: list[str]) -> None:
    """Walk obj and check any 'confidence' or 'evidence_level' string values."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "confidence" and isinstance(v, str):
                if v not in ALLOWED_CONFIDENCE_LEVELS:
                    errors.append(
                        f"invalid confidence value: '{v}' "
                        f"(allowed: {sorted(ALLOWED_CONFIDENCE_LEVELS)})"
                    )
            elif k == "evidence_level" and isinstance(v, str):
                if v not in ALLOWED_EVIDENCE_LEVELS:
                    errors.append(
                        f"invalid evidence_level value: '{v}' "
                        f"(allowed: {sorted(ALLOWED_EVIDENCE_LEVELS)})"
                    )
            else:
                _check_labels_recursive(v, errors)
    elif isinstance(obj, list):
        for item in obj:
            _check_labels_recursive(item, errors)


# ── Forbidden phrase check ────────────────────────────────────────────────────

def _check_forbidden_phrases(obj: Any, errors: list[str]) -> None:
    """Recursively scan all string values for forbidden certainty phrases."""
    if isinstance(obj, str):
        lower = obj.lower()
        for phrase in FORBIDDEN_CERTAINTY_PHRASES:
            if phrase.lower() in lower:
                # Truncate to avoid leaking large model output into error messages
                snippet = obj[:120].replace("\n", " ")
                errors.append(
                    f"forbidden certainty phrase '{phrase}' found in output: \"{snippet}\""
                )
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k.startswith("_"):
                continue  # skip provider diagnostics
            _check_forbidden_phrases(v, errors)
    elif isinstance(obj, list):
        for item in obj:
            _check_forbidden_phrases(item, errors)


# ── C code detection ──────────────────────────────────────────────────────────

def _check_no_c_code(obj: Any, errors: list[str]) -> None:
    """
    Detect C code snippets in suggestion text fields.
    Only checks 'text' keys and 'summary.text' to avoid false positives
    from C excerpts in the packet (which are expected).
    """
    _scan_text_fields(obj, errors, depth=0)


def _scan_text_fields(obj: Any, errors: list[str], depth: int) -> None:
    if depth > 20:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.startswith("_"):
                continue
            # Skip packet echo fields
            if k in ("conservative_c_excerpt", "readable_c_excerpt",
                      "conservative_c", "readable_c", "packet"):
                continue
            if k == "text" and isinstance(v, str):
                if _C_CODE_PATTERN.search(v):
                    errors.append(
                        f"C code detected in 'text' field: \"{v[:120]}\""
                    )
            else:
                _scan_text_fields(v, errors, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _scan_text_fields(item, errors, depth + 1)


# ── recovered_agent.c check ───────────────────────────────────────────────────

def _check_no_recovered_agent_c(obj: Any, errors: list[str]) -> None:
    _scan_for_string(obj, "recovered_agent.c", errors)


def _scan_for_string(obj: Any, needle: str, errors: list[str]) -> None:
    if isinstance(obj, str):
        if needle.lower() in obj.lower():
            errors.append(
                f"forbidden reference to '{needle}' found in output"
            )
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k.startswith("_"):
                continue
            _scan_for_string(v, needle, errors)
    elif isinstance(obj, list):
        for item in obj:
            _scan_for_string(item, needle, errors)


# ── Reconstruction agent checks ───────────────────────────────────────────────

def _check_reconstruction_names(output: dict, errors: list[str]) -> None:
    """
    Speculative suggested_names must:
      - Start with 'possible_' if not backed by an existing symbol
      - Have requires_human_approval == True
      - Have a non-empty basis list
    """
    for item in output.get("suggested_names", []):
        if not isinstance(item, dict):
            continue
        name = item.get("suggested_name", "")
        evidence_level = item.get("evidence_level", "")
        requires_approval = item.get("requires_human_approval", False)
        basis = item.get("basis", [])

        # Speculative = not static_evidence backed
        is_speculative = evidence_level not in ("static_evidence",)

        if is_speculative and isinstance(name, str):
            if not name.startswith("possible_"):
                errors.append(
                    f"speculative suggested_name '{name}' must start with 'possible_'"
                )
        if is_speculative and not requires_approval:
            errors.append(
                f"speculative suggested_name '{name}' must have requires_human_approval=true"
            )
        if not basis:
            errors.append(
                f"suggested_name '{name}' has empty basis list"
            )

    for hyp in output.get("hypotheses", []):
        if not isinstance(hyp, dict):
            continue
        if not hyp.get("basis"):
            kind = hyp.get("kind", "(unknown)")
            errors.append(f"hypothesis '{kind}' has empty basis list")
        if not hyp.get("evidence_level"):
            kind = hyp.get("kind", "(unknown)")
            errors.append(f"hypothesis '{kind}' missing evidence_level")
        if not hyp.get("confidence"):
            kind = hyp.get("kind", "(unknown)")
            errors.append(f"hypothesis '{kind}' missing confidence")


# ── Finalizer agent checks ────────────────────────────────────────────────────

def _check_finalizer_suggestions(output: dict, errors: list[str]) -> None:
    for suggestion in output.get("suggestions", []):
        if not isinstance(suggestion, dict):
            continue
        if not suggestion.get("basis"):
            target = suggestion.get("target", "(unknown)")
            errors.append(f"finalizer suggestion for '{target}' has empty basis list")
        if not suggestion.get("evidence_level"):
            target = suggestion.get("target", "(unknown)")
            errors.append(f"finalizer suggestion for '{target}' missing evidence_level")
        if not suggestion.get("confidence"):
            target = suggestion.get("target", "(unknown)")
            errors.append(f"finalizer suggestion for '{target}' missing confidence")
