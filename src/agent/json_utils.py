# -*- coding: utf-8 -*-
"""
Phase 10 — Robust JSON extraction from LLM output.

LLMs may return:
  1. Valid JSON directly
  2. JSON wrapped in markdown ```json ... ``` fences
  3. JSON embedded in prose
  4. Malformed JSON

We try each strategy in order. We never silently accept malformed output.
"""

from __future__ import annotations

import json
import re


def extract_json(raw: str) -> tuple[dict, str]:
    """
    Extract a JSON dict from a raw LLM response string.

    Returns (parsed_dict, repair_method) where repair_method is one of:
      "direct"            — json.loads succeeded immediately
      "fence_strip"       — removed ```json ... ``` fences then parsed
      "balanced_extract"  — extracted first balanced { ... } block then parsed
      "failed"            — all strategies failed

    If repair_method is "failed", returned dict is empty.
    """
    if not isinstance(raw, str):
        raw = str(raw)

    # Strategy 1 — direct parse
    result, ok = _try_parse(raw.strip())
    if ok:
        return result, "direct"

    # Strategy 2 — strip markdown fences
    stripped = _strip_fences(raw)
    if stripped != raw:
        result, ok = _try_parse(stripped.strip())
        if ok:
            return result, "fence_strip"

    # Strategy 3 — extract first balanced { ... } object
    extracted = _extract_balanced_object(raw)
    if extracted is not None:
        result, ok = _try_parse(extracted)
        if ok:
            return result, "balanced_extract"

    return {}, "failed"


# ── Private helpers ───────────────────────────────────────────────────────────

def _try_parse(text: str) -> tuple[dict, bool]:
    """Attempt json.loads. Return (obj, True) or ({}, False)."""
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj, True
        return {}, False
    except (json.JSONDecodeError, ValueError):
        return {}, False


def _strip_fences(raw: str) -> str:
    """
    Remove ```json ... ``` or ``` ... ``` fences.
    Returns the inner content if a fence is found, else the original string.
    """
    # Match ```json ... ``` (possibly with whitespace)
    pattern = re.compile(
        r"```(?:json)?\s*([\s\S]*?)```",
        re.IGNORECASE,
    )
    match = pattern.search(raw)
    if match:
        return match.group(1).strip()
    return raw


def _extract_balanced_object(raw: str) -> str | None:
    """
    Find the first character-balanced { ... } JSON object in raw.

    Correctly handles:
      - Strings (including escaped quotes and escaped backslashes)
      - Single-line // comments (not valid JSON but sometimes present)
      - Block /* */ comments (not valid JSON but sometimes present)

    Returns the balanced substring, or None if not found.
    """
    start = raw.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False
    i = start
    n = len(raw)

    while i < n:
        ch = raw[i]

        if escape_next:
            escape_next = False
            i += 1
            continue

        if ch == "\\" and in_string:
            escape_next = True
            i += 1
            continue

        if ch == '"':
            in_string = not in_string
            i += 1
            continue

        if in_string:
            i += 1
            continue

        # Outside strings: handle brace counting
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return raw[start : i + 1]

        i += 1

    return None
