# -*- coding: utf-8 -*-
"""
Test: Phase 11 sanitizer.

Tests:
  - strips markdown fences
  - rejects recovered_agent.c mention
  - rejects forbidden certainty phrases
  - rejects multiple unrelated functions in function-by-function mode
  - rejects JSON wrappers
  - accepts clean C function
  - rejects empty input
  - normalizes CRLF to LF
"""

from __future__ import annotations

import pytest

from src.agent_source.sanitizer import (
    sanitize_function_output,
    sanitize_whole_file_output,
)


class TestSanitizeFunctionOutput:
    def test_clean_c_function_accepted(self):
        raw = """\
int32_t foo(int32_t x) {
    /* Evidence: static_evidence */
    return x + 1;
}
"""
        text, issues, ok = sanitize_function_output(raw, fn_name="foo")
        assert ok is True
        assert "foo" in text

    def test_strips_markdown_fences(self):
        raw = "```c\nint32_t foo(void) { return 0; }\n```"
        text, issues, ok = sanitize_function_output(raw, fn_name="foo")
        assert ok is True
        assert "```" not in text
        assert any("stripped" in i.lower() for i in issues)

    def test_strips_bare_backtick_lines(self):
        raw = "```\nint32_t foo(void) { return 0; }\n```"
        text, issues, ok = sanitize_function_output(raw, fn_name="foo")
        assert ok is True
        assert "```" not in text

    def test_rejects_json_wrapper(self):
        raw = '{"generated_c": "int32_t foo(void) { return 0; }"}'
        text, issues, ok = sanitize_function_output(raw, fn_name="foo")
        assert ok is False
        assert text == ""
        assert any("json" in i.lower() for i in issues)

    def test_rejects_recovered_agent_c_mention(self):
        raw = "/* see recovered_agent.c */ int32_t foo(void) { return 0; }"
        text, issues, ok = sanitize_function_output(raw, fn_name="foo")
        assert ok is False
        assert text == ""
        assert any("recovered_agent.c" in i for i in issues)

    def test_rejects_semantic_equivalence_phrase(self):
        raw = "/* semantically equivalent to original */ int32_t foo(void) { return 0; }"
        text, issues, ok = sanitize_function_output(raw, fn_name="foo")
        assert ok is False
        assert text == ""
        assert any("forbidden" in i.lower() for i in issues)

    def test_rejects_guaranteed_phrase(self):
        raw = "/* guaranteed */ int32_t foo(void) { return 0; }"
        text, issues, ok = sanitize_function_output(raw, fn_name="foo")
        assert ok is False

    def test_rejects_multiple_unrelated_functions_in_function_mode(self):
        raw = """\
int32_t foo(int32_t x) { return x; }
int32_t bar(int32_t y) { return y; }
int32_t baz(int32_t z) { return z; }
"""
        text, issues, ok = sanitize_function_output(
            raw, fn_name="foo", generation_mode="function_by_function"
        )
        assert ok is False
        assert any("multiple" in i.lower() for i in issues)

    def test_allows_same_named_function_in_function_mode(self):
        raw = "int32_t foo(int32_t x) { return x + 1; }"
        text, issues, ok = sanitize_function_output(
            raw, fn_name="foo", generation_mode="function_by_function"
        )
        assert ok is True

    def test_normalizes_crlf(self):
        raw = "int32_t foo(void) {\r\n    return 0;\r\n}"
        text, issues, ok = sanitize_function_output(raw, fn_name="foo")
        assert ok is True
        assert "\r\n" not in text
        assert "\r" not in text

    def test_empty_input_rejected(self):
        text, issues, ok = sanitize_function_output("", fn_name="foo")
        assert ok is False
        assert text == ""

    def test_whitespace_only_rejected(self):
        text, issues, ok = sanitize_function_output("   \n\n   ", fn_name="foo")
        assert ok is False

    def test_allows_extra_related_function_with_warning(self):
        raw = """\
int32_t foo(int32_t x) { return x; }
int32_t foo_helper(int32_t x) { return x * 2; }
"""
        text, issues, ok = sanitize_function_output(
            raw, fn_name="foo", generation_mode="function_by_function"
        )
        # This has 2 distinct names but only 1 unrelated → warning, not rejection
        # (foo_helper is only 1 extra, threshold is >= 2 extras)
        assert ok is True
        assert any("extra function" in i.lower() or "warning" in i.lower() for i in issues)


class TestSanitizeWholFileOutput:
    def test_clean_c_file_accepted(self):
        raw = """\
/* Header */
int32_t foo(int32_t x) { return x; }
int32_t bar(void) { return 0; }
"""
        text, issues, ok = sanitize_whole_file_output(raw)
        assert ok is True

    def test_rejects_json_whole_file(self):
        raw = '{"generated_c": "int main() {}"}'
        text, issues, ok = sanitize_whole_file_output(raw)
        assert ok is False

    def test_rejects_forbidden_phrase_whole_file(self):
        raw = "/* definitely equivalent */ int main() {}"
        text, issues, ok = sanitize_whole_file_output(raw)
        assert ok is False

    def test_strips_fences_whole_file(self):
        raw = "```c\nint main() { return 0; }\n```"
        text, issues, ok = sanitize_whole_file_output(raw)
        assert ok is True
        assert "```" not in text

    def test_empty_input_rejected(self):
        text, issues, ok = sanitize_whole_file_output("")
        assert ok is False
