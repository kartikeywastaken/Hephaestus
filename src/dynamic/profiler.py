# -*- coding: utf-8 -*-
"""
Phase 8 — Dynamic Behavior Capture: behavior profiler.

Summarizes raw run results into behavior_profile.json.

Rules:
    - argv_sensitive requires >= 2 different argv groups with different stdout or exit code
    - stdin_sensitive requires >= 2 different stdin groups with different stdout
    - Do not over-infer from one run
    - Observations are conservative; prefer "not observed" over speculation
"""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# Grouping helpers
# ---------------------------------------------------------------------------

def _argv_key(result: dict) -> str:
    """Canonical string key for a run's argv."""
    argv = result.get("argv", [])
    return repr(argv)


def _stdin_key(result: dict) -> str:
    """Canonical string key for a run's stdin (by sha256)."""
    return result.get("stdin_sha256", "")


# ---------------------------------------------------------------------------
# Core profiler
# ---------------------------------------------------------------------------

def build_behavior_profile(
    binary_path: str | Path,
    binary_sha256: str,
    run_results: list[dict],
    input_spec: dict,
) -> dict:
    """
    Build behavior_profile.json content from raw run results.

    Returns a dict ready to be JSON-serialised.
    """
    total = len(run_results)

    # ---- Aggregate fields ----
    exit_codes: list[int] = []
    crashes: list[str] = []
    timeouts: list[str] = []
    stdout_sha256s: list[str] = []
    stderr_sha256s: list[str] = []

    for r in run_results:
        ec = r.get("exit_code")
        if ec is not None:
            exit_codes.append(ec)

        if r.get("signal") is not None:
            crashes.append(r.get("name", "unnamed"))

        if r.get("timed_out"):
            timeouts.append(r.get("name", "unnamed"))

        stdout_sha256s.append(r.get("stdout_sha256", ""))
        stderr_sha256s.append(r.get("stderr_sha256", ""))

    distinct_exit_codes: list[int] = sorted(set(exit_codes))
    crashes_observed = len(crashes) > 0
    timeouts_observed = len(timeouts) > 0
    stdout_varies = len(set(stdout_sha256s)) > 1
    stderr_varies = len(set(stderr_sha256s)) > 1

    # ---- argv sensitivity ----
    # Group runs by argv. Requires >= 2 different argv groups.
    argv_groups: dict[str, list[dict]] = {}
    for r in run_results:
        key = _argv_key(r)
        argv_groups.setdefault(key, []).append(r)

    argv_sensitive = False
    if len(argv_groups) >= 2:
        # Check if stdout sha256 or exit code differs across argv groups
        group_stdout_hashes = set()
        group_exit_codes = set()
        for group_runs in argv_groups.values():
            # Use first run in each group as representative
            rep = group_runs[0]
            group_stdout_hashes.add(rep.get("stdout_sha256", ""))
            ec = rep.get("exit_code")
            if ec is not None:
                group_exit_codes.add(ec)
        if len(group_stdout_hashes) > 1 or len(group_exit_codes) > 1:
            argv_sensitive = True

    # ---- stdin sensitivity ----
    stdin_groups: dict[str, list[dict]] = {}
    for r in run_results:
        key = _stdin_key(r)
        stdin_groups.setdefault(key, []).append(r)

    stdin_sensitive = False
    if len(stdin_groups) >= 2:
        group_stdout_hashes2 = set()
        for group_runs in stdin_groups.values():
            rep = group_runs[0]
            group_stdout_hashes2.add(rep.get("stdout_sha256", ""))
        if len(group_stdout_hashes2) > 1:
            stdin_sensitive = True

    # ---- Deterministic stdout ----
    # True only if all runs with same argv+stdin produce identical stdout sha256
    deterministic_stdout = not stdout_varies

    # ---- Observations ----
    observations: list[dict] = []

    if argv_sensitive:
        # Determine which observation kinds to emit
        argv_stdout_differs = False
        argv_exit_differs = False
        if len(argv_groups) >= 2:
            stdout_set = set()
            ec_set = set()
            for group_runs in argv_groups.values():
                rep = group_runs[0]
                stdout_set.add(rep.get("stdout_sha256", ""))
                ec = rep.get("exit_code")
                if ec is not None:
                    ec_set.add(ec)
            argv_stdout_differs = len(stdout_set) > 1
            argv_exit_differs = len(ec_set) > 1

        evidence_runs = list(argv_groups.keys())
        # Use the run names instead of argv keys for evidence_runs
        argv_group_names: list[str] = []
        for group_runs in argv_groups.values():
            argv_group_names.append(group_runs[0].get("name", "unnamed"))

        if argv_stdout_differs:
            observations.append({
                "kind": "argv_sensitive_stdout",
                "description": "stdout changed across argv variants",
                "evidence_runs": argv_group_names,
                "confidence": "dynamic_observed",
            })
        if argv_exit_differs:
            observations.append({
                "kind": "argv_sensitive_exit_code",
                "description": "exit code changed across argv variants",
                "evidence_runs": argv_group_names,
                "confidence": "dynamic_observed",
            })
    else:
        if len(argv_groups) >= 2:
            observations.append({
                "kind": "argv_insensitive",
                "description": "stdout and exit code identical across argv variants",
                "evidence_runs": [r.get("name", "unnamed") for r in run_results],
                "confidence": "dynamic_observed",
            })

    if stdin_sensitive:
        stdin_group_names = [
            group_runs[0].get("name", "unnamed")
            for group_runs in stdin_groups.values()
        ]
        observations.append({
            "kind": "stdin_sensitive_stdout",
            "description": "stdout changed across stdin variants",
            "evidence_runs": stdin_group_names,
            "confidence": "dynamic_observed",
        })

    stderr_runs = [r.get("name", "unnamed") for r in run_results if r.get("stderr", "")]
    if stderr_runs:
        observations.append({
            "kind": "stderr_output_observed",
            "description": "stderr was non-empty for some runs",
            "evidence_runs": stderr_runs,
            "confidence": "dynamic_observed",
        })

    nonzero_runs = [
        r.get("name", "unnamed")
        for r in run_results
        if r.get("exit_code") not in (None, 0)
    ]
    if nonzero_runs:
        observations.append({
            "kind": "nonzero_exit_observed",
            "description": "nonzero exit code observed",
            "evidence_runs": nonzero_runs,
            "confidence": "dynamic_observed",
        })

    if crashes:
        observations.append({
            "kind": "crash_observed",
            "description": "process terminated by signal",
            "evidence_runs": crashes,
            "confidence": "dynamic_observed",
        })

    if timeouts:
        observations.append({
            "kind": "timeout_observed",
            "description": "process timed out",
            "evidence_runs": timeouts,
            "confidence": "dynamic_observed",
        })

    if deterministic_stdout and total > 1:
        observations.append({
            "kind": "deterministic_stdout",
            "description": "stdout was identical across all runs",
            "evidence_runs": [r.get("name", "unnamed") for r in run_results],
            "confidence": "dynamic_observed",
        })

    # ---- Run matrix ----
    run_matrix = []
    for r in run_results:
        run_matrix.append({
            "name": r.get("name", "unnamed"),
            "argv": r.get("argv", []),
            "exit_code": r.get("exit_code"),
            "timed_out": r.get("timed_out", False),
            "stdout_sha256": r.get("stdout_sha256", ""),
            "stderr_sha256": r.get("stderr_sha256", ""),
            "stdout_bytes": r.get("stdout_bytes", 0),
            "stderr_bytes": r.get("stderr_bytes", 0),
            "duration_ms": r.get("duration_ms", 0),
        })

    return {
        "schema_version": "behavior-profile-1.0",
        "phase": "8.0",
        "binary_path": str(binary_path),
        "binary_sha256": binary_sha256,
        "summary": {
            "runs_total": total,
            "distinct_exit_codes": distinct_exit_codes,
            "stdout_varies": stdout_varies,
            "stderr_varies": stderr_varies,
            "crashes_observed": crashes_observed,
            "timeouts_observed": timeouts_observed,
            "argv_sensitive": argv_sensitive,
            "stdin_sensitive": stdin_sensitive,
        },
        "observations": observations,
        "run_matrix": run_matrix,
    }
