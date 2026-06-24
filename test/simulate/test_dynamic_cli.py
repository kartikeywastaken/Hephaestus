# -*- coding: utf-8 -*-
"""
Tests for Phase 8 CLI: src/dynamic/cli.py

Uses tiny Python fixture scripts as cross-platform "binaries".
Does not require the actual ARM64 target binary.
"""

import json
import sys
import textwrap
from pathlib import Path

import pytest

from src.dynamic.cli import run_dynamic_cli


# ---------------------------------------------------------------------------
# Fixture script helpers
# ---------------------------------------------------------------------------

def _make_binary(tmp_path: Path, name: str, code: str) -> Path:
    script = tmp_path / name
    script.write_text(
        f"#!/usr/bin/env python3\n{textwrap.dedent(code)}", encoding="utf-8"
    )
    script.chmod(0o755)
    return script


def _inputs_file(tmp_path: Path, runs: list) -> Path:
    p = tmp_path / "inputs.json"
    p.write_text(
        json.dumps({"schema_version": "dynamic-inputs-1.0", "runs": runs}),
        encoding="utf-8",
    )
    return p


# ---------------------------------------------------------------------------
# All four Phase 8 artifacts are written
# ---------------------------------------------------------------------------

def test_writes_all_artifacts(tmp_path):
    binary = _make_binary(tmp_path, "ok", "print('hello')")
    out_dir = tmp_path / "out"

    code = run_dynamic_cli([
        str(binary),
        "--out-dir", str(out_dir),
    ])
    assert code == 0

    for artifact in (
        "dynamic_inputs.resolved.json",
        "dynamic_runs.json",
        "behavior_profile.json",
        "dynamic_report.json",
    ):
        assert (out_dir / artifact).exists(), f"missing: {artifact}"


def test_dynamic_runs_has_correct_schema(tmp_path):
    binary = _make_binary(tmp_path, "ok2", "pass")
    out_dir = tmp_path / "out"
    run_dynamic_cli([str(binary), "--out-dir", str(out_dir)])
    data = json.loads((out_dir / "dynamic_runs.json").read_text())
    assert data["schema_version"] == "dynamic-runs-1.0"
    assert "runs" in data
    assert data["runs_total"] >= 1


def test_behavior_profile_has_correct_schema(tmp_path):
    binary = _make_binary(tmp_path, "ok3", "pass")
    out_dir = tmp_path / "out"
    run_dynamic_cli([str(binary), "--out-dir", str(out_dir)])
    data = json.loads((out_dir / "behavior_profile.json").read_text())
    assert data["schema_version"] == "behavior-profile-1.0"
    assert "summary" in data


# ---------------------------------------------------------------------------
# --json flag: compact JSON summary to stdout
# ---------------------------------------------------------------------------

def test_json_flag_prints_summary(tmp_path, capsys):
    binary = _make_binary(tmp_path, "json_ok", "print('hi')")
    out_dir = tmp_path / "out"
    code = run_dynamic_cli([str(binary), "--out-dir", str(out_dir), "--json"])
    assert code == 0
    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert "status" in summary
    assert "runs_total" in summary
    assert "artifacts" in summary


# ---------------------------------------------------------------------------
# Missing binary → clean error, nonzero exit
# ---------------------------------------------------------------------------

def test_missing_binary_returns_nonzero(tmp_path):
    out_dir = tmp_path / "out"
    code = run_dynamic_cli([
        "/absolutely/nonexistent/binary_hephaestus_test",
        "--out-dir", str(out_dir),
    ])
    assert code != 0


# ---------------------------------------------------------------------------
# Default inputs (no --inputs flag)
# ---------------------------------------------------------------------------

def test_default_inputs_used_when_no_flag(tmp_path):
    binary = _make_binary(tmp_path, "default_in", "pass")
    out_dir = tmp_path / "out"
    run_dynamic_cli([str(binary), "--out-dir", str(out_dir)])

    resolved = json.loads((out_dir / "dynamic_inputs.resolved.json").read_text())
    assert resolved.get("using_default_inputs") is True

    report = json.loads((out_dir / "dynamic_report.json").read_text())
    assert report.get("using_default_inputs") is True


def test_explicit_inputs_not_default(tmp_path):
    binary = _make_binary(tmp_path, "explicit_in", "pass")
    inputs = _inputs_file(tmp_path, [
        {"name": "custom", "argv": [], "stdin": "", "env": {}},
    ])
    out_dir = tmp_path / "out"
    run_dynamic_cli([str(binary), "--out-dir", str(out_dir), "--inputs", str(inputs)])

    resolved = json.loads((out_dir / "dynamic_inputs.resolved.json").read_text())
    assert resolved.get("using_default_inputs") is False


# ---------------------------------------------------------------------------
# --timeout-s enforces timeout
# ---------------------------------------------------------------------------

def test_timeout_enforced(tmp_path):
    binary = _make_binary(tmp_path, "slow", "import time; time.sleep(60)")
    out_dir = tmp_path / "out"
    code = run_dynamic_cli([
        str(binary),
        "--out-dir", str(out_dir),
        "--timeout-s", "0.5",
    ])
    # exit code may be 0 or 1 depending on allow-nonzero, but artifact must exist
    runs_data = json.loads((out_dir / "dynamic_runs.json").read_text())
    assert runs_data["runs_timed_out"] >= 1
    assert runs_data["runs"][0]["timed_out"] is True


# ---------------------------------------------------------------------------
# read-only guard: recovered.c and recovered_readable.c not modified
# ---------------------------------------------------------------------------

def test_does_not_modify_recovered_c(tmp_path):
    binary = _make_binary(tmp_path, "safe_run", "pass")
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True)

    # Plant a fake recovered.c
    recovered = out_dir / "recovered.c"
    recovered.write_text("/* original */\n", encoding="utf-8")
    import hashlib
    original_hash = hashlib.sha256(recovered.read_bytes()).hexdigest()

    run_dynamic_cli([str(binary), "--out-dir", str(out_dir)])

    assert hashlib.sha256(recovered.read_bytes()).hexdigest() == original_hash, \
        "recovered.c was modified!"


def test_does_not_modify_recovered_readable_c(tmp_path):
    binary = _make_binary(tmp_path, "safe_run2", "pass")
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True)

    readable = out_dir / "recovered_readable.c"
    readable.write_text("/* readable original */\n", encoding="utf-8")
    import hashlib
    original_hash = hashlib.sha256(readable.read_bytes()).hexdigest()

    run_dynamic_cli([str(binary), "--out-dir", str(out_dir)])

    assert hashlib.sha256(readable.read_bytes()).hexdigest() == original_hash, \
        "recovered_readable.c was modified!"


# ---------------------------------------------------------------------------
# Multiple runs with --inputs
# ---------------------------------------------------------------------------

def test_multiple_runs_all_captured(tmp_path):
    binary = _make_binary(tmp_path, "multi", """
import sys
print(f"argv_count={len(sys.argv)-1}")
""")
    inputs = _inputs_file(tmp_path, [
        {"name": "zero",  "argv": [],         "stdin": "", "env": {}},
        {"name": "one",   "argv": ["a"],       "stdin": "", "env": {}},
        {"name": "two",   "argv": ["a", "b"],  "stdin": "", "env": {}},
    ])
    out_dir = tmp_path / "out"
    code = run_dynamic_cli([str(binary), "--out-dir", str(out_dir), "--inputs", str(inputs)])
    assert code == 0

    runs_data = json.loads((out_dir / "dynamic_runs.json").read_text())
    assert runs_data["runs_total"] == 3
    assert len(runs_data["runs"]) == 3
