# -*- coding: utf-8 -*-
"""
Phase 9 — Static-Dynamic Behavior Fusion: core fusion logic.

Implements heuristics H1–H6 conservatively.
Every hypothesis cites its static and/or dynamic evidence.
No semantic equivalence is claimed.
No source names, structs, or fields are invented.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.behavior.loader import BehaviorArtifacts
from src.behavior.models import (
    OUTPUT_PRODUCING_CALLS,
    ARGV_RELATED_CALLS,
    STANDARD_UNCERTAINTIES,
    SCHEMA_BEHAVIOR_MODEL,
)


# ---------------------------------------------------------------------------
# Static artifact helpers
# ---------------------------------------------------------------------------

def _get_functions(arts: BehaviorArtifacts) -> list[dict]:
    """Return per-function records from source_reconstruction.json."""
    if arts.source_reconstruction is None:
        return []
    fns = arts.source_reconstruction.get("data", {}).get("functions", []) or arts.source_reconstruction.get("functions", [])
    if not isinstance(fns, list):
        return []
    return fns


def _function_calls(fn: dict) -> list[str]:
    """Return the list of call targets for a function."""
    calls = fn.get("calls", [])
    if isinstance(calls, list):
        return [str(c) for c in calls]
    return []


def _function_loops(fn: dict) -> int:
    return int(fn.get("loops", 0) or 0)


def _function_conditions(fn: dict) -> int:
    return int(fn.get("conditions", 0) or fn.get("conditionals", 0) or 0)


def _function_returns(fn: dict) -> int:
    return int(fn.get("returns", 0) or 0)


def _function_layout_candidates(fn: dict) -> list:
    return fn.get("layout_candidates", []) or []


def _main_has_argc_argv(fn: dict) -> bool:
    """Heuristic: does the main function signature include argc/argv?"""
    sig = fn.get("signature", "") or ""
    params = fn.get("params", []) or []
    # Check signature string
    if re.search(r"\bargc\b|\bargv\b", sig):
        return True
    # Check params list
    for p in params:
        if isinstance(p, str) and re.search(r"\bargc\b|\bargv\b", p):
            return True
        if isinstance(p, dict):
            name = str(p.get("name", "") or p.get("type", ""))
            if re.search(r"\bargc\b|\bargv\b", name):
                return True
    # Check recovered body if no explicit params
    body = fn.get("body", "") or fn.get("readable_c", "") or ""
    if re.search(r"\b(argc|argv)\b", body):
        return True
    return False


def _calls_any(fn: dict, target_set: frozenset[str]) -> bool:
    return bool(set(_function_calls(fn)) & target_set)


def _find_function_by_name(fns: list[dict], name: str) -> dict | None:
    for fn in fns:
        if fn.get("name") == name or fn.get("function") == name:
            return fn
    return None


# ---------------------------------------------------------------------------
# Dynamic artifact helpers
# ---------------------------------------------------------------------------

def _has_dynamic(arts: BehaviorArtifacts) -> bool:
    return arts.behavior_profile is not None


def _profile_summary(arts: BehaviorArtifacts) -> dict:
    if arts.behavior_profile is None:
        return {}
    return arts.behavior_profile.get("summary", {})


def _dynamic_runs_list(arts: BehaviorArtifacts) -> list[dict]:
    if arts.dynamic_runs is None:
        return []
    return arts.dynamic_runs.get("runs", [])


def _any_stdout_nonempty(arts: BehaviorArtifacts) -> bool:
    for r in _dynamic_runs_list(arts):
        if r.get("stdout", ""):
            return True
    return False


def _any_stderr_nonempty(arts: BehaviorArtifacts) -> bool:
    for r in _dynamic_runs_list(arts):
        if r.get("stderr", ""):
            return True
    return False


def _binary_path_from_dynamic(arts: BehaviorArtifacts) -> str:
    if arts.behavior_profile:
        return arts.behavior_profile.get("binary_path", "")
    if arts.dynamic_runs:
        return arts.dynamic_runs.get("binary_path", "")
    return ""


def _binary_sha256_from_dynamic(arts: BehaviorArtifacts) -> str:
    if arts.behavior_profile:
        return arts.behavior_profile.get("binary_sha256", "")
    if arts.dynamic_runs:
        return arts.dynamic_runs.get("binary_sha256", "")
    return ""


# ---------------------------------------------------------------------------
# H1 — argv sensitivity
# ---------------------------------------------------------------------------

def _h1_argv_sensitivity(main_fn: dict | None, arts: BehaviorArtifacts) -> dict | None:
    """
    H1: main likely depends on command-line input.
    Requires:
        behavior_profile.summary.argv_sensitive == True
        AND main has argc/argv OR calls strlen/strcmp/strncmp/getopt
    """
    if not _has_dynamic(arts):
        return None
    summary = _profile_summary(arts)
    if not summary.get("argv_sensitive"):
        return None
    if main_fn is None:
        return None
    has_argc_argv = _main_has_argc_argv(main_fn)
    calls_argv_fn = _calls_any(main_fn, ARGV_RELATED_CALLS)
    if not (has_argc_argv or calls_argv_fn):
        return None

    basis = ["behavior_profile.summary.argv_sensitive == true"]
    if has_argc_argv:
        basis.append("main signature includes argc/argv parameters")
    if calls_argv_fn:
        calls_found = list(set(_function_calls(main_fn)) & ARGV_RELATED_CALLS)
        basis.append(f"main calls argv-related functions: {calls_found}")

    return {
        "kind": "argv_dependency",
        "text": "Function main likely depends on command-line input.",
        "basis": basis,
        "confidence": "medium",
        "evidence_level": "static_dynamic_fused",
        "uncertainties": list(STANDARD_UNCERTAINTIES),
    }


# ---------------------------------------------------------------------------
# H2 — stdout output driver
# ---------------------------------------------------------------------------

def _h2_output_drivers(fns: list[dict], arts: BehaviorArtifacts) -> list[tuple[str, dict]]:
    """
    H2: functions calling output routines are likely output drivers.
    Requires: dynamic stdout non-empty AND static calls to printf/puts/write/etc.
    Returns list of (function_name, dynamic_link) tuples.
    """
    if not _has_dynamic(arts):
        return []
    if not _any_stdout_nonempty(arts):
        return []

    links: list[tuple[str, dict]] = []
    for fn in fns:
        fn_name = fn.get("name") or fn.get("function", "")
        if not _calls_any(fn, OUTPUT_PRODUCING_CALLS):
            continue
        output_calls = list(set(_function_calls(fn)) & OUTPUT_PRODUCING_CALLS)
        links.append((fn_name, {
            "kind": "likely_output_driver",
            "basis": (
                f"function calls output-producing routines {output_calls} "
                f"and dynamic stdout was non-empty"
            ),
            "confidence": "medium",
            "evidence_level": "static_dynamic_fused",
            "note": (
                "Attribution is approximate; "
                "exact output lines cannot be attributed without instrumentation."
            ),
        }))
    return links


# ---------------------------------------------------------------------------
# H3 — exit code behavior
# ---------------------------------------------------------------------------

def _h3_exit_code(main_fn: dict | None, arts: BehaviorArtifacts) -> dict | None:
    """
    H3: exit code depends on main's computed return value.
    Requires: multiple distinct exit codes AND main returns a value.
    """
    if not _has_dynamic(arts):
        return None
    summary = _profile_summary(arts)
    codes = summary.get("distinct_exit_codes", [])
    if len(set(codes)) <= 1:
        return None
    if main_fn is None:
        return None
    # Check if main returns a value (non-void return)
    returns_value = main_fn.get("returns_value", True)  # assume true for main
    return_type = main_fn.get("return_type", "int")
    if return_type in ("void",) and not returns_value:
        return None

    return {
        "kind": "exit_code_dependency",
        "text": (
            "Observed exit code likely depends on computed return value of main. "
            f"Observed distinct exit codes: {sorted(set(codes))}."
        ),
        "basis": [
            f"dynamic_runs shows distinct exit codes: {sorted(set(codes))}",
            "main has non-void return type",
        ],
        "confidence": "medium",
        "evidence_level": "static_dynamic_fused",
        "uncertainties": list(STANDARD_UNCERTAINTIES),
    }


# ---------------------------------------------------------------------------
# H4 — crash behavior
# ---------------------------------------------------------------------------

def _h4_crashes(arts: BehaviorArtifacts) -> dict | None:
    """H4: crash observed globally (no function attribution)."""
    if not _has_dynamic(arts):
        return None
    summary = _profile_summary(arts)
    if not summary.get("crashes_observed"):
        return None
    crash_runs = [
        r.get("name", "unnamed")
        for r in _dynamic_runs_list(arts)
        if r.get("signal") is not None
    ]
    return {
        "kind": "crash_observed",
        "description": "Process terminated by signal under tested inputs.",
        "evidence_runs": crash_runs,
        "confidence": "dynamic_observed",
        "evidence_level": "dynamic_observed",
        "note": "No function-level attribution without instrumentation.",
    }


# ---------------------------------------------------------------------------
# H5 — timeout behavior
# ---------------------------------------------------------------------------

def _h5_timeouts(fns: list[dict], arts: BehaviorArtifacts) -> dict | None:
    """H5: timeout observed globally; optionally linked to functions with loops."""
    if not _has_dynamic(arts):
        return None
    summary = _profile_summary(arts)
    if not summary.get("timeouts_observed"):
        return None
    timeout_runs = [
        r.get("name", "unnamed")
        for r in _dynamic_runs_list(arts)
        if r.get("timed_out")
    ]

    obs: dict = {
        "kind": "timeout_observed",
        "description": "Process timed out under tested inputs.",
        "evidence_runs": timeout_runs,
        "confidence": "dynamic_observed",
        "evidence_level": "dynamic_observed",
        "note": "This does not prove an infinite loop.",
    }

    # Speculative loop link (low confidence)
    loop_fns = [
        fn.get("name") or fn.get("function", "")
        for fn in fns
        if _function_loops(fn) > 0
    ]
    if loop_fns:
        obs["speculative_loop_link"] = {
            "text": (
                f"Timeout may relate to loop behavior in: {loop_fns}. "
                "This is speculative and not proven."
            ),
            "confidence": "low",
            "evidence_level": "hypothesis",
        }

    return obs


# ---------------------------------------------------------------------------
# H6 — static-only summaries
# ---------------------------------------------------------------------------

def _h6_static_summary(fn: dict) -> dict:
    """H6: static evidence summary for a single function."""
    return {
        "calls": _function_calls(fn),
        "loops": _function_loops(fn),
        "conditions": _function_conditions(fn),
        "returns": _function_returns(fn),
        "layout_candidates": _function_layout_candidates(fn),
        "evidence_level": "static_evidence",
    }


# ---------------------------------------------------------------------------
# Main fusion entry point
# ---------------------------------------------------------------------------

def build_behavior_model(
    arts: BehaviorArtifacts,
    binary_path: str = "",
) -> dict:
    """
    Build behavior_model.json content from loaded artifacts.

    Returns a dict ready for JSON serialisation.
    """
    fns = _get_functions(arts)
    main_fn = _find_function_by_name(fns, "main")

    # Resolved binary info (prefer dynamic source)
    bp = binary_path or _binary_path_from_dynamic(arts)
    sha = _binary_sha256_from_dynamic(arts)

    # ---- Run heuristics ----
    global_behavior: list[dict] = []

    h1 = _h1_argv_sensitivity(main_fn, arts)
    h4 = _h4_crashes(arts)
    h5 = _h5_timeouts(fns, arts)
    h2_links = _h2_output_drivers(fns, arts)

    if h4:
        global_behavior.append(h4)
    if h5:
        global_behavior.append(h5)

    # Index H2 links by function name
    h2_by_fn: dict[str, dict] = {fn_name: link for fn_name, link in h2_links}

    # ---- Per-function entries ----
    function_entries: list[dict] = []
    fns_with_static = 0
    fns_with_dynamic = 0
    hypotheses_total = 0
    hyp_static_only = 0
    hyp_dynamic_observed = 0
    hyp_fused = 0

    for fn in fns:
        fn_name = fn.get("name") or fn.get("function", "unnamed")
        static_summary = _h6_static_summary(fn)
        fns_with_static += 1

        dynamic_links: list[dict] = []
        hypotheses: list[dict] = []
        fn_has_dynamic = False

        # H2: output driver link
        if fn_name in h2_by_fn:
            dynamic_links.append(h2_by_fn[fn_name])
            fn_has_dynamic = True

        # H1 and H3 apply only to main
        if fn_name == "main":
            if h1:
                hypotheses.append(h1)
                hyp_fused += 1
                fn_has_dynamic = True
            h3 = _h3_exit_code(fn, arts)
            if h3:
                hypotheses.append(h3)
                hyp_fused += 1
                fn_has_dynamic = True

        # If no dynamic hypotheses, note static-only
        if not hypotheses and not dynamic_links:
            hyp_static_only += 1

        if fn_has_dynamic:
            fns_with_dynamic += 1

        hypotheses_total += len(hypotheses)

        uncertainties = list(STANDARD_UNCERTAINTIES) if fn_has_dynamic else [
            "no dynamic evidence available for this function"
        ]

        fn_entry: dict = {
            "function": fn_name,
            "entry_point": fn.get("entry_point", fn.get("address", "")),
            "static_summary": static_summary,
            "dynamic_links": dynamic_links,
            "hypotheses": hypotheses,
            "uncertainties": uncertainties,
        }
        function_entries.append(fn_entry)

    # ---- Input artifact manifest ----
    has_dynamic = _has_dynamic(arts)
    input_artifacts: dict[str, str] = {}
    if arts.source_reconstruction is not None:
        input_artifacts["source_reconstruction"] = "source_reconstruction.json"
    if arts.readability_report is not None:
        input_artifacts["readability_report"] = "readability_report.json"
    if arts.behavior_profile is not None:
        input_artifacts["behavior_profile"] = "behavior_profile.json"
    if arts.dynamic_runs is not None:
        input_artifacts["dynamic_runs"] = "dynamic_runs.json"
    if arts.phase4_semantics is not None:
        input_artifacts["phase4_semantics"] = "phase4_semantics.json"

    status = "ok" if not arts.warnings else "partial"
    if not arts.source_reconstruction and not arts.behavior_profile:
        status = "empty"

    return {
        "schema_version": SCHEMA_BEHAVIOR_MODEL,
        "phase": "9.0",
        "status": status,
        "binary_path": bp,
        "binary_sha256": sha,
        "input_artifacts": input_artifacts,
        "summary": {
            "functions_total": len(fns),
            "functions_with_static_evidence": fns_with_static,
            "functions_with_dynamic_evidence": fns_with_dynamic,
            "global_behavior_observations": len(global_behavior),
            "hypotheses_total": hypotheses_total,
            "hypotheses_static_only": hyp_static_only,
            "hypotheses_dynamic_observed": hyp_dynamic_observed,
            "hypotheses_static_dynamic_fused": hyp_fused,
        },
        "global_behavior": global_behavior,
        "functions": function_entries,
        "diagnostics": arts.warnings,
    }
