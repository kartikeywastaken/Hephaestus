# -*- coding: utf-8 -*-
"""
Shared Token-Safe C Scanning Utilities

Provides conservative C source text decomposition and identifier extraction
used by Phase 5 (source reconstruction) and Phase 7 (readability) passes.

Functions here must never fabricate evidence — they only inspect text that
already exists in emitted C bodies.

Core invariant: identifiers that appear only inside string literals, character
literals, line comments, or block comments must NEVER be counted as executable
code usages.
"""

from __future__ import annotations

import re
from typing import List, Set, Tuple


def split_c_line(
    line: str,
    inside_block_comment: bool,
) -> Tuple[List[Tuple[str, str]], bool]:
    """
    Statefully split one C source line into (type, content) chunks.

    Chunk types:
        "code"    — executable C text (identifiers here matter)
        "comment" — // line comment or /* ... */ block comment content
        "string"  — double-quoted string literal or single-quoted char literal

    Parameters
    ----------
    line                 : Raw source line (may contain \\n / \\r\\n).
    inside_block_comment : Whether we are currently inside a /* ... */ comment
                           that started on a previous line.

    Returns
    -------
    (chunks, still_inside_block_comment)
    """
    chunks: List[Tuple[str, str]] = []
    n = len(line)
    i = 0
    current_code: List[str] = []

    def flush_code() -> None:
        if current_code:
            chunks.append(("code", "".join(current_code)))
            current_code.clear()

    while i < n:
        if inside_block_comment:
            # Scan for the closing */ marker.
            # Emit the content before */ as one chunk, then */ as a separate chunk,
            # so callers can detect the exact boundary (matches original contract).
            end_idx = line.find("*/", i)
            if end_idx != -1:
                if end_idx > i:
                    chunks.append(("comment", line[i:end_idx]))
                chunks.append(("comment", "*/"))
                i = end_idx + 2
                inside_block_comment = False
            else:
                chunks.append(("comment", line[i:]))
                i = n
        else:
            if i + 1 < n and line[i : i + 2] == "/*":
                flush_code()
                inside_block_comment = True
                # Emit the opening marker as its own chunk (original contract)
                chunks.append(("comment", "/*"))
                i += 2
            elif i + 1 < n and line[i : i + 2] == "//":
                flush_code()
                chunks.append(("comment", line[i:]))
                i = n
            elif line[i] == '"':
                flush_code()
                j = i + 1
                escaped = False
                while j < n:
                    c = line[j]
                    if escaped:
                        escaped = False
                    elif c == "\\":
                        escaped = True
                    elif c == '"':
                        j += 1
                        break
                    j += 1
                chunks.append(("string", line[i:j]))
                i = j
            elif line[i] == "'":
                flush_code()
                j = i + 1
                escaped = False
                while j < n:
                    c = line[j]
                    if escaped:
                        escaped = False
                    elif c == "\\":
                        escaped = True
                    elif c == "'":
                        j += 1
                        break
                    j += 1
                chunks.append(("string", line[i:j]))
                i = j
            else:
                current_code.append(line[i])
                i += 1

    flush_code()
    return chunks, inside_block_comment


# Identifiers that are helpers rather than real code variables and should be
# excluded from executable-usage scanning.
_HEPHAESTUS_HELPER_NAMES: Set[str] = {
    "HEPHAESTUS_UNKNOWN_COND",
    "HEPHAESTUS_CSET",
}

_IDENTIFIER_RE = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b")


def collect_identifiers_from_code_only(lines: List[str]) -> Set[str]:
    """
    Return the set of all C identifiers that appear in executable code chunks
    of the given source lines.

    Identifiers that appear ONLY inside:
        - double-quoted string literals
        - single-quoted char literals
        - // line comments
        - /* block comments */
        - HEPHAESTUS_UNKNOWN_COND(...) or HEPHAESTUS_CSET(...) evidence strings

    are explicitly excluded. Only code-chunk identifiers count.

    Parameters
    ----------
    lines : Source lines (may contain line endings).

    Returns
    -------
    Set of identifier strings found in executable code positions.
    """
    found: Set[str] = set()
    inside_block_comment = False

    for line in lines:
        chunks, inside_block_comment = split_c_line(line, inside_block_comment)
        for chunk_type, content in chunks:
            if chunk_type == "code":
                for word in _IDENTIFIER_RE.findall(content):
                    if word not in _HEPHAESTUS_HELPER_NAMES:
                        found.add(word)

    return found
