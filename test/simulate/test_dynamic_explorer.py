# -*- coding: utf-8 -*-
"""
Tests for src/dynamic/explorer.py
"""
import pytest

from src.dynamic.explorer import (
    generate_adaptive_inputs,
    build_input_influence_report,
    build_exploration_report,
    _safe_argv,
)


def _run(name: str, argv: list[str], exit_code: int = 0,
         stdout_sha256: str = "aaa", stderr_sha256: str = "bbb",
         **kw) -> dict:
    return {
        "name": name,
        "argv": argv,
        "exit_code": exit_code,
        "stdout_sha256": stdout_sha256,
        "stderr_sha256": stderr_sha256,
        "timed_out": False,
        "signal": None,
        **kw,
    }


class TestGenerateAdaptiveInputs:
    def test_single_run_generates_additional_cases(self):
        """If only one run exists, explorer should generate additional cases."""
        runs = {"runs": [_run("run0", [])]}
        cases, diag = generate_adaptive_inputs(runs)
        assert len(cases) > 0
        assert any("Generated" in d for d in diag)

    def test_stdout_varies_generates_mutations(self):
        """If stdout varies across argv, explorer should mutate strings."""
        runs = {"runs": [
            _run("run0", ["hello"], stdout_sha256="hash1"),
            _run("run1", ["world"], stdout_sha256="hash2"),
        ]}
        cases, diag = generate_adaptive_inputs(runs)
        assert len(cases) > 0
        # Should include string mutations
        argvs = [c["argv"] for c in cases]
        assert any(len(a) >= 1 for a in argvs)

    def test_exit_codes_vary_generates_numeric_variants(self):
        """If exit codes vary, explorer should generate numeric inputs."""
        runs = {"runs": [
            _run("run0", ["0"], exit_code=0, stdout_sha256="h1"),
            _run("run1", ["1"], exit_code=1, stdout_sha256="h2"),
        ]}
        cases, _ = generate_adaptive_inputs(runs)
        argvs = [c["argv"] for c in cases]
        # Should include numeric variants like ["-1"], ["127"], etc.
        flat_args = [a[0] for a in argvs if len(a) == 1]
        assert any(arg.lstrip("-").isdigit() for arg in flat_args if arg)

    def test_argc_matters_generates_different_argc(self):
        """If different argc produces different results, explorer generates argc variants."""
        runs = {"runs": [
            _run("run0", [], stdout_sha256="h1"),
            _run("run1", ["a"], stdout_sha256="h2"),
        ]}
        cases, _ = generate_adaptive_inputs(runs)
        argvs = [c["argv"] for c in cases]
        arg_counts = set(len(a) for a in argvs)
        assert len(arg_counts) > 1  # Multiple argc values

    def test_obeys_max_new_cases(self):
        runs = {"runs": [
            _run("run0", ["hello"], stdout_sha256="h1"),
            _run("run1", ["world"], stdout_sha256="h2"),
        ]}
        cases, _ = generate_adaptive_inputs(runs, max_new_cases=5)
        assert len(cases) <= 5

    def test_rejects_unsafe_null_byte_inputs(self):
        """All generated cases must not contain null bytes."""
        runs = {"runs": [
            _run("run0", ["test\x00bad"], stdout_sha256="h1"),
            _run("run1", ["good"], stdout_sha256="h2"),
        ]}
        cases, _ = generate_adaptive_inputs(runs)
        for case in cases:
            for arg in case["argv"]:
                assert "\x00" not in arg

    def test_reports_diagnostics(self):
        runs = {"runs": [_run("run0", [])]}
        _, diag = generate_adaptive_inputs(runs)
        assert len(diag) > 0
        assert any("Initial runs" in d for d in diag)

    def test_empty_runs_returns_empty(self):
        cases, diag = generate_adaptive_inputs({"runs": []})
        assert len(cases) == 0
        assert any("No initial runs" in d for d in diag)

    def test_all_cases_pass_safety(self):
        """Every generated case must pass _safe_argv."""
        runs = {"runs": [
            _run("r0", ["hello"], stdout_sha256="h1"),
            _run("r1", ["world"], stdout_sha256="h2"),
            _run("r2", ["123"], exit_code=1, stdout_sha256="h3"),
        ]}
        cases, _ = generate_adaptive_inputs(runs, max_new_cases=50)
        for case in cases:
            assert _safe_argv(case["argv"]), f"Unsafe argv: {case['argv']}"


class TestBuildInputInfluenceReport:
    def test_basic_report_structure(self):
        initial = [_run("r0", [], stdout_sha256="h1")]
        adaptive = [_run("r1", ["a"], stdout_sha256="h2")]
        report = build_input_influence_report(initial, adaptive)
        assert report["schema_version"] == "input-influence-1.0"
        assert report["initial_runs"] == 1
        assert report["adaptive_runs"] == 1
        assert "argv_sensitive" in report
        assert "stdout_varies" in report
        assert "input_dimensions" in report

    def test_detects_argv_sensitivity(self):
        initial = [
            _run("r0", ["a"], stdout_sha256="h1"),
            _run("r1", ["b"], stdout_sha256="h2"),
        ]
        report = build_input_influence_report(initial, [])
        assert report["argv_sensitive"] is True
        assert report["stdout_varies"] is True

    def test_detects_exit_code_variation(self):
        initial = [
            _run("r0", ["0"], exit_code=0),
            _run("r1", ["1"], exit_code=1),
        ]
        report = build_input_influence_report(initial, [])
        assert report["exit_code_varies"] is True


class TestBuildExplorationReport:
    def test_report_structure(self):
        report = build_exploration_report(
            diagnostics=["test"],
            initial_run_count=5,
            adaptive_run_count=10,
            new_cases_count=8,
        )
        assert report["schema_version"] == "dynamic-exploration-1.0"
        assert report["initial_runs"] == 5
        assert report["adaptive_runs_executed"] == 10
        assert report["adaptive_cases_generated"] == 8
        assert report["diagnostics"] == ["test"]
