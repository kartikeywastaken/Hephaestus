# -*- coding: utf-8 -*-
"""
Tests for src/dynamic/input_generator.py
"""
import json
import pytest
import tempfile
from pathlib import Path

from src.dynamic.input_generator import (
    generate_default_input_cases,
    merge_and_deduplicate,
    build_input_spec_from_cases,
    write_generated_inputs_artifact,
)
from src.dynamic.safety import validate_argv


class TestGenerateDefaultInputCases:
    def test_generates_empty_argv_case(self):
        cases = generate_default_input_cases()
        argvs = [c["argv"] for c in cases]
        assert [] in argvs

    def test_generates_empty_string_case(self):
        cases = generate_default_input_cases()
        argvs = [c["argv"] for c in cases]
        assert [""] in argvs

    def test_generates_one_arg_and_two_arg_cases(self):
        cases = generate_default_input_cases()
        argvs = [c["argv"] for c in cases]
        # At least one single-arg case
        assert any(len(a) == 1 for a in argvs)
        # At least one two-arg case
        assert any(len(a) == 2 for a in argvs)

    def test_all_generated_cases_pass_validate_argv(self):
        cases = generate_default_input_cases()
        for case in cases:
            # Should not raise
            result = validate_argv(case["argv"])
            assert isinstance(result, list)

    def test_no_shell_strings_requiring_shell_true(self):
        """Generated cases should not contain shell-dangerous metacharacters
        that would require shell=True."""
        # These chars would require shell=True: |, &, ;, $, `, (, )
        shell_dangerous = set("|&;$`()")
        cases = generate_default_input_cases()
        for case in cases:
            for arg in case["argv"]:
                for ch in shell_dangerous:
                    assert ch not in arg, f"Shell char '{ch}' in argv arg: {arg!r}"

    def test_respects_max_case_count(self):
        cases = generate_default_input_cases(max_cases=3)
        assert len(cases) <= 3

    def test_cases_have_stdin_and_env(self):
        cases = generate_default_input_cases()
        for case in cases:
            assert "stdin" in case
            assert "env" in case
            assert isinstance(case["env"], dict)


class TestMergeAndDeduplicate:
    def test_deduplicates_identical_argvs(self):
        user = [{"argv": ["hello"]}, {"argv": ["world"]}]
        gen = [{"argv": ["hello"]}, {"argv": ["test"]}]
        merged = merge_and_deduplicate(user, gen)
        argvs = [c["argv"] for c in merged]
        assert argvs.count(["hello"]) == 1
        assert len(merged) == 3  # hello, world, test

    def test_user_cases_appear_first(self):
        user = [{"argv": ["user_first"]}]
        gen = [{"argv": ["gen_second"]}]
        merged = merge_and_deduplicate(user, gen)
        assert merged[0]["argv"] == ["user_first"]

    def test_empty_user_cases(self):
        gen = [{"argv": ["a"]}, {"argv": ["b"]}]
        merged = merge_and_deduplicate([], gen)
        assert len(merged) == 2

    def test_empty_generated_cases(self):
        user = [{"argv": ["x"]}]
        merged = merge_and_deduplicate(user, [])
        assert len(merged) == 1


class TestBuildInputSpec:
    def test_spec_has_schema_version(self):
        spec = build_input_spec_from_cases([{"argv": ["a"]}], generated=True)
        assert "schema_version" in spec
        assert spec["generated"] is True

    def test_spec_has_runs(self):
        spec = build_input_spec_from_cases(
            [{"argv": []}, {"argv": ["hello"]}],
            generated=True,
        )
        assert len(spec["runs"]) == 2
        assert spec["runs"][0]["name"] == "case_0"
        assert spec["runs"][1]["argv"] == ["hello"]


class TestWriteArtifact:
    def test_writes_json_file(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            cases = generate_default_input_cases(max_cases=3)
            out = write_generated_inputs_artifact(cases, p, max_cases=3)
            assert out.exists()
            data = json.loads(out.read_text())
            assert data["generated"] is True
            assert data["generation_strategy"] == "default_safe_argv_cases"
            assert len(data["runs"]) == 3
