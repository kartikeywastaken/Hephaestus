# -*- coding: utf-8 -*-
"""
Tests for Phase 11.6 provider 413/429 retry handling.
"""
import pytest
from unittest.mock import MagicMock, patch

from src.agent.providers.groq import (
    GroqProviderError,
    GroqPayloadTooLargeError,
    GroqRateLimitError,
    _parse_retry_after,
)
from src.agent.debate import run_debate_for_function, run_debate


FAKE_COMPLETE_RESULT = {
    "function": "main",
    "facts": {
        "calls": [], "loops": 0, "conditions": 0,
        "returns_value": True, "constants": [],
        "layout_candidates": [], "dynamic_observations_present": False,
        "global_behavior_refs": [],
    },
    "evidence_refs": [{"kind": "static", "source": "a.json", "detail": "test"}],
    "uncertainties": [],
    "dynamic_behavior": [],
    "limitations": [],
    "hypotheses": [],
    "suggested_names": [],
    "suggested_structs": [],
    "critic_findings": [],
    "rejected_suggestions": [],
    "summary": {
        "text": "test",
        "confidence": "low",
        "evidence_level": "static_evidence",
        "critic_status": "accept",
        "requires_human_approval": True,
    },
    "suggestions": [],
    "rejected": [],
    "_provider_diagnostics": {
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "json_repair": "direct",
        "duration_ms": 50,
        "parse_status": "ok",
    },
}


class TestGroqPayloadTooLargeError:
    def test_413_detected_in_debate(self):
        """If provider raises GroqPayloadTooLargeError, debate marks function as 'oversized'."""
        provider = MagicMock()
        provider.complete_json.side_effect = GroqPayloadTooLargeError(
            "413 too large", schema_name="evidence_agent", body_snippet="too big"
        )

        record, suggestions = run_debate_for_function(
            {"function": "main"}, provider,
        )
        assert record["status"] == "oversized"
        assert len(suggestions) == 0
        assert "413" in record.get("error", "")

    def test_413_has_schema_name(self):
        err = GroqPayloadTooLargeError(
            "too large", schema_name="evidence_agent", body_snippet="big"
        )
        assert err.schema_name == "evidence_agent"

    def test_413_is_groq_provider_error(self):
        err = GroqPayloadTooLargeError("too large")
        assert isinstance(err, GroqProviderError)


class TestGroqRateLimitError:
    def test_429_without_wait_marks_failed(self):
        """Without wait_on_429, 429 errors should mark function as failed."""
        provider = MagicMock()
        provider.complete_json.side_effect = GroqRateLimitError(
            "429 rate limited", schema_name="evidence_agent",
            retry_after_s=5.0, body_snippet="try again"
        )

        record, suggestions = run_debate_for_function(
            {"function": "main"}, provider,
            wait_on_429=False,
        )
        assert record["status"] == "failed"
        assert len(suggestions) == 0

    @patch("src.agent.debate.time.sleep")
    def test_429_with_wait_retries_once(self, mock_sleep):
        """With wait_on_429=True, debate should sleep and retry."""
        provider = MagicMock()
        call_count = [0]

        def side_effect(*, system_prompt, user_payload, schema_name):
            call_count[0] += 1
            if call_count[0] <= 1:  # First call fails with 429
                raise GroqRateLimitError(
                    "429", schema_name=schema_name,
                    retry_after_s=2.0, body_snippet="try again in 2s"
                )
            return FAKE_COMPLETE_RESULT  # Subsequent calls succeed

        provider.complete_json.side_effect = side_effect

        record, suggestions = run_debate_for_function(
            {"function": "main"}, provider,
            wait_on_429=True,
        )
        # Should have called sleep with ~3.0s (2.0 + 1.0)
        mock_sleep.assert_called_once()
        delay = mock_sleep.call_args[0][0]
        assert 2.5 < delay < 4.0

    def test_429_has_retry_after(self):
        err = GroqRateLimitError(
            "429", retry_after_s=10.0, schema_name="test"
        )
        assert err.retry_after_s == 10.0

    def test_429_is_groq_provider_error(self):
        err = GroqRateLimitError("429")
        assert isinstance(err, GroqProviderError)


class TestParseRetryAfter:
    def test_parses_header(self):
        exc = MagicMock()
        exc.headers = {"Retry-After": "5"}
        result = _parse_retry_after(exc, "")
        assert result == 5.0

    def test_parses_body_try_again(self):
        exc = MagicMock()
        exc.headers = {}
        result = _parse_retry_after(exc, "Please try again in 3.5s")
        assert result == 3.5

    def test_returns_none_if_unparseable(self):
        exc = MagicMock()
        exc.headers = {}
        result = _parse_retry_after(exc, "unknown error")
        assert result is None


class TestRunDebateRetryIntegration:
    def test_run_debate_forwards_retry_params(self):
        """run_debate should forward retry params to per-function calls."""
        provider = MagicMock()
        provider.complete_json.side_effect = GroqPayloadTooLargeError(
            "413", schema_name="evidence_agent"
        )

        records, suggestions = run_debate(
            [{"function": "main"}],
            provider,
            retry_on_413=True,
            wait_on_429=True,
            max_provider_retries=2,
        )
        assert len(records) == 1
        assert records[0]["status"] == "oversized"
