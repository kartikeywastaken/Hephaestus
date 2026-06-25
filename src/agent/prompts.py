# -*- coding: utf-8 -*-
"""
Phase 10 — Agent system prompts and user payload builders.

Every system prompt includes the common contract from models.py.
Every user payload includes task, allowed_confidence_levels,
allowed_evidence_levels, forbidden_claims, required_output_schema,
and the packet.

Five agents:
  1. evidence_agent
  2. dynamic_behavior_agent
  3. reconstruction_agent
  4. critic_agent
  5. finalizer_agent
"""

from __future__ import annotations

import json

from src.agent.models import (
    ALLOWED_CONFIDENCE_LEVELS,
    ALLOWED_EVIDENCE_LEVELS,
    COMMON_PROMPT_CONTRACT,
    FORBIDDEN_CLAIMS,
)

_FORBIDDEN_CLAIMS_LIST = list(FORBIDDEN_CLAIMS)
_ALLOWED_CONF = sorted(ALLOWED_CONFIDENCE_LEVELS)
_ALLOWED_EVID = sorted(ALLOWED_EVIDENCE_LEVELS)


# ── Shared schema snippets ────────────────────────────────────────────────────

_EVIDENCE_REFS_SCHEMA = {
    "evidence_refs": [
        {
            "kind": "static|dynamic",
            "source": "artifact_name.json",
            "detail": "specific field or observation",
        }
    ]
}

_UNCERTAINTY_SCHEMA = {"uncertainties": ["string", "..."]}


# ── Agent 1 — Evidence Agent ──────────────────────────────────────────────────

EVIDENCE_AGENT_SYSTEM = (
    "You are the Evidence Agent for the Hephaestus binary reconstruction system.\n"
    "Your role: extract ONLY facts that are directly supported by the provided packet.\n"
    "You must NOT guess, rename, or infer source intent.\n"
    "You must NOT claim anything is equivalent to original source.\n"
    "Cite specific packet fields for every fact.\n\n"
    + COMMON_PROMPT_CONTRACT
)


def evidence_agent_payload(packet: dict) -> dict:
    return {
        "task": (
            "Extract all artifact-backed facts from this function packet. "
            "Include only what is directly present in the packet fields. "
            "Do not propose names. Do not infer source intent. "
            "Do not call anything equivalent."
        ),
        "allowed_confidence_levels": _ALLOWED_CONF,
        "allowed_evidence_levels": _ALLOWED_EVID,
        "forbidden_claims": _FORBIDDEN_CLAIMS_LIST,
        "required_output_schema": {
            "function": "string",
            "facts": {
                "calls": ["string"],
                "loops": "int",
                "conditions": "int",
                "returns_value": "bool|null",
                "constants": ["string"],
                "layout_candidates": ["object"],
                "dynamic_observations_present": "bool",
                "global_behavior_refs": ["string"],
            },
            "evidence_refs": _EVIDENCE_REFS_SCHEMA["evidence_refs"],
            "uncertainties": ["string"],
        },
        "packet": _condensed_packet(packet),
    }


# ── Agent 2 — Dynamic Behavior Agent ─────────────────────────────────────────

DYNAMIC_BEHAVIOR_AGENT_SYSTEM = (
    "You are the Dynamic Behavior Agent for the Hephaestus binary reconstruction system.\n"
    "Your role: summarize ONLY observed runtime behavior relevant to this function.\n"
    "You must NOT claim behavior for inputs that were not tested.\n"
    "You must NOT attribute output to a function unless the behavior model explicitly links it.\n"
    "You must NOT claim exact output generation without direct observation.\n\n"
    + COMMON_PROMPT_CONTRACT
)


def dynamic_behavior_agent_payload(packet: dict) -> dict:
    return {
        "task": (
            "Summarize only observed runtime behavior relevant to this function "
            "based on the dynamic_summary and behavior_model_entry in the packet. "
            "Do not claim behavior for untested inputs. "
            "Do not attribute output unless directly linked in the behavior model."
        ),
        "allowed_confidence_levels": _ALLOWED_CONF,
        "allowed_evidence_levels": _ALLOWED_EVID,
        "forbidden_claims": _FORBIDDEN_CLAIMS_LIST,
        "required_output_schema": {
            "function": "string",
            "dynamic_behavior": [
                {
                    "kind": "string",
                    "text": "string",
                    "basis": ["string"],
                    "confidence": "high|medium|low|unknown",
                    "evidence_level": "one of allowed_evidence_levels",
                }
            ],
            "limitations": ["string"],
        },
        "packet": _condensed_packet_dynamic(packet),
    }


# ── Agent 3 — Reconstruction Agent ───────────────────────────────────────────

RECONSTRUCTION_AGENT_SYSTEM = (
    "You are the Reconstruction Agent for the Hephaestus binary reconstruction system.\n"
    "Your role: generate high-level interpretations and possible rename suggestions.\n"
    "Suggestions are allowed. Certainty is not.\n"
    "Every speculative suggested name MUST start with 'possible_' unless backed by an existing symbol.\n"
    "Speculative suggestions MUST set requires_human_approval = true.\n"
    "Do NOT output C code.\n\n"
    + COMMON_PROMPT_CONTRACT
)


def reconstruction_agent_payload(packet: dict, evidence_output: dict) -> dict:
    return {
        "task": (
            "Generate high-level function summary hypotheses and possible rename suggestions "
            "based on static and dynamic evidence in the packet and prior evidence agent output. "
            "Speculative suggested names must start with 'possible_'. "
            "Do not output C code."
        ),
        "allowed_confidence_levels": _ALLOWED_CONF,
        "allowed_evidence_levels": _ALLOWED_EVID,
        "forbidden_claims": _FORBIDDEN_CLAIMS_LIST,
        "required_output_schema": {
            "function": "string",
            "hypotheses": [
                {
                    "kind": "string",
                    "text": "string",
                    "basis": ["string"],
                    "confidence": "high|medium|low|unknown",
                    "evidence_level": "one of allowed_evidence_levels",
                    "requires_human_approval": "bool",
                }
            ],
            "suggested_names": [
                {
                    "target": "string",
                    "suggested_name": "string (must start with possible_ if speculative)",
                    "basis": ["string"],
                    "confidence": "low|medium",
                    "evidence_level": "one of allowed_evidence_levels",
                    "requires_human_approval": True,
                }
            ],
            "suggested_structs": ["object"],
        },
        "packet": _condensed_packet(packet),
        "evidence_agent_output": _top_n(evidence_output, 5),
    }


# ── Agent 4 — Critic Agent ────────────────────────────────────────────────────

CRITIC_AGENT_SYSTEM = (
    "You are the Critic Agent for the Hephaestus binary reconstruction system.\n"
    "Your role: attack unsupported or overconfident claims.\n"
    "Downgrade speculative claims. Reject invented certainty.\n"
    "You MUST reject anything that:\n"
    "  - claims semantic equivalence\n"
    "  - invents exact source variable names without a 'possible_' prefix\n"
    "  - invents struct field names\n"
    "  - generalizes behavior beyond tested inputs\n"
    "  - emits C code\n"
    "Allowed status values: accept, accept_with_warning, downgrade, reject\n\n"
    + COMMON_PROMPT_CONTRACT
)


def critic_agent_payload(
    packet: dict,
    evidence_output: dict,
    dynamic_output: dict,
    reconstruction_output: dict,
) -> dict:
    return {
        "task": (
            "Review the outputs from the Evidence Agent, Dynamic Behavior Agent, "
            "and Reconstruction Agent. Attack unsupported or overconfident claims. "
            "Downgrade or reject any that violate the rules."
        ),
        "allowed_confidence_levels": _ALLOWED_CONF,
        "allowed_evidence_levels": _ALLOWED_EVID,
        "allowed_critic_statuses": ["accept", "accept_with_warning", "downgrade", "reject"],
        "forbidden_claims": _FORBIDDEN_CLAIMS_LIST,
        "required_output_schema": {
            "function": "string",
            "critic_findings": [
                {
                    "target": "string (e.g. hypotheses[0], suggested_names[0])",
                    "status": "accept|accept_with_warning|downgrade|reject",
                    "reason": "string",
                    "recommended_confidence": "high|medium|low|unknown",
                    "recommended_evidence_level": "one of allowed_evidence_levels",
                }
            ],
            "rejected_suggestions": ["string (target identifiers)"],
        },
        "packet_summary": {
            "function": packet.get("function"),
            "entry_point": packet.get("entry_point"),
            "signature": packet.get("signature"),
            "known_uncertainties": packet.get("known_uncertainties", []),
        },
        "evidence_agent_output": _top_n(evidence_output, 5),
        "dynamic_behavior_output": _top_n(dynamic_output, 5),
        "reconstruction_output": _top_n(reconstruction_output, 5),
    }


# ── Agent 5 — Finalizer Agent ─────────────────────────────────────────────────

FINALIZER_AGENT_SYSTEM = (
    "You are the Finalizer Agent for the Hephaestus binary reconstruction system.\n"
    "Your role: merge all prior agent outputs and produce a final, clean suggestion set.\n"
    "You must respect critic findings. Rejected items must NOT appear in final suggestions.\n"
    "You must NOT emit C code.\n"
    "You must NOT produce recovered_agent.c.\n"
    "All suggestions must cite their evidence basis.\n\n"
    + COMMON_PROMPT_CONTRACT
)


def finalizer_agent_payload(
    packet: dict,
    evidence_output: dict,
    dynamic_output: dict,
    reconstruction_output: dict,
    critic_output: dict,
    validation_errors: list[str],
) -> dict:
    return {
        "task": (
            "Merge and finalize all agent outputs into a clean suggestion set. "
            "Honor critic findings (rejected items must not appear). "
            "Do not emit C code. Do not produce recovered_agent.c."
        ),
        "allowed_confidence_levels": _ALLOWED_CONF,
        "allowed_evidence_levels": _ALLOWED_EVID,
        "forbidden_claims": _FORBIDDEN_CLAIMS_LIST,
        "validation_errors_from_validator": validation_errors,
        "required_output_schema": {
            "function": "string",
            "summary": {
                "text": "string",
                "confidence": "high|medium|low|unknown",
                "evidence_level": "one of allowed_evidence_levels",
                "critic_status": "accept|accept_with_warning|downgrade|reject",
                "requires_human_approval": "bool",
            },
            "suggestions": [
                {
                    "kind": "string",
                    "target": "string",
                    "text": "string",
                    "confidence": "high|medium|low|unknown",
                    "evidence_level": "one of allowed_evidence_levels",
                    "requires_human_approval": "bool",
                    "basis": ["string"],
                    "critic_status": "accept|accept_with_warning|downgrade|reject",
                }
            ],
            "rejected": ["string"],
        },
        "packet_summary": {
            "function": packet.get("function"),
            "signature": packet.get("signature"),
            "known_uncertainties": packet.get("known_uncertainties", []),
        },
        "evidence_agent_output": _top_n(evidence_output, 5),
        "dynamic_behavior_output": _top_n(dynamic_output, 5),
        "reconstruction_output": _top_n(reconstruction_output, 5),
        "critic_output": critic_output,
    }


# ── Payload condensers ────────────────────────────────────────────────────────

def _condensed_packet(packet: dict) -> dict:
    """Return a packet stripped of large C slices (to control context size)."""
    return {
        "function": packet.get("function"),
        "entry_point": packet.get("entry_point"),
        "signature": packet.get("signature"),
        "static_summary": packet.get("static_summary", {}),
        "dynamic_summary": packet.get("dynamic_summary", {}),
        "behavior_model_entry": packet.get("behavior_model_entry", {}),
        "global_behavior": packet.get("global_behavior", []),
        "evidence_slice": packet.get("evidence_slice", {}),
        "trace_slice": packet.get("trace_slice", {}),
        "quality_gate_summary": packet.get("quality_gate_summary", {}),
        "known_uncertainties": packet.get("known_uncertainties", []),
        "forbidden_claims": packet.get("forbidden_claims", []),
        # C slices are large — include but truncated for evidence/dynamic prompts
        "conservative_c_excerpt": (packet.get("conservative_c") or "")[:1500],
        "readable_c_excerpt": (packet.get("readable_c") or "")[:1500],
    }


def _condensed_packet_dynamic(packet: dict) -> dict:
    """Return a packet focused on dynamic fields only."""
    return {
        "function": packet.get("function"),
        "entry_point": packet.get("entry_point"),
        "signature": packet.get("signature"),
        "dynamic_summary": packet.get("dynamic_summary", {}),
        "behavior_model_entry": packet.get("behavior_model_entry", {}),
        "global_behavior": packet.get("global_behavior", []),
        "known_uncertainties": packet.get("known_uncertainties", []),
        "forbidden_claims": packet.get("forbidden_claims", []),
    }


def _top_n(obj: dict, n: int) -> dict:
    """Return a condensed view of a prior agent output (first n items per list)."""
    result = {}
    for k, v in obj.items():
        if k.startswith("_"):
            continue
        if isinstance(v, list):
            result[k] = v[:n]
        else:
            result[k] = v
    return result
