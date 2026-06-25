# -*- coding: utf-8 -*-
"""
Phase 10 — Agent CLI commands.

Two subcommands:
  build-agent-packets   Build per-function packets from all artifacts.
  agent-debate          Run the 5-agent debate against a real provider.

Provider selection:
  --provider ollama     OllamaProvider (no API key required)
  --provider groq       GroqProvider   (API key from env)

API key handling for Groq:
  1. --api-key-env FLAG_VALUE  (name of the env var to read)
  2. GROQ_API_KEY env var
  3. HEPHAESTUS_GROQ_API_KEY env var
  → Fail cleanly if none found. Never print the key.

Hash guards:
  Before and after packet build and debate, sha256 of:
    recovered.c, recovered_readable.c,
    source_reconstruction.json, behavior_model.json
  If any changes → exit(2).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List

logger = logging.getLogger("agent.cli")

SUPPORTED_PROVIDERS = ("ollama", "groq")


# ── build-agent-packets ───────────────────────────────────────────────────────

def run_build_agent_packets_cli(argv: List[str]) -> int:
    from src.utils.env_loader import load_default_env_files
    load_default_env_files()
    """
    Build per-function agent packets from all available artifacts.

    Exit codes:
      0  — success
      1  — soft failure (no source_reconstruction.json, etc.)
      2  — safety violation (input artifact hash changed)
    """
    parser = argparse.ArgumentParser(
        description="Build per-function agent packets from Hephaestus artifacts."
    )
    parser.add_argument(
        "--out-dir", default="artifacts",
        help="Directory containing Hephaestus artifacts."
    )
    parser.add_argument(
        "--max-slice-lines", type=int, default=200,
        help="Maximum lines per C function slice (default: 200)."
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Print clean JSON result on stdout."
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if e.code is not None else 2

    out_dir = Path(args.out_dir).resolve()
    json_mode = args.json

    from src.agent.packet_builder import (
        build_all_packets,
        verify_input_hashes,
    )
    from src.agent.packet_writer import write_packets

    # 1. Build packets (records hashes before any I/O)
    try:
        packets, diagnostics, hashes_before = build_all_packets(
            out_dir, max_slice_lines=args.max_slice_lines
        )
    except Exception as e:
        msg = f"[build-agent-packets] unexpected error: {e}"
        logger.exception(msg)
        if json_mode:
            print(json.dumps({"status": "failed", "error": str(e)}))
        else:
            print(f"Error: {msg}", file=sys.stderr)
        return 1

    if not packets:
        msg = (
            "No packets built. "
            "Ensure source_reconstruction.json exists in --out-dir."
        )
        if json_mode:
            print(json.dumps({
                "status": "partial",
                "packets_written": 0,
                "diagnostics": diagnostics,
                "message": msg,
            }))
        else:
            print(f"Warning: {msg}", file=sys.stderr)
        return 1

    # 2. Write packets
    try:
        manifest_path = write_packets(packets, out_dir, diagnostics)
    except Exception as e:
        msg = f"[build-agent-packets] write error: {e}"
        logger.exception(msg)
        if json_mode:
            print(json.dumps({"status": "failed", "error": str(e)}))
        else:
            print(f"Error: {msg}", file=sys.stderr)
        return 1

    # 3. Hash guard — verify input artifacts unchanged after I/O
    changed = verify_input_hashes(out_dir, hashes_before)
    if changed:
        msg = (
            f"[build-agent-packets] SAFETY VIOLATION: "
            f"input artifacts modified during execution: {changed}"
        )
        logger.error(msg)
        if json_mode:
            print(json.dumps({"status": "failed", "error": msg}))
        else:
            print(f"Error: {msg}", file=sys.stderr)
        return 2

    if json_mode:
        print(json.dumps({
            "status": "ok",
            "packets_written": len(packets),
            "manifest": str(manifest_path),
            "diagnostics": diagnostics,
        }))
    else:
        print(f"[build-agent-packets] status=ok packets={len(packets)}")
        print(f"[build-agent-packets] manifest written to: {manifest_path}")
        if diagnostics:
            for d in diagnostics:
                print(f"[build-agent-packets] diagnostic: {d}", file=sys.stderr)

    return 0


# ── agent-debate ──────────────────────────────────────────────────────────────

def run_agent_debate_cli(argv: List[str]) -> int:
    from src.utils.env_loader import load_default_env_files
    load_default_env_files()
    """
    Run the 5-agent debate against a real LLM provider.

    Exit codes:
      0  — success (all functions debated)
      1  — soft failure (Ollama/Groq unavailable, partial run, etc.)
      2  — safety violation (input artifact hash changed)
    """
    parser = argparse.ArgumentParser(
        description="Run Hephaestus multi-agent debate via a real LLM provider."
    )
    parser.add_argument("--out-dir", default="artifacts",
                        help="Directory containing Hephaestus artifacts.")
    parser.add_argument("--function", default=None,
                        help="Debate only this function name.")
    parser.add_argument("--max-functions", type=int, default=None,
                        help="Maximum number of functions to debate.")
    parser.add_argument("--provider", default="ollama",
                        choices=list(SUPPORTED_PROVIDERS),
                        help="LLM provider: ollama or groq.")
    parser.add_argument("--model", default=None,
                        help="Model name (overrides env and defaults).")
    parser.add_argument("--ollama-host", default=None,
                        help="Ollama host URL (ollama provider only).")
    parser.add_argument("--groq-host", default=None,
                        help="Groq API host URL (groq provider only).")
    parser.add_argument("--api-key-env", default=None, metavar="ENV_NAME",
                        help="Name of env var holding the Groq API key.")
    parser.add_argument("--timeout-s", type=int, default=300,
                        help="Request timeout in seconds (default: 300).")
    parser.add_argument("--num-ctx", type=int, default=8192,
                        help="Context window tokens for Ollama (default: 8192).")
    parser.add_argument("--temperature", type=float, default=0.0,
                        help="Sampling temperature (default: 0.0).")
    parser.add_argument("--fail-fast", action="store_true",
                        help="Abort on first function failure.")
    parser.add_argument("--json", action="store_true",
                        help="Print clean JSON result on stdout.")
    parser.add_argument("--packet-mode", default="compact", choices=["compact", "full"],
                        help="Packet mode: compact or full (default: compact).")
    parser.add_argument("--max-packet-chars", type=int, default=16000,
                        help="Max characters per optimized packet (default: 16000).")
    parser.add_argument("--max-evidence-items", type=int, default=20,
                        help="Max evidence items inside optimized packet (default: 20).")
    parser.add_argument("--retry-on-413", action="store_true", default=True,
                        help="Retry on 413 Payload Too Large (default: True).")
    parser.add_argument("--no-retry-on-413", dest="retry_on_413", action="store_false",
                        help="Disable retry on 413 Payload Too Large.")
    parser.add_argument("--wait-on-429", action="store_true", default=False,
                        help="Retry on 429 Rate Limit (default: False).")
    parser.add_argument("--max-provider-retries", type=int, default=1,
                        help="Max provider retries for 413/429 (default: 1).")

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if e.code is not None else 2

    out_dir = Path(args.out_dir).resolve()
    json_mode = args.json

    # ── Validate provider ──────────────────────────────────────────────────
    if args.provider not in SUPPORTED_PROVIDERS:
        msg = (
            f"Unsupported provider: '{args.provider}'. "
            f"Supported: {', '.join(SUPPORTED_PROVIDERS)}"
        )
        if json_mode:
            print(json.dumps({"status": "failed", "error": msg}))
        else:
            print(f"Error: {msg}", file=sys.stderr)
        return 1

    # ── Load packets ───────────────────────────────────────────────────────
    packets_dir = out_dir / "agent_packets"
    manifest_path = out_dir / "agent_packet_manifest.json"

    # Auto-build packets if missing
    if not packets_dir.exists() or not manifest_path.exists():
        if not json_mode:
            print(
                "[agent-debate] agent_packets/ missing — running build-agent-packets...",
                file=sys.stderr,
            )
        rc = run_build_agent_packets_cli(["--out-dir", str(out_dir)])
        if rc != 0:
            msg = "build-agent-packets failed; cannot proceed with debate."
            if json_mode:
                print(json.dumps({"status": "failed", "error": msg}))
            else:
                print(f"Error: {msg}", file=sys.stderr)
            return rc

    if args.packet_mode == "compact":
        from src.agent.context_optimizer import optimize_agent_packets
        optimize_agent_packets(
            out_dir,
            packet_mode="compact",
            max_packet_chars=args.max_packet_chars,
            max_evidence_items=args.max_evidence_items,
        )
        packets_dir = out_dir / "agent_packets_compact"

    packets = _load_packets(packets_dir, args.function)
    if not packets:
        msg = (
            f"No packets found in {packets_dir}. "
            "Run build-agent-packets first, or check --function name."
        )
        if json_mode:
            print(json.dumps({"status": "failed", "error": msg}))
        else:
            print(f"Error: {msg}", file=sys.stderr)
        return 1

    # ── Build provider ─────────────────────────────────────────────────────
    try:
        provider, provider_name, model_name, api_key_env_used = _build_provider(args)
    except _ProviderBuildError as e:
        if json_mode:
            print(json.dumps({"status": "failed", "error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

    # ── Health check ───────────────────────────────────────────────────────
    avail = provider.check_available()
    if not avail.get("available"):
        err = avail.get("error", "Provider unavailable.")
        suggestion = avail.get("suggestion", "")
        msg = f"Provider unavailable: {err}"
        if suggestion:
            msg += f"\nSuggestion: {suggestion}"
        if json_mode:
            print(json.dumps({"status": "failed", "error": msg}))
        else:
            print(f"Error: {msg}", file=sys.stderr)
        return 1

    if not json_mode:
        # Compute the actual count that will be debated (after filtering)
        from src.agent.library_filter import filter_debatable_packets
        _preview_debatable, _preview_skipped = filter_debatable_packets(
            packets, max_functions=args.max_functions,
        )
        print(
            f"[agent-debate] provider={provider_name} model={model_name} "
            f"functions={len(_preview_debatable)}"
            + (f" skipped_library={len(_preview_skipped)}" if _preview_skipped else "")
        )

    # ── Hash guard (before debate) ─────────────────────────────────────────
    from src.agent.packet_builder import compute_input_hashes, verify_input_hashes
    hashes_before = compute_input_hashes(out_dir)

    # ── Run debate ─────────────────────────────────────────────────────────
    from src.agent.debate import run_debate, write_debate_report, DebateFailFastError

    try:
        function_records, all_suggestions = run_debate(
            packets,
            provider,
            fail_fast=args.fail_fast,
            max_functions=args.max_functions,
            retry_on_413=args.retry_on_413,
            wait_on_429=args.wait_on_429,
            max_provider_retries=args.max_provider_retries,
        )
    except DebateFailFastError as e:
        if json_mode:
            print(json.dumps({"status": "failed", "error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.exception("[agent-debate] unexpected error: %s", e)
        if json_mode:
            print(json.dumps({"status": "failed", "error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1

    # ── Hash guard (after debate — must not have changed) ──────────────────
    changed = verify_input_hashes(out_dir, hashes_before)
    if changed:
        msg = (
            f"[agent-debate] SAFETY VIOLATION: "
            f"input artifacts modified during debate: {changed}"
        )
        logger.error(msg)
        if json_mode:
            print(json.dumps({"status": "failed", "error": msg}))
        else:
            print(f"Error: {msg}", file=sys.stderr)
        return 2

    # ── Write reports ──────────────────────────────────────────────────────
    try:
        debate_path, suggestions_path = write_debate_report(
            function_records,
            all_suggestions,
            out_dir,
            provider_name=provider_name,
            model=model_name,
            api_key_env=api_key_env_used,
        )
    except Exception as e:
        logger.exception("[agent-debate] report write error: %s", e)
        if json_mode:
            print(json.dumps({"status": "failed", "error": str(e)}))
        else:
            print(f"Error writing reports: {e}", file=sys.stderr)
        return 1

    functions_failed = sum(
        1 for r in function_records if r.get("status") == "failed"
    )
    overall_status = (
        "failed" if functions_failed == len(function_records)
        else "partial" if functions_failed > 0
        else "ok"
    )

    if json_mode:
        print(json.dumps({
            "status": overall_status,
            "provider": provider_name,
            "model": model_name,
            "functions_reviewed": len(function_records),
            "functions_failed": functions_failed,
            "suggestions_total": len(all_suggestions),
            "debate_report": str(debate_path),
            "suggestions": str(suggestions_path),
        }))
    else:
        print(
            f"[agent-debate] status={overall_status} "
            f"functions={len(function_records)} "
            f"failed={functions_failed} "
            f"suggestions={len(all_suggestions)}"
        )
        print(f"[agent-debate] debate report: {debate_path}")
        print(f"[agent-debate] suggestions:   {suggestions_path}")

    return 0 if overall_status in ("ok", "partial") else 1


# ── Provider factory ──────────────────────────────────────────────────────────

class _ProviderBuildError(RuntimeError):
    pass


def _build_provider(
    args: argparse.Namespace,
) -> tuple[object, str, str, str | None]:
    """
    Instantiate the requested provider.

    Returns (provider, provider_name, model_name, api_key_env_name_used).
    """
    from src.agent.models import (
        DEFAULT_OLLAMA_HOST, DEFAULT_OLLAMA_MODEL,
        DEFAULT_OLLAMA_TIMEOUT_S, DEFAULT_OLLAMA_TEMPERATURE, DEFAULT_OLLAMA_NUM_CTX,
    )
    from src.agent.providers.groq import (
        DEFAULT_GROQ_HOST, DEFAULT_GROQ_MODEL,
        resolve_groq_api_key, GroqApiKeyMissingError,
    )

    if args.provider == "ollama":
        from src.agent.providers.ollama import OllamaProvider
        model = args.model or DEFAULT_OLLAMA_MODEL
        provider = OllamaProvider(
            host=args.ollama_host or DEFAULT_OLLAMA_HOST,
            model=model,
            timeout_s=args.timeout_s,
            temperature=args.temperature,
            num_ctx=args.num_ctx,
        )
        return provider, "ollama", model, None

    elif args.provider == "groq":
        from src.agent.providers.groq import GroqProvider
        try:
            api_key = resolve_groq_api_key(api_key_env=args.api_key_env)
        except GroqApiKeyMissingError as e:
            raise _ProviderBuildError(str(e)) from e

        # Which env var was actually used?
        api_key_env_used = args.api_key_env or (
            "GROQ_API_KEY"
            if __import__("os").environ.get("GROQ_API_KEY")
            else "HEPHAESTUS_GROQ_API_KEY"
        )

        model = args.model or DEFAULT_GROQ_MODEL
        groq_host = getattr(args, "groq_host", None) or DEFAULT_GROQ_HOST
        provider = GroqProvider(
            api_key=api_key,
            host=groq_host,
            model=model,
            timeout_s=args.timeout_s,
            temperature=args.temperature,
        )
        return provider, "groq", model, api_key_env_used

    else:
        raise _ProviderBuildError(
            f"Unknown provider '{args.provider}'. "
            f"Supported: {', '.join(SUPPORTED_PROVIDERS)}"
        )


# ── Packet loader ─────────────────────────────────────────────────────────────

def _load_packets(
    packets_dir: Path,
    function_filter: str | None,
) -> list[dict]:
    """Load packet JSON files from agent_packets/ directory."""
    packets = []
    for p in sorted(packets_dir.glob("*.json")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                packet = json.load(f)
            if function_filter and packet.get("function") != function_filter:
                continue
            packets.append(packet)
        except Exception as e:
            logger.warning("[agent-debate] failed to load packet %s: %s", p.name, e)
    return packets
