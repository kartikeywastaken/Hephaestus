# -*- coding: utf-8 -*-
"""
Phase 11.6 — Library / import function filter.

Identifies obvious libc/external/PLT-stub functions and marks them
as skippable for agent debate and agent source generation.

Detection heuristics (conservative — false negatives are acceptable):
  1. Known libc names (with and without leading underscore).
  2. PLT / import metadata if present in packet.
  3. Tiny stub-like CFG + known external name.

Functions are never *removed* from artifacts — they are only filtered
out of the LLM call list.
"""

from __future__ import annotations

from typing import Any


# ── Known library function names ──────────────────────────────────────────────

# Standard libc / POSIX / compiler-builtin names that should never consume an
# LLM call.  The set is intentionally conservative — missing entries just mean
# those functions get debated normally, which is safe.
KNOWN_LIBRARY_FUNCTIONS: frozenset[str] = frozenset({
    # stdio
    "printf", "fprintf", "sprintf", "snprintf", "vprintf", "vfprintf",
    "vsprintf", "vsnprintf", "puts", "fputs", "putchar", "putc", "fputc",
    "scanf", "fscanf", "sscanf", "fgets", "getchar", "getc", "fgetc",
    "fopen", "fclose", "fread", "fwrite", "fseek", "ftell", "rewind",
    "fflush", "feof", "ferror", "clearerr", "perror",
    # stdlib
    "malloc", "calloc", "realloc", "free",
    "exit", "_exit", "abort", "atexit",
    "atoi", "atol", "atof", "strtol", "strtoul", "strtoll", "strtoull",
    "strtod", "strtof", "strtold",
    "rand", "srand", "abs", "labs", "llabs",
    "qsort", "bsearch", "getenv", "system",
    # string
    "strlen", "strcmp", "strncmp", "strcpy", "strncpy",
    "strcat", "strncat", "strchr", "strrchr", "strstr",
    "memcpy", "memmove", "memset", "memcmp", "memchr",
    "strerror", "strdup", "strndup",
    # ctype
    "isalpha", "isdigit", "isalnum", "isspace", "isupper", "islower",
    "toupper", "tolower", "isprint", "isxdigit",
    # math
    "sin", "cos", "tan", "sqrt", "pow", "log", "log10", "exp",
    "ceil", "floor", "fabs", "fmod", "round",
    # unistd / posix
    "read", "write", "open", "close", "lseek", "dup", "dup2", "pipe",
    "fork", "execve", "execvp", "wait", "waitpid",
    "getpid", "getppid", "getuid", "getgid",
    "sleep", "usleep", "nanosleep",
    # signal
    "signal", "raise", "kill", "sigaction",
    # dynamic linker / compiler support
    "__stack_chk_fail", "__cxa_atexit", "__cxa_finalize",
    "__libc_start_main", "__gmon_start__",
    "_start",
})


def _normalize_name(name: str) -> str:
    """Strip leading underscore for macOS / linker-prefixed symbols."""
    if name.startswith("_") and not name.startswith("__"):
        return name[1:]
    return name


# ── Classification ────────────────────────────────────────────────────────────

def classify_function_role(packet: dict) -> str:
    """
    Classify a function packet as ``external_library_function`` or
    ``user_defined_function``.

    The classification is conservative — if uncertain, returns
    ``user_defined_function`` so the function is debated normally.
    """
    fn_name = packet.get("function", "")

    # 1. Known names (exact or underscore-stripped)
    if fn_name in KNOWN_LIBRARY_FUNCTIONS:
        return "external_library_function"
    stripped = _normalize_name(fn_name)
    if stripped in KNOWN_LIBRARY_FUNCTIONS:
        return "external_library_function"

    # 2. PLT / import metadata
    metadata = packet.get("metadata", {})
    if isinstance(metadata, dict):
        if metadata.get("is_plt") or metadata.get("is_import"):
            return "external_library_function"
        section = metadata.get("section", "")
        if isinstance(section, str) and section in (".plt", ".plt.got", ".plt.sec", "__stubs"):
            return "external_library_function"

    # 3. Role hint already set by packet builder
    role = packet.get("role", "")
    if role in ("external", "import", "plt_stub", "external_library_function"):
        return "external_library_function"

    return "user_defined_function"


def is_skippable_for_debate(packet: dict) -> bool:
    """Return True if the function should be skipped for LLM debate."""
    return classify_function_role(packet) == "external_library_function"


def is_skippable_for_source(packet: dict) -> bool:
    """Return True if the function should be skipped for LLM source generation."""
    return classify_function_role(packet) == "external_library_function"


# ── Packet filtering ─────────────────────────────────────────────────────────

def filter_debatable_packets(
    packets: list[dict],
    *,
    max_functions: int | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Separate library stubs from user-defined functions.

    Returns ``(debatable, skipped)`` where:
    - ``skipped`` contains all external/library packets
    - ``debatable`` contains user-defined packets, limited to ``max_functions``

    Library functions **never** count toward ``max_functions``.
    """
    debatable: list[dict] = []
    skipped: list[dict] = []

    for pkt in packets:
        if is_skippable_for_debate(pkt):
            skipped.append(pkt)
        else:
            debatable.append(pkt)

    if max_functions is not None and max_functions > 0:
        debatable = debatable[:max_functions]

    return debatable, skipped
