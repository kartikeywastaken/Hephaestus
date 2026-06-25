# -*- coding: utf-8 -*-
"""
Phase 10 — AgentProvider abstract base class.

All providers must implement complete_json and check_available.
No mock provider is implemented in this file or anywhere in product code.
"""

from __future__ import annotations
from abc import ABC, abstractmethod


class AgentProvider(ABC):
    """Abstract base for LLM completion providers."""

    @abstractmethod
    def complete_json(
        self,
        *,
        system_prompt: str,
        user_payload: dict,
        schema_name: str,
    ) -> dict:
        """
        Send a prompt to the provider and return a parsed JSON dict.

        Implementations must:
          - POST to the provider's chat endpoint
          - Request JSON-format output
          - Use json_utils.extract_json for robust parsing
          - Embed _provider_diagnostics in the returned dict
          - Never silently discard parse errors

        Parameters
        ----------
        system_prompt:
            The full system prompt string including the common contract.
        user_payload:
            The user-turn dict (will be JSON-serialised into the message content).
        schema_name:
            A short label for logging/diagnostics (e.g. "evidence_agent").

        Returns
        -------
        dict
            Parsed response with _provider_diagnostics injected.
        """
        raise NotImplementedError

    @abstractmethod
    def check_available(self) -> dict:
        """
        Verify provider reachability and model availability.

        Returns
        -------
        dict with keys:
          available: bool
          host: str
          model: str
          error: str | None   (None when available)
          suggestion: str | None   (fix hint when not available)
        """
        raise NotImplementedError
