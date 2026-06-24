# -*- coding: utf-8 -*-
"""
Tests for Phase 9 fusion: src/behavior/fusion.py and src/behavior/loader.py
"""

import json
import pytest
from pathlib import Path

from src.behavior.loader import BehaviorArtifacts, load_behavior_artifacts
from src.behavior.fusion import build_behavior_model
from src.behavior.models import FORBIDDEN_CERTAINTY_PHRASES


# ---------------------------------------------------------------------------
# Helpers: build minimal artifact sets
# ---------------------------------------------------------------------------

def _minimal_source_reconstruction(functions: list[dict] | None = None) -> dict:
    return {
        "schema_version": "source-reconstruction-1.0",
        "functions": functions or [],
    }


def _main_fn(**kwargs) -> dict:
    base = {
        "name": "main",
        "function": "main",
        "entry_point": "0x100003f44",
        "signature": "int main(int argc, char **argv)",
        "calls": ["printf", "strlen"],
        "loops": 1,
        "conditions": 3,
        "returns": 1,
        "returns_value": True,
        "return_type": "int",
        "layout_candidates": [],
        "params": ["argc", "argv"],
    }
    base.update(kwargs)
    return base


def _fn(name: str, **kwargs) -> dict:
    base = {
        "name": name,
        "function": name,
        "entry_point": "0xdeadbeef",
        "signature": f"int {name}()",
        "calls": [],
        "loops": 0,
        "conditions": 0,
        "returns": 1,
        "returns_value": True,
        "return_type": "int",
        "layout_candidates": [],
    }
    base.update(kwargs)
    return base


def _behavior_profile(argv_sensitive=False, distinct_exit_codes=None,
                      stdout_varies=False, crashes_observed=False,
                      timeouts_observed=False, run_matrix=None) -> dict:
    return {
        "schema_version": "behavior-profile-1.0",
        "phase": "8.0",
        "binary_path": "./t",
        "binary_sha256": "a" * 64,
        "summary": {
            "runs_total": 3,
            "distinct_exit_codes": distinct_exit_codes or [0],
            "stdout_varies": stdout_varies,
            "stderr_varies": False,
            "crashes_observed": crashes_observed,
            "timeouts_observed": timeouts_observed,
            "argv_sensitive": argv_sensitive,
            "stdin_sensitive": False,
        },
        "observations": [],
        "run_matrix": run_matrix or [],
    }


def _dynamic_runs(runs=None) -> dict:
    return {
        "schema_version": "dynamic-runs-1.0",
        "phase": "8.0",
        "binary_path": "./t",
        "binary_sha256": "a" * 64,
        "runs_total": len(runs or []),
        "runs": runs or [],
    }


def _run_result(name, stdout="", stderr="", exit_code=0, timed_out=False, signal=None):
    return {
        "name": name,
        "argv": [],
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "signal": signal,
        "stdout_sha256": "s" * 64,
        "stderr_sha256": "e" * 64,
        "stdin_sha256": "i" * 64,
        "stdout_bytes": len(stdout.encode()),
        "stderr_bytes": len(stderr.encode()),
        "duration_ms": 10,
        "status": "ok",
        "diagnostics": [],
        "stdout_truncated": False,
        "stderr_truncated": False,
        "timeout_s": 5.0,
    }


def _arts_with(
    source_reconstruction=None,
    behavior_profile=None,
    dynamic_runs=None,
) -> BehaviorArtifacts:
    arts = BehaviorArtifacts()
    arts.source_reconstruction = source_reconstruction
    arts.behavior_profile = behavior_profile
    arts.dynamic_runs = dynamic_runs
    return arts


# ---------------------------------------------------------------------------
# Recursive forbidden phrase scanner
# ---------------------------------------------------------------------------

def _find_forbidden_phrases(obj, path="root") -> list[str]:
    """Recursively scan all string values for forbidden certainty phrases."""
    findings = []
    if isinstance(obj, str):
        lower = obj.lower()
        for phrase in FORBIDDEN_CERTAINTY_PHRASES:
            if phrase.lower() in lower:
                findings.append(f"{path}: found forbidden phrase {phrase!r}")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            findings.extend(_find_forbidden_phrases(v, path=f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            findings.extend(_find_forbidden_phrases(v, path=f"{path}[{i}]"))
    return findings


# ---------------------------------------------------------------------------
# Schema and structure
# ---------------------------------------------------------------------------

def test_behavior_model_schema_version():
    arts = _arts_with()
    model = build_behavior_model(arts)
    assert model["schema_version"] == "behavior-model-1.0"


def test_behavior_model_required_keys():
    arts = _arts_with()
    model = build_behavior_model(arts)
    for key in ("schema_version", "phase", "status", "binary_path", "binary_sha256",
                "input_artifacts", "summary", "global_behavior", "functions", "diagnostics"):
        assert key in model, f"missing key: {key}"


def test_summary_required_fields():
    arts = _arts_with(
        source_reconstruction=_minimal_source_reconstruction([_main_fn()])
    )
    model = build_behavior_model(arts)
    s = model["summary"]
    for f in ("functions_total", "functions_with_static_evidence",
              "functions_with_dynamic_evidence", "global_behavior_observations",
              "hypotheses_total"):
        assert f in s, f"missing summary field: {f}"


# ---------------------------------------------------------------------------
# H1 — argv sensitivity
# ---------------------------------------------------------------------------

def test_h1_fires_when_argv_sensitive_and_argc_argv():
    arts = _arts_with(
        source_reconstruction=_minimal_source_reconstruction([_main_fn()]),
        behavior_profile=_behavior_profile(argv_sensitive=True),
        dynamic_runs=_dynamic_runs(),
    )
    model = build_behavior_model(arts)
    main_entry = next(f for f in model["functions"] if f["function"] == "main")
    h1_hyps = [h for h in main_entry["hypotheses"] if h["kind"] == "argv_dependency"]
    assert len(h1_hyps) == 1
    assert h1_hyps[0]["evidence_level"] == "static_dynamic_fused"
    assert h1_hyps[0]["confidence"] == "medium"


def test_h1_does_not_fire_when_argv_sensitive_false():
    arts = _arts_with(
        source_reconstruction=_minimal_source_reconstruction([_main_fn()]),
        behavior_profile=_behavior_profile(argv_sensitive=False),
        dynamic_runs=_dynamic_runs(),
    )
    model = build_behavior_model(arts)
    main_entry = next(f for f in model["functions"] if f["function"] == "main")
    h1_hyps = [h for h in main_entry["hypotheses"] if h["kind"] == "argv_dependency"]
    assert len(h1_hyps) == 0


def test_h1_does_not_fire_when_no_argc_argv_and_no_relevant_calls():
    fn = _main_fn(signature="int main()", params=[], calls=["malloc"])
    arts = _arts_with(
        source_reconstruction=_minimal_source_reconstruction([fn]),
        behavior_profile=_behavior_profile(argv_sensitive=True),
        dynamic_runs=_dynamic_runs(),
    )
    model = build_behavior_model(arts)
    main_entry = next(f for f in model["functions"] if f["function"] == "main")
    h1_hyps = [h for h in main_entry["hypotheses"] if h["kind"] == "argv_dependency"]
    assert len(h1_hyps) == 0


def test_h1_fires_when_argv_sensitive_and_calls_strlen():
    fn = _main_fn(signature="int main()", params=[], calls=["strlen", "printf"])
    arts = _arts_with(
        source_reconstruction=_minimal_source_reconstruction([fn]),
        behavior_profile=_behavior_profile(argv_sensitive=True),
        dynamic_runs=_dynamic_runs(),
    )
    model = build_behavior_model(arts)
    main_entry = next(f for f in model["functions"] if f["function"] == "main")
    h1_hyps = [h for h in main_entry["hypotheses"] if h["kind"] == "argv_dependency"]
    assert len(h1_hyps) == 1


# ---------------------------------------------------------------------------
# H2 — stdout output driver
# ---------------------------------------------------------------------------

def test_h2_links_printf_caller_when_stdout_nonempty():
    fn = _main_fn(calls=["printf", "strlen"])
    arts = _arts_with(
        source_reconstruction=_minimal_source_reconstruction([fn]),
        behavior_profile=_behavior_profile(),
        dynamic_runs=_dynamic_runs(runs=[
            _run_result("r1", stdout="hello\n"),
        ]),
    )
    model = build_behavior_model(arts)
    main_entry = next(f for f in model["functions"] if f["function"] == "main")
    h2_links = [l for l in main_entry["dynamic_links"] if l["kind"] == "likely_output_driver"]
    assert len(h2_links) == 1
    assert h2_links[0]["evidence_level"] == "static_dynamic_fused"


def test_h2_does_not_fire_when_stdout_empty():
    fn = _main_fn(calls=["printf"])
    arts = _arts_with(
        source_reconstruction=_minimal_source_reconstruction([fn]),
        behavior_profile=_behavior_profile(),
        dynamic_runs=_dynamic_runs(runs=[_run_result("r1", stdout="")]),
    )
    model = build_behavior_model(arts)
    main_entry = next(f for f in model["functions"] if f["function"] == "main")
    h2_links = [l for l in main_entry["dynamic_links"] if l["kind"] == "likely_output_driver"]
    assert len(h2_links) == 0


def test_h2_does_not_fire_for_non_output_callers():
    fn = _fn("sort_fn", calls=["malloc", "free"])
    arts = _arts_with(
        source_reconstruction=_minimal_source_reconstruction([fn]),
        behavior_profile=_behavior_profile(),
        dynamic_runs=_dynamic_runs(runs=[_run_result("r1", stdout="hello")]),
    )
    model = build_behavior_model(arts)
    sort_entry = next(f for f in model["functions"] if f["function"] == "sort_fn")
    h2_links = [l for l in sort_entry["dynamic_links"] if l["kind"] == "likely_output_driver"]
    assert len(h2_links) == 0


# ---------------------------------------------------------------------------
# H3 — exit code behavior
# ---------------------------------------------------------------------------

def test_h3_fires_when_multiple_exit_codes_and_main_returns():
    arts = _arts_with(
        source_reconstruction=_minimal_source_reconstruction([_main_fn()]),
        behavior_profile=_behavior_profile(distinct_exit_codes=[0, 42, 123]),
        dynamic_runs=_dynamic_runs(),
    )
    model = build_behavior_model(arts)
    main_entry = next(f for f in model["functions"] if f["function"] == "main")
    h3_hyps = [h for h in main_entry["hypotheses"] if h["kind"] == "exit_code_dependency"]
    assert len(h3_hyps) == 1
    assert "42" in h3_hyps[0]["text"] or "123" in h3_hyps[0]["text"]
    assert h3_hyps[0]["evidence_level"] == "static_dynamic_fused"


def test_h3_does_not_fire_when_single_exit_code():
    arts = _arts_with(
        source_reconstruction=_minimal_source_reconstruction([_main_fn()]),
        behavior_profile=_behavior_profile(distinct_exit_codes=[0]),
        dynamic_runs=_dynamic_runs(),
    )
    model = build_behavior_model(arts)
    main_entry = next(f for f in model["functions"] if f["function"] == "main")
    h3_hyps = [h for h in main_entry["hypotheses"] if h["kind"] == "exit_code_dependency"]
    assert len(h3_hyps) == 0


# ---------------------------------------------------------------------------
# H4 — crash behavior
# ---------------------------------------------------------------------------

def test_h4_global_entry_when_crash_observed():
    arts = _arts_with(
        source_reconstruction=_minimal_source_reconstruction([_main_fn()]),
        behavior_profile=_behavior_profile(crashes_observed=True),
        dynamic_runs=_dynamic_runs(runs=[_run_result("crash_run", signal=11)]),
    )
    model = build_behavior_model(arts)
    h4_entries = [g for g in model["global_behavior"] if g["kind"] == "crash_observed"]
    assert len(h4_entries) == 1
    assert h4_entries[0]["evidence_level"] == "dynamic_observed"
    assert "no function" in h4_entries[0].get("note", "").lower()


def test_h4_no_function_attribution():
    arts = _arts_with(
        behavior_profile=_behavior_profile(crashes_observed=True),
        dynamic_runs=_dynamic_runs(runs=[_run_result("r", signal=11)]),
    )
    model = build_behavior_model(arts)
    # H4 should ONLY appear in global_behavior, not in any function's hypotheses
    for fn_entry in model["functions"]:
        h4_hyps = [h for h in fn_entry.get("hypotheses", []) if h.get("kind") == "crash_observed"]
        assert len(h4_hyps) == 0


# ---------------------------------------------------------------------------
# H5 — timeout behavior
# ---------------------------------------------------------------------------

def test_h5_global_entry_when_timeout():
    fn = _fn("loop_fn", loops=3)
    arts = _arts_with(
        source_reconstruction=_minimal_source_reconstruction([fn]),
        behavior_profile=_behavior_profile(timeouts_observed=True),
        dynamic_runs=_dynamic_runs(runs=[_run_result("to", timed_out=True)]),
    )
    model = build_behavior_model(arts)
    h5_entries = [g for g in model["global_behavior"] if g["kind"] == "timeout_observed"]
    assert len(h5_entries) == 1
    # Should have a speculative loop link since loops exist
    assert "speculative_loop_link" in h5_entries[0]


def test_h5_low_confidence_loop_link():
    fn = _fn("loop_fn", loops=2)
    arts = _arts_with(
        source_reconstruction=_minimal_source_reconstruction([fn]),
        behavior_profile=_behavior_profile(timeouts_observed=True),
        dynamic_runs=_dynamic_runs(runs=[_run_result("to", timed_out=True)]),
    )
    model = build_behavior_model(arts)
    h5 = next(g for g in model["global_behavior"] if g["kind"] == "timeout_observed")
    loop_link = h5["speculative_loop_link"]
    assert loop_link["confidence"] == "low"
    assert loop_link["evidence_level"] == "hypothesis"


# ---------------------------------------------------------------------------
# H6 — static-only summaries
# ---------------------------------------------------------------------------

def test_h6_static_summary_for_all_functions():
    fns = [_main_fn(), _fn("helper"), _fn("walk", loops=2)]
    arts = _arts_with(
        source_reconstruction=_minimal_source_reconstruction(fns),
    )
    model = build_behavior_model(arts)
    assert len(model["functions"]) == 3
    for fn_entry in model["functions"]:
        ss = fn_entry.get("static_summary", {})
        assert ss.get("evidence_level") == "static_evidence"
        assert "calls" in ss
        assert "loops" in ss


def test_h6_loop_count_captured():
    fn = _fn("walk", loops=5)
    arts = _arts_with(source_reconstruction=_minimal_source_reconstruction([fn]))
    model = build_behavior_model(arts)
    fn_entry = model["functions"][0]
    assert fn_entry["static_summary"]["loops"] == 5


# ---------------------------------------------------------------------------
# Missing dynamic artifacts
# ---------------------------------------------------------------------------

def test_missing_dynamic_warning_not_error():
    arts = _arts_with(
        source_reconstruction=_minimal_source_reconstruction([_main_fn()]),
    )
    arts.missing_dynamic = ["behavior_profile.json", "dynamic_runs.json"]
    arts.warnings = ["Dynamic artifacts missing: ..."]
    model = build_behavior_model(arts)
    assert model["status"] in ("partial", "ok")
    # No H1/H2/H3 without dynamic data
    main_entry = next(f for f in model["functions"] if f["function"] == "main")
    assert len(main_entry["hypotheses"]) == 0


def test_missing_dynamic_require_raises(tmp_path):
    # No dynamic files exist
    with pytest.raises(RuntimeError, match="Dynamic artifacts missing"):
        load_behavior_artifacts(tmp_path, require_dynamic=True)


def test_fuse_produces_partial_when_dynamic_missing(tmp_path):
    # No dynamic artifacts, but static reconstruction present
    sr = {"schema_version": "source-reconstruction-1.0", "functions": []}
    (tmp_path / "source_reconstruction.json").write_text(json.dumps(sr))
    arts = load_behavior_artifacts(tmp_path, require_dynamic=False)
    model = build_behavior_model(arts)
    assert model["status"] in ("ok", "partial", "empty")
    assert len(model["diagnostics"]) > 0  # warnings recorded


# ---------------------------------------------------------------------------
# Forbidden phrase scan (regression)
# ---------------------------------------------------------------------------

def test_no_forbidden_phrases_in_behavior_model():
    """Recursive scan — no forbidden certainty phrase must appear anywhere."""
    arts = _arts_with(
        source_reconstruction=_minimal_source_reconstruction([_main_fn()]),
        behavior_profile=_behavior_profile(
            argv_sensitive=True,
            distinct_exit_codes=[0, 42],
            stdout_varies=True,
        ),
        dynamic_runs=_dynamic_runs(runs=[
            _run_result("r1", stdout="positive:42\n", exit_code=42),
            _run_result("r2", stdout="positive:0\n", exit_code=0),
        ]),
    )
    model = build_behavior_model(arts)
    findings = _find_forbidden_phrases(model)
    assert findings == [], f"Forbidden phrases found:\n" + "\n".join(findings)


def test_no_forbidden_phrases_static_only():
    """Static-only model must also be phrase-clean."""
    fns = [_main_fn(), _fn("helper"), _fn("walk", loops=3)]
    arts = _arts_with(source_reconstruction=_minimal_source_reconstruction(fns))
    model = build_behavior_model(arts)
    findings = _find_forbidden_phrases(model)
    assert findings == [], f"Forbidden phrases found:\n" + "\n".join(findings)


# ---------------------------------------------------------------------------
# Uncertainties
# ---------------------------------------------------------------------------

def test_fused_hypotheses_have_uncertainties():
    arts = _arts_with(
        source_reconstruction=_minimal_source_reconstruction([_main_fn()]),
        behavior_profile=_behavior_profile(argv_sensitive=True),
        dynamic_runs=_dynamic_runs(),
    )
    model = build_behavior_model(arts)
    main_entry = next(f for f in model["functions"] if f["function"] == "main")
    for hyp in main_entry["hypotheses"]:
        assert "uncertainties" in hyp
        assert len(hyp["uncertainties"]) > 0


def test_static_only_functions_have_uncertainty_note():
    fn = _fn("helper")
    arts = _arts_with(source_reconstruction=_minimal_source_reconstruction([fn]))
    model = build_behavior_model(arts)
    fn_entry = model["functions"][0]
    assert any(
        "no dynamic evidence" in u.lower()
        for u in fn_entry.get("uncertainties", [])
    )
