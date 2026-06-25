# -*- coding: utf-8 -*-
"""
Phase 11 — Agent-Assisted Source Generation: CLI entry point.

Subcommand: generate-agent-source

Usage:
  python3 main.py generate-agent-source [OPTIONS]

Required:
  --out-dir DIR        Output directory (must contain recovered_readable.c and
                       agent_suggestions.json)

Provider:
  --provider {ollama,groq}    Default: ollama
  --model MODEL               Override default model
  --ollama-host URL           Ollama host (default: http://localhost:11434)
  --groq-host URL             Groq host (default: https://api.groq.com/openai/v1)
  --api-key-env ENV_NAME      Name of env var holding Groq API key
  --timeout-s N               Request timeout seconds (default: 300)
  --temperature FLOAT         Sampling temperature (default: 0.0)
  --num-ctx N                 Context window tokens (default: 8192, Ollama only)

Generation control:
  --max-functions N            Max functions to process with LLM (default: 1)
  --function NAME              Only generate a single named function
  --mode {function_by_function,whole_file}  Default: function_by_function
  --fail-fast                  Abort on first generation failure
  --allow-human-suggestions    Enable suggestions requiring human approval

Safety:
  --overwrite                  Allow overwriting existing recovered_agent.c

Exit codes:
  0  Success
  1  Input error (missing artifact, bad flag, provider unavailable)
  2  Safety violation (guarded artifact modified during run)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger("agent_source.cli")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="generate-agent-source",
        description="Phase 11 — Agent-Assisted Source Generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--out-dir", required=True, help="Hephaestus artifact directory")

    # Provider
    pg = p.add_argument_group("provider")
    pg.add_argument("--provider", choices=["ollama", "groq"], default="ollama")
    pg.add_argument("--model", default=None)
    pg.add_argument("--ollama-host", default=None)
    pg.add_argument("--groq-host", default=None)
    pg.add_argument("--api-key-env", default=None, metavar="ENV_NAME",
                    help="Name of env var holding Groq API key")
    pg.add_argument("--timeout-s", type=int, default=300)
    pg.add_argument("--temperature", type=float, default=0.0)
    pg.add_argument("--num-ctx", type=int, default=8192)

    # Generation control
    gg = p.add_argument_group("generation")
    gg.add_argument("--max-functions", type=int, default=1,
                    help="Max functions to process with LLM (default: 1)")
    gg.add_argument("--function", default=None, metavar="NAME",
                    help="Only generate a single named function")
    gg.add_argument("--mode", choices=["function_by_function", "whole_file"],
                    default="function_by_function")
    gg.add_argument("--fail-fast", action="store_true")
    gg.add_argument("--allow-human-suggestions", action="store_true")

    # Safety
    p.add_argument("--overwrite", action="store_true",
                   help="Allow overwriting existing recovered_agent.c")

    return p


def run_generate_agent_source_cli(argv: list[str]) -> int:
    from src.utils.env_loader import load_default_env_files
    load_default_env_files()
    """
    Entry point for generate-agent-source subcommand.
    Returns exit code: 0 (success), 1 (input error), 2 (safety violation).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir).resolve()

    if not out_dir.exists():
        logger.error("[generate-agent-source] --out-dir does not exist: %s", out_dir)
        print(f"Error: --out-dir does not exist: {out_dir}", file=sys.stderr)
        return 1

    # ── Overwrite guard ───────────────────────────────────────────────────────
    from src.agent_source.loader import (
        load_phase11_artifacts,
        compute_phase11_hashes,
        verify_phase11_hashes,
    )

    recovered_agent_path = out_dir / "recovered_agent.c"
    if recovered_agent_path.exists() and not args.overwrite:
        logger.error(
            "[generate-agent-source] recovered_agent.c already exists. "
            "Pass --overwrite to regenerate."
        )
        print(
            "Error: recovered_agent.c already exists. Pass --overwrite to regenerate.",
            file=sys.stderr,
        )
        return 1

    # ── Hash guard: before ────────────────────────────────────────────────────
    hashes_before = compute_phase11_hashes(out_dir)

    # ── Load artifacts ────────────────────────────────────────────────────────
    arts = load_phase11_artifacts(out_dir, overwrite=args.overwrite)

    if arts.missing_required:
        for name in arts.missing_required:
            logger.error("[generate-agent-source] missing required artifact: %s", name)
            print(f"Error: missing required artifact: {name}", file=sys.stderr)
        return 1

    for w in arts.warnings:
        logger.warning("[generate-agent-source] %s", w)

    # ── Build plan ────────────────────────────────────────────────────────────
    from src.agent_source.plan_builder import build_source_plan
    plan_entries, plan_diagnostics = build_source_plan(
        arts,
        allow_human_suggestions=args.allow_human_suggestions,
    )
    logger.info("[generate-agent-source] plan: %d entries", len(plan_entries))

    # ── Build provider ────────────────────────────────────────────────────────
    from src.agent_source.provider_bridge import build_provider_from_args, ProviderBridgeError
    try:
        provider, provider_name, model_name, api_key_env_used = build_provider_from_args(args)
    except ProviderBridgeError as e:
        logger.error("[generate-agent-source] provider build failed: %s", e)
        print(f"Error: {e}", file=sys.stderr)
        return 1

    logger.info(
        "[generate-agent-source] provider=%s model=%s", provider_name, model_name
    )

    # Check provider availability (Ollama only)
    if provider_name == "ollama":
        avail = provider.check_available()
        if not avail["available"]:
            logger.error(
                "[generate-agent-source] Ollama not available: %s", avail["error"]
            )
            print(
                f"Error: Ollama not available: {avail['error']}\n"
                f"Suggestion: {avail.get('suggestion', '')}",
                file=sys.stderr,
            )
            return 1

    # ── Generate ──────────────────────────────────────────────────────────────
    from src.agent_source.generator import generate_source, GeneratorFailFastError
    try:
        generated_c, function_records, global_diagnostics = generate_source(
            arts,
            plan_entries,
            provider,
            mode=args.mode,
            max_functions=args.max_functions,
            function_filter=args.function,
            fail_fast=args.fail_fast,
        )
    except GeneratorFailFastError as e:
        logger.error("[generate-agent-source] fail-fast triggered: %s", e)
        print(f"Error (fail-fast): {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.exception("[generate-agent-source] generation error: %s", e)
        print(f"Error: generation failed: {e}", file=sys.stderr)
        return 1

    for diag in global_diagnostics:
        logger.info("[generate-agent-source] %s", diag)

    # ── Hash guard: after generation, before write ────────────────────────────
    changed = verify_phase11_hashes(out_dir, hashes_before)
    if changed:
        logger.error(
            "[generate-agent-source] ABORT: guarded artifacts changed during "
            "generation: %s", changed
        )
        print(
            f"SAFETY VIOLATION (exit 2): guarded artifacts modified: {changed}",
            file=sys.stderr,
        )
        return 2

    # ── Validate ──────────────────────────────────────────────────────────────
    from src.agent_source.validator import validate_agent_source
    val_ok, val_issues, clang_status = validate_agent_source(
        generated_c,
        out_dir,
        function_records,
        hashes_before=hashes_before,
        expected_functions=None,
    )

    for issue in val_issues:
        if "FAIL" in issue or "ABORT" in issue:
            logger.error("[generate-agent-source] %s", issue)
        elif "WARNING" in issue:
            logger.warning("[generate-agent-source] %s", issue)
        else:
            logger.info("[generate-agent-source] %s", issue)

    # If hash guard triggered inside validator, exit 2
    if any("ABORT" in issue for issue in val_issues):
        print("SAFETY VIOLATION (exit 2): guarded artifact modified", file=sys.stderr)
        return 2

    # ── Write artifacts ───────────────────────────────────────────────────────
    from src.agent_source.writer import write_agent_source_artifacts
    try:
        plan_path, c_path, report_path, val_path = write_agent_source_artifacts(
            out_dir=out_dir,
            plan_entries=plan_entries,
            generated_c=generated_c,
            function_records=function_records,
            validation_result=(val_ok, val_issues, clang_status),
            provider_name=provider_name,
            model_name=model_name,
            global_diagnostics=global_diagnostics,
            plan_diagnostics=plan_diagnostics,
            generation_mode=args.mode,
            max_functions=args.max_functions,
        )
    except Exception as e:
        logger.exception("[generate-agent-source] write failed: %s", e)
        print(f"Error: write failed: {e}", file=sys.stderr)
        return 1

    # ── Final hash guard: after write ─────────────────────────────────────────
    changed = verify_phase11_hashes(out_dir, hashes_before)
    if changed:
        logger.error(
            "[generate-agent-source] ABORT: guarded artifacts modified after write: %s",
            changed,
        )
        print(
            f"SAFETY VIOLATION (exit 2): guarded artifacts modified after write: {changed}",
            file=sys.stderr,
        )
        return 2

    # ── Summary ───────────────────────────────────────────────────────────────
    generated_count = sum(1 for r in function_records if r.get("generated"))
    copied_count = sum(
        1 for r in function_records
        if not r.get("generated") and r.get("status") == "copied_unchanged"
    )
    failed_count = sum(1 for r in function_records if r.get("status") == "failed")

    print(
        f"\n[Phase 11] generate-agent-source complete\n"
        f"  provider:   {provider_name} / {model_name}\n"
        f"  mode:       {args.mode}\n"
        f"  functions:  generated={generated_count} "
        f"copied={copied_count} failed={failed_count}\n"
        f"  validation: {'PASS' if val_ok else 'FAIL'} "
        f"(clang={clang_status})\n"
        f"  outputs:\n"
        f"    {c_path}\n"
        f"    {plan_path}\n"
        f"    {report_path}\n"
        f"    {val_path}\n"
    )

    return 0
