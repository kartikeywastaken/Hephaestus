# -*- coding: utf-8 -*-
"""
Phase 11.6 — Automatic dynamic input generation.

Generates safe default argv test cases when the user does not provide
enough inputs or explicitly requests auto-generation.

All generated inputs:
  - Pass ``validate_argv()`` from ``safety.py``
  - Contain no shell metacharacters requiring ``shell=True``
  - Do not mutate the environment
  - Do not produce filesystem or network side effects
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.dynamic.safety import validate_argv


# ── Default safe argv cases ───────────────────────────────────────────────────

_DEFAULT_ARGV_CASES: list[list[str]] = [
    [],
    [""],
    ["a"],
    ["A"],
    ["AA"],
    ["AAAA"],
    ["AAAAAAAAAA"],
    ["hello"],
    ["world"],
    ["hello", "world"],
    ["0"],
    ["1"],
    ["-1"],
    ["123"],
    ["999999"],
    ["%s"],
    ["../../x"],
]


# ── Public API ────────────────────────────────────────────────────────────────

def generate_default_input_cases(*, max_cases: int = 20) -> list[dict]:
    """
    Return safe default argv test cases.

    Must not include shell execution.
    Must not include env mutation.
    Must not include filesystem/network side effects.

    Returns list of ``{"argv": [...], "stdin": "", "env": {}}`` dicts,
    limited to ``max_cases``.
    """
    cases: list[dict] = []
    for argv in _DEFAULT_ARGV_CASES:
        if len(cases) >= max_cases:
            break
        # Validate safety
        try:
            validate_argv(argv)
        except Exception:
            continue  # skip unsafe inputs (should not happen with our defaults)
        cases.append({
            "argv": argv,
            "stdin": "",
            "env": {},
        })
    return cases


def _argv_canonical_key(argv: list[str]) -> str:
    """Canonical string key for deduplication."""
    return repr(argv)


def merge_and_deduplicate(
    user_cases: list[dict],
    generated_cases: list[dict],
) -> list[dict]:
    """
    Merge user-provided and generated cases.

    - User cases take priority (appear first).
    - Deduplicates by argv canonical key.
    - Preserves original ordering within each group.
    """
    seen: set[str] = set()
    merged: list[dict] = []

    for case in user_cases:
        key = _argv_canonical_key(case.get("argv", []))
        if key not in seen:
            seen.add(key)
            merged.append(case)

    for case in generated_cases:
        key = _argv_canonical_key(case.get("argv", []))
        if key not in seen:
            seen.add(key)
            merged.append(case)

    return merged


def build_input_spec_from_cases(
    cases: list[dict],
    *,
    generated: bool = False,
    generation_strategy: str = "default_safe_argv_cases",
    max_cases: int = 20,
) -> dict:
    """
    Build a full input spec dict from a list of cases.

    Each case is converted to a named run entry.
    """
    runs: list[dict] = []
    for idx, case in enumerate(cases):
        argv = case.get("argv", [])
        runs.append({
            "name": f"case_{idx}",
            "argv": argv,
            "stdin": case.get("stdin", ""),
            "env": case.get("env", {}),
        })

    return {
        "schema_version": "dynamic-inputs-generated-1.0",
        "generated": generated,
        "cases": cases,
        "generation_strategy": generation_strategy,
        "limits": {
            "max_cases": max_cases,
        },
        "runs": runs,
    }


def write_generated_inputs_artifact(
    cases: list[dict],
    out_dir: Path,
    *,
    generation_strategy: str = "default_safe_argv_cases",
    max_cases: int = 20,
) -> Path:
    """
    Write ``dynamic_inputs.generated.json`` artifact.

    Returns the path to the written file.
    """
    spec = build_input_spec_from_cases(
        cases,
        generated=True,
        generation_strategy=generation_strategy,
        max_cases=max_cases,
    )
    out_path = out_dir / "dynamic_inputs.generated.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
    return out_path
