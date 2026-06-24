# -*- coding: utf-8 -*-
"""
Tests for Phase 9 CLI: src/behavior/cli.py
"""

import json
import textwrap
import sys
from pathlib import Path
import pytest

from src.behavior.cli import run_fuse_behavior_cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def _source_reconstruction(fns=None) -> dict:
    return {
        "schema_version": "source-reconstruction-1.0",
        "functions": fns or [
            {
                "name": "main",
                "function": "main",
                "entry_point": "0x1000",
                "signature": "int main(int argc, char **argv)",
                "calls": ["printf", "strlen"],
                "loops": 1,
                "conditions": 2,
                "returns": 1,
                "returns_value": True,
                "return_type": "int",
                "layout_candidates": [],
                "params": ["argc", "argv"],
            }
        ],
    }


def _behavior_profile(argv_sensitive=False, distinct_exit_codes=None) -> dict:
    return {
        "schema_version": "behavior-profile-1.0",
        "phase": "8.0",
        "binary_path": "./t",
        "binary_sha256": "a" * 64,
        "summary": {
            "runs_total": 2,
            "distinct_exit_codes": distinct_exit_codes or [0],
            "stdout_varies": False,
            "stderr_varies": False,
            "crashes_observed": False,
            "timeouts_observed": False,
            "argv_sensitive": argv_sensitive,
            "stdin_sensitive": False,
        },
        "observations": [],
        "run_matrix": [],
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


def _run_result(name, stdout="", exit_code=0):
    return {
        "name": name, "argv": [], "stdout": stdout, "stderr": "",
        "exit_code": exit_code, "timed_out": False, "signal": None,
        "stdout_sha256": "s" * 64, "stderr_sha256": "e" * 64,
        "stdin_sha256": "i" * 64,
        "stdout_bytes": len(stdout.encode()), "stderr_bytes": 0,
        "duration_ms": 10, "status": "ok", "diagnostics": [],
        "stdout_truncated": False, "stderr_truncated": False, "timeout_s": 5.0,
    }


# ---------------------------------------------------------------------------
# Writes behavior_model.json
# ---------------------------------------------------------------------------

def test_writes_behavior_model(tmp_path):
    _write_json(tmp_path / "source_reconstruction.json", _source_reconstruction())
    _write_json(tmp_path / "behavior_profile.json", _behavior_profile())
    _write_json(tmp_path / "dynamic_runs.json", _dynamic_runs())

    code = run_fuse_behavior_cli(["--out-dir", str(tmp_path)])
    assert (tmp_path / "behavior_model.json").exists()


def test_writes_behavior_fusion_report(tmp_path):
    _write_json(tmp_path / "source_reconstruction.json", _source_reconstruction())
    run_fuse_behavior_cli(["--out-dir", str(tmp_path)])
    assert (tmp_path / "behavior_fusion_report.json").exists()


def test_behavior_model_schema(tmp_path):
    _write_json(tmp_path / "source_reconstruction.json", _source_reconstruction())
    _write_json(tmp_path / "behavior_profile.json", _behavior_profile())
    _write_json(tmp_path / "dynamic_runs.json", _dynamic_runs())

    run_fuse_behavior_cli(["--out-dir", str(tmp_path)])
    model = json.loads((tmp_path / "behavior_model.json").read_text())
    assert model["schema_version"] == "behavior-model-1.0"
    assert "functions" in model
    assert "summary" in model


def test_fusion_report_schema(tmp_path):
    _write_json(tmp_path / "source_reconstruction.json", _source_reconstruction())
    run_fuse_behavior_cli(["--out-dir", str(tmp_path)])
    report = json.loads((tmp_path / "behavior_fusion_report.json").read_text())
    assert report["schema_version"] == "behavior-fusion-report-1.0"
    assert "status" in report


# ---------------------------------------------------------------------------
# --json flag
# ---------------------------------------------------------------------------

def test_json_flag_prints_summary(tmp_path, capsys):
    _write_json(tmp_path / "source_reconstruction.json", _source_reconstruction())
    _write_json(tmp_path / "behavior_profile.json", _behavior_profile())
    _write_json(tmp_path / "dynamic_runs.json", _dynamic_runs())

    code = run_fuse_behavior_cli(["--out-dir", str(tmp_path), "--json"])
    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert "status" in summary
    assert "functions_total" in summary
    assert "artifacts" in summary


# ---------------------------------------------------------------------------
# No dynamic artifacts → partial, warning, no crash
# ---------------------------------------------------------------------------

def test_no_dynamic_artifacts_produces_partial(tmp_path):
    _write_json(tmp_path / "source_reconstruction.json", _source_reconstruction())
    # No behavior_profile.json, no dynamic_runs.json
    code = run_fuse_behavior_cli(["--out-dir", str(tmp_path)])
    model = json.loads((tmp_path / "behavior_model.json").read_text())
    # Must not crash; diagnostics should mention missing dynamic
    assert len(model["diagnostics"]) > 0


def test_no_dynamic_returns_nonzero_exit_with_require_dynamic(tmp_path):
    _write_json(tmp_path / "source_reconstruction.json", _source_reconstruction())
    code = run_fuse_behavior_cli([
        "--out-dir", str(tmp_path),
        "--require-dynamic",
    ])
    assert code == 1


# ---------------------------------------------------------------------------
# --require-readable fails if file absent
# ---------------------------------------------------------------------------

def test_require_readable_fails_when_absent(tmp_path):
    code = run_fuse_behavior_cli([
        "--out-dir", str(tmp_path),
        "--require-readable",
    ])
    assert code == 1


def test_require_readable_passes_when_present(tmp_path):
    (tmp_path / "recovered_readable.c").write_text("/* readable */\n")
    _write_json(tmp_path / "source_reconstruction.json", _source_reconstruction())
    code = run_fuse_behavior_cli([
        "--out-dir", str(tmp_path),
        "--require-readable",
    ])
    # Must not fail on --require-readable (file exists)
    assert (tmp_path / "behavior_model.json").exists()


# ---------------------------------------------------------------------------
# fuse-behavior does NOT execute the binary
# ---------------------------------------------------------------------------

def test_fuse_behavior_does_not_execute_binary(tmp_path, monkeypatch):
    """fuse-behavior must never call subprocess.Popen or subprocess.run."""
    import subprocess

    def _fail(*args, **kwargs):
        raise AssertionError(
            "fuse-behavior MUST NOT call subprocess! "
            f"Called with: {args}, {kwargs}"
        )

    monkeypatch.setattr(subprocess, "Popen", _fail)
    monkeypatch.setattr(subprocess, "run", _fail)

    _write_json(tmp_path / "source_reconstruction.json", _source_reconstruction())
    code = run_fuse_behavior_cli(["--out-dir", str(tmp_path)])
    # If no AssertionError was raised, subprocess was not called — test passes


# ---------------------------------------------------------------------------
# Forbidden phrase check on written files
# ---------------------------------------------------------------------------

def test_no_forbidden_phrases_in_written_behavior_model(tmp_path):
    _write_json(tmp_path / "source_reconstruction.json", _source_reconstruction())
    _write_json(tmp_path / "behavior_profile.json", _behavior_profile(
        argv_sensitive=True, distinct_exit_codes=[0, 42]
    ))
    _write_json(tmp_path / "dynamic_runs.json", _dynamic_runs(runs=[
        _run_result("r1", stdout="positive:42\n", exit_code=42),
        _run_result("r2", stdout="positive:0\n", exit_code=0),
    ]))

    run_fuse_behavior_cli(["--out-dir", str(tmp_path)])
    model = json.loads((tmp_path / "behavior_model.json").read_text())

    from src.behavior.models import FORBIDDEN_CERTAINTY_PHRASES
    findings = []

    def _scan(obj, path="root"):
        if isinstance(obj, str):
            for phrase in FORBIDDEN_CERTAINTY_PHRASES:
                if phrase.lower() in obj.lower():
                    findings.append(f"{path}: {phrase!r}")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                _scan(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _scan(v, f"{path}[{i}]")

    _scan(model)
    assert findings == [], f"Forbidden phrases found:\n" + "\n".join(findings)
