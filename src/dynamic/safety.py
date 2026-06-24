# -*- coding: utf-8 -*-
"""
Phase 8 — Dynamic Behavior Capture: safety guards.

All guards are called before any subprocess is launched.
No subprocess logic lives here — only validation and environment construction.
"""

from __future__ import annotations

import os
from pathlib import Path


class SafetyError(ValueError):
    """Raised when a safety guard fails."""


# ---------------------------------------------------------------------------
# Binary path validation
# ---------------------------------------------------------------------------

def validate_binary_path(path: str | Path) -> Path:
    """
    Resolve, check exists, check is a file, check is executable.
    Returns resolved Path.
    Raises SafetyError with a clear message on failure.
    """
    try:
        p = Path(path).resolve()
    except Exception as e:
        raise SafetyError(f"Cannot resolve binary path {path!r}: {e}") from e

    if not p.exists():
        raise SafetyError(f"Binary does not exist: {p}")
    if not p.is_file():
        raise SafetyError(f"Binary path is not a file: {p}")
    if not os.access(p, os.X_OK):
        raise SafetyError(f"Binary is not executable: {p}")

    return p


# ---------------------------------------------------------------------------
# argv validation
# ---------------------------------------------------------------------------

def validate_argv(argv: object) -> list[str]:
    """
    Ensure argv is list[str]. Raises SafetyError on non-string items.
    """
    if not isinstance(argv, list):
        raise SafetyError(
            f"argv must be a list, got {type(argv).__name__}"
        )
    result: list[str] = []
    for i, item in enumerate(argv):
        if not isinstance(item, str):
            raise SafetyError(
                f"argv[{i}] must be a string, got {type(item).__name__}: {item!r}"
            )
        result.append(item)
    return result


# ---------------------------------------------------------------------------
# Environment construction
# ---------------------------------------------------------------------------

def validate_env_overlay(env: object) -> dict[str, str]:
    """
    Ensure env is dict[str, str]. Rejects keys/values with null bytes.
    Raises SafetyError on invalid input.
    """
    if not isinstance(env, dict):
        raise SafetyError(
            f"env must be a dict, got {type(env).__name__}"
        )
    result: dict[str, str] = {}
    for k, v in env.items():
        if not isinstance(k, str):
            raise SafetyError(f"env key {k!r} must be a string")
        if "\x00" in k:
            raise SafetyError(f"env key {k!r} contains null bytes")
        if not isinstance(v, str):
            raise SafetyError(f"env[{k!r}] must be a string, got {type(v).__name__}")
        if "\x00" in v:
            raise SafetyError(f"env[{k!r}] value contains null bytes")
        result[k] = v
    return result


def build_safe_env(
    overlay: dict[str, str],
    *,
    inherit: bool = False,
) -> dict[str, str]:
    """
    Build the subprocess environment.

    inherit=False (default):
        Start from {"PATH": os.environ.get("PATH", "")}, then apply overlay.
        This minimises environment leakage.

    inherit=True:
        Start from os.environ.copy(), then apply overlay.
        Only used when --inherit-env is explicitly requested.
    """
    if inherit:
        base: dict[str, str] = dict(os.environ)
    else:
        base = {"PATH": os.environ.get("PATH", "")}

    base.update(overlay)
    return base


# ---------------------------------------------------------------------------
# Output truncation
# ---------------------------------------------------------------------------

def truncate_output(data: bytes, max_bytes: int) -> tuple[bytes, bool]:
    """
    Truncate data to max_bytes.
    Returns (truncated_data, was_truncated).
    """
    if len(data) > max_bytes:
        return data[:max_bytes], True
    return data, False
