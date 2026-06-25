# -*- coding: utf-8 -*-
"""
Phase 10 — Multi-agent debate orchestrator.

Pipeline per function:
  1. Evidence Agent       (LLM)
  2. Dynamic Behavior Agent (LLM)
  3. Reconstruction Agent (LLM)
  4. Critic Agent         (LLM)
  5. Python Validator     (deterministic — no LLM)
  6. Finalizer Agent      (LLM)

Each agent failure is caught at function scope.
One failed function does NOT abort the debate unless --fail-fast is set.
The Finalizer receives validation errors so it can exclude invalid items.
"""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Any

from src.agent.providers.base import AgentProvider
from src.agent.prompts import (
    EVIDENCE_AGENT_SYSTEM,
    DYNAMIC_BEHAVIOR_AGENT_SYSTEM,
    RECONSTRUCTION_AGENT_SYSTEM,
    CRITIC_AGENT_SYSTEM,
    FINALIZER_AGENT_SYSTEM,
    evidence_agent_payload,
    dynamic_behavior_agent_payload,
    reconstruction_agent_payload,
    critic_agent_payload,
    finalizer_agent_payload,
)
from src.agent.validators import validate_agent_output
from src.agent.models import (
    SCHEMA_AGENT_DEBATE,
    SCHEMA_AGENT_SUGGESTIONS,
)

logger = logging.getLogger("agent.debate")


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Per-function debate ───────────────────────────────────────────────────────

def run_debate_for_function(
    packet: dict,
    provider: AgentProvider,
) -> tuple[dict, list[dict]]:
    """
    Run the full 5-agent debate for a single function packet.

    Returns (function_record, suggestions_list).
    On provider or parse failure the function_record has status="failed".
    Suggestions are empty on failure.
    """
    fn_name = packet.get("function", "unknown")
    logger.info("[debate] starting debate for function '%s'", fn_name)

    steps: list[dict] = []
    suggestions: list[dict] = []

    def _step(name: str, agent_kind: str, result: dict) -> dict:
        ok, errs = validate_agent_output(result, agent_kind)
        entry = {
            "step": name,
            "agent_kind": agent_kind,
            "function": fn_name,
            "validation_ok": ok,
            "validation_errors": errs,
            "diagnostics": result.get("_provider_diagnostics", {}),
        }
        steps.append(entry)
        if not ok:
            logger.warning(
                "[debate] validation failed for %s/%s: %s",
                fn_name, name, errs,
            )
        return result

    try:
        # ── Step 1: Evidence Agent ─────────────────────────────────────────
        ev_result = provider.complete_json(
            system_prompt=EVIDENCE_AGENT_SYSTEM,
            user_payload=evidence_agent_payload(packet),
            schema_name="evidence_agent",
        )
        _step("evidence_agent", "evidence", ev_result)

        # ── Step 2: Dynamic Behavior Agent ────────────────────────────────
        dyn_result = provider.complete_json(
            system_prompt=DYNAMIC_BEHAVIOR_AGENT_SYSTEM,
            user_payload=dynamic_behavior_agent_payload(packet),
            schema_name="dynamic_behavior_agent",
        )
        _step("dynamic_behavior_agent", "dynamic_behavior", dyn_result)

        # ── Step 3: Reconstruction Agent ──────────────────────────────────
        recon_result = provider.complete_json(
            system_prompt=RECONSTRUCTION_AGENT_SYSTEM,
            user_payload=reconstruction_agent_payload(packet, ev_result),
            schema_name="reconstruction_agent",
        )
        _step("reconstruction_agent", "reconstruction", recon_result)

        # ── Step 4: Critic Agent ──────────────────────────────────────────
        critic_result = provider.complete_json(
            system_prompt=CRITIC_AGENT_SYSTEM,
            user_payload=critic_agent_payload(
                packet, ev_result, dyn_result, recon_result
            ),
            schema_name="critic_agent",
        )
        _step("critic_agent", "critic", critic_result)

        # ── Step 5: Python Validator (deterministic) ──────────────────────
        # Collect validation errors from reconstruction (the riskiest step)
        _, recon_errors = validate_agent_output(recon_result, "reconstruction")

        # ── Step 6: Finalizer Agent ───────────────────────────────────────
        final_result = provider.complete_json(
            system_prompt=FINALIZER_AGENT_SYSTEM,
            user_payload=finalizer_agent_payload(
                packet,
                ev_result,
                dyn_result,
                recon_result,
                critic_result,
                validation_errors=recon_errors,
            ),
            schema_name="finalizer_agent",
        )
        _step("finalizer_agent", "finalizer", final_result)

        # ── Extract validated suggestions ─────────────────────────────────
        final_ok, final_errs = validate_agent_output(final_result, "finalizer")
        final_suggestions = final_result.get("suggestions", [])

        # Enforce: drop suggestions that were critic-rejected
        rejected_targets = set(critic_result.get("rejected_suggestions", []))
        if rejected_targets:
            before = len(final_suggestions)
            final_suggestions = [
                s for s in final_suggestions
                if s.get("target") not in rejected_targets
            ]
            if len(final_suggestions) < before:
                logger.info(
                    "[debate] %d suggestion(s) dropped due to critic rejection for '%s'",
                    before - len(final_suggestions), fn_name,
                )

        # Annotate suggestions with function name + model summary
        for s in final_suggestions:
            s.setdefault("function", fn_name)

        suggestions = final_suggestions

        fn_status = "ok" if final_ok else "partial"
        fn_record = {
            "function": fn_name,
            "status": fn_status,
            "steps": steps,
            "suggestions_count": len(suggestions),
            "final_summary": final_result.get("summary", {}),
            "final_rejected": final_result.get("rejected", []),
            "critic_findings": critic_result.get("critic_findings", []),
            "validation_errors": final_errs,
        }
        logger.info(
            "[debate] function '%s' done: status=%s suggestions=%d",
            fn_name, fn_status, len(suggestions),
        )
        return fn_record, suggestions

    except Exception as e:
        logger.exception("[debate] function '%s' failed: %s", fn_name, e)
        fn_record = {
            "function": fn_name,
            "status": "failed",
            "error": str(e),
            "steps": steps,
            "suggestions_count": 0,
            "final_summary": {},
            "final_rejected": [],
            "critic_findings": [],
            "validation_errors": [],
        }
        return fn_record, []


# ── Debate orchestration ──────────────────────────────────────────────────────

def run_debate(
    packets: list[dict],
    provider: AgentProvider,
    *,
    fail_fast: bool = False,
    max_functions: int | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Run the agent debate for all packets (up to max_functions).

    Returns (function_records, all_suggestions).
    """
    target_packets = packets
    if max_functions is not None and max_functions > 0:
        target_packets = packets[:max_functions]

    function_records: list[dict] = []
    all_suggestions: list[dict] = []

    for packet in target_packets:
        fn_record, suggestions = run_debate_for_function(packet, provider)
        function_records.append(fn_record)
        all_suggestions.extend(suggestions)

        if fail_fast and fn_record.get("status") == "failed":
            logger.error(
                "[debate] --fail-fast: aborting after failure in '%s'",
                fn_record.get("function"),
            )
            raise DebateFailFastError(
                f"Function '{fn_record.get('function')}' failed and --fail-fast is set."
            )

    return function_records, all_suggestions


# ── Report writers ────────────────────────────────────────────────────────────

def write_debate_report(
    function_records: list[dict],
    all_suggestions: list[dict],
    out_dir: Path,
    *,
    provider_name: str,
    model: str,
    api_key_env: str | None = None,
) -> tuple[Path, Path]:
    """
    Write agent_debate_report.json and agent_suggestions.json.

    The API key is NEVER written — only the env var name (if given).
    Returns (debate_report_path, suggestions_path).
    """
    out_dir = out_dir.resolve()
    generated_at = _now_iso()

    functions_failed = sum(
        1 for r in function_records if r.get("status") == "failed"
    )
    functions_with_suggestions = sum(
        1 for r in function_records if r.get("suggestions_count", 0) > 0
    )
    overall_status = "failed" if functions_failed == len(function_records) else (
        "partial" if functions_failed > 0 else "ok"
    )

    # Build provider info (never includes the key value)
    provider_info: dict[str, Any] = {
        "provider": provider_name,
        "model": model,
    }
    if api_key_env:
        provider_info["api_key_env"] = api_key_env

    debate_report = {
        "schema_version": SCHEMA_AGENT_DEBATE,
        "phase": "10.2",
        "generated_at": generated_at,
        "status": overall_status,
        **provider_info,
        "functions_reviewed": len(function_records),
        "functions_failed": functions_failed,
        "functions_with_suggestions": functions_with_suggestions,
        "suggestions_total": len(all_suggestions),
        "diagnostics": [],
        "functions": function_records,
    }

    suggestions_report = {
        "schema_version": SCHEMA_AGENT_SUGGESTIONS,
        "phase": "10.2",
        "generated_at": generated_at,
        "status": overall_status,
        **provider_info,
        "suggestions_total": len(all_suggestions),
        "suggestions": all_suggestions,
    }

    debate_path = out_dir / "agent_debate_report.json"
    suggestions_path = out_dir / "agent_suggestions.json"

    with open(debate_path, "w", encoding="utf-8") as f:
        json.dump(debate_report, f, indent=2, ensure_ascii=False)
    with open(suggestions_path, "w", encoding="utf-8") as f:
        json.dump(suggestions_report, f, indent=2, ensure_ascii=False)

    logger.info(
        "[debate] reports written: status=%s functions=%d suggestions=%d",
        overall_status, len(function_records), len(all_suggestions),
    )
    return debate_path, suggestions_path


class DebateFailFastError(RuntimeError):
    """Raised when --fail-fast is set and a function debate fails."""
    pass
