# -*- coding: utf-8 -*-
"""
Phase 8 — Dynamic Behavior Capture: data models.

All types are plain dicts / TypedDicts; no external dependencies.
Evidence label constants are defined here and shared across the module.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Evidence/confidence label sets
# ---------------------------------------------------------------------------

DYNAMIC_EVIDENCE_LEVELS: frozenset[str] = frozenset({
    "dynamic_observed",
    "static_evidence",
    "static_dynamic_fused",
    "hypothesis",
    "unsupported",
})

DYNAMIC_CONFIDENCE: frozenset[str] = frozenset({
    "high",
    "medium",
    "low",
    "unknown",
})

# Allowed observation kinds for behavior_profile.json
OBSERVATION_KINDS: frozenset[str] = frozenset({
    "argv_sensitive_stdout",
    "argv_sensitive_exit_code",
    "stdin_sensitive_stdout",
    "stderr_output_observed",
    "nonzero_exit_observed",
    "crash_observed",
    "timeout_observed",
    "deterministic_stdout",
    "argv_insensitive",
})

# ---------------------------------------------------------------------------
# Schema version constants
# ---------------------------------------------------------------------------

SCHEMA_DYNAMIC_INPUTS_RESOLVED = "dynamic-inputs-resolved-1.0"
SCHEMA_DYNAMIC_RUNS            = "dynamic-runs-1.0"
SCHEMA_BEHAVIOR_PROFILE        = "behavior-profile-1.0"
SCHEMA_DYNAMIC_REPORT          = "dynamic-report-1.0"

# ---------------------------------------------------------------------------
# Default input spec
# ---------------------------------------------------------------------------

def default_input_spec() -> dict:
    """Return the minimal default input spec (single no_args run)."""
    return {
        "schema_version": "dynamic-inputs-1.0",
        "runs": [
            {
                "name": "no_args",
                "argv": [],
                "stdin": "",
                "env": {},
            }
        ],
    }
