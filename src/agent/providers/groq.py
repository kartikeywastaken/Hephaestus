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
import re
import time
import urllib.error
import urllib.request
from typing import Any

from src.agent.providers.base import AgentProvider
from src.agent.json_utils import extract_json

logger = logging.getLogger("agent.providers.groq")

DEFAULT_GROQ_HOST  = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

_USER_AGENT = "Hephaestus/1.0 Python urllib"


# ── Secret redaction ──────────────────────────────────────────────────────────

def _redact_secrets(text: str, api_key: str | None = None) -> str:
    """
    Remove API key material from a string before it is used in error messages
    or logs.  Never store or print the key itself.
    """
    if not text:
        return text
    redacted = text
    # Redact the literal key value if we know it
    if api_key:
        redacted = redacted.replace(api_key, "[REDACTED_API_KEY]")
    # Defensively redact common Groq key prefixes
    redacted = re.sub(r"gsk_[A-Za-z0-9_\-]+", "gsk_[REDACTED]", redacted)
    # Redact bare Bearer tokens
    redacted = re.sub(
        r"Bearer\s+[A-Za-z0-9_\-\.]+", "Bearer [REDACTED]", redacted
    )
    return redacted


# ── Request helpers ───────────────────────────────────────────────────────────

def _make_headers(api_key: str) -> dict[str, str]:
    """
    Build the canonical Groq request headers.

    Every outgoing request (GET /models and POST /chat/completions) MUST use
    these headers so that Groq's API fingerprinting accepts the request.
    """
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": _USER_AGENT,
    }


def _read_error_body(exc: urllib.error.HTTPError, api_key: str | None) -> str:
    """
    Safely read and redact the response body from an HTTPError.

    Returns at most 1 000 characters so error messages stay readable.
    """
    try:
        raw = exc.read().decode("utf-8", errors="replace")
    except Exception:
        raw = ""
    return _redact_secrets(raw, api_key)[:1000]


# ── Key resolution ────────────────────────────────────────────────────────────

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


# ── Provider ──────────────────────────────────────────────────────────────────

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
            headers=_make_headers(self._api_key),
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                data = json.loads(raw)
        except urllib.error.HTTPError as e:
            body = _read_error_body(e, self._api_key)
            if e.code == 401:
                return {
                    "available": False,
                    "host": self.host,
                    "model": self.model,
                    "error": f"Groq API key rejected or expired (HTTP 401): {body}",
                    "suggestion": "Set a valid GROQ_API_KEY environment variable.",
                }
            if e.code == 403:
                return {
                    "available": False,
                    "host": self.host,
                    "model": self.model,
                    "error": f"Groq API access forbidden (HTTP 403): {body}",
                    "suggestion": (
                        "Check that your GROQ_API_KEY is active and the endpoint "
                        "is correct. Body: " + body
                    ),
                }
            return {
                "available": False,
                "host": self.host,
                "model": self.model,
                "error": f"Groq API HTTP error: {e.code}: {body}",
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
        except json.JSONDecodeError:
            return {
                "available": False,
                "host": self.host,
                "model": self.model,
                "error": "Groq /models response was not valid JSON.",
                "suggestion": "Check GROQ_API_KEY and network connectivity.",
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
                "suggestion": "Use a supported model name. Check `groq.com` for available models.",
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
            headers=_make_headers(self._api_key),
        )

        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw_response = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            body_snippet = _read_error_body(e, self._api_key)
            if e.code == 413:
                raise GroqPayloadTooLargeError(
                    f"Groq HTTP 413 for schema '{schema_name}': payload too large. {body_snippet}",
                    schema_name=schema_name,
                    body_snippet=body_snippet,
                ) from e
            if e.code == 429:
                # Try to parse retry-after from header or body
                retry_after_s = _parse_retry_after(e, body_snippet)
                raise GroqRateLimitError(
                    f"Groq HTTP 429 for schema '{schema_name}': rate limited. {body_snippet}",
                    schema_name=schema_name,
                    retry_after_s=retry_after_s,
                    body_snippet=body_snippet,
                ) from e
            raise GroqProviderError(
                f"Groq HTTP {e.code} for schema '{schema_name}': {body_snippet}"
            ) from e
        except urllib.error.URLError as e:
            raise GroqProviderError(
                f"Groq network error for schema '{schema_name}': {e.reason}"
            ) from e
        except TimeoutError:
            raise GroqProviderError(
                f"Groq request timed out after {self.timeout_s}s for schema '{schema_name}'"
            )
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


class GroqPayloadTooLargeError(GroqProviderError):
    """Raised on HTTP 413 — payload exceeds Groq's context/token limit."""
    def __init__(self, msg: str, *, schema_name: str = "", body_snippet: str = ""):
        super().__init__(msg)
        self.schema_name = schema_name
        self.body_snippet = body_snippet


class GroqRateLimitError(GroqProviderError):
    """Raised on HTTP 429 — Groq rate limit exceeded."""
    def __init__(
        self,
        msg: str,
        *,
        schema_name: str = "",
        retry_after_s: float | None = None,
        body_snippet: str = "",
    ):
        super().__init__(msg)
        self.schema_name = schema_name
        self.retry_after_s = retry_after_s
        self.body_snippet = body_snippet


def _parse_retry_after(
    exc: urllib.error.HTTPError,
    body_snippet: str,
) -> float | None:
    """
    Extract retry-after delay from the HTTP 429 response.

    Checks:
      1. Retry-After header (seconds or date)
      2. Body JSON field (e.g. Groq's "error.message" with delay)
    Returns None if not parseable.
    """
    import re as _re

    # 1. Header
    retry_hdr = exc.headers.get("Retry-After") if exc.headers else None
    if retry_hdr:
        try:
            return float(retry_hdr)
        except (ValueError, TypeError):
            pass

    # 2. Body — look for "Please try again in Xs" or similar
    match = _re.search(r"try again in ([\d.]+)s", body_snippet)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            pass

    return None
