# -*- coding: utf-8 -*-
"""
Phase 10 — Groq cloud provider.

Uses urllib.request only (no third-party HTTP library required).
Endpoint: POST {host}/chat/completions  (OpenAI-compatible)

API key resolution order:
  1. Explicit api_key constructor argument
  2. --api-key-env CLI flag value (name of env var)
  3. GROQ_API_KEY environment variable
  4. HEPHAESTUS_GROQ_API_KEY environment variable
  → Fail cleanly if none found.

The API key is NEVER written to:
  - JSON artifacts
  - diagnostics
  - log messages
  - exceptions
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

logger = logging.getLogger("agent.providers.groq")

DEFAULT_GROQ_HOST  = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


def resolve_groq_api_key(
    explicit_key: str | None = None,
    api_key_env: str | None = None,
) -> str:
    """
    Resolve the Groq API key from the priority chain.

    Parameters
    ----------
    explicit_key:
        Key passed directly (e.g. for testing — never log it).
    api_key_env:
        Name of an environment variable to read (from --api-key-env flag).

    Returns
    -------
    str  — the resolved key.

    Raises
    ------
    GroqApiKeyMissingError if no key is found.
    """
    # 1. Explicit key (constructor or test)
    if explicit_key:
        return explicit_key

    # 2. Named env var from --api-key-env
    if api_key_env:
        val = os.environ.get(api_key_env, "").strip()
        if val:
            return val

    # 3. Standard env vars
    for env_name in ("GROQ_API_KEY", "HEPHAESTUS_GROQ_API_KEY"):
        val = os.environ.get(env_name, "").strip()
        if val:
            return val

    raise GroqApiKeyMissingError(
        "Groq API key missing. Set GROQ_API_KEY or HEPHAESTUS_GROQ_API_KEY."
    )


class GroqProvider(AgentProvider):
    """
    Real Groq cloud provider (OpenAI-compatible /chat/completions endpoint).

    The api_key is stored only in memory and never written to any artifact.
    """

    def __init__(
        self,
        *,
        api_key: str,
        host: str = DEFAULT_GROQ_HOST,
        model: str = DEFAULT_GROQ_MODEL,
        timeout_s: int = 300,
        temperature: float = 0.0,
        # num_ctx not used by Groq (cloud handles context window)
    ) -> None:
        self._api_key = api_key          # private — never log or serialize
        self.host = host.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self.temperature = temperature
        logger.debug(
            "[groq] host=%s model=%s timeout_s=%s temperature=%s",
            self.host, self.model, self.timeout_s, self.temperature,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def check_available(self) -> dict:
        """
        Check Groq API availability by listing models.

        Returns dict with:
          available: bool
          host: str
          model: str
          error: str | None
          suggestion: str | None
        """
        url = f"{self.host}/models"
        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                data = json.loads(raw)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return {
                    "available": False,
                    "host": self.host,
                    "model": self.model,
                    "error": "Groq API key rejected or expired (HTTP 401).",
                    "suggestion": "Set a valid GROQ_API_KEY environment variable.",
                }
            return {
                "available": False,
                "host": self.host,
                "model": self.model,
                "error": f"Groq API HTTP error: {e.code}",
                "suggestion": "Check GROQ_API_KEY and network connectivity.",
            }
        except urllib.error.URLError as e:
            return {
                "available": False,
                "host": self.host,
                "model": self.model,
                "error": f"Groq API unreachable: {e.reason}",
                "suggestion": "Check network connectivity.",
            }
        except Exception as e:
            return {
                "available": False,
                "host": self.host,
                "model": self.model,
                "error": f"Groq check unexpected error: {type(e).__name__}",
                "suggestion": "Check GROQ_API_KEY and network connectivity.",
            }

        # Verify model exists
        model_ids = [m.get("id", "") for m in data.get("data", [])]
        if self.model not in model_ids:
            return {
                "available": False,
                "host": self.host,
                "model": self.model,
                "error": (
                    f"Groq model not found: {self.model}. "
                    f"Available: {model_ids or '(none)'}"
                ),
                "suggestion": f"Use a supported model name. Check `groq.com` for available models.",
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
        POST /chat/completions and return parsed JSON dict.

        Injects _provider_diagnostics. Never includes the API key.
        """
        url = f"{self.host}/chat/completions"
        user_content = json.dumps(user_payload, ensure_ascii=False)

        body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_content},
            ],
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
        }

        body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body_bytes,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )

        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw_response = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            body_snippet = ""
            try:
                body_snippet = e.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            raise GroqProviderError(
                f"Groq HTTP {e.code} for schema '{schema_name}': {body_snippet}"
            ) from e
        except urllib.error.URLError as e:
            raise GroqProviderError(
                f"Groq network error for schema '{schema_name}': {e.reason}"
            ) from e
        except Exception as e:
            raise GroqProviderError(
                f"Groq unexpected error for schema '{schema_name}': {type(e).__name__}"
            ) from e

        duration_ms = int((time.perf_counter() - t0) * 1000)

        # Parse envelope
        try:
            envelope = json.loads(raw_response)
        except json.JSONDecodeError:
            logger.warning("[groq] envelope not JSON for %s", schema_name)
            return _failed_response(
                raw=raw_response,
                schema_name=schema_name,
                model=self.model,
                duration_ms=duration_ms,
                reason="envelope_not_json",
            )

        # Extract content from choices[0].message.content
        try:
            content = envelope["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            logger.warning("[groq] unexpected envelope shape for %s", schema_name)
            return _failed_response(
                raw=raw_response,
                schema_name=schema_name,
                model=self.model,
                duration_ms=duration_ms,
                reason="unexpected_envelope_shape",
            )

        if not isinstance(content, str):
            content = str(content)

        parsed, repair_method = extract_json(content)

        diagnostics = {
            "_provider_diagnostics": {
                "provider": "groq",
                "model": self.model,
                "schema_name": schema_name,
                "json_repair": repair_method,
                "duration_ms": duration_ms,
                "parse_status": "ok" if repair_method != "failed" else "failed",
                # api_key_env intentionally omitted — recorded at CLI level only
            }
        }

        if repair_method == "failed":
            logger.warning(
                "[groq] JSON extraction failed for %s (raw len=%d)",
                schema_name, len(content),
            )
            return {**diagnostics, "_raw_content": content[:2000]}

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
            "provider": "groq",
            "model": model,
            "schema_name": schema_name,
            "json_repair": "failed",
            "duration_ms": duration_ms,
            "parse_status": "failed",
            "failure_reason": reason,
        },
        "_raw_content": raw[:2000],
    }


class GroqApiKeyMissingError(RuntimeError):
    """Raised when no Groq API key can be resolved."""
    pass


class GroqProviderError(RuntimeError):
    """Raised on unrecoverable HTTP/network errors from the Groq provider."""
    pass
