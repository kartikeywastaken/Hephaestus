# -*- coding: utf-8 -*-
"""
Real Ollama integration tests.

These tests require:
  1. A running Ollama instance: `ollama serve`
  2. The target model pulled: `ollama pull llama3.3:70b`
  3. Environment variable: HEPHAESTUS_RUN_OLLAMA_TESTS=1

Skip unless the env var is set.
"""
import json
import os
import pytest
import tempfile
from pathlib import Path

pytestmark = pytest.mark.skipif(
    os.environ.get("HEPHAESTUS_RUN_OLLAMA_TESTS") != "1",
    reason="Set HEPHAESTUS_RUN_OLLAMA_TESTS=1 to run real Ollama integration tests."
)

from src.agent.providers.ollama import OllamaProvider
from src.agent.models import DEFAULT_OLLAMA_HOST, DEFAULT_OLLAMA_MODEL


OLLAMA_HOST = os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
OLLAMA_MODEL = os.environ.get("HEPHAESTUS_AGENT_MODEL", DEFAULT_OLLAMA_MODEL)


# ── Provider health check ──────────────────────────────────────────────────────

class TestOllamaProviderAvailability:
    def test_check_available_returns_dict(self):
        p = OllamaProvider(host=OLLAMA_HOST, model=OLLAMA_MODEL)
        result = p.check_available()
        assert isinstance(result, dict)
        assert "available" in result

    def test_provider_is_available(self):
        p = OllamaProvider(host=OLLAMA_HOST, model=OLLAMA_MODEL)
        result = p.check_available()
        assert result["available"] is True, (
            f"Ollama unavailable: {result.get('error')}. "
            f"Suggestion: {result.get('suggestion')}"
        )


# ── complete_json ─────────────────────────────────────────────────────────────

class TestOllamaCompleteJson:
    def _make_provider(self) -> OllamaProvider:
        return OllamaProvider(
            host=OLLAMA_HOST,
            model=OLLAMA_MODEL,
            timeout_s=120,
            temperature=0.0,
            num_ctx=4096,
        )

    def test_sends_post_to_api_chat(self):
        """Verify the provider reaches out to /api/chat successfully."""
        p = self._make_provider()
        result = p.complete_json(
            system_prompt="Return only valid JSON. No markdown. No explanation.",
            user_payload={"task": "Return {\"status\": \"ok\"}"},
            schema_name="test_basic",
        )
        assert "_provider_diagnostics" in result
        assert result["_provider_diagnostics"]["provider"] == "ollama"

    def test_uses_stream_false(self):
        """
        Indirectly verified: if stream=true were used, the response would be
        newline-delimited chunks, causing our JSON parser to see an incomplete
        object. A successful parse implies stream=false was honoured.
        """
        p = self._make_provider()
        result = p.complete_json(
            system_prompt="Return only valid JSON. No markdown.",
            user_payload={"task": "Return {\"status\": \"ok\"}"},
            schema_name="test_stream",
        )
        # If stream was True, parse would fail
        diag = result.get("_provider_diagnostics", {})
        assert diag.get("parse_status") != "failed", (
            "stream=false likely not honoured — response could not be parsed as JSON"
        )

    def test_uses_format_json(self):
        """format=json should force model to return valid JSON."""
        p = self._make_provider()
        result = p.complete_json(
            system_prompt="Return only valid JSON with key 'hello' set to 'world'.",
            user_payload={"task": "Return the JSON object."},
            schema_name="test_format",
        )
        diag = result.get("_provider_diagnostics", {})
        assert diag.get("parse_status") == "ok", (
            f"Expected JSON output but got parse_status={diag.get('parse_status')}"
        )

    def test_returns_dict_not_list(self):
        p = self._make_provider()
        result = p.complete_json(
            system_prompt="Return only valid JSON with a 'result' key.",
            user_payload={"task": "Return {\"result\": 1}"},
            schema_name="test_dict",
        )
        assert isinstance(result, dict)

    def test_diagnostics_include_duration_ms(self):
        p = self._make_provider()
        result = p.complete_json(
            system_prompt="Return only valid JSON.",
            user_payload={"task": "Return {\"ok\": true}"},
            schema_name="test_diag",
        )
        diag = result["_provider_diagnostics"]
        assert "duration_ms" in diag
        assert isinstance(diag["duration_ms"], int)
        assert diag["duration_ms"] > 0
