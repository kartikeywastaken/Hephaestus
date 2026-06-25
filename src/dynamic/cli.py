# -*- coding: utf-8 -*-
"""
Phase 8 — Dynamic Behavior Capture: CLI command handler.

Entry point: run_dynamic_cli(args_list) -> int
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Hash helper (read-only guard)
# ---------------------------------------------------------------------------

def _file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main CLI
# ---------------------------------------------------------------------------

def run_dynamic_cli(args_list: list[str]) -> int:
    """
    CLI for:  python3 main.py run-dynamic ./binary [options]

    Returns exit code (0 = success, 1 = error, 2 = safety violation).
    """
    parser = argparse.ArgumentParser(
        description="Phase 8: Run target binary and capture dynamic behavior."
    )
    parser.add_argument(
        "binary_path",
        help="Path to the target binary to execute.",
    )
    parser.add_argument(
        "--out-dir", default="artifacts",
        help="Output directory for Phase 8 artifacts. (default: artifacts)",
    )
    parser.add_argument(
        "--inputs", default=None, metavar="PATH",
        help="Path to dynamic_inputs.json. If omitted, uses default no_args run.",
    )
    parser.add_argument(
        "--timeout-s", type=float, default=5.0,
        help="Per-run timeout in seconds. (default: 5.0)",
    )
    parser.add_argument(
        "--max-output-bytes", type=int, default=1_048_576,
        help="Max bytes captured per stream per run. (default: 1048576)",
    )
    parser.add_argument(
        "--cwd", default=None, metavar="PATH",
        help="Working directory for subprocess execution.",
    )
    parser.add_argument(
        "--env", action="append", default=[], metavar="KEY=VALUE",
        help="Additional environment variable overlay (repeatable).",
    )
    parser.add_argument(
        "--allow-nonzero", action="store_true",
        help="Do not fail on nonzero exit codes.",
    )
    parser.add_argument(
        "--fail-fast", action="store_true",
        help="Abort after first failed run.",
    )
    parser.add_argument(
        "--inherit-env", action="store_true",
        help="Inherit the full current environment (default: minimal PATH only).",
    )
    parser.add_argument(
        "--json", dest="json_output", action="store_true",
        help="Print compact JSON summary to stdout.",
    )
    parser.add_argument(
        "--auto-inputs", action="store_true",
        help="Enable automatic dynamic input generation."
    )
    parser.add_argument(
        "--dynamic-max-generated-inputs", type=int, default=20,
        help="Max number of auto-generated inputs. (default: 20)"
    )
    parser.add_argument(
        "--adaptive-dynamic", action="store_true",
        help="Enable adaptive dynamic exploration."
    )
    parser.add_argument(
        "--dynamic-mutation-rounds", type=int, default=2,
        help="Number of mutation rounds for adaptive exploration. (default: 2)"
    )
    parser.add_argument(
        "--dynamic-max-adaptive-inputs", type=int, default=30,
        help="Max number of adaptive inputs generated. (default: 30)"
    )

    try:
        args = parser.parse_args(args_list)
    except SystemExit:
        return 2

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- Read-only guard: hash static artifacts before doing anything ----
    recovered_c = out_dir / "recovered.c"
    recovered_readable_c = out_dir / "recovered_readable.c"
    hash_before = {
        "recovered.c": _file_sha256(recovered_c),
        "recovered_readable.c": _file_sha256(recovered_readable_c),
    }

    # ---- Resolve inputs ----
    from src.dynamic.input_spec import resolve_input_spec

    if args.auto_inputs:
        from src.dynamic.input_generator import (
            generate_default_input_cases,
            merge_and_deduplicate,
            build_input_spec_from_cases,
            write_generated_inputs_artifact,
        )
        try:
            spec, using_default = resolve_input_spec(args.inputs)
        except (ValueError, FileNotFoundError) as e:
            _error(args.json_output, f"Input spec error: {e}")
            return 1

        gen_cases = generate_default_input_cases(max_cases=args.dynamic_max_generated_inputs)
        user_cases = spec.get("runs", [])
        merged_cases = merge_and_deduplicate(user_cases, gen_cases)
        spec = build_input_spec_from_cases(
            merged_cases,
            generated=True,
            max_cases=args.dynamic_max_generated_inputs,
        )
        write_generated_inputs_artifact(
            merged_cases,
            out_dir,
            max_cases=args.dynamic_max_generated_inputs,
        )
        using_default = False
    else:
        try:
            spec, using_default = resolve_input_spec(args.inputs)
        except (ValueError, FileNotFoundError) as e:
            _error(args.json_output, f"Input spec error: {e}")
            return 1

    # ---- Parse --env overlays ----
    extra_env: dict[str, str] = {}
    for kv in args.env:
        if "=" not in kv:
            _error(args.json_output, f"--env argument must be KEY=VALUE, got: {kv!r}")
            return 1
        k, _, v = kv.partition("=")
        extra_env[k] = v

    # Merge extra_env into each run's env overlay
    if extra_env:
        for run in spec.get("runs", []):
            merged = dict(extra_env)
            merged.update(run.get("env", {}))
            run["env"] = merged

    # ---- CWD ----
    cwd: Path | None = None
    if args.cwd:
        cwd = Path(args.cwd)
        if not cwd.is_dir():
            _error(args.json_output, f"--cwd path is not a directory: {cwd}")
            return 1

    # ---- Execute all runs ----
    from src.dynamic.runner import run_all
    from src.dynamic.safety import SafetyError

    try:
        results, binary_sha256 = run_all(
            Path(args.binary_path),
            spec,
            timeout_s=args.timeout_s,
            max_output_bytes=args.max_output_bytes,
            cwd=cwd,
            inherit_env=args.inherit_env,
            fail_fast=args.fail_fast,
        )
    except SafetyError as e:
        _error(args.json_output, f"Safety error: {e}")
        return 1
    except Exception as e:
        _error(args.json_output, f"Unexpected error during execution: {e}")
        return 1

    # ---- Read-only guard: verify static artifacts unchanged ----
    hash_after = {
        "recovered.c": _file_sha256(recovered_c),
        "recovered_readable.c": _file_sha256(recovered_readable_c),
    }
    for name, h_before in hash_before.items():
        h_after = hash_after.get(name)
        if h_before is not None and h_before != h_after:
            _error(
                args.json_output,
                f"SAFETY VIOLATION: {name} was modified during dynamic execution!",
            )
            return 2

    # ---- Adaptive Dynamic Exploration (Phase 11.6 Part C) ----
    adaptive_results = []
    adaptive_cases = []
    explorer_diag = []
    if args.adaptive_dynamic:
        from src.dynamic.explorer import (
            generate_adaptive_inputs,
            build_input_influence_report,
            build_exploration_report,
        )
        initial_dynamic_runs = {"runs": results}
        adaptive_cases, explorer_diag = generate_adaptive_inputs(
            initial_dynamic_runs,
            max_new_cases=args.dynamic_max_adaptive_inputs,
            mutation_rounds=args.dynamic_mutation_rounds,
        )

        # Build input spec for adaptive runs
        adaptive_spec = build_input_spec_from_cases(
            adaptive_cases,
            generated=True,
            max_cases=args.dynamic_max_adaptive_inputs,
        )
        # Write to adaptive_inputs.json
        adaptive_inputs_path = out_dir / "adaptive_inputs.json"
        with open(adaptive_inputs_path, "w", encoding="utf-8") as f:
            json.dump(adaptive_spec, f, indent=2, sort_keys=False)
            f.write("\n")

        if adaptive_cases:
            # Run them
            try:
                adaptive_results, _ = run_all(
                    Path(args.binary_path),
                    adaptive_spec,
                    timeout_s=args.timeout_s,
                    max_output_bytes=args.max_output_bytes,
                    cwd=cwd,
                    inherit_env=args.inherit_env,
                    fail_fast=args.fail_fast,
                )
            except SafetyError as e:
                _error(args.json_output, f"Safety error in adaptive exploration: {e}")
                return 1
            except Exception as e:
                _error(args.json_output, f"Unexpected error in adaptive exploration: {e}")
                return 1

            # Check read-only guard again!
            hash_after2 = {
                "recovered.c": _file_sha256(recovered_c),
                "recovered_readable.c": _file_sha256(recovered_readable_c),
            }
            for name, h_before in hash_before.items():
                h_after2 = hash_after2.get(name)
                if h_before is not None and h_before != h_after2:
                    _error(
                        args.json_output,
                        f"SAFETY VIOLATION: {name} was modified during adaptive dynamic execution!",
                    )
                    return 2

            # Write adaptive_dynamic_runs.json
            adaptive_runs_completed = sum(1 for r in adaptive_results if r.get("status") == "ok")
            adaptive_runs_timed_out = sum(1 for r in adaptive_results if r.get("timed_out"))
            adaptive_runs_crashed = sum(1 for r in adaptive_results if r.get("signal") is not None)
            from src.dynamic.writer import _now_iso
            adaptive_runs_payload = {
                "schema_version": SCHEMA_DYNAMIC_RUNS,
                "phase": "11.6",
                "generated_at": _now_iso(),
                "binary_path": str(args.binary_path),
                "binary_sha256": binary_sha256,
                "timeout_s": args.timeout_s,
                "runs_total": len(adaptive_results),
                "runs_completed": adaptive_runs_completed,
                "runs_timed_out": adaptive_runs_timed_out,
                "runs_crashed": adaptive_runs_crashed,
                "runs": adaptive_results,
                "diagnostics": explorer_diag,
            }
            adaptive_runs_path = out_dir / "adaptive_dynamic_runs.json"
            with open(adaptive_runs_path, "w", encoding="utf-8") as f:
                json.dump(adaptive_runs_payload, f, indent=2, sort_keys=False)
                f.write("\n")
        else:
            from src.dynamic.writer import _now_iso
            adaptive_runs_payload = {
                "schema_version": SCHEMA_DYNAMIC_RUNS,
                "phase": "11.6",
                "generated_at": _now_iso(),
                "binary_path": str(args.binary_path),
                "binary_sha256": binary_sha256,
                "timeout_s": args.timeout_s,
                "runs_total": 0,
                "runs_completed": 0,
                "runs_timed_out": 0,
                "runs_crashed": 0,
                "runs": [],
                "diagnostics": explorer_diag,
            }
            adaptive_runs_path = out_dir / "adaptive_dynamic_runs.json"
            with open(adaptive_runs_path, "w", encoding="utf-8") as f:
                json.dump(adaptive_runs_payload, f, indent=2, sort_keys=False)
                f.write("\n")

        # build input influence report
        influence_report = build_input_influence_report(results, adaptive_results)
        influence_path = out_dir / "input_influence_report.json"
        with open(influence_path, "w", encoding="utf-8") as f:
            json.dump(influence_report, f, indent=2, sort_keys=False)
            f.write("\n")

        # build exploration report
        exploration_report = build_exploration_report(
            explorer_diag,
            initial_run_count=len(results),
            adaptive_run_count=len(adaptive_results),
            new_cases_count=len(adaptive_cases),
        )
        exploration_path = out_dir / "dynamic_exploration_report.json"
        with open(exploration_path, "w", encoding="utf-8") as f:
            json.dump(exploration_report, f, indent=2, sort_keys=False)
            f.write("\n")

    # ---- Build and write artifacts ----
    from src.dynamic.profiler import build_behavior_profile
    from src.dynamic.writer import (
        write_dynamic_inputs_resolved,
        write_dynamic_runs,
        write_behavior_profile,
        write_dynamic_report,
    )

    profile = build_behavior_profile(
        binary_path=args.binary_path,
        binary_sha256=binary_sha256,
        run_results=results,
        input_spec=spec,
    )

    warnings: list[str] = []
    diagnostics: list[str] = []

    if using_default:
        warnings.append(
            "No --inputs file provided. Using default single no_args run. "
            "argv_sensitive and stdin_sensitive require multiple input variants to detect."
        )

    # Check for execution failures
    failed_runs = [r for r in results if r.get("status") == "failed_to_execute"]
    if failed_runs:
        for fr in failed_runs:
            for d in fr.get("diagnostics", []):
                diagnostics.append(f"[{fr.get('name', 'unnamed')}] {d}")

    status = "ok"
    if failed_runs and not args.allow_nonzero:
        status = "partial"
    if len(failed_runs) == len(results) and results:
        status = "failed"

    resolved_path = write_dynamic_inputs_resolved(
        spec, args.binary_path, out_dir, using_default=using_default
    )
    runs_path = write_dynamic_runs(
        results, args.binary_path, binary_sha256, args.timeout_s, out_dir
    )
    profile_path = write_behavior_profile(profile, out_dir)
    report_path = write_dynamic_report(
        status=status,
        artifacts={
            "dynamic_inputs_resolved": str(resolved_path.name),
            "dynamic_runs": str(runs_path.name),
            "behavior_profile": str(profile_path.name),
        },
        diagnostics=diagnostics,
        warnings=warnings,
        out_dir=out_dir,
        using_default_inputs=using_default,
    )

    runs_total = len(results)
    runs_ok = sum(1 for r in results if r.get("status") == "ok")
    runs_timed_out = sum(1 for r in results if r.get("timed_out"))

    if args.json_output:
        summary = {
            "status": status,
            "runs_total": runs_total,
            "runs_ok": runs_ok,
            "runs_timed_out": runs_timed_out,
            "runs_failed": len(failed_runs),
            "argv_sensitive": profile["summary"]["argv_sensitive"],
            "stdout_varies": profile["summary"]["stdout_varies"],
            "artifacts": {
                "dynamic_inputs_resolved": str(resolved_path),
                "dynamic_runs": str(runs_path),
                "behavior_profile": str(profile_path),
                "dynamic_report": str(report_path),
            },
        }
        print(json.dumps(summary))
    else:
        print(
            f"[run-dynamic] status={status} "
            f"runs={runs_total} ok={runs_ok} "
            f"timed_out={runs_timed_out} failed={len(failed_runs)}"
        )
        print(
            f"[run-dynamic] argv_sensitive={profile['summary']['argv_sensitive']} "
            f"stdout_varies={profile['summary']['stdout_varies']}"
        )
        print(f"[run-dynamic] artifacts written to: {out_dir}")

    return 0 if status in ("ok", "partial") else 1


def _error(json_output: bool, message: str) -> None:
    if json_output:
        print(json.dumps({"status": "error", "message": message}))
    else:
        print(f"[run-dynamic] error: {message}", file=sys.stderr)
