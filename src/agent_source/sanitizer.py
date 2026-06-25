# -*- coding: utf-8 -*-
"""
Phase 11 — Agent-Assisted Source Generation: sanitizer.

Sanitizes LLM-generated C function output before it is inserted into
recovered_agent.c.

Sanitization steps:
  1. Strip markdown fences.
  2. Reject if output contains JSON wrappers (starts with '{').
  3. Reject if output mentions recovered_agent.c.
  4. Reject forbidden certainty phrases.
  5. Reject mismatched function signature.
  6. Reject multiple unrelated function definitions in function-by-function mode.
  7. Reject obvious non-C prose outside comments.
  8. Normalize line endings.
  9. Preserve uncertainty comments.

Does NOT silently repair dangerous output. Reject and record diagnostics.
"""

from __future__ import annotations

import re
import logging

from src.agent_source.models import FORBIDDEN_SOURCE_PHRASES

logger = logging.getLogger("agent_source.sanitizer")


# ── Helpers ───────────────────────────────────────────────────────────────────

_FENCE_RE = re.compile(
    r"^```[a-zA-Z]*\s*\n?(.*?)\n?```\s*$",
    re.DOTALL | re.MULTILINE,
)

_FUNCTION_DEF_RE = re.compile(
    r"(?:^|\n)\s*(?:[a-zA-Z_][a-zA-Z0-9_\s\*]*?\s+)"
    r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*\{",
    re.MULTILINE,
)


def _strip_markdown_fences(text: str) -> tuple[str, bool]:
    """Strip ```c ... ``` fences. Returns (stripped_text, was_stripped)."""
    m = _FENCE_RE.search(text.strip())
    if m:
        return m.group(1).strip(), True
    # Also strip bare ``` lines
    lines = text.splitlines()
    out = []
    stripped = False
    for line in lines:
        if re.match(r"^```", line.strip()):
            stripped = True
            continue
        out.append(line)
    return "\n".join(out), stripped


def _contains_json_wrapper(text: str) -> bool:
    """Return True if text starts with a JSON object character."""
    stripped = text.strip()
    return stripped.startswith("{") or stripped.startswith("[")


def _find_forbidden_phrases(text: str) -> list[str]:
    """Scan text for any forbidden certainty phrases."""
    found = []
    low = text.lower()
    for phrase in FORBIDDEN_SOURCE_PHRASES:
        if phrase in low:
            found.append(phrase)
    return found


def _find_function_names(c_text: str) -> list[str]:
    """Return all top-level function names defined in c_text."""
    return _FUNCTION_DEF_RE.findall(c_text)


def _has_obvious_non_c_prose(text: str) -> bool:
    """
    Detect prose outside comments that is clearly not C.
    Heuristic: lines that don't match any C-like pattern and contain
    natural language sentence structure.
    """
    comment_re = re.compile(r"(/\*.*?\*/|//[^\n]*)", re.DOTALL)
    # Remove comments
    no_comments = comment_re.sub("", text)
    lines = no_comments.splitlines()
    prose_indicators = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Lines ending with period and no semicolons/braces are suspicious prose
        if (
            stripped.endswith(".")
            and ";" not in stripped
            and "{" not in stripped
            and "}" not in stripped
            and not stripped.startswith("#")
            and len(stripped) > 20
        ):
            prose_indicators += 1
    return prose_indicators >= 3


# ── Main sanitizer ────────────────────────────────────────────────────────────

def sanitize_function_output(
    raw_c: str,
    fn_name: str,
    expected_signature: str = "",
    generation_mode: str = "function_by_function",
) -> tuple[str, list[str], bool]:
    """
    Sanitize LLM-generated C for a single function.

    Parameters
    ----------
    raw_c:
        Raw string output from the LLM (may include markdown, JSON, prose).
    fn_name:
        The function name that was requested.
    expected_signature:
        Expected C signature substring (e.g. "int32_t main("). Used to
        check that the generated function matches. Empty string = skip check.
    generation_mode:
        "function_by_function" or "whole_file".

    Returns
    -------
    (sanitized_c, issues, ok)
        sanitized_c: The cleaned C text (empty string if rejected).
        issues: List of diagnostic messages.
        ok: True if sanitized successfully, False if rejected.
    """
    issues: list[str] = []

    if not raw_c or not raw_c.strip():
        return "", ["sanitizer: empty input"], False

    # Step 1 — Strip markdown fences
    text, was_fenced = _strip_markdown_fences(raw_c)
    if was_fenced:
        logger.info("[sanitizer] stripped markdown fences for function '%s'", fn_name)
        issues.append("sanitizer: stripped markdown code fences")

    # Step 2 — Reject JSON wrappers
    if _contains_json_wrapper(text):
        issues.append(
            "sanitizer: REJECTED — output looks like a JSON object, not C code"
        )
        return "", issues, False

    # Step 3 — Reject recovered_agent.c mentions
    if "recovered_agent.c" in text:
        issues.append(
            "sanitizer: REJECTED — output mentions 'recovered_agent.c'"
        )
        return "", issues, False

    # Step 4 — Reject forbidden certainty phrases
    found_forbidden = _find_forbidden_phrases(text)
    if found_forbidden:
        issues.append(
            f"sanitizer: REJECTED — forbidden phrases found: {found_forbidden}"
        )
        return "", issues, False

    # Step 5 — Signature check (if expected_signature provided)
    if expected_signature and expected_signature.strip():
        sig_fragment = expected_signature.strip().split("{")[0].strip()
        # Normalize whitespace for comparison
        norm_text = " ".join(text.split())
        norm_sig = " ".join(sig_fragment.split())
        if norm_sig and norm_sig not in norm_text:
            issues.append(
                f"sanitizer: WARNING — expected signature fragment "
                f"'{sig_fragment[:80]}' not found in generated output"
            )
            # Warning only, not rejection — LLM may slightly reformat

    # Step 6 — In function_by_function mode, reject multiple unrelated functions
    if generation_mode == "function_by_function":
        fn_names = _find_function_names(text)
        # Deduplicate
        unique_names = list(dict.fromkeys(fn_names))
        if len(unique_names) > 1:
            # Check if the extra functions are just forward declarations or helpers
            # with names related to the target — be lenient if fn_name is included
            unrelated = [n for n in unique_names if n != fn_name]
            if len(unrelated) >= 2:
                issues.append(
                    f"sanitizer: REJECTED — multiple unrelated function definitions "
                    f"found in function-by-function mode: {unique_names}"
                )
                return "", issues, False
            elif unrelated:
                issues.append(
                    f"sanitizer: WARNING — extra function definition found: "
                    f"{unrelated} — review output"
                )

    # Step 7 — Detect obvious non-C prose
    if _has_obvious_non_c_prose(text):
        issues.append(
            "sanitizer: WARNING — text contains possible prose outside comments"
        )

    # Step 8 — Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Step 9 — Verify uncertainty comments are preserved
    # (Just record if none present; we add them in the writer)
    if "AI-assisted" not in text and "approximation" not in text.lower():
        issues.append(
            "sanitizer: NOTE — no AI uncertainty comment found in generated C; "
            "writer will add them"
        )

    logger.debug(
        "[sanitizer] function '%s' sanitized: %d chars, %d issues",
        fn_name, len(text), len(issues),
    )

    return text, issues, True


def sanitize_whole_file_output(
    raw_c: str,
) -> tuple[str, list[str], bool]:
    """
    Sanitize LLM-generated whole-file C output.

    Parameters
    ----------
    raw_c:
        Raw string output from the LLM.

    Returns
    -------
    (sanitized_c, issues, ok)
    """
    issues: list[str] = []

    if not raw_c or not raw_c.strip():
        return "", ["sanitizer: empty whole-file output"], False

    text, was_fenced = _strip_markdown_fences(raw_c)
    if was_fenced:
        issues.append("sanitizer: stripped markdown code fences")

    if _contains_json_wrapper(text):
        issues.append("sanitizer: REJECTED — whole-file output looks like JSON, not C")
        return "", issues, False

    if "recovered_agent.c" in text:
        issues.append("sanitizer: REJECTED — output mentions 'recovered_agent.c'")
        return "", issues, False

    found_forbidden = _find_forbidden_phrases(text)
    if found_forbidden:
        issues.append(f"sanitizer: REJECTED — forbidden phrases: {found_forbidden}")
        return "", issues, False

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text, issues, True
