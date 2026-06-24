# -*- coding: utf-8 -*-
"""
Phase 9 — Static-Dynamic Behavior Fusion: CLI command handler.

Entry point: run_fuse_behavior_cli(args_list) -> int
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def run_fuse_behavior_cli(args_list: list[str]) -> int:
    """
    CLI for:  python3 main.py fuse-behavior [options]

    IMPORTANT: This command NEVER executes the target binary.
               It only reads existing artifacts.

    Returns exit code (0 = success, 1 = error or partial, 2 = safety violation).
    """
    parser = argparse.ArgumentParser(
        description=(
            "Phase 9: Fuse static and dynamic artifacts into a behavior model. "
            "Does NOT execute the target binary."
        )
    )
    parser.add_argument(
        "--out-dir", default="artifacts",
        help="Directory containing static + dynamic artifacts. (default: artifacts)",
    )
    parser.add_argument(
        "--require-dynamic", action="store_true",
        help="Fail with exit code 1 if dynamic artifacts are missing.",
    )
    parser.add_argument(
        "--require-readable", action="store_true",
        help="Fail with exit code 1 if recovered_readable.c is missing.",
    )
    parser.add_argument(
        "--json", dest="json_output", action="store_true",
        help="Print compact JSON summary to stdout.",
    )

    try:
        args = parser.parse_args(args_list)
    except SystemExit:
        return 2

    out_dir = Path(args.out_dir)

    # ---- Readable check ----
    if args.require_readable:
        readable = out_dir / "recovered_readable.c"
        if not readable.exists():
            msg = f"recovered_readable.c not found in {out_dir}"
            _error(args.json_output, msg)
            return 1

    # ---- Load artifacts ----
    from src.behavior.loader import load_behavior_artifacts

    try:
        arts = load_behavior_artifacts(out_dir, require_dynamic=args.require_dynamic)
    except RuntimeError as e:
        _error(args.json_output, str(e))
        return 1

    # ---- Build behavior model ----
    from src.behavior.fusion import build_behavior_model
    from src.behavior.writer import write_behavior_model, write_behavior_fusion_report

    model = build_behavior_model(arts)

    # ---- Write artifacts ----
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = write_behavior_model(model, out_dir)
    status = model.get("status", "ok")

    report_path = write_behavior_fusion_report(
        status=status,
        artifacts={"behavior_model": str(model_path.name)},
        diagnostics=arts.warnings,
        warnings=[],
        out_dir=out_dir,
    )

    # ---- Summary ----
    summary_data = model.get("summary", {})

    if args.json_output:
        summary = {
            "status": status,
            "functions_total": summary_data.get("functions_total", 0),
            "functions_with_dynamic_evidence": summary_data.get("functions_with_dynamic_evidence", 0),
            "hypotheses_total": summary_data.get("hypotheses_total", 0),
            "global_behavior_observations": summary_data.get("global_behavior_observations", 0),
            "diagnostics": arts.warnings,
            "artifacts": {
                "behavior_model": str(model_path),
                "behavior_fusion_report": str(report_path),
            },
        }
        print(json.dumps(summary))
    else:
        has_dynamic = arts.behavior_profile is not None
        print(
            f"[fuse-behavior] status={status} "
            f"functions={summary_data.get('functions_total', 0)} "
            f"has_dynamic={has_dynamic}"
        )
        print(
            f"[fuse-behavior] hypotheses={summary_data.get('hypotheses_total', 0)} "
            f"global_behavior={summary_data.get('global_behavior_observations', 0)}"
        )
        if arts.warnings:
            for w in arts.warnings:
                print(f"[fuse-behavior] warning: {w}", file=sys.stderr)
        print(f"[fuse-behavior] artifacts written to: {out_dir}")

    return 0 if status in ("ok",) else 1


def _error(json_output: bool, message: str) -> None:
    if json_output:
        print(json.dumps({"status": "error", "message": message}))
    else:
        print(f"[fuse-behavior] error: {message}", file=sys.stderr)
