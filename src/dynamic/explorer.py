# -*- coding: utf-8 -*-
"""
Phase 11.6 — Adaptive dynamic exploration.

Generates additional safe argv cases based on observed dynamic behavior
from an initial run set.  All mutations are deterministic heuristics —
no LLM is involved.

Safety invariants:
  - Max argv count enforced
  - Max string length enforced
  - No null bytes
  - No env mutation
  - No shell execution
  - All generated inputs pass ``validate_argv()``
"""

from __future__ import annotations

import datetime
import hashlib
import json
import random
from pathlib import Path
from typing import Any

from src.dynamic.safety import validate_argv


# ── Safety limits ─────────────────────────────────────────────────────────────

MAX_ARGV_COUNT = 10
MAX_ARGV_STRING_LEN = 256


# ── Mutation helpers ──────────────────────────────────────────────────────────

def _safe_argv(argv: list[str]) -> bool:
    """Check if an argv list passes safety validation."""
    if len(argv) > MAX_ARGV_COUNT:
        return False
    for arg in argv:
        if not isinstance(arg, str):
            return False
        if len(arg) > MAX_ARGV_STRING_LEN:
            return False
        if "\x00" in arg:
            return False
    try:
        validate_argv(argv)
        return True
    except Exception:
        return False


def _mutate_string(s: str) -> list[str]:
    """Generate safe string mutations."""
    mutations = []
    if s:
        mutations.append(s.upper())
        mutations.append(s.lower())
        mutations.append(s[:len(s) // 2])  # shrink
        mutations.append(s + s[:2])         # extend slightly
        mutations.append(s[0])             # single char
    mutations.append("")
    if s.isdigit():
        try:
            n = int(s)
            mutations.append(str(n + 1))
            mutations.append(str(n - 1))
            mutations.append(str(n * 2))
        except (ValueError, OverflowError):
            pass
    # Filter to safe lengths
    return [m for m in mutations if len(m) <= MAX_ARGV_STRING_LEN and "\x00" not in m]


def _generate_argc_variants(observed_argvs: list[list[str]]) -> list[list[str]]:
    """Generate 0, 1, 2, 3 arg variants based on observed argv patterns."""
    variants: list[list[str]] = []
    # Always try these argc values
    variants.append([])         # argc=1 (program name only)
    variants.append(["x"])      # argc=2
    variants.append(["x", "y"]) # argc=3
    variants.append(["x", "y", "z"])  # argc=4

    # Build from observed args
    all_args: list[str] = []
    for argv in observed_argvs:
        all_args.extend(argv)
    if all_args:
        # Single observed arg
        variants.append([all_args[0]])
        # Two observed args if available
        if len(all_args) >= 2:
            variants.append([all_args[0], all_args[1]])

    return variants


def _generate_numeric_variants() -> list[list[str]]:
    """Generate numeric and byte-pattern variants."""
    return [
        ["0"],
        ["1"],
        ["-1"],
        ["127"],
        ["128"],
        ["255"],
        ["256"],
        ["65535"],
        ["2147483647"],   # INT_MAX
        ["-2147483648"],  # INT_MIN
    ]


def _generate_string_mutations(observed_argvs: list[list[str]]) -> list[list[str]]:
    """Mutate observed string arguments."""
    mutations: list[list[str]] = []
    for argv in observed_argvs:
        for i, arg in enumerate(argv):
            for mutated in _mutate_string(arg):
                new_argv = argv[:i] + [mutated] + argv[i + 1:]
                mutations.append(new_argv)
    return mutations


# ── Core explorer ─────────────────────────────────────────────────────────────

def generate_adaptive_inputs(
    dynamic_runs: dict,
    *,
    max_new_cases: int = 30,
    mutation_rounds: int = 2,
) -> tuple[list[dict], list[str]]:
    """
    Generate additional safe argv cases based on observed dynamic behavior.

    Parameters
    ----------
    dynamic_runs : dict
        The ``dynamic_runs.json`` content (must have ``runs`` key).
    max_new_cases : int
        Maximum number of new cases to generate.
    mutation_rounds : int
        Number of mutation rounds to apply.

    Returns
    -------
    (new_cases, diagnostics)
        new_cases: list of ``{"argv": [...], "stdin": "", "env": {}}``
        diagnostics: list of human-readable diagnostic strings
    """
    diagnostics: list[str] = []
    run_results = dynamic_runs.get("runs", [])

    if not run_results:
        diagnostics.append("No initial runs available for adaptive exploration.")
        return [], diagnostics

    # Analyze initial behavior
    observed_argvs: list[list[str]] = []
    exit_codes: set[int] = set()
    stdout_hashes: set[str] = set()
    stderr_hashes: set[str] = set()

    for r in run_results:
        observed_argvs.append(r.get("argv", []))
        ec = r.get("exit_code")
        if ec is not None:
            exit_codes.add(ec)
        stdout_hashes.add(r.get("stdout_sha256", ""))
        stderr_hashes.add(r.get("stderr_sha256", ""))

    argv_sensitive = len(set(repr(a) for a in observed_argvs)) > 1 and len(stdout_hashes) > 1
    argc_sensitive = len(set(len(a) for a in observed_argvs)) > 1
    stdout_varies = len(stdout_hashes) > 1
    stderr_varies = len(stderr_hashes) > 1
    exit_code_varies = len(exit_codes) > 1

    diagnostics.append(f"Initial runs: {len(run_results)}")
    diagnostics.append(f"argv_sensitive={argv_sensitive}")
    diagnostics.append(f"argc_sensitive={argc_sensitive}")
    diagnostics.append(f"stdout_varies={stdout_varies}")
    diagnostics.append(f"exit_code_varies={exit_code_varies}")

    # Collect candidate argv lists
    candidates: list[list[str]] = []
    seen_keys: set[str] = set()

    # Dedup helper
    def _add(argv: list[str]) -> None:
        key = repr(argv)
        if key not in seen_keys and _safe_argv(argv):
            seen_keys.add(key)
            candidates.append(argv)

    # Mark existing as seen
    for argv in observed_argvs:
        seen_keys.add(repr(argv))

    # Strategy 1: argc variants (always useful)
    for argv in _generate_argc_variants(observed_argvs):
        _add(argv)

    # Strategy 2: numeric variants (especially if exit code varies)
    if exit_code_varies or len(run_results) <= 2:
        for argv in _generate_numeric_variants():
            _add(argv)

    # Strategy 3: string mutations (if argv-sensitive or stdout varies)
    for _round in range(mutation_rounds):
        source = observed_argvs if _round == 0 else [c for c in candidates[-10:]]
        for argv in _generate_string_mutations(source):
            _add(argv)
            if len(candidates) >= max_new_cases:
                break
        if len(candidates) >= max_new_cases:
            break

    # Limit
    candidates = candidates[:max_new_cases]
    diagnostics.append(f"Generated {len(candidates)} adaptive cases")

    # Convert to case dicts
    new_cases = [
        {"argv": argv, "stdin": "", "env": {}}
        for argv in candidates
    ]

    return new_cases, diagnostics


# ── Influence report builder ─────────────────────────────────────────────────

def build_input_influence_report(
    initial_runs: list[dict],
    adaptive_runs: list[dict],
) -> dict:
    """
    Build ``input_influence_report.json`` summarizing input sensitivity.
    """
    all_runs = initial_runs + adaptive_runs

    # Aggregate
    argvs: list[list[str]] = []
    exit_codes: set[int] = set()
    stdout_hashes: set[str] = set()
    stderr_hashes: set[str] = set()
    crashes_observed = False
    timeouts_observed = False

    for r in all_runs:
        argvs.append(r.get("argv", []))
        ec = r.get("exit_code")
        if ec is not None:
            exit_codes.add(ec)
        stdout_hashes.add(r.get("stdout_sha256", ""))
        stderr_hashes.add(r.get("stderr_sha256", ""))
        if r.get("signal") is not None:
            crashes_observed = True
        if r.get("timed_out"):
            timeouts_observed = True

    # Argv grouping for sensitivity
    argv_groups: dict[str, list[dict]] = {}
    for r in all_runs:
        key = repr(r.get("argv", []))
        argv_groups.setdefault(key, []).append(r)

    argv_sensitive = False
    if len(argv_groups) >= 2:
        group_stdout = set()
        group_ec = set()
        for runs in argv_groups.values():
            group_stdout.add(runs[0].get("stdout_sha256", ""))
            ec = runs[0].get("exit_code")
            if ec is not None:
                group_ec.add(ec)
        argv_sensitive = len(group_stdout) > 1 or len(group_ec) > 1

    argc_sensitive = len(set(len(a) for a in argvs)) > 1
    stdout_varies = len(stdout_hashes) > 1
    stderr_varies = len(stderr_hashes) > 1
    exit_code_varies = len(exit_codes) > 1

    # Input dimension analysis
    input_dimensions: dict[str, str] = {}
    argc_values = set(len(a) for a in argvs)
    if len(argc_values) > 1:
        input_dimensions["argc"] = "varies"
    else:
        input_dimensions["argc"] = "constant"

    # Analyze first argument
    first_args = [a[0] for a in argvs if a]
    if first_args:
        lengths = set(len(s) for s in first_args)
        contents = set(first_args)
        if len(lengths) > 1:
            input_dimensions["argv_1_length"] = "possible influence"
        if len(contents) > 1:
            input_dimensions["argv_1_content"] = "possible influence"

    return {
        "schema_version": "input-influence-1.0",
        "phase": "11.6",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "initial_runs": len(initial_runs),
        "adaptive_runs": len(adaptive_runs),
        "total_runs": len(all_runs),
        "argv_sensitive": argv_sensitive,
        "argc_sensitive": argc_sensitive,
        "stdout_varies": stdout_varies,
        "stderr_varies": stderr_varies,
        "exit_code_varies": exit_code_varies,
        "crashes_observed": crashes_observed,
        "timeouts_observed": timeouts_observed,
        "input_dimensions": input_dimensions,
    }


# ── Exploration report ────────────────────────────────────────────────────────

def build_exploration_report(
    diagnostics: list[str],
    initial_run_count: int,
    adaptive_run_count: int,
    new_cases_count: int,
) -> dict:
    """Build ``dynamic_exploration_report.json``."""
    return {
        "schema_version": "dynamic-exploration-1.0",
        "phase": "11.6",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "initial_runs": initial_run_count,
        "adaptive_cases_generated": new_cases_count,
        "adaptive_runs_executed": adaptive_run_count,
        "diagnostics": diagnostics,
    }
