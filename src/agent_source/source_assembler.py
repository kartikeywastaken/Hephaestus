# -*- coding: utf-8 -*-
"""
Phase 11.8 — Safe Source Assembler.

Provides a brace-tracking parser to identify top-level C function spans
and a safe replacement function that preserves the entire file structure
(prelude, helpers, non-target functions, comments, typedefs) exactly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class FunctionSpan:
    """Represents a top-level C function in source text."""
    name: str
    start: int        # byte offset of first char of return type / signature
    end: int          # byte offset just past the closing '}'
    signature: str    # full signature line (return type + name + params)
    body: str         # full function text including signature and braces


def _skip_comment_or_string(text: str, i: int, n: int):
    """
    If position i starts a comment or string literal, skip past it.
    Returns (new_position, was_skipped).
    """
    ch = text[i]

    # Block comment
    if ch == '/' and i + 1 < n and text[i + 1] == '*':
        j = text.find('*/', i + 2)
        if j == -1:
            return n, True
        return j + 2, True

    # Line comment
    if ch == '/' and i + 1 < n and text[i + 1] == '/':
        j = text.find('\n', i + 2)
        if j == -1:
            return n, True
        return j + 1, True

    # String literal
    if ch == '"':
        j = i + 1
        while j < n:
            if text[j] == '\\':
                j += 2
                continue
            if text[j] == '"':
                return j + 1, True
            j += 1
        return n, True

    # Char literal
    if ch == "'":
        j = i + 1
        while j < n:
            if text[j] == '\\':
                j += 2
                continue
            if text[j] == "'":
                return j + 1, True
            j += 1
        return n, True

    return i, False


def find_top_level_functions(c_text: str) -> list[FunctionSpan]:
    """
    Parse top-level C function definitions from source text.

    Uses a brace-tracking state machine that properly handles
    comments, string literals, and char literals.

    Returns a list of FunctionSpan in source order.
    """
    results: list[FunctionSpan] = []
    n = len(c_text)

    # Regex to match a function signature at top-level:
    #   optional return-type tokens, function name, parameter list, opening brace
    sig_pattern = re.compile(
        r'(?:^|\n)'
        r'((?:[a-zA-Z_][a-zA-Z0-9_\s\*]*?\s+)?'
        r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\))'
        r'\s*\{',
        re.MULTILINE,
    )

    for m in sig_pattern.finditer(c_text):
        signature = m.group(1).strip()
        name = m.group(2)
        # Find the opening brace position
        brace_pos = m.end() - 1
        assert c_text[brace_pos] == '{'

        # Determine the true start of this function (beginning of the line)
        line_start = c_text.rfind('\n', 0, m.start() + 1)
        if line_start < 0:
            func_start = 0
        else:
            func_start = line_start + 1

        # Verify this is top-level: no unmatched '{' before this position
        # that would indicate we're inside another function.
        # Quick check: scan from func_start backward to see depth.
        # For efficiency, just check if any existing span covers this position.
        inside_existing = False
        for existing in results:
            if existing.start <= func_start < existing.end:
                inside_existing = True
                break
        if inside_existing:
            continue

        # Track braces to find the matching closing '}'
        depth = 1
        i = brace_pos + 1
        while i < n and depth > 0:
            new_i, skipped = _skip_comment_or_string(c_text, i, n)
            if skipped:
                i = new_i
                continue
            ch = c_text[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
            i += 1

        if depth != 0:
            # Unbalanced braces — skip this function
            continue

        func_end = i  # just past the closing '}'
        body = c_text[func_start:func_end]
        results.append(FunctionSpan(
            name=name,
            start=func_start,
            end=func_end,
            signature=signature,
            body=body,
        ))

    return results


def replace_function_body_preserving_file(
    base_text: str,
    function_name: str,
    replacement_function_text: str,
) -> tuple[str, bool, list[str]]:
    """
    Replace a single top-level function in base_text with replacement_function_text,
    preserving everything else (prelude, helpers, non-target functions, comments) exactly.

    Parameters
    ----------
    base_text:
        The full C source file text.
    function_name:
        Name of the function to replace.
    replacement_function_text:
        The replacement function text (full signature + body).

    Returns
    -------
    (new_text, replaced, diagnostics)
        new_text: The resulting source text.
        replaced: True if replacement was performed.
        diagnostics: List of diagnostic messages.
    """
    diagnostics: list[str] = []
    spans = find_top_level_functions(base_text)

    target_span = None
    for span in spans:
        if span.name == function_name:
            target_span = span
            break

    if target_span is None:
        diagnostics.append(
            f"source_assembler: function '{function_name}' not found in base text — no replacement performed"
        )
        return base_text, False, diagnostics

    # Validate replacement text has balanced braces
    replacement_stripped = replacement_function_text.strip()
    depth = 0
    temp_i = 0
    temp_n = len(replacement_stripped)
    while temp_i < temp_n:
        new_i, skipped = _skip_comment_or_string(replacement_stripped, temp_i, temp_n)
        if skipped:
            temp_i = new_i
            continue
        ch = replacement_stripped[temp_i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
        temp_i += 1

    if depth != 0:
        diagnostics.append(
            f"source_assembler: replacement for '{function_name}' has unbalanced braces (depth={depth}) — no replacement performed"
        )
        return base_text, False, diagnostics

    # Perform the replacement
    new_text = base_text[:target_span.start] + replacement_stripped + base_text[target_span.end:]

    diagnostics.append(
        f"source_assembler: replaced function '{function_name}' "
        f"(original {target_span.end - target_span.start} bytes → {len(replacement_stripped)} bytes)"
    )

    return new_text, True, diagnostics
