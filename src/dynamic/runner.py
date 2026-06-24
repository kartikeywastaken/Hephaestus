# -*- coding: utf-8 -*-
"""
Phase 8 — Dynamic Behavior Capture: subprocess runner.

Executes the target binary safely under each dynamic run spec.

Invariants:
    - shell=False always
    - argv passed as Python list
    - timeout always enforced
    - stdout/stderr captured then truncated
    - process killed on timeout
    - no full environment leakage by default
"""

from __future__ import annotations

import hashlib
import subprocess
import time
from pathlib import Path

from src.dynamic.safety import (
    validate_argv,
    validate_env_overlay,
    build_safe_env,
    truncate_output,
    validate_binary_path,
    SafetyError,
)


# ---------------------------------------------------------------------------
# Hashing helpers
# ---------------------------------------------------------------------------

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Single run
# ---------------------------------------------------------------------------

def run_single(
    binary_path: Path,
    run_spec: dict,
    *,
    timeout_s: float = 5.0,
    max_output_bytes: int = 1_048_576,
    cwd: Path | None = None,
    inherit_env: bool = False,
) -> dict:
    """
    Execute the binary under one run spec.

    Returns a RunResult dict containing:
        name, argv, stdin_sha256, timeout_s,
        exit_code, signal, timed_out, duration_ms,
        stdout, stderr (decoded, possibly truncated),
        stdout_sha256, stderr_sha256,
        stdout_truncated, stderr_truncated,
        stdout_bytes, stderr_bytes,
        diagnostics
    """
    name: str = run_spec.get("name", "unnamed")
    diagnostics: list[str] = []

    # --- Validate inputs ---
    try:
        argv = validate_argv(run_spec.get("argv", []))
        env_overlay = validate_env_overlay(run_spec.get("env", {}))
    except SafetyError as e:
        return {
            "name": name,
            "argv": run_spec.get("argv", []),
            "stdin_sha256": _sha256_bytes(b""),
            "timeout_s": timeout_s,
            "status": "failed_to_execute",
            "exit_code": None,
            "signal": None,
            "timed_out": False,
            "duration_ms": 0,
            "stdout": "",
            "stderr": "",
            "stdout_sha256": _sha256_bytes(b""),
            "stderr_sha256": _sha256_bytes(b""),
            "stdout_truncated": False,
            "stderr_truncated": False,
            "stdout_bytes": 0,
            "stderr_bytes": 0,
            "diagnostics": [f"Safety validation failed: {e}"],
        }

    stdin_str: str = run_spec.get("stdin", "")
    if not isinstance(stdin_str, str):
        stdin_str = ""
    stdin_bytes = stdin_str.encode("utf-8", errors="replace")
    stdin_sha256 = _sha256_bytes(stdin_bytes)

    safe_env = build_safe_env(env_overlay, inherit=inherit_env)
    cmd = [str(binary_path), *argv]

    # --- Execute ---
    timed_out = False
    exit_code: int | None = None
    sig: int | None = None
    raw_stdout = b""
    raw_stderr = b""
    start = time.perf_counter()

    try:
        proc = subprocess.Popen(
            cmd,
            shell=False,          # INVARIANT: never shell=True
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=safe_env,
            cwd=str(cwd) if cwd else None,
        )
        try:
            raw_stdout, raw_stderr = proc.communicate(
                input=stdin_bytes,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            try:
                raw_stdout, raw_stderr = proc.communicate(timeout=2.0)
            except Exception:
                raw_stdout = b""
                raw_stderr = b""
            diagnostics.append(
                f"Process timed out after {timeout_s}s and was killed."
            )

        rc = proc.returncode
        if rc is not None:
            exit_code = rc
            # On Unix, negative returncode means killed by signal
            if rc < 0:
                sig = -rc
        else:
            exit_code = None

    except (OSError, PermissionError, FileNotFoundError) as e:
        duration_ms = int((time.perf_counter() - start) * 1000)
        return {
            "name": name,
            "argv": argv,
            "stdin_sha256": stdin_sha256,
            "timeout_s": timeout_s,
            "status": "failed_to_execute",
            "exit_code": None,
            "signal": None,
            "timed_out": False,
            "duration_ms": duration_ms,
            "stdout": "",
            "stderr": "",
            "stdout_sha256": _sha256_bytes(b""),
            "stderr_sha256": _sha256_bytes(b""),
            "stdout_truncated": False,
            "stderr_truncated": False,
            "stdout_bytes": 0,
            "stderr_bytes": 0,
            "diagnostics": [
                "Binary could not be executed on this platform or permission was denied.",
                f"Detail: {e}",
            ],
        }

    duration_ms = int((time.perf_counter() - start) * 1000)

    # --- Truncate outputs ---
    raw_stdout, stdout_truncated = truncate_output(raw_stdout, max_output_bytes)
    raw_stderr, stderr_truncated = truncate_output(raw_stderr, max_output_bytes)

    if stdout_truncated:
        diagnostics.append(
            f"stdout truncated to {max_output_bytes} bytes."
        )
    if stderr_truncated:
        diagnostics.append(
            f"stderr truncated to {max_output_bytes} bytes."
        )

    stdout_str = raw_stdout.decode("utf-8", errors="replace")
    stderr_str = raw_stderr.decode("utf-8", errors="replace")

    return {
        "name": name,
        "argv": argv,
        "stdin_sha256": stdin_sha256,
        "timeout_s": timeout_s,
        "status": "timed_out" if timed_out else "ok",
        "exit_code": exit_code,
        "signal": sig,
        "timed_out": timed_out,
        "duration_ms": duration_ms,
        "stdout": stdout_str,
        "stderr": stderr_str,
        "stdout_sha256": _sha256_bytes(raw_stdout),
        "stderr_sha256": _sha256_bytes(raw_stderr),
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
        "stdout_bytes": len(raw_stdout),
        "stderr_bytes": len(raw_stderr),
        "diagnostics": diagnostics,
    }


# ---------------------------------------------------------------------------
# All runs
# ---------------------------------------------------------------------------

def run_all(
    binary_path: Path,
    input_spec: dict,
    *,
    timeout_s: float = 5.0,
    max_output_bytes: int = 1_048_576,
    cwd: Path | None = None,
    inherit_env: bool = False,
    fail_fast: bool = False,
) -> tuple[list[dict], str]:
    """
    Execute all runs in the input spec.

    Returns:
        (results, binary_sha256)

    If fail_fast=True, stops on the first run with status != "ok".
    """
    try:
        validated_path = validate_binary_path(binary_path)
    except SafetyError as e:
        raise SafetyError(str(e)) from e

    binary_sha256 = _sha256_file(validated_path)
    runs = input_spec.get("runs", [])
    results: list[dict] = []

    for run_spec in runs:
        result = run_single(
            validated_path,
            run_spec,
            timeout_s=timeout_s,
            max_output_bytes=max_output_bytes,
            cwd=cwd,
            inherit_env=inherit_env,
        )
        results.append(result)

        if fail_fast and result.get("status") not in ("ok", "timed_out"):
            break

    return results, binary_sha256
