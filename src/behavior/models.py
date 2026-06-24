# -*- coding: utf-8 -*-
"""
Phase 9 — Static-Dynamic Behavior Fusion: data models and constants.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Evidence / confidence label sets
# ---------------------------------------------------------------------------

P9_EVIDENCE_LEVELS: frozenset[str] = frozenset({
    "static_evidence",
    "dynamic_observed",
    "static_dynamic_fused",
    "hypothesis",
    "unsupported",
})

P9_CONFIDENCE: frozenset[str] = frozenset({
    "high",
    "medium",
    "low",
    "unknown",
})

# ---------------------------------------------------------------------------
# Language guardrails
# ---------------------------------------------------------------------------

# Phrases that must never appear in any string field of behavior_model.json
FORBIDDEN_CERTAINTY_PHRASES: tuple[str, ...] = (
    "definitely equivalent",
    "original source variable",
    "exact source",
    "guaranteed",
    "proven struct",
    "recovered field name",
    "semantic equivalence",
    "proves",
    "definitely",
)

# Uncertainty boilerplate appended to every fused hypothesis
STANDARD_UNCERTAINTIES: list[str] = [
    "dynamic evidence only covers provided inputs",
    "function-level attribution is approximate without instrumentation",
    "behavior may differ under untested inputs",
]

# Allowed words for hypothesis language
ALLOWED_HEDGE_WORDS: tuple[str, ...] = (
    "likely",
    "appears",
    "suggests",
    "may",
    "observed under tested inputs",
)

# ---------------------------------------------------------------------------
# Schema version constants
# ---------------------------------------------------------------------------

SCHEMA_BEHAVIOR_MODEL         = "behavior-model-1.0"
SCHEMA_BEHAVIOR_FUSION_REPORT = "behavior-fusion-report-1.0"

# ---------------------------------------------------------------------------
# Output-producing function names (for H2 heuristic)
# ---------------------------------------------------------------------------

OUTPUT_PRODUCING_CALLS: frozenset[str] = frozenset({
    "printf", "fprintf", "vprintf", "vfprintf",
    "puts", "fputs", "putchar", "fputc", "putc",
    "write",
    "fwrite",
})

# ---------------------------------------------------------------------------
# argv-handling function names (for H1 heuristic)
# ---------------------------------------------------------------------------

ARGV_RELATED_CALLS: frozenset[str] = frozenset({
    "strlen", "strcmp", "strncmp", "strcat", "strncpy", "strcpy",
    "atoi", "atol", "strtol", "strtoul",
    "getopt", "getopt_long",
})
