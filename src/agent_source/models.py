# -*- coding: utf-8 -*-
"""
Phase 11 — Agent-Assisted Source Generation: constants and schema versions.

These constants are authoritative for the entire agent_source layer.
No LLM is involved in this file.
"""

from __future__ import annotations

# ── Schema versions ───────────────────────────────────────────────────────────

SCHEMA_AGENT_SOURCE_PLAN       = "agent-source-plan-1.0"
SCHEMA_AGENT_SOURCE_REPORT     = "agent-source-report-1.0"
SCHEMA_AGENT_SOURCE_VALIDATION = "agent-source-validation-1.0"

# ── Generation modes ──────────────────────────────────────────────────────────

GENERATION_MODES = ("function_by_function", "whole_file")
DEFAULT_GENERATION_MODE = "function_by_function"
DEFAULT_MAX_FUNCTIONS = 1

# ── Forbidden source phrases ──────────────────────────────────────────────────
# Recursive scan of all string values in generated C and artifacts must find none.

FORBIDDEN_SOURCE_PHRASES: frozenset[str] = frozenset({
    "definitely equivalent",
    "semantic equivalence",
    "semantically equivalent",
    "same behavior as original",
    "exact source",
    "original source variable",
    "recovered field name",
    "guaranteed equivalent",
    "identical to original",
    "reconstructed field",
    "full behavioral equivalence",
    "semantic equivalence proven",
    "exact original source",
    "exact original variable names",
    "exact original struct field names",
    "fully equivalent",
})

# ── Warning header for recovered_agent.c ─────────────────────────────────────

WARNING_HEADER = """\
/*
 * Hephaestus recovered_agent.c
 *
 * AI-assisted approximation generated from recovered_readable.c,
 * agent_suggestions.json, and behavior_model.json.
 *
 * This file is NOT claimed to be the original source.
 * This file is NOT claimed to be semantically equivalent to the binary.
 * Dynamic observations cover only tested inputs.
 */"""

# ── Guarded artifacts (read-only; hash checked before and after) ──────────────

GUARDED_ARTIFACTS: list[str] = [
    "recovered.c",
    "recovered_readable.c",
    "source_reconstruction.json",
    "behavior_model.json",
    "agent_suggestions.json",
    "agent_debate_report.json",
]

# ── Allowed transformation kinds ─────────────────────────────────────────────

ALLOWED_TRANSFORMATION_KINDS: frozenset[str] = frozenset({
    # Source-transform kinds (trigger LLM generation)
    "add_warning_header",
    "add_function_comment",
    "rename_variable",
    "rename_function",
    "add_readability_comment",
    # Metadata-only kinds (recorded in plan but do not trigger LLM)
    "preserve_signature",
    "preserve_control_flow",
    "preserve_fallback_markers",
    "name",
    "comment",
    "role",
    "hypothesis",
})

# ── Disallowed transformation categories (for plan notes) ────────────────────

DISALLOWED_TRANSFORMATION_REASONS: tuple[str, ...] = (
    "do not remove functions",
    "do not invent new public APIs",
    "do not invent exact struct names",
    "do not invent exact field names",
    "do not change main signature",
    "do not remove evidence comments",
    "do not remove fallback/unimplemented markers",
    "do not claim equivalence",
    "do not add behavior not in behavior_model.json",
)

# ── Slice defaults ────────────────────────────────────────────────────────────

DEFAULT_MAX_SLICE_LINES: int = 200
SLICE_TRUNCATION_COMMENT: str = "/* [HEPHAESTUS: slice truncated at {max_lines} lines] */"

# ── Supported providers ───────────────────────────────────────────────────────

SUPPORTED_PROVIDERS: tuple[str, ...] = ("ollama", "groq")
