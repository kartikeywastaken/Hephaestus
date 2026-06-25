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
        err = urllib.error.HTTPError(url="", code=401, msg="Unauthorized", hdrs=None, fp=None)
        with patch("urllib.request.urlopen", side_effect=err):
            p = GroqProvider(api_key="sk-bad")
            result = p.check_available()
        assert result["available"] is False
        assert "401" in result["error"] or "rejected" in result["error"].lower()

    def test_unavailable_on_network_error(self, monkeypatch):
        import urllib.error
        err = urllib.error.URLError(reason="Connection refused")
        with patch("urllib.request.urlopen", side_effect=err):
            p = GroqProvider(api_key="sk-test")
            result = p.check_available()
        assert result["available"] is False
        assert "unreachable" in result["error"].lower()


# ── complete_json ─────────────────────────────────────────────────────────────

class TestGroqCompleteJson:
    def _make_chat_response(self, content: str) -> MagicMock:
        envelope = {
            "choices": [{"message": {"role": "assistant", "content": content}}]
        }
        return _make_mock_response(200, envelope)

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

    def test_handles_401_http_error(self):
        import urllib.error
        from src.agent.providers.groq import GroqProviderError
        err = urllib.error.HTTPError(url="", code=401, msg="Unauthorized", hdrs=None, fp=BytesIO(b"{}"))
        with patch("urllib.request.urlopen", side_effect=err):
            p = GroqProvider(api_key="sk-bad")
            with pytest.raises(GroqProviderError):
                p.complete_json(system_prompt="x", user_payload={}, schema_name="x")
