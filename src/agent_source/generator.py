# -*- coding: utf-8 -*-
"""
Phase 11 — Agent-Assisted Source Generation: source generator.

Implements two generation modes:
  function_by_function  (default)
    1. Slice each function from recovered_readable.c.
    2. Build function-specific approved plan.
    3. Send one function payload to provider.
    4. Parse JSON response.
    5. Sanitize generated function C.
    6. Replace that function in a working copy.
    7. Non-generated functions copied from recovered_readable.c unchanged.

  whole_file
    1. Send the entire recovered_readable.c as baseline.
    2. Parse JSON response.
    3. Sanitize the whole output.
    4. Write as-is.

Supports:
  --max-functions N
  --function NAME
  --fail-fast

Failed provider calls: record function failure,
copy original recovered_readable.c function unchanged,
continue unless --fail-fast.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from src.agent_source.models import (
    DEFAULT_MAX_SLICE_LINES,
    SLICE_TRUNCATION_COMMENT,
    FORBIDDEN_SOURCE_PHRASES,
    WARNING_HEADER,
)
from src.agent_source.plan_builder import (
    get_approved_transforms_for_function,
    get_forbidden_transforms,
)
from src.agent_source.prompts import build_system_prompt, build_user_payload
from src.agent_source.sanitizer import sanitize_function_output, sanitize_whole_file_output

logger = logging.getLogger("agent_source.generator")


class GeneratorFailFastError(RuntimeError):
    """Raised when fail_fast=True and a function fails."""
    pass


# ── C slicer (reuse logic from agent.packet_builder) ─────────────────────────

def _extract_function_slice(
    c_source: str,
    function_name: str,
    max_lines: int = DEFAULT_MAX_SLICE_LINES,
) -> tuple[str, list[str]]:
    """
    Extract function body from C source using a brace-counting state machine
    that ignores braces inside strings, char literals, and comments.

    Returns (slice_text, diagnostics).
    """
    diagnostics: list[str] = []

    pattern = re.compile(
        r"(?:^|\n)(?:[a-zA-Z_][a-zA-Z0-9_\s\*]*?\s+)?"
        + re.escape(function_name)
        + r"\s*\([^)]*\)\s*\{",
        re.MULTILINE,
    )
    match = pattern.search(c_source)
    if not match:
        diagnostics.append(f"function_slice: '{function_name}' not found in C source")
        return "", diagnostics

    body_start = match.end() - 1  # include the '{'
    depth = 0
    in_string = in_char = in_block_comment = in_line_comment = escape_next = False

    i = body_start
    n = len(c_source)
    while i < n:
        ch = c_source[i]
        if escape_next:
            escape_next = False
            i += 1
            continue
        if ch == "\\" and (in_string or in_char):
            escape_next = True
            i += 1
            continue
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and i + 1 < n and c_source[i + 1] == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue
        if in_string:
            if ch == '"':
                in_string = False
            i += 1
            continue
        if in_char:
            if ch == "'":
                in_char = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            i += 1
            continue
        if ch == "'":
            in_char = True
            i += 1
            continue
        if ch == "/" and i + 1 < n and c_source[i + 1] == "*":
            in_block_comment = True
            i += 2
            continue
        if ch == "/" and i + 1 < n and c_source[i + 1] == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                raw_slice = c_source[body_start: i + 1]
                lines = raw_slice.splitlines()
                if len(lines) > max_lines:
                    truncated = "\n".join(lines[:max_lines])
                    truncated += "\n" + SLICE_TRUNCATION_COMMENT.format(max_lines=max_lines)
                    diagnostics.append(
                        f"function_slice: '{function_name}' truncated at {max_lines} lines"
                    )
                    return truncated, diagnostics
                return raw_slice, diagnostics
        i += 1

    diagnostics.append(
        f"function_slice: '{function_name}' — unbalanced braces or truncated source"
    )
    return "", diagnostics


def _extract_function_header(
    c_source: str,
    function_name: str,
) -> str:
    """Extract the function declaration line (return type + signature) before the body."""
    pattern = re.compile(
        r"(?:^|\n)((?:[a-zA-Z_][a-zA-Z0-9_\s\*]*?\s+)?"
        + re.escape(function_name)
        + r"\s*\([^)]*\))\s*\{",
        re.MULTILINE,
    )
    m = pattern.search(c_source)
    if m:
        return m.group(1).strip()
    return ""


def _extract_function_with_header(
    c_source: str,
    function_name: str,
    fallback_names: list[str] | None = None,
    max_lines: int = DEFAULT_MAX_SLICE_LINES,
) -> tuple[str, str, list[str]]:
    """
    Extract the full function (header + body) from C source.

    Returns (full_function_text, signature, diagnostics).
    """
    diagnostics: list[str] = []

    names_to_try = [function_name]
    if fallback_names:
        for n in fallback_names:
            if n and n not in names_to_try:
                names_to_try.append(n)

    for name in names_to_try:
        header = _extract_function_header(c_source, name)
        body, diag = _extract_function_slice(c_source, name, max_lines)
        if body:
            full = f"{header}\n{body}" if header else body
            diagnostics.extend(diag)
            return full, header, diagnostics

    diagnostics.append(
        f"generator: function '{function_name}' not found "
        f"(tried: {names_to_try})"
    )
    return "", "", diagnostics


def _get_source_reconstruction_functions(arts: Any) -> list[dict]:
    """Get function list from source_reconstruction.json (supports data.functions nesting)."""
    if arts.source_reconstruction is None:
        return []
    fns = (
        arts.source_reconstruction.get("data", {}).get("functions", [])
        or arts.source_reconstruction.get("functions", [])
    )
    return fns if isinstance(fns, list) else []


def _get_function_names(arts: Any) -> list[tuple[str, str]]:
    """
    Return list of (canonical_name, c_name) tuples for all functions.
    c_name is the name used in recovered_readable.c.
    """
    fns = _get_source_reconstruction_functions(arts)
    result = []
    for fn in fns:
        canonical = fn.get("name") or fn.get("canonical_name", "")
        c_name = fn.get("c_name") or canonical
        if canonical:
            result.append((canonical, c_name))
    return result


def _get_behavior_model_entry(arts: Any, fn_name: str) -> dict:
    """Find behavior model entry for fn_name."""
    if arts.behavior_model is None:
        return {}
    for entry in arts.behavior_model.get("functions", []):
        if entry.get("function") == fn_name or entry.get("name") == fn_name:
            return entry
    return {}


def _fallback_comment_wrap(fn_text: str, fn_name: str, reason: str) -> str:
    """Wrap a function with a failure comment, preserving the original body."""
    return (
        f"/* [HEPHAESTUS Phase 11: generation failed for '{fn_name}': {reason}]\n"
        f"   Original recovered_readable.c function preserved unchanged. */\n"
        + fn_text
    )


# ── Main generator ────────────────────────────────────────────────────────────

def generate_source(
    arts: Any,  # Phase11Artifacts
    plan_entries: list[dict],
    provider: Any,  # AgentProvider
    *,
    mode: str = "function_by_function",
    max_functions: int | None = 1,
    function_filter: str | None = None,
    fail_fast: bool = False,
) -> tuple[str, list[dict], list[str]]:
    """
    Generate recovered_agent.c text.

    Parameters
    ----------
    arts:
        Phase11Artifacts with loaded input artifacts.
    plan_entries:
        Transformation plan (from plan_builder).
    provider:
        AgentProvider instance (Ollama or Groq).
    mode:
        "function_by_function" or "whole_file".
    max_functions:
        Maximum functions to process with LLM (None = unlimited).
    function_filter:
        If set, only generate this one function by name.
    fail_fast:
        If True, raise GeneratorFailFastError on first failure.

    Returns
    -------
    (generated_c_text, function_records, global_diagnostics)
    """
    if mode == "whole_file":
        return _generate_whole_file(arts, plan_entries, provider, fail_fast=fail_fast)
    return _generate_function_by_function(
        arts, plan_entries, provider,
        max_functions=max_functions,
        function_filter=function_filter,
        fail_fast=fail_fast,
    )


def _generate_function_by_function(
    arts: Any,
    plan_entries: list[dict],
    provider: Any,
    *,
    max_functions: int | None,
    function_filter: str | None,
    fail_fast: bool,
) -> tuple[str, list[dict], list[str]]:
    """Generate functions one at a time, building up recovered_agent.c."""
    global_diagnostics: list[str] = []
    function_records: list[dict] = []

    readable_c = arts.recovered_readable_c or ""
    conservative_c = arts.recovered_c or ""

    if not readable_c.strip():
        global_diagnostics.append(
            "generator: recovered_readable.c is empty — cannot generate"
        )
        return "", [], global_diagnostics

    # Get function list from source_reconstruction, or use recovered_readable.c directly
    fn_pairs = _get_function_names(arts)  # list of (canonical_name, c_name)

    # If no function metadata, parse directly from recovered_readable.c
    if not fn_pairs:
        # Parse function names from the C source
        raw_fn_names = _find_top_level_functions(readable_c)
        fn_pairs = [(n, n) for n in raw_fn_names]
        global_diagnostics.append(
            f"generator: source_reconstruction.json not available; "
            f"parsed {len(fn_pairs)} functions from recovered_readable.c"
        )

    # Filter by function name if requested
    if function_filter:
        fn_pairs = [
            (can, cn) for (can, cn) in fn_pairs
            if can == function_filter or cn == function_filter
        ]
        if not fn_pairs:
            global_diagnostics.append(
                f"generator: function '{function_filter}' not found"
            )
            return "", [], global_diagnostics

    system_prompt = build_system_prompt()
    forbidden_transforms = get_forbidden_transforms()

    # Build the output file as sections
    sections: list[str] = []
    llm_count = 0

    for canonical_name, c_name in fn_pairs:
        # Find the function text in recovered_readable.c
        full_fn, signature, slice_diag = _extract_function_with_header(
            readable_c, c_name,
            fallback_names=[canonical_name, c_name.lstrip("_")],
        )
        global_diagnostics.extend(slice_diag)

        if not full_fn:
            # Record skip — function not found in source
            function_records.append({
                "function": canonical_name,
                "c_name": c_name,
                "status": "skipped_not_found",
                "generated": False,
                "diagnostics": slice_diag,
                "applied_transformations": [],
                "skipped_transformations": [],
                "uncertainties": [],
                "notes": ["function not found in recovered_readable.c"],
            })
            continue

        # Decide: LLM generate or copy unchanged?
        if max_functions is not None and llm_count >= max_functions:
            # Copy unchanged
            sections.append(full_fn)
            function_records.append({
                "function": canonical_name,
                "c_name": c_name,
                "status": "copied_unchanged",
                "generated": False,
                "diagnostics": [],
                "applied_transformations": [],
                "skipped_transformations": [],
                "uncertainties": [],
                "notes": ["max_functions limit reached; copied from recovered_readable.c"],
            })
            continue

        # LLM generation
        approved_transforms = get_approved_transforms_for_function(
            plan_entries, canonical_name
        ) or get_approved_transforms_for_function(plan_entries, c_name)

        # Conservative C slice for this function
        cons_fn, _, _ = _extract_function_with_header(
            conservative_c, c_name,
            fallback_names=[canonical_name, c_name.lstrip("_")],
        )

        behavior_entry = _get_behavior_model_entry(arts, canonical_name)

        user_payload = build_user_payload(
            fn_name=c_name,
            baseline_c=full_fn,
            conservative_c=cons_fn,
            behavior_model_entry=behavior_entry,
            approved_transforms=approved_transforms,
            forbidden_transforms=forbidden_transforms,
            generation_mode="function_by_function",
        )

        record: dict = {
            "function": canonical_name,
            "c_name": c_name,
            "status": "ok",
            "generated": True,
            "diagnostics": list(slice_diag),
            "applied_transformations": [],
            "skipped_transformations": [],
            "uncertainties": [],
            "notes": [],
        }

        try:
            response = provider.complete_json(
                system_prompt=system_prompt,
                user_payload=user_payload,
                schema_name=f"agent_source_function_{c_name}",
            )

            # Extract _provider_diagnostics
            prov_diag = response.pop("_provider_diagnostics", {})
            if prov_diag.get("parse_status") == "failed":
                raw = response.get("_raw_content", "")
                raise RuntimeError(
                    f"Provider parse failed for {c_name}: {prov_diag.get('failure_reason')}; "
                    f"raw={raw[:200]}"
                )

            # Extract generated_c from response
            generated_c = response.get("generated_c", "")
            if not generated_c:
                raise RuntimeError(
                    f"Provider returned no 'generated_c' for {c_name}. "
                    f"Response keys: {list(response.keys())}"
                )

            # Sanitize
            sanitized_c, san_issues, san_ok = sanitize_function_output(
                generated_c,
                fn_name=c_name,
                expected_signature=signature,
                generation_mode="function_by_function",
            )
            record["diagnostics"].extend(san_issues)

            if not san_ok:
                raise RuntimeError(
                    f"Sanitizer rejected output for '{c_name}': {san_issues}"
                )

            sections.append(sanitized_c)
            record["applied_transformations"] = response.get("applied_transformations", [])
            record["skipped_transformations"] = response.get("skipped_transformations", [])
            record["uncertainties"] = response.get("uncertainties", [
                "AI-assisted approximation only",
                "dynamic evidence only covers tested inputs",
            ])
            record["notes"] = response.get("notes", [])
            llm_count += 1

        except GeneratorFailFastError:
            raise
        except Exception as e:
            logger.warning(
                "[generator] function '%s' generation failed: %s", c_name, e
            )
            record["status"] = "failed"
            record["generated"] = False
            record["diagnostics"].append(f"generator error: {e}")
            record["notes"].append("copied from recovered_readable.c unchanged due to error")

            # Copy original unchanged with failure comment
            wrapped = _fallback_comment_wrap(full_fn, c_name, str(e)[:200])
            sections.append(wrapped)

            if fail_fast:
                function_records.append(record)
                raise GeneratorFailFastError(
                    f"fail-fast: generation failed for '{c_name}': {e}"
                ) from e

        function_records.append(record)

    # Assemble full file
    if not sections:
        global_diagnostics.append(
            "generator: no function sections produced — generated_c will be empty"
        )
        return "", function_records, global_diagnostics

    # Build file: prelude headers from recovered_readable.c + generated sections
    prelude = _extract_prelude(readable_c)
    body = "\n\n".join(sections)
    full_text = (prelude + "\n\n" + body).strip() + "\n"

    return full_text, function_records, global_diagnostics


def _generate_whole_file(
    arts: Any,
    plan_entries: list[dict],
    provider: Any,
    *,
    fail_fast: bool,
) -> tuple[str, list[dict], list[str]]:
    """Whole-file generation mode — sends entire recovered_readable.c."""
    global_diagnostics: list[str] = []
    function_records: list[dict] = []

    readable_c = arts.recovered_readable_c or ""
    if not readable_c.strip():
        global_diagnostics.append(
            "generator: recovered_readable.c is empty — cannot generate"
        )
        return "", function_records, global_diagnostics

    approved_transforms = [e for e in plan_entries if e.get("enabled")]
    forbidden_transforms = get_forbidden_transforms()
    behavior_model_global = (
        arts.behavior_model.get("global_behavior", [])
        if arts.behavior_model else []
    )

    system_prompt = build_system_prompt()
    user_payload = {
        "task": "Generate a whole-file AI-assisted C approximation from the baseline.",
        "generation_mode": "whole_file",
        "baseline_c": readable_c,
        "approved_transformations": approved_transforms,
        "forbidden_transformations": forbidden_transforms,
        "global_behavior": behavior_model_global,
        "required_header_notice": WARNING_HEADER,
        "required_output_schema": {
            "generated_c": "string — the complete generated C file",
            "function_summaries": "list of {function, applied_transformations, uncertainties}",
            "notes": "list of strings",
        },
    }

    try:
        response = provider.complete_json(
            system_prompt=system_prompt,
            user_payload=user_payload,
            schema_name="agent_source_whole_file",
        )
        prov_diag = response.pop("_provider_diagnostics", {})
        if prov_diag.get("parse_status") == "failed":
            raise RuntimeError(
                f"Provider parse failed: {prov_diag.get('failure_reason')}"
            )

        generated_c = response.get("generated_c", "")
        if not generated_c:
            raise RuntimeError("Provider returned no 'generated_c' for whole-file mode")

        sanitized_c, san_issues, san_ok = sanitize_whole_file_output(generated_c)
        global_diagnostics.extend(san_issues)

        if not san_ok:
            raise RuntimeError(f"Sanitizer rejected whole-file output: {san_issues}")

        # Build summary records per function
        for summary in response.get("function_summaries", []):
            if isinstance(summary, dict):
                function_records.append({
                    "function": summary.get("function", "unknown"),
                    "c_name": summary.get("function", "unknown"),
                    "status": "ok",
                    "generated": True,
                    "diagnostics": [],
                    "applied_transformations": summary.get("applied_transformations", []),
                    "skipped_transformations": [],
                    "uncertainties": summary.get("uncertainties", []),
                    "notes": [],
                })

        return sanitized_c.strip() + "\n", function_records, global_diagnostics

    except Exception as e:
        global_diagnostics.append(f"generator: whole-file generation failed: {e}")
        if fail_fast:
            raise GeneratorFailFastError(str(e)) from e
        return "", function_records, global_diagnostics


def _find_top_level_functions(c_source: str) -> list[str]:
    """Parse top-level function names from C source (fallback when no metadata)."""
    pattern = re.compile(
        r"(?:^|\n)(?:[a-zA-Z_][a-zA-Z0-9_\s\*]*?\s+)"
        r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*\{",
        re.MULTILINE,
    )
    return list(dict.fromkeys(pattern.findall(c_source)))  # deduplicated


def _extract_prelude(c_source: str) -> str:
    """
    Extract the file header (includes, typedefs, forward declarations, macros)
    before the first function definition.
    """
    pattern = re.compile(
        r"(?:^|\n)(?:[a-zA-Z_][a-zA-Z0-9_\s\*]*?\s+)"
        r"[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*\{",
        re.MULTILINE,
    )
    m = pattern.search(c_source)
    if not m:
        return c_source

    # Find start of the line containing the match
    start = c_source.rfind("\n", 0, m.start())
    if start < 0:
        start = 0
    else:
        start += 1

    return c_source[:start].strip()
