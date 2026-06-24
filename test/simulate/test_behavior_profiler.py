# -*- coding: utf-8 -*-
"""
Tests for src/dynamic/profiler.py
"""

import pytest
from src.dynamic.profiler import build_behavior_profile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BINARY = "./t"
_SHA256 = "a" * 64


def _run(name, argv=None, exit_code=0, stdout_sha="aaa", stderr_sha="bbb",
         stdout="", stderr="", timed_out=False, signal=None):
    return {
        "name": name,
        "argv": argv or [],
        "exit_code": exit_code,
        "timed_out": timed_out,
        "signal": signal,
        "stdout": stdout,
        "stderr": stderr,
        "stdout_sha256": stdout_sha,
        "stderr_sha256": stderr_sha,
        "stdout_bytes": len(stdout.encode()),
        "stderr_bytes": len(stderr.encode()),
        "stdin_sha256": "0" * 64,
        "duration_ms": 10,
        "status": "ok",
        "diagnostics": [],
        "stdout_truncated": False,
        "stderr_truncated": False,
    }


def _spec(*names):
    return {
        "schema_version": "dynamic-inputs-1.0",
        "runs": [{"name": n, "argv": [], "stdin": "", "env": {}} for n in names],
    }


# ---------------------------------------------------------------------------
# Schema and top-level structure
# ---------------------------------------------------------------------------

def test_schema_version():
    profile = build_behavior_profile(_BINARY, _SHA256, [_run("r")], _spec("r"))
    assert profile["schema_version"] == "behavior-profile-1.0"


def test_required_top_level_keys():
    profile = build_behavior_profile(_BINARY, _SHA256, [_run("r")], _spec("r"))
    for key in ("schema_version", "phase", "binary_path", "binary_sha256",
                "summary", "observations", "run_matrix"):
        assert key in profile, f"missing key: {key}"


def test_summary_required_fields():
    profile = build_behavior_profile(_BINARY, _SHA256, [_run("r")], _spec("r"))
    s = profile["summary"]
    for key in ("runs_total", "distinct_exit_codes", "stdout_varies",
                "stderr_varies", "crashes_observed", "timeouts_observed",
                "argv_sensitive", "stdin_sensitive"):
        assert key in s, f"missing summary field: {key}"


# ---------------------------------------------------------------------------
# argv sensitivity
# ---------------------------------------------------------------------------

def test_argv_sensitive_true_when_stdout_differs():
    runs = [
        _run("no_args",   argv=[],        stdout_sha="sha_A"),
        _run("short_arg", argv=["hello"], stdout_sha="sha_B"),
    ]
    profile = build_behavior_profile(_BINARY, _SHA256, runs, _spec("no_args", "short_arg"))
    assert profile["summary"]["argv_sensitive"] is True


def test_argv_sensitive_false_when_stdout_same():
    runs = [
        _run("r1", argv=[],        stdout_sha="same"),
        _run("r2", argv=["hello"], stdout_sha="same"),
    ]
    profile = build_behavior_profile(_BINARY, _SHA256, runs, _spec("r1", "r2"))
    assert profile["summary"]["argv_sensitive"] is False


def test_argv_sensitive_requires_two_argv_groups():
    # Only one distinct argv → cannot infer sensitivity
    runs = [_run("only_one", argv=[])]
    profile = build_behavior_profile(_BINARY, _SHA256, runs, _spec("only_one"))
    assert profile["summary"]["argv_sensitive"] is False


def test_argv_sensitive_true_on_exit_code_difference():
    runs = [
        _run("r1", argv=[],    exit_code=0),
        _run("r2", argv=["x"], exit_code=1),
    ]
    profile = build_behavior_profile(_BINARY, _SHA256, runs, _spec("r1", "r2"))
    assert profile["summary"]["argv_sensitive"] is True


# ---------------------------------------------------------------------------
# stdin sensitivity
# ---------------------------------------------------------------------------

def test_stdin_sensitive_true():
    r1 = _run("r1", stdout_sha="sha_A")
    r1["stdin_sha256"] = "stdin_hash_1"
    r2 = _run("r2", stdout_sha="sha_B")
    r2["stdin_sha256"] = "stdin_hash_2"
    profile = build_behavior_profile(_BINARY, _SHA256, [r1, r2], _spec("r1", "r2"))
    assert profile["summary"]["stdin_sensitive"] is True


def test_stdin_sensitive_false_when_same_stdout():
    r1 = _run("r1", stdout_sha="same")
    r1["stdin_sha256"] = "stdin_hash_1"
    r2 = _run("r2", stdout_sha="same")
    r2["stdin_sha256"] = "stdin_hash_2"
    profile = build_behavior_profile(_BINARY, _SHA256, [r1, r2], _spec("r1", "r2"))
    assert profile["summary"]["stdin_sensitive"] is False


# ---------------------------------------------------------------------------
# Crash / timeout
# ---------------------------------------------------------------------------

def test_crashes_observed():
    runs = [_run("crash_run", signal=11)]
    profile = build_behavior_profile(_BINARY, _SHA256, runs, _spec("crash_run"))
    assert profile["summary"]["crashes_observed"] is True


def test_timeouts_observed():
    runs = [_run("timeout_run", timed_out=True)]
    profile = build_behavior_profile(_BINARY, _SHA256, runs, _spec("timeout_run"))
    assert profile["summary"]["timeouts_observed"] is True


# ---------------------------------------------------------------------------
# distinct_exit_codes / stdout_varies / stderr_varies
# ---------------------------------------------------------------------------

def test_distinct_exit_codes():
    runs = [
        _run("r1", exit_code=0),
        _run("r2", exit_code=42),
        _run("r3", exit_code=0),
    ]
    profile = build_behavior_profile(_BINARY, _SHA256, runs, _spec("r1", "r2", "r3"))
    assert sorted(profile["summary"]["distinct_exit_codes"]) == [0, 42]


def test_stdout_varies_true():
    runs = [_run("r1", stdout_sha="a"), _run("r2", stdout_sha="b")]
    profile = build_behavior_profile(_BINARY, _SHA256, runs, _spec("r1", "r2"))
    assert profile["summary"]["stdout_varies"] is True


def test_stdout_varies_false():
    runs = [_run("r1", stdout_sha="same"), _run("r2", stdout_sha="same")]
    profile = build_behavior_profile(_BINARY, _SHA256, runs, _spec("r1", "r2"))
    assert profile["summary"]["stdout_varies"] is False


def test_stderr_varies_true():
    runs = [_run("r1", stderr_sha="x"), _run("r2", stderr_sha="y")]
    profile = build_behavior_profile(_BINARY, _SHA256, runs, _spec("r1", "r2"))
    assert profile["summary"]["stderr_varies"] is True


# ---------------------------------------------------------------------------
# Observations
# ---------------------------------------------------------------------------

def test_observation_argv_sensitive_stdout_present():
    runs = [
        _run("r1", argv=[],    stdout_sha="sha_A"),
        _run("r2", argv=["x"], stdout_sha="sha_B"),
    ]
    profile = build_behavior_profile(_BINARY, _SHA256, runs, _spec("r1", "r2"))
    kinds = {o["kind"] for o in profile["observations"]}
    assert "argv_sensitive_stdout" in kinds


def test_observation_crash_present():
    runs = [_run("crash", signal=11)]
    profile = build_behavior_profile(_BINARY, _SHA256, runs, _spec("crash"))
    kinds = {o["kind"] for o in profile["observations"]}
    assert "crash_observed" in kinds


def test_observation_timeout_present():
    runs = [_run("to", timed_out=True)]
    profile = build_behavior_profile(_BINARY, _SHA256, runs, _spec("to"))
    kinds = {o["kind"] for o in profile["observations"]}
    assert "timeout_observed" in kinds


def test_observation_deterministic_stdout_multiple_runs():
    runs = [_run("r1", stdout_sha="same"), _run("r2", stdout_sha="same")]
    profile = build_behavior_profile(_BINARY, _SHA256, runs, _spec("r1", "r2"))
    kinds = {o["kind"] for o in profile["observations"]}
    assert "deterministic_stdout" in kinds


def test_observation_nonzero_exit():
    runs = [_run("r1", exit_code=1)]
    profile = build_behavior_profile(_BINARY, _SHA256, runs, _spec("r1"))
    kinds = {o["kind"] for o in profile["observations"]}
    assert "nonzero_exit_observed" in kinds


# ---------------------------------------------------------------------------
# Run matrix
# ---------------------------------------------------------------------------

def test_run_matrix_one_row_per_run():
    runs = [_run("r1"), _run("r2"), _run("r3")]
    profile = build_behavior_profile(_BINARY, _SHA256, runs, _spec("r1", "r2", "r3"))
    assert len(profile["run_matrix"]) == 3


def test_run_matrix_fields():
    runs = [_run("r1", exit_code=5, stdout_sha="sh1")]
    profile = build_behavior_profile(_BINARY, _SHA256, runs, _spec("r1"))
    row = profile["run_matrix"][0]
    for field in ("name", "argv", "exit_code", "timed_out", "stdout_sha256",
                  "stderr_sha256", "stdout_bytes", "stderr_bytes", "duration_ms"):
        assert field in row, f"missing run_matrix field: {field}"
    assert row["exit_code"] == 5
    assert row["stdout_sha256"] == "sh1"
