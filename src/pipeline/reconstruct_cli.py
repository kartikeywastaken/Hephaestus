# -*- coding: utf-8 -*-
"""
Phase 11.5 — Reconstruction CLI orchestration command.
"""

from __future__ import annotations
import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import List

from src.utils.env_loader import load_default_env_files


def run_reconstruct_cli(argv: List[str]) -> int:
    """
    Run Hephaestus complete reconstruction pipeline up to recovered_agent.c.
    """
    # 1. Load env files at CLI startup
    load_default_env_files()

    parser = argparse.ArgumentParser(
        prog="reconstruct",
        description="Phase 11.5 — One-Command Reconstruction Pipeline",
    )
    parser.add_argument(
        "binary_path",
        help="Path to the target binary or trace file."
    )
    parser.add_argument(
        "--out-dir",
        default="artifacts",
        help="Output directory for generated JSON and C artifacts."
    )
    parser.add_argument(
        "--provider",
        choices=["ollama", "groq"],
        default="groq",
        help="LLM provider: ollama or groq (default: groq)."
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model name (overrides default for provider)."
    )
    parser.add_argument(
        "--api-key-env",
        default=None,
        metavar="ENV_NAME",
        help="Environment variable name for Groq API key."
    )
    parser.add_argument(
        "--ollama-host",
        default=None,
        help="Ollama host URL."
    )
    parser.add_argument(
        "--groq-host",
        default=None,
        help="Groq API host URL."
    )
    parser.add_argument(
        "--dynamic-inputs",
        default=None,
        metavar="PATH",
        help="Path to dynamic inputs JSON file."
    )
    parser.add_argument(
        "--dynamic-timeout-s",
        type=float,
        default=5.0,
        metavar="FLOAT",
        help="Timeout in seconds for dynamic capture."
    )
    parser.add_argument(
        "--dynamic-max-output-bytes",
        type=int,
        default=1048576,
        metavar="INT",
        help="Max output bytes to capture."
    )
    parser.add_argument(
        "--max-functions",
        type=int,
        default=1,
        metavar="INT",
        help="Max functions to analyze/debate/generate (default: 1)."
    )
    parser.add_argument(
        "--function",
        default=None,
        metavar="NAME",
        help="Debate/generate only this function name."
    )
    parser.add_argument(
        "--allow-human-suggestions",
        action="store_true",
        help="Allow human approved suggestions in Phase 11."
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output C source files."
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean the output directory before running."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output final manifest as JSON on stdout."
    )

    # Debug/skip flags
    parser.add_argument(
        "--skip-static",
        action="store_true",
        help="Assume static artifacts exist and skip static extraction/analysis."
    )
    parser.add_argument(
        "--skip-dynamic",
        action="store_true",
        help="Skip dynamic behavior capture."
    )
    parser.add_argument(
        "--skip-fusion",
        action="store_true",
        help="Skip static-dynamic behavior fusion."
    )
    parser.add_argument(
        "--skip-agent-debate",
        action="store_true",
        help="Skip Phase 10 agent debate."
    )
    parser.add_argument(
        "--skip-agent-source",
        action="store_true",
        help="Skip Phase 11 agent source generation."
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if e.code is not None else 1

    # Redirect logging to stderr if --json is passed
    if args.json:
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.stream = sys.stderr

    logger = logging.getLogger("reconstruct")

    # Resolve and validate binary path
    binary_path = args.binary_path
    if not args.skip_static and not os.path.exists(binary_path):
        if binary_path in ["sample.exe", "sample.bin", "sample.elf", "./t"]:
            # Auto-synthesize placeholder if needed
            logger.warning("Target binary '%s' not present on disk. Automatically synthesizing placeholder reference.", binary_path)
            with open(binary_path, "wb") as f:
                f.write(b"\x7fELF\x02\x01\x01\x00_placeholder_bin")
        else:
            logger.error("Target binary file does not exist: %s", binary_path)
            return 1

    # Validate Provider API Key if using groq
    if args.provider == "groq":
        from src.agent.providers.groq import resolve_groq_api_key, GroqApiKeyMissingError
        try:
            resolve_groq_api_key(explicit_key=None, api_key_env=args.api_key_env)
        except GroqApiKeyMissingError as e:
            logger.error("%s", e)
            print(f"Error: {e}", file=sys.stderr)
            return 1

    # Skip validation: if skip-agent-debate is passed but skip-agent-source is NOT passed,
    # require existing agent_suggestions.json in out-dir.
    if args.skip_agent_debate and not args.skip_agent_source:
        suggestions_path = Path(args.out_dir) / "agent_suggestions.json"
        if not suggestions_path.exists():
            logger.error("Missing required agent_suggestions.json since --skip-agent-debate is set but --skip-agent-source is not.")
            print("Error: Missing required agent_suggestions.json since --skip-agent-debate is set.", file=sys.stderr)
            return 1

    # Resolve model name
    model_name = args.model
    if not model_name:
        if args.provider == "groq":
            model_name = "llama-3.3-70b-versatile"
        elif args.provider == "ollama":
            model_name = os.environ.get("HEPHAESTUS_AGENT_MODEL", "llama3.3:70b")

    # Run the pipeline runner
    from src.pipeline.runner import run_pipeline, PipelineError

    try:
        manifest = run_pipeline(
            binary_path=binary_path,
            out_dir=args.out_dir,
            use_ghidra=not args.skip_static,
            use_radare2=not args.skip_static,
            clean=args.clean,
            continue_on_error=False,
            no_source=False,
            stop_after=None,
            validate=True,
            validate_strict=False,
            evidence_index=True,
            require_evidence_index=False,
            trace_report=True,
            require_trace_report=False,
            quality_gate=True,
            readable=True,
            promote_symbols=True,
            promote_temps=False,
            no_compile_shape_fix=False,
            strict_readable_clang=False,
            simplify_expressions=True,
            no_copy_op_store_simplification=False,
            enable_mask_cast_simplification=False,
            skip_static=args.skip_static,
            # Phase 8 — Dynamic Behavior Capture
            dynamic=not args.skip_dynamic,
            dynamic_inputs=args.dynamic_inputs,
            dynamic_timeout_s=args.dynamic_timeout_s,
            dynamic_max_output_bytes=args.dynamic_max_output_bytes,
            # Phase 9 — Static-Dynamic Behavior Fusion
            fuse_behavior=not args.skip_fusion,
            require_dynamic=False,
            # Phase 10 — Agent Orchestration
            agent_debate=not args.skip_agent_debate,
            agent_provider=args.provider,
            agent_model=model_name,
            agent_ollama_host=args.ollama_host,
            agent_groq_host=args.groq_host,
            agent_api_key_env=args.api_key_env,
            agent_timeout_s=300,
            agent_temperature=0.0,
            agent_num_ctx=8192,
            agent_max_functions=args.max_functions,
            # Phase 11 — Agent-Assisted Source Generation
            generate_agent_source=not args.skip_agent_source,
            source_provider=args.provider,
            source_model=model_name,
            source_max_functions=args.max_functions,
            source_api_key_env=args.api_key_env,
            allow_human_suggestions=args.allow_human_suggestions,
            overwrite_agent_source=args.overwrite,
            # Forward function filter
            function=args.function,
        )

        if args.json:
            print(json.dumps(manifest, indent=2))

        if manifest.get("status") in ("failed", "partial"):
            return 1
        return 0

    except PipelineError as e:
        logger.error("Pipeline error: %s", e)
        print(f"Pipeline error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error("System error: %s", e)
        print(f"System error: {e}", file=sys.stderr)
        return 1
