# -*- coding: utf-8 -*-
"""
Tests for src/agent/json_utils.py — robust JSON extraction.
No Ollama or Groq required.
"""
import pytest
from src.agent.json_utils import extract_json, _strip_fences, _extract_balanced_object


class TestExtractJsonDirect:
    def test_valid_json_direct(self):
        raw = '{"function": "main", "status": "ok"}'
        obj, method = extract_json(raw)
        assert method == "direct"
        assert obj["function"] == "main"

    def test_valid_json_with_whitespace(self):
        raw = '  \n  {"a": 1}  \n  '
        obj, method = extract_json(raw)
        assert method == "direct"
        assert obj["a"] == 1

    def test_non_dict_json_returns_failed(self):
        raw = '["a", "b", "c"]'
        obj, method = extract_json(raw)
        assert method == "failed"
        assert obj == {}


class TestExtractJsonFenceStrip:
    def test_json_fence(self):
        raw = '```json\n{"key": "value"}\n```'
        obj, method = extract_json(raw)
        assert method == "fence_strip"
        assert obj["key"] == "value"

    def test_plain_fence(self):
        raw = '```\n{"x": 42}\n```'
        obj, method = extract_json(raw)
        assert method == "fence_strip"
        assert obj["x"] == 42

    def test_fence_with_prose_before(self):
        raw = 'Here is the output:\n```json\n{"result": true}\n```'
        obj, method = extract_json(raw)
        assert method == "fence_strip"
        assert obj["result"] is True


class TestExtractJsonBalanced:
    def test_json_embedded_in_prose(self):
        raw = 'The agent says: {"function": "foo", "calls": []} — end.'
        obj, method = extract_json(raw)
        assert method == "balanced_extract"
        assert obj["function"] == "foo"

    def test_nested_object(self):
        raw = 'Output: {"outer": {"inner": 1}} done.'
        obj, method = extract_json(raw)
        assert method == "balanced_extract"
        assert obj["outer"]["inner"] == 1

    def test_brace_in_string_not_counted(self):
        raw = 'Data: {"msg": "open { not a brace", "val": 1} end'
        obj, method = extract_json(raw)
        assert method == "balanced_extract"
        assert obj["msg"] == "open { not a brace"
        assert obj["val"] == 1


class TestExtractJsonFailed:
    def test_totally_malformed(self):
        raw = "This is just plain text with no JSON at all."
        obj, method = extract_json(raw)
        assert method == "failed"
        assert obj == {}

    def test_empty_string(self):
        obj, method = extract_json("")
        assert method == "failed"
        assert obj == {}

    def test_unbalanced_braces(self):
        raw = '{"a": 1'  # no closing brace
        obj, method = extract_json(raw)
        # direct fails, fence fails, balanced extract returns nothing
        assert method == "failed"
        assert obj == {}


class TestStripFences:
    def test_strip_json_fence(self):
        raw = '```json\n{"a":1}\n```'
        result = _strip_fences(raw)
        assert result == '{"a":1}'

    def test_strip_plain_fence(self):
        raw = '```\n{"b":2}\n```'
        result = _strip_fences(raw)
        assert result == '{"b":2}'

    def test_no_fence_returns_original(self):
        raw = '{"c":3}'
        result = _strip_fences(raw)
        assert result == raw


class TestExtractBalancedObject:
    def test_simple(self):
        raw = '{"k": "v"}'
        result = _extract_balanced_object(raw)
        assert result == '{"k": "v"}'

    def test_nested(self):
        raw = '{"a": {"b": 1}}'
        result = _extract_balanced_object(raw)
        assert result == '{"a": {"b": 1}}'

    def test_no_object(self):
        result = _extract_balanced_object("no braces here")
        assert result is None

    def test_escaped_string(self):
        raw = r'{"msg": "say \"hi\""}'
        result = _extract_balanced_object(raw)
        import json
        obj = json.loads(result)
        assert obj["msg"] == 'say "hi"'
