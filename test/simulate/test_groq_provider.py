# -*- coding: utf-8 -*-
"""
Tests for Groq provider (src/agent/providers/groq.py).
HTTP calls are monkeypatched. No real API key needed.
"""
import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import BytesIO

from src.agent.providers.groq import (
    GroqProvider,
    GroqApiKeyMissingError,
    GroqProviderError,
    _redact_secrets,
    _make_headers,
    resolve_groq_api_key,
)


# ── API Key Resolution ────────────────────────────────────────────────────────

class TestApiKeyResolution:
    def test_explicit_key_used(self):
        key = resolve_groq_api_key(explicit_key="sk-test-explicit")
        assert key == "sk-test-explicit"

    def test_api_key_env_flag(self, monkeypatch):
        monkeypatch.setenv("MY_CUSTOM_KEY", "sk-custom")
        key = resolve_groq_api_key(api_key_env="MY_CUSTOM_KEY")
        assert key == "sk-custom"

    def test_groq_api_key_env(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "sk-from-env")
        monkeypatch.delenv("HEPHAESTUS_GROQ_API_KEY", raising=False)
        key = resolve_groq_api_key()
        assert key == "sk-from-env"

    def test_hephaestus_fallback(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.setenv("HEPHAESTUS_GROQ_API_KEY", "sk-hep")
        key = resolve_groq_api_key()
        assert key == "sk-hep"

    def test_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("HEPHAESTUS_GROQ_API_KEY", raising=False)
        with pytest.raises(GroqApiKeyMissingError) as exc_info:
            resolve_groq_api_key()
        assert "GROQ_API_KEY" in str(exc_info.value)


# ── Provider Construction ─────────────────────────────────────────────────────

class TestGroqProviderInit:
    def test_default_host_and_model(self):
        p = GroqProvider(api_key="sk-test")
        assert "groq.com" in p.host
        assert "70b" in p.model.lower() or "versatile" in p.model.lower()

    def test_custom_host_and_model(self):
        p = GroqProvider(api_key="sk-test", host="https://custom.host/v1", model="mymodel")
        assert p.host == "https://custom.host/v1"
        assert p.model == "mymodel"

    def test_api_key_not_exposed(self):
        p = GroqProvider(api_key="sk-secret")
        assert not hasattr(p, "api_key")  # public attr should not exist
        # str(p) should not leak it
        assert "sk-secret" not in str(p)
        assert "sk-secret" not in repr(p)


# ── _redact_secrets helper ────────────────────────────────────────────────────

class TestRedactSecrets:
    def test_redacts_literal_key(self):
        result = _redact_secrets("error: invalid gsk_abc123XYZ token", "gsk_abc123XYZ")
        assert "gsk_abc123XYZ" not in result
        assert "[REDACTED_API_KEY]" in result

    def test_redacts_gsk_prefix_even_without_key(self):
        result = _redact_secrets("token=gsk_someLongKey1234567890 found", None)
        assert "gsk_someLongKey1234567890" not in result
        assert "gsk_[REDACTED]" in result

    def test_redacts_bearer_token(self):
        result = _redact_secrets("Authorization: Bearer sk-mytoken123", None)
        assert "sk-mytoken123" not in result
        assert "Bearer [REDACTED]" in result

    def test_empty_string_safe(self):
        assert _redact_secrets("", "mykey") == ""

    def test_none_key_does_not_crash(self):
        result = _redact_secrets("some error body", None)
        assert isinstance(result, str)


# ── _make_headers helper ──────────────────────────────────────────────────────

class TestMakeHeaders:
    def test_includes_authorization_bearer(self):
        h = _make_headers("sk-test-123")
        assert h["Authorization"] == "Bearer sk-test-123"

    def test_includes_content_type(self):
        h = _make_headers("sk-test")
        assert h["Content-Type"] == "application/json"

    def test_includes_accept(self):
        h = _make_headers("sk-test")
        assert h["Accept"] == "application/json"

    def test_includes_user_agent(self):
        h = _make_headers("sk-test")
        assert "User-Agent" in h
        assert len(h["User-Agent"]) > 0
        assert "Hephaestus" in h["User-Agent"]


# ── check_available ────────────────────────────────────────────────────────────

def _make_mock_response(status: int, body: dict | str):
    if isinstance(body, dict):
        body_bytes = json.dumps(body).encode()
    else:
        body_bytes = body.encode() if isinstance(body, str) else body
    mock_resp = MagicMock()
    mock_resp.read.return_value = body_bytes
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestGroqCheckAvailable:
    def test_available_when_model_found(self, monkeypatch):
        body = {"data": [{"id": "llama-3.3-70b-versatile"}, {"id": "other"}]}
        mock_resp = _make_mock_response(200, body)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            p = GroqProvider(api_key="sk-test", model="llama-3.3-70b-versatile")
            result = p.check_available()
        assert result["available"] is True
        assert result["error"] is None

    def test_unavailable_when_model_not_found(self, monkeypatch):
        body = {"data": [{"id": "other-model"}]}
        mock_resp = _make_mock_response(200, body)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            p = GroqProvider(api_key="sk-test", model="llama-3.3-70b-versatile")
            result = p.check_available()
        assert result["available"] is False
        assert "not found" in result["error"].lower()

    def test_unavailable_on_401(self, monkeypatch):
        import urllib.error
        err = urllib.error.HTTPError(
            url="", code=401, msg="Unauthorized", hdrs=None,
            fp=BytesIO(b'{"error":"invalid_api_key"}'),
        )
        with patch("urllib.request.urlopen", side_effect=err):
            p = GroqProvider(api_key="sk-bad")
            result = p.check_available()
        assert result["available"] is False
        assert "401" in result["error"] or "rejected" in result["error"].lower()

    def test_unavailable_on_403_includes_body(self, monkeypatch):
        """HTTP 403 response body must be surfaced so the user can diagnose the issue."""
        import urllib.error
        err = urllib.error.HTTPError(
            url="", code=403, msg="Forbidden", hdrs=None,
            fp=BytesIO(b'{"error":{"code":"forbidden","message":"IP blocked"}}'),
        )
        with patch("urllib.request.urlopen", side_effect=err):
            p = GroqProvider(api_key="sk-test")
            result = p.check_available()
        assert result["available"] is False
        assert "403" in result["error"]
        # The sanitised body must appear in either error or suggestion
        combined = result["error"] + (result.get("suggestion") or "")
        assert "blocked" in combined or "forbidden" in combined.lower()

    def test_unavailable_on_network_error(self, monkeypatch):
        import urllib.error
        err = urllib.error.URLError(reason="Connection refused")
        with patch("urllib.request.urlopen", side_effect=err):
            p = GroqProvider(api_key="sk-test")
            result = p.check_available()
        assert result["available"] is False
        assert "unreachable" in result["error"].lower()

    def test_check_available_sends_accept_header(self):
        """check_available must include Accept: application/json."""
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["headers"] = dict(req.headers)
            body = {"data": [{"id": "llama-3.3-70b-versatile"}]}
            return _make_mock_response(200, body)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            p = GroqProvider(api_key="sk-test", model="llama-3.3-70b-versatile")
            p.check_available()

        hdrs = {k.lower(): v for k, v in captured["headers"].items()}
        assert hdrs.get("accept") == "application/json"

    def test_check_available_sends_user_agent(self):
        """check_available must include a User-Agent header."""
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["headers"] = dict(req.headers)
            body = {"data": [{"id": "llama-3.3-70b-versatile"}]}
            return _make_mock_response(200, body)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            p = GroqProvider(api_key="sk-test", model="llama-3.3-70b-versatile")
            p.check_available()

        hdrs = {k.lower(): v for k, v in captured["headers"].items()}
        assert "user-agent" in hdrs
        assert len(hdrs["user-agent"]) > 0

    def test_api_key_not_in_check_available_error(self):
        """API key must be scrubbed from check_available error messages."""
        import urllib.error
        secret = "gsk_SuperSecretKeyAbcDef123"
        err = urllib.error.HTTPError(
            url="", code=403, msg="Forbidden", hdrs=None,
            fp=BytesIO(f'{{"key":"{secret}"}}'.encode()),
        )
        with patch("urllib.request.urlopen", side_effect=err):
            p = GroqProvider(api_key=secret)
            result = p.check_available()
        combined = json.dumps(result)
        assert secret not in combined


# ── complete_json ─────────────────────────────────────────────────────────────

class TestGroqCompleteJson:
    def _make_chat_response(self, content: str) -> MagicMock:
        envelope = {
            "choices": [{"message": {"role": "assistant", "content": content}}]
        }
        return _make_mock_response(200, envelope)

    # ── Header tests ──────────────────────────────────────────────────────────

    def test_sends_authorization_header(self):
        captured_request = {}

        def fake_urlopen(req, timeout=None):
            captured_request["headers"] = dict(req.headers)
            content = json.dumps({"function": "main"})
            envelope = {"choices": [{"message": {"content": content}}]}
            return _make_mock_response(200, envelope)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            p = GroqProvider(api_key="sk-mykey", model="llama-3.3-70b-versatile")
            p.complete_json(
                system_prompt="test",
                user_payload={"task": "test"},
                schema_name="test",
            )

        auth_header = captured_request["headers"].get(
            "Authorization", captured_request["headers"].get("authorization", "")
        )
        assert "Bearer" in auth_header
        assert "sk-mykey" in auth_header

    def test_sends_accept_header(self):
        """complete_json must include Accept: application/json."""
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["headers"] = dict(req.headers)
            content = json.dumps({"x": 1})
            envelope = {"choices": [{"message": {"content": content}}]}
            return _make_mock_response(200, envelope)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            p = GroqProvider(api_key="sk-test")
            p.complete_json(system_prompt="s", user_payload={}, schema_name="t")

        hdrs = {k.lower(): v for k, v in captured["headers"].items()}
        assert hdrs.get("accept") == "application/json"

    def test_sends_user_agent_header(self):
        """complete_json must include a non-empty User-Agent header."""
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["headers"] = dict(req.headers)
            content = json.dumps({"x": 1})
            envelope = {"choices": [{"message": {"content": content}}]}
            return _make_mock_response(200, envelope)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            p = GroqProvider(api_key="sk-test")
            p.complete_json(system_prompt="s", user_payload={}, schema_name="t")

        hdrs = {k.lower(): v for k, v in captured["headers"].items()}
        assert "user-agent" in hdrs
        assert len(hdrs["user-agent"]) > 0

    def test_sends_content_type_header(self):
        """complete_json must include Content-Type: application/json."""
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["headers"] = dict(req.headers)
            content = json.dumps({"x": 1})
            envelope = {"choices": [{"message": {"content": content}}]}
            return _make_mock_response(200, envelope)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            p = GroqProvider(api_key="sk-test")
            p.complete_json(system_prompt="s", user_payload={}, schema_name="t")

        hdrs = {k.lower(): v for k, v in captured["headers"].items()}
        assert hdrs.get("content-type") == "application/json"

    # ── Body shape tests ──────────────────────────────────────────────────────

    def test_sends_response_format_json_object(self):
        captured_body = {}

        def fake_urlopen(req, timeout=None):
            import json as _json
            captured_body["data"] = _json.loads(req.data)
            content = json.dumps({"function": "main"})
            envelope = {"choices": [{"message": {"content": content}}]}
            return _make_mock_response(200, envelope)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            p = GroqProvider(api_key="sk-test", model="llama-3.3-70b-versatile")
            p.complete_json(
                system_prompt="test",
                user_payload={"task": "test"},
                schema_name="test",
            )

        assert captured_body["data"]["response_format"]["type"] == "json_object"

    def test_request_body_includes_model_messages_temperature(self):
        """Request body must include model, messages, temperature, response_format."""
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data)
            content = json.dumps({"x": 1})
            envelope = {"choices": [{"message": {"content": content}}]}
            return _make_mock_response(200, envelope)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            p = GroqProvider(api_key="sk-test", model="mymodel", temperature=0.1)
            p.complete_json(system_prompt="sys", user_payload={"k": "v"}, schema_name="s")

        b = captured["body"]
        assert b["model"] == "mymodel"
        assert isinstance(b["messages"], list)
        assert len(b["messages"]) >= 2
        assert b["temperature"] == pytest.approx(0.1)
        assert b["response_format"] == {"type": "json_object"}

    # ── Response parsing tests ────────────────────────────────────────────────

    def test_parses_choices_0_message_content(self):
        content = json.dumps({"function": "main", "facts": {"calls": []}})
        mock_resp = self._make_chat_response(content)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            p = GroqProvider(api_key="sk-test")
            result = p.complete_json(
                system_prompt="test",
                user_payload={},
                schema_name="test",
            )
        assert result["function"] == "main"

    def test_handles_malformed_json_content(self):
        mock_resp = self._make_chat_response("NOT JSON AT ALL")
        with patch("urllib.request.urlopen", return_value=mock_resp):
            p = GroqProvider(api_key="sk-test")
            result = p.complete_json(
                system_prompt="test",
                user_payload={},
                schema_name="test",
            )
        diag = result.get("_provider_diagnostics", {})
        assert diag.get("parse_status") == "failed"

    def test_diagnostics_do_not_include_api_key(self):
        content = json.dumps({"result": "ok"})
        mock_resp = self._make_chat_response(content)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            p = GroqProvider(api_key="sk-super-secret", model="m")
            result = p.complete_json(
                system_prompt="test",
                user_payload={},
                schema_name="test",
            )
        result_str = json.dumps(result)
        assert "sk-super-secret" not in result_str

    def test_diagnostics_records_provider_and_model(self):
        content = json.dumps({"result": "ok"})
        mock_resp = self._make_chat_response(content)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            p = GroqProvider(api_key="sk-test", model="llama-3.3-70b-versatile")
            result = p.complete_json(
                system_prompt="test",
                user_payload={},
                schema_name="evidence_agent",
            )
        diag = result["_provider_diagnostics"]
        assert diag["provider"] == "groq"
        assert diag["model"] == "llama-3.3-70b-versatile"
        assert "api_key" not in diag
        assert "sk-test" not in json.dumps(diag)

    # ── Error handling tests ──────────────────────────────────────────────────

    def test_handles_401_http_error(self):
        import urllib.error
        err = urllib.error.HTTPError(
            url="", code=401, msg="Unauthorized", hdrs=None, fp=BytesIO(b"{}")
        )
        with patch("urllib.request.urlopen", side_effect=err):
            p = GroqProvider(api_key="sk-bad")
            with pytest.raises(GroqProviderError):
                p.complete_json(system_prompt="x", user_payload={}, schema_name="x")

    def test_http_error_body_included_in_raised_error(self):
        """HTTPError response body must be surfaced in the raised GroqProviderError."""
        import urllib.error
        body_content = b'{"error":{"message":"Rate limit reached","code":"rate_limit_exceeded"}}'
        err = urllib.error.HTTPError(
            url="", code=429, msg="Too Many Requests", hdrs=None,
            fp=BytesIO(body_content),
        )
        with patch("urllib.request.urlopen", side_effect=err):
            p = GroqProvider(api_key="sk-test")
            with pytest.raises(GroqProviderError) as exc_info:
                p.complete_json(system_prompt="x", user_payload={}, schema_name="x")
        # The error message must include meaningful body content
        assert "429" in str(exc_info.value)
        assert "rate_limit" in str(exc_info.value) or "Rate limit" in str(exc_info.value)

    def test_api_key_redacted_from_raised_error(self):
        """API key must not appear in any raised exception text."""
        import urllib.error
        secret = "gsk_MyTopSecretKey99887766"
        body_content = f'{{"key_hint":"{secret}"}}'.encode()
        err = urllib.error.HTTPError(
            url="", code=403, msg="Forbidden", hdrs=None,
            fp=BytesIO(body_content),
        )
        with patch("urllib.request.urlopen", side_effect=err):
            p = GroqProvider(api_key=secret)
            with pytest.raises(GroqProviderError) as exc_info:
                p.complete_json(system_prompt="x", user_payload={}, schema_name="x")
        assert secret not in str(exc_info.value)

    # ── Regression: Invalid API Key response ──────────────────────────────────

    def test_invalid_api_key_response_surfaced_without_key(self):
        """
        Regression test: Groq returns a standard invalid_api_key error body.
        The raised GroqProviderError must contain 'invalid_api_key' in the message
        but must NOT contain the actual key value.
        """
        import urllib.error
        real_key = "gsk_RealKeyThatShouldBeRedacted_XXXXXXXXX"
        groq_error_body = json.dumps({
            "error": {
                "message": "Invalid API Key",
                "type": "invalid_request_error",
                "code": "invalid_api_key",
            }
        }).encode()
        err = urllib.error.HTTPError(
            url="", code=401, msg="Unauthorized", hdrs=None,
            fp=BytesIO(groq_error_body),
        )
        with patch("urllib.request.urlopen", side_effect=err):
            p = GroqProvider(api_key=real_key)
            with pytest.raises(GroqProviderError) as exc_info:
                p.complete_json(system_prompt="test", user_payload={}, schema_name="test")
        error_text = str(exc_info.value)
        # Must surface the error code from the body
        assert "invalid_api_key" in error_text
        # Must NOT contain the real key
        assert real_key not in error_text
        assert "gsk_RealKeyThatShouldBeRedacted_XXXXXXXXX" not in error_text
