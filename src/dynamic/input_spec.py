# -*- coding: utf-8 -*-
"""
Phase 8 — Dynamic Behavior Capture: input spec loader and validator.

Loads and validates dynamic_inputs.json files.
If no file is provided, returns the default single-run spec.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.dynamic.models import default_input_spec


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _has_null_byte(s: str) -> bool:
    return "\x00" in s


def _validate_run(run: Any, idx: int) -> list[str]:
    """Validate a single run entry. Returns list of error strings."""
    errors: list[str] = []
    prefix = f"runs[{idx}]"

    if not isinstance(run, dict):
        errors.append(f"{prefix}: must be a dict, got {type(run).__name__}")
        return errors

    # name
    name = run.get("name")
    if not isinstance(name, str) or not name:
        errors.append(f"{prefix}.name: must be a non-empty string")
    elif _has_null_byte(name):
        errors.append(f"{prefix}.name: must not contain null bytes")

    # argv
    argv = run.get("argv")
    if argv is None:
        errors.append(f"{prefix}.argv: missing (must be a list of strings)")
    elif not isinstance(argv, list):
        errors.append(f"{prefix}.argv: must be a list, got {type(argv).__name__}")
    else:
        for i, item in enumerate(argv):
            if not isinstance(item, str):
                errors.append(
                    f"{prefix}.argv[{i}]: must be a string, got {type(item).__name__}"
                )
            elif _has_null_byte(item):
                errors.append(f"{prefix}.argv[{i}]: must not contain null bytes")

    # stdin
    stdin = run.get("stdin", "")
    if not isinstance(stdin, str):
        errors.append(f"{prefix}.stdin: must be a string, got {type(stdin).__name__}")
    elif _has_null_byte(stdin):
        errors.append(f"{prefix}.stdin: must not contain null bytes")

    # env
    env = run.get("env", {})
    if not isinstance(env, dict):
        errors.append(f"{prefix}.env: must be a dict, got {type(env).__name__}")
    else:
        for k, v in env.items():
            if not isinstance(k, str):
                errors.append(f"{prefix}.env key {k!r}: must be a string")
            elif _has_null_byte(k):
                errors.append(f"{prefix}.env key {k!r}: must not contain null bytes")
            if not isinstance(v, str):
                errors.append(
                    f"{prefix}.env[{k!r}]: must be a string, got {type(v).__name__}"
                )
            elif _has_null_byte(v):
                errors.append(f"{prefix}.env[{k!r}]: must not contain null bytes")

    return errors


def validate_input_spec(spec: dict) -> list[str]:
    """
    Validate a dynamic inputs spec dict.
    Returns a list of error strings. Empty list = valid.
    """
    errors: list[str] = []

    if not isinstance(spec, dict):
        return ["Input spec must be a JSON object (dict)"]

    # schema_version
    sv = spec.get("schema_version")
    if not isinstance(sv, str) or not sv:
        errors.append("schema_version: must be a non-empty string")

    # runs
    runs = spec.get("runs")
    if runs is None:
        errors.append("runs: missing")
        return errors
    if not isinstance(runs, list):
        errors.append(f"runs: must be a list, got {type(runs).__name__}")
        return errors
    if len(runs) == 0:
        errors.append("runs: must be a non-empty list")
        return errors

    # Validate each run
    for idx, run in enumerate(runs):
        errors.extend(_validate_run(run, idx))

    # Unique names
    names = [r.get("name") for r in runs if isinstance(r, dict)]
    seen: set[str] = set()
    for name in names:
        if isinstance(name, str):
            if name in seen:
                errors.append(f"runs: duplicate name {name!r}")
            seen.add(name)

    return errors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_input_spec(path: str | Path) -> dict:
    """
    Load and validate a dynamic_inputs.json file.
    Raises ValueError with human-readable message if invalid.
    Raises FileNotFoundError if the file does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Dynamic inputs file not found: {p}")

    try:
        with p.open("r", encoding="utf-8") as f:
            spec = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Dynamic inputs file is not valid JSON: {e}") from e

    errors = validate_input_spec(spec)
    if errors:
        msg = "\n".join(f"  - {e}" for e in errors)
        raise ValueError(f"Dynamic inputs spec validation failed:\n{msg}")

    return spec


def resolve_input_spec(inputs_path: str | Path | None) -> tuple[dict, bool]:
    """
    Resolve the input spec to use.

    Returns:
        (spec, using_default) where using_default=True if no file was given.

    Raises:
        ValueError / FileNotFoundError on invalid/missing file when path is provided.
    """
    if inputs_path is None:
        return default_input_spec(), True
    return load_input_spec(inputs_path), False
