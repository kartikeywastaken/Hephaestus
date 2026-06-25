# -*- coding: utf-8 -*-
"""
Test: Phase 11 validator.

Tests:
  - requires warning header
  - rejects duplicate main
  - rejects missing warning header
  - rejects markdown fences
  - rejects JSON wrappers at file level
  - balanced brace check
  - clang syntax check when clang exists
  - hash guard catches changed artifacts
  - hash guard passes when nothing changed
"""

from __future__ import annotations

import os
import json
import tempfile
from pathlib import Path

import pytest

from src.agent_source.validator import validate_agent_source, _check_balanced_braces
from src.agent_source.models import WARNING_HEADER


def _make_valid_c(fn_name: str = "foo") -> str:
    return (
        WARNING_HEADER
        + f"\n\nint32_t {fn_name}(int32_t x) {{\n    /* AI-assisted approximation */\n    return x + 1;\n}}\n"
    )


def _make_valid_c_with_main() -> str:
    return (
        WARNING_HEADER
        + "\n\nint32_t main(int32_t argc, char **argv) {\n    /* AI-assisted approximation */\n    return 0;\n}\n"
    )


class TestWarningHeader:
    def test_valid_c_with_header_passes(self, tmp_path):
        c_text = _make_valid_c()
        ok, issues, clang_status = validate_agent_source(
            c_text, tmp_path, []
        )
        header_issues = [i for i in issues if "warning header" in i.lower()]
        assert any("ok" in i.lower() for i in header_issues)

    def test_c_without_header_fails(self, tmp_path):
        c_text = "int32_t foo(int32_t x) { return x; }\n"
        ok, issues, clang_status = validate_agent_source(
            c_text, tmp_path, []
        )
        assert ok is False
        assert any("warning header" in i.lower() and "fail" in i.lower() for i in issues)


class TestForbiddenPhrases:
    def test_forbidden_phrase_causes_fail(self, tmp_path):
        c_text = _make_valid_c() + "/* semantically equivalent */\n"
        ok, issues, clang_status = validate_agent_source(
            c_text, tmp_path, []
        )
        assert ok is False
        assert any("forbidden phrase" in i.lower() for i in issues)

    def test_no_forbidden_phrases_passes(self, tmp_path):
        c_text = _make_valid_c()
        ok, issues, clang_status = validate_agent_source(
            c_text, tmp_path, []
        )
        phrase_fails = [i for i in issues if "forbidden phrase" in i.lower() and "FAIL" in i]
        assert len(phrase_fails) == 0


class TestMarkdownFences:
    def test_fences_in_file_causes_fail(self, tmp_path):
        c_text = _make_valid_c() + "\n```c\n// should not be here\n```\n"
        ok, issues, clang_status = validate_agent_source(
            c_text, tmp_path, []
        )
        assert ok is False
        assert any("markdown" in i.lower() for i in issues)

    def test_no_fences_passes(self, tmp_path):
        c_text = _make_valid_c()
        ok, issues, clang_status = validate_agent_source(
            c_text, tmp_path, []
        )
        fence_fails = [i for i in issues if "markdown" in i.lower() and "FAIL" in i]
        assert len(fence_fails) == 0


class TestJSONWrapper:
    def test_json_wrapper_causes_fail(self, tmp_path):
        c_text = '{"generated_c": "int main() {}"}'
        ok, issues, clang_status = validate_agent_source(
            c_text, tmp_path, []
        )
        assert ok is False
        assert any("json" in i.lower() for i in issues)


class TestDuplicateMain:
    def test_single_main_passes(self, tmp_path):
        c_text = _make_valid_c_with_main()
        ok, issues, _ = validate_agent_source(c_text, tmp_path, [])
        main_fails = [i for i in issues if "duplicate" in i.lower() and "FAIL" in i]
        assert len(main_fails) == 0

    def test_duplicate_main_fails(self, tmp_path):
        c_text = (
            _make_valid_c_with_main()
            + "\nint32_t main(int32_t argc, char **argv) { return 1; }\n"
        )
        ok, issues, _ = validate_agent_source(c_text, tmp_path, [])
        assert ok is False
        assert any("duplicate" in i.lower() for i in issues)


class TestBalancedBraces:
    def test_balanced_braces(self):
        assert _check_balanced_braces("int foo() { return 0; }") is True

    def test_unbalanced_open(self):
        assert _check_balanced_braces("int foo() { return 0;") is False

    def test_unbalanced_close(self):
        assert _check_balanced_braces("int foo() { return 0; }}") is False

    def test_braces_in_string_ignored(self):
        assert _check_balanced_braces('int foo() { char *s = "{"; return 0; }') is True

    def test_braces_in_comment_ignored(self):
        assert _check_balanced_braces("int foo() { /* { */ return 0; }") is True

    def test_empty_string_balanced(self):
        assert _check_balanced_braces("") is True

    def test_valid_file_balanced(self, tmp_path):
        c_text = _make_valid_c()
        assert _check_balanced_braces(c_text) is True


class TestHashGuard:
    def test_hash_guard_passes_when_nothing_changed(self, tmp_path):
        # Write a dummy guarded artifact
        (tmp_path / "recovered.c").write_text("int main() {}", encoding="utf-8")
        from src.agent_source.loader import compute_phase11_hashes
        hashes = compute_phase11_hashes(tmp_path)

        c_text = _make_valid_c()
        ok, issues, _ = validate_agent_source(
            c_text, tmp_path, [], hashes_before=hashes
        )
        hash_fails = [i for i in issues if "ABORT" in i]
        assert len(hash_fails) == 0

    def test_hash_guard_fails_when_artifact_changed(self, tmp_path):
        (tmp_path / "recovered.c").write_text("int main() {}", encoding="utf-8")
        from src.agent_source.loader import compute_phase11_hashes
        hashes = compute_phase11_hashes(tmp_path)

        # Now modify recovered.c
        (tmp_path / "recovered.c").write_text("int modified() {}", encoding="utf-8")

        c_text = _make_valid_c()
        ok, issues, _ = validate_agent_source(
            c_text, tmp_path, [], hashes_before=hashes
        )
        assert ok is False
        assert any("ABORT" in i for i in issues)


class TestClangStatus:
    def test_clang_status_is_string(self, tmp_path):
        c_text = _make_valid_c()
        ok, issues, clang_status = validate_agent_source(c_text, tmp_path, [])
        assert isinstance(clang_status, str)
        assert clang_status in ("passed", "failed", "not_available", "error", "skipped")

    def test_clang_status_in_issues(self, tmp_path):
        c_text = _make_valid_c()
        ok, issues, clang_status = validate_agent_source(c_text, tmp_path, [])
        assert any(f"clang_status={clang_status}" in i for i in issues)
