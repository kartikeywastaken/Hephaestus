# -*- coding: utf-8 -*-
"""
Phase 11 — Agent-Assisted Source Generation: validator.

Validates recovered_agent.c after generation.

Checks:
  1. Warning header present.
  2. No forbidden certainty phrases.
  3. No markdown code fences.
  4. No JSON wrappers.
  5. No duplicate main function.
  6. All expected function names present (for function-by-function mode).
  7. Balanced top-level braces.
  8. Input artifact hashes unchanged (hash guard).
  9. clang -fsyntax-only if available.

Returns (ok, issues, clang_status)
  ok:           True if all hard checks pass.
  issues:       List of diagnostic strings.
  clang_status: "passed" | "failed" | "skipped" | "not_available"
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from src.agent_source.models import (
    WARNING_HEADER,
    FORBIDDEN_SOURCE_PHRASES,
)
from src.agent_source.loader import verify_phase11_hashes

logger = logging.getLogger("agent_source.validator")


def validate_agent_source(
    c_text: str,
    out_dir: Path,
    function_records: list[dict],
    *,
    hashes_before: dict[str, str | None] | None = None,
    expected_functions: list[str] | None = None,
) -> tuple[bool, list[str], str]:
    """
    Validate recovered_agent.c.

    Parameters
    ----------
    c_text:
        The full text of recovered_agent.c to validate.
    out_dir:
        Artifact output directory for hash verification.
    function_records:
        Per-function records from generator (used to compute expected names).
    hashes_before:
        SHA-256 hashes from before generation (for hash guard).
    expected_functions:
        Explicit list of expected function names; if None, derived from records.

    Returns
    -------
    (ok, issues, clang_status)
    """
    issues: list[str] = []
    ok = True

    # 1. Warning header
    if WARNING_HEADER.splitlines()[0].strip() not in c_text:
        issues.append(
            "validator: FAIL — warning header missing from recovered_agent.c"
        )
        ok = False
    else:
        issues.append("validator: ok — warning header present")

    # 2. Forbidden phrases — scan body AFTER the warning header
    # The warning header itself legitimately contains negation phrases like
    # "NOT claimed to be semantically equivalent" — that is allowed.
    # Strip the warning header from scan scope.
    header_end = c_text.find("*/")
    scan_text = c_text[header_end + 2:] if header_end != -1 else c_text
    low = scan_text.lower()
    for phrase in FORBIDDEN_SOURCE_PHRASES:
        if phrase in low:
            issues.append(
                f"validator: FAIL — forbidden phrase found: '{phrase}'"
            )
            ok = False

    # 3. No markdown fences
    if "```" in c_text:
        issues.append(
            "validator: FAIL — markdown code fences found in recovered_agent.c"
        )
        ok = False

    # 4. No JSON wrappers at file level (single { as first char)
    stripped = c_text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        issues.append(
            "validator: FAIL — file appears to be a JSON object, not C source"
        )
        ok = False

    # 5. No duplicate main
    main_matches = len(re.findall(r"(?:^|\n)\s*[a-zA-Z_][a-zA-Z0-9_\s\*]*\bmain\s*\(", c_text))
    if main_matches > 1:
        issues.append(
            f"validator: FAIL — duplicate 'main' definitions found ({main_matches})"
        )
        ok = False

    # 6. Expected functions present
    fn_names = expected_functions
    if fn_names is None:
        fn_names = [
            r.get("c_name") or r.get("function", "")
            for r in function_records
            if r.get("generated") and r.get("status") == "ok"
        ]

    missing_fns = []
    for fn_name in fn_names:
        if not fn_name:
            continue
        pattern = re.compile(
            r"(?:^|\n)(?:[a-zA-Z_][a-zA-Z0-9_\s\*]*\s+)?"
            + re.escape(fn_name)
            + r"\s*\(",
            re.MULTILINE,
        )
        if not pattern.search(c_text):
            missing_fns.append(fn_name)

    if missing_fns:
        issues.append(
            f"validator: WARNING — expected functions not found in recovered_agent.c: "
            f"{missing_fns}"
        )
        # Not a hard fail — fallback functions may be from recovered_readable.c

    # 7. Balanced top-level braces
    if not _check_balanced_braces(c_text):
        issues.append(
            "validator: FAIL — unbalanced braces in recovered_agent.c"
        )
        ok = False
    else:
        issues.append("validator: ok — braces balanced")

    # 8. Hash guard
    if hashes_before:
        changed = verify_phase11_hashes(out_dir, hashes_before)
        if changed:
            issues.append(
                f"validator: ABORT — guarded artifacts changed during generation: "
                f"{changed}"
            )
            ok = False
        else:
            issues.append("validator: ok — guarded artifact hashes unchanged")

    # 9. clang -fsyntax-only
    clang_status = _run_clang_syntax_check(c_text)
    issues.append(f"validator: clang_status={clang_status}")

    return ok, issues, clang_status


def _check_balanced_braces(c_text: str) -> bool:
    """Check that top-level braces are balanced (ignoring braces in strings/comments)."""
    depth = 0
    in_string = in_char = in_block_comment = in_line_comment = escape_next = False
    for i, ch in enumerate(c_text):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and (in_string or in_char):
            escape_next = True
            continue
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            continue
        if in_block_comment:
            if ch == "*" and i + 1 < len(c_text) and c_text[i + 1] == "/":
                in_block_comment = False
            continue
        if in_string:
            if ch == '"':
                in_string = False
            continue
        if in_char:
            if ch == "'":
                in_char = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "'":
            in_char = True
        elif ch == "/" and i + 1 < len(c_text) and c_text[i + 1] == "*":
            in_block_comment = True
        elif ch == "/" and i + 1 < len(c_text) and c_text[i + 1] == "/":
            in_line_comment = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1

    return depth == 0


def _run_clang_syntax_check(c_text: str) -> str:
    """
    Run `clang -fsyntax-only` on c_text.

    Returns "passed" | "failed" | "not_available" | "error".
    """
    clang_path = shutil.which("clang")
    if not clang_path:
        return "not_available"

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".c", mode="w", encoding="utf-8", delete=False
        ) as tf:
            tf.write(c_text)
            tf_path = tf.name

        result = subprocess.run(
            [clang_path, "-fsyntax-only", "-w", tf_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return "passed"
        logger.info(
            "[validator] clang syntax check failed for recovered_agent.c:\n%s",
            (result.stderr or result.stdout)[:2000],
        )
        return "failed"

    except subprocess.TimeoutExpired:
        logger.warning("[validator] clang syntax check timed out")
        return "error"
    except Exception as e:
        logger.warning("[validator] clang syntax check error: %s", e)
        return "error"
    finally:
        import os
        try:
            os.unlink(tf_path)
        except Exception:
            pass
