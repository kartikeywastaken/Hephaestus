# -*- coding: utf-8 -*-
"""
Phase 10 — Agent constants, schema versions, forbidden phrases, allowed labels.

These constants are authoritative for the entire agent layer.
No LLM is involved in this file.
"""

from __future__ import annotations

# ── Schema versions ──────────────────────────────────────────────────────────

SCHEMA_AGENT_PACKET           = "agent-packet-1.0"
SCHEMA_AGENT_PACKET_MANIFEST  = "agent-packet-manifest-1.0"
SCHEMA_AGENT_DEBATE           = "agent-debate-1.0"
SCHEMA_AGENT_SUGGESTIONS      = "agent-suggestions-1.0"

# ── Allowed vocabulary ────────────────────────────────────────────────────────

ALLOWED_CONFIDENCE_LEVELS: frozenset[str] = frozenset({
    "high",
    "medium",
    "low",
    "unknown",
})

ALLOWED_EVIDENCE_LEVELS: frozenset[str] = frozenset({
    "static_evidence",
    "dynamic_observed",
    "static_dynamic_fused",
    "pattern_inferred",
    "hypothesis",
    "unsupported",
})

ALLOWED_CRITIC_STATUSES: frozenset[str] = frozenset({
    "accept",
    "accept_with_warning",
    "downgrade",
    "reject",
})

# ── Forbidden certainty phrases ───────────────────────────────────────────────
# Recursive scan of all string values in agent output must find none of these.

FORBIDDEN_CERTAINTY_PHRASES: tuple[str, ...] = (
    "definitely equivalent",
    "semantic equivalence",
    "semantically equivalent",
    "original source variable",
    "exact source",
    "proven struct",
    "recovered field name",
    "full behavioral equivalence",
    "same behavior as original",
    "guaranteed",
    "proven",
    "proves",
    "definitely",
    "identical to original",
    "reconstructed field",
)

# ── Standard uncertainties ────────────────────────────────────────────────────

STANDARD_UNCERTAINTIES: tuple[str, ...] = (
    "dynamic evidence only covers provided inputs",
    "function-level attribution is approximate without instrumentation",
    "source variable names are unknown",
    "struct field names are unknown",
    "behavioral equivalence is not claimed",
)

# ── Forbidden claims injected into every packet ───────────────────────────────

FORBIDDEN_CLAIMS: tuple[str, ...] = (
    "Do not claim semantic equivalence.",
    "Do not invent exact source variable names.",
    "Do not invent struct field names.",
    "Do not claim full behavioral equivalence.",
    "Do not output C code.",
    "Do not emit recovered_agent.c.",
    "Do not replace recovered.c or recovered_readable.c.",
)

# ── Known uncertainties injected into every packet ───────────────────────────

KNOWN_UNCERTAINTIES: tuple[str, ...] = (
    "dynamic evidence only covers provided inputs",
    "function-level attribution is approximate without instrumentation",
    "source variable names are unknown",
    "struct field names are unknown",
    "behavioral equivalence is not claimed",
)

# ── Common prompt contract appended to every system prompt ───────────────────

COMMON_PROMPT_CONTRACT: str = """\
ABSOLUTE RULES (these override all other instructions):
- Return ONLY valid JSON. No markdown. No code fences. No explanation outside JSON.
- Do not claim semantic equivalence.
- Do not invent exact original source names.
- Do not invent struct field names.
- Do not claim full behavioral equivalence.
- Do not modify or emit C code.
- Do not emit recovered_agent.c.
- Every suggestion must cite evidence from the provided packet.
- Use only these confidence levels: high, medium, low, unknown.
- Use only these evidence levels: static_evidence, dynamic_observed, \
static_dynamic_fused, pattern_inferred, hypothesis, unsupported.
"""

# ── C slice defaults ──────────────────────────────────────────────────────────

DEFAULT_MAX_SLICE_LINES: int = 200
SLICE_TRUNCATION_COMMENT: str = "/* [HEPHAESTUS: slice truncated at {max_lines} lines] */"

# ── Default Ollama settings ───────────────────────────────────────────────────

DEFAULT_OLLAMA_HOST:       str   = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL:      str   = "llama3.3:70b"
DEFAULT_OLLAMA_TIMEOUT_S:  int   = 300
DEFAULT_OLLAMA_TEMPERATURE: float = 0.0
DEFAULT_OLLAMA_NUM_CTX:    int   = 8192
