# -*- coding: utf-8 -*-
"""
Phase 11 — Agent-Assisted Source Generation: provider bridge.

Reuses the Phase 10 provider layer (OllamaProvider and GroqProvider).
Supports:
  --provider ollama|groq
  --model MODEL
  --ollama-host URL
  --groq-host URL
  --api-key-env ENV_NAME
  --timeout-s N
  --temperature FLOAT
  --num-ctx N

API key handling for Groq:
  1. --api-key-env value (name of env var to read)
  2. GROQ_API_KEY
  3. HEPHAESTUS_GROQ_API_KEY
  → Fail cleanly if none found. Never print the key.

The provider bridge never writes Authorization headers or API keys
to artifacts, logs, or diagnostics.
"""

from __future__ import annotations

import argparse
import logging

from src.agent_source.models import SUPPORTED_PROVIDERS

logger = logging.getLogger("agent_source.provider_bridge")


class ProviderBridgeError(RuntimeError):
    """Raised when provider instantiation fails."""
    pass


def build_provider_from_args(
    args: argparse.Namespace,
) -> tuple[object, str, str, str | None]:
    """
    Instantiate the LLM provider from parsed CLI args.

    Returns
    -------
    (provider, provider_name, model_name, api_key_env_name_used)
    """
    from src.agent.models import (
        DEFAULT_OLLAMA_HOST, DEFAULT_OLLAMA_MODEL,
        DEFAULT_OLLAMA_TIMEOUT_S, DEFAULT_OLLAMA_TEMPERATURE,
        DEFAULT_OLLAMA_NUM_CTX,
    )
    from src.agent.providers.groq import (
        DEFAULT_GROQ_HOST, DEFAULT_GROQ_MODEL,
        resolve_groq_api_key, GroqApiKeyMissingError,
    )

    provider_name = getattr(args, "provider", "ollama")
    if provider_name not in SUPPORTED_PROVIDERS:
        raise ProviderBridgeError(
            f"Unsupported provider '{provider_name}'. "
            f"Supported: {', '.join(SUPPORTED_PROVIDERS)}"
        )

    timeout_s = getattr(args, "timeout_s", DEFAULT_OLLAMA_TIMEOUT_S)
    temperature = getattr(args, "temperature", DEFAULT_OLLAMA_TEMPERATURE)
    api_key_env = getattr(args, "api_key_env", None)

    if provider_name == "ollama":
        from src.agent.providers.ollama import OllamaProvider
        ollama_host = getattr(args, "ollama_host", None)
        model = getattr(args, "model", None) or DEFAULT_OLLAMA_MODEL
        num_ctx = getattr(args, "num_ctx", DEFAULT_OLLAMA_NUM_CTX)
        provider = OllamaProvider(
            host=ollama_host or DEFAULT_OLLAMA_HOST,
            model=model,
            timeout_s=timeout_s,
            temperature=temperature,
            num_ctx=num_ctx,
        )
        return provider, "ollama", model, None

    elif provider_name == "groq":
        from src.agent.providers.groq import GroqProvider
        try:
            api_key = resolve_groq_api_key(api_key_env=api_key_env)
        except GroqApiKeyMissingError as e:
            raise ProviderBridgeError(str(e)) from e

        import os
        api_key_env_used = api_key_env or (
            "GROQ_API_KEY"
            if os.environ.get("GROQ_API_KEY")
            else "HEPHAESTUS_GROQ_API_KEY"
        )

        groq_host = getattr(args, "groq_host", None)
        model = getattr(args, "model", None) or DEFAULT_GROQ_MODEL
        provider = GroqProvider(
            api_key=api_key,
            host=groq_host or DEFAULT_GROQ_HOST,
            model=model,
            timeout_s=timeout_s,
            temperature=temperature,
        )
        return provider, "groq", model, api_key_env_used

    else:
        raise ProviderBridgeError(
            f"Unknown provider '{provider_name}'. "
            f"Supported: {', '.join(SUPPORTED_PROVIDERS)}"
        )
