# -*- coding: utf-8 -*-
"""
Phase 10 — Real Ollama provider.

Uses urllib.request only (no third-party HTTP library required).
No mock mode. No fallback. If Ollama is unavailable, we fail cleanly.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any

from src.agent.providers.base import AgentProvider
from src.agent.json_utils import extract_json
from src.agent.models import (
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_TIMEOUT_S,
    DEFAULT_OLLAMA_TEMPERATURE,
    DEFAULT_OLLAMA_NUM_CTX,
)

logger = logging.getLogger("agent.providers.ollama")


class OllamaProvider(AgentProvider):
    """
    Real Ollama HTTP provider.

    Sends POST /api/chat with stream=false and format=json.
    Environment fallbacks: OLLAMA_HOST, HEPHAESTUS_AGENT_MODEL.
    CLI args override environment variables.
    """

    def __init__(
        self,
        *,
        host: str | None = None,
        model: str | None = None,
        timeout_s: int = DEFAULT_OLLAMA_TIMEOUT_S,
        temperature: float = DEFAULT_OLLAMA_TEMPERATURE,
        num_ctx: int = DEFAULT_OLLAMA_NUM_CTX,
    ) -> None:
        # CLI > env > default
        self.host = (
            host
            or os.environ.get("OLLAMA_HOST", "").strip()
            or DEFAULT_OLLAMA_HOST
        ).rstrip("/")
        self.model = (
            model
            or os.environ.get("HEPHAESTUS_AGENT_MODEL", "").strip()
            or DEFAULT_OLLAMA_MODEL
        )
        self.timeout_s = timeout_s
        self.temperature = temperature
        self.num_ctx = num_ctx
        logger.debug(
            "[ollama] host=%s model=%s timeout_s=%s temperature=%s num_ctx=%s",
            self.host, self.model, self.timeout_s, self.temperature, self.num_ctx,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def check_available(self) -> dict:
        """
        Verify Ollama host is reachable and the model exists locally.

        Returns a dict:
          available: bool
          host: str
          model: str
          error: str | None
          suggestion: str | None
        """
        url = f"{self.host}/api/tags"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                data = json.loads(raw)
        except urllib.error.URLError as e:
            return {
                "available": False,
                "host": self.host,
                "model": self.model,
                "error": f"Cannot reach Ollama host: {e}",
                "suggestion": (
                    f"Start Ollama with `ollama serve` and pull the model "
                    f"with `ollama pull {self.model}`."
                ),
            }
        except Exception as e:
            return {
                "available": False,
                "host": self.host,
                "model": self.model,
                "error": f"Unexpected error checking Ollama: {e}",
                "suggestion": (
                    f"Start Ollama with `ollama serve` and pull the model "
                    f"with `ollama pull {self.model}`."
                ),
            }

        # Check model list
        models = data.get("models", [])
        model_names = [m.get("name", "") for m in models]
        # Also accept bare name match (strip :tag for comparison)
        bare_target = self.model.split(":")[0]
        found = any(
            m == self.model or m.split(":")[0] == bare_target
            for m in model_names
        )
        if not found:
            return {
                "available": False,
                "host": self.host,
                "model": self.model,
                "error": (
                    f"Model '{self.model}' not found locally. "
                    f"Available: {model_names or '(none)'}"
                ),
                "suggestion": f"Pull the model with `ollama pull {self.model}`.",
            }

        return {
            "available": True,
            "host": self.host,
            "model": self.model,
            "error": None,
            "suggestion": None,
        }

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_payload: dict,
        schema_name: str,
    ) -> dict:
        """
        POST /api/chat and return a parsed JSON dict.

        Injects _provider_diagnostics into every returned dict.
        Raises OllamaProviderError on unrecoverable HTTP/network failures.
        Returns a dict with _provider_diagnostics.parse_status == "failed"
        if the model returned non-parseable output.
        """
        url = f"{self.host}/api/chat"
        user_content = json.dumps(user_payload, ensure_ascii=False)

        body: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_content},
            ],
            "options": {
                "temperature": self.temperature,
                "num_ctx": self.num_ctx,
            },
        }

        body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body_bytes,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw_response = resp.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as e:
            raise OllamaProviderError(
                f"Ollama HTTP error for schema '{schema_name}': {e}"
            ) from e
        except Exception as e:
            raise OllamaProviderError(
                f"Ollama unexpected error for schema '{schema_name}': {e}"
            ) from e

        duration_ms = int((time.perf_counter() - t0) * 1000)

        # Parse the Ollama response envelope
        try:
            envelope = json.loads(raw_response)
        except json.JSONDecodeError:
            logger.warning("[ollama] envelope not JSON for %s", schema_name)
            return _failed_response(
                raw=raw_response,
                schema_name=schema_name,
                model=self.model,
                duration_ms=duration_ms,
                reason="envelope_not_json",
            )

        # Extract the assistant message content
        # Ollama /api/chat non-streaming response shape:
        # {"model":..., "message":{"role":"assistant","content":"..."}, ...}
        message = envelope.get("message", {})
        if not isinstance(message, dict):
            logger.warning("[ollama] missing message field for %s", schema_name)
            return _failed_response(
                raw=raw_response,
                schema_name=schema_name,
                model=self.model,
                duration_ms=duration_ms,
                reason="no_message_field",
            )

        content = message.get("content", "")
        if not isinstance(content, str):
            content = str(content)

        # Robust JSON extraction
        parsed, repair_method = extract_json(content)

        diagnostics = {
            "_provider_diagnostics": {
                "provider": "ollama",
                "model": self.model,
                "schema_name": schema_name,
                "json_repair": repair_method,
                "duration_ms": duration_ms,
                "parse_status": "ok" if repair_method != "failed" else "failed",
            }
        }

        if repair_method == "failed":
            logger.warning(
                "[ollama] JSON extraction failed for %s (raw len=%d)",
                schema_name, len(content),
            )
            return {
                **diagnostics,
                "_raw_content": content[:2000],  # preserve first 2000 chars
            }

        if repair_method != "direct":
            logger.info(
                "[ollama] JSON repaired via %s for %s", repair_method, schema_name
            )

        return {**parsed, **diagnostics}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _failed_response(
    *,
    raw: str,
    schema_name: str,
    model: str,
    duration_ms: int,
    reason: str,
) -> dict:
    return {
        "_provider_diagnostics": {
            "provider": "ollama",
            "model": model,
            "schema_name": schema_name,
            "json_repair": "failed",
            "duration_ms": duration_ms,
            "parse_status": "failed",
            "failure_reason": reason,
        },
        "_raw_content": raw[:2000],
    }


class OllamaProviderError(RuntimeError):
    """Raised on unrecoverable network/HTTP errors from the Ollama provider."""
    pass
