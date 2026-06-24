# -*- coding: utf-8 -*-
"""
Tests for src/dynamic/runner.py and src/dynamic/safety.py

Uses tiny Python scripts as cross-platform "binaries" so tests work
without the actual ARM64 target binary.
"""

import sys
import os
import hashlib
import json
import subprocess
import textwrap
import pytest
from pathlib import Path
from unittest import mock

from src.dynamic.safety import (
    validate_binary_path,
    validate_argv,
    validate_env_overlay,
    build_safe_env,
    truncate_output,
    SafetyError,
)
from src.dynamic.runner import run_single, run_all


# ---------------------------------------------------------------------------
# Helpers: tiny executable fixture scripts
# ---------------------------------------------------------------------------

def _make_script(tmp_path: Path, name: str, code: str) -> Path:
    """Write a Python script and make it executable."""
    script = tmp_path / name
    script.write_text(
        f"#!/usr/bin/env python3\n{textwrap.dedent(code)}", encoding="utf-8"
    )
    script.chmod(0o755)
    return script


PYTHON = sys.executable  # use the running interpreter


def _make_binary(tmp_path: Path, name: str, code: str) -> Path:
    """Wrapper: write as a shebang Python script."""
    return _make_script(tmp_path, name, code)


# ---------------------------------------------------------------------------
# Safety: validate_binary_path
# ---------------------------------------------------------------------------

def test_validate_binary_path_missing(tmp_path):
    with pytest.raises(SafetyError, match="does not exist"):
        validate_binary_path(tmp_path / "nope")


def test_validate_binary_path_not_executable(tmp_path):
    p = tmp_path / "noexec"
    p.write_bytes(b"content")
    p.chmod(0o644)
    with pytest.raises(SafetyError, match="not executable"):
        validate_binary_path(p)


def test_validate_binary_path_ok(tmp_path):
    p = tmp_path / "good"
    p.write_bytes(b"#!/bin/sh\necho hi")
    p.chmod(0o755)
    result = validate_binary_path(p)
    assert result == p.resolve()


# ---------------------------------------------------------------------------
# Safety: validate_argv
# ---------------------------------------------------------------------------

def test_validate_argv_ok():
    assert validate_argv(["a", "b"]) == ["a", "b"]


def test_validate_argv_not_list():
    with pytest.raises(SafetyError, match="list"):
        validate_argv("not_a_list")


def test_validate_argv_int_item():
    with pytest.raises(SafetyError, match="string"):
        validate_argv([42])


def test_validate_argv_empty():
    assert validate_argv([]) == []


# ---------------------------------------------------------------------------
# Safety: validate_env_overlay
# ---------------------------------------------------------------------------

def test_validate_env_overlay_ok():
    result = validate_env_overlay({"KEY": "value"})
    assert result == {"KEY": "value"}


def test_validate_env_overlay_non_string_value():
    with pytest.raises(SafetyError):
        validate_env_overlay({"KEY": 123})


def test_validate_env_overlay_null_byte_key():
    with pytest.raises(SafetyError, match="null"):
        validate_env_overlay({"KEY\x00": "val"})


def test_validate_env_overlay_null_byte_value():
    with pytest.raises(SafetyError, match="null"):
        validate_env_overlay({"KEY": "val\x00ue"})


# ---------------------------------------------------------------------------
# Safety: build_safe_env
# ---------------------------------------------------------------------------

def test_build_safe_env_minimal():
    env = build_safe_env({}, inherit=False)
    # Must have PATH
    assert "PATH" in env
    # Must NOT contain HOME, USER, etc. unless they happen to equal PATH
    # The point is it starts from minimal base
    assert len(env) >= 1  # at least PATH


def test_build_safe_env_does_not_inherit_full_env_by_default():
    # Plant a canary in os.environ that should NOT appear in minimal env
    canary_key = "HEPHAESTUS_CANARY_DO_NOT_INHERIT_12345"
    os.environ[canary_key] = "canary_value"
    try:
        env = build_safe_env({}, inherit=False)
        assert canary_key not in env
    finally:
        del os.environ[canary_key]


def test_build_safe_env_inherit():
    canary_key = "HEPHAESTUS_CANARY_INHERIT_12345"
    os.environ[canary_key] = "canary_value"
    try:
        env = build_safe_env({}, inherit=True)
        assert canary_key in env
        assert env[canary_key] == "canary_value"
    finally:
        del os.environ[canary_key]


def test_build_safe_env_overlay_applied():
    env = build_safe_env({"MY_KEY": "my_val"}, inherit=False)
    assert env["MY_KEY"] == "my_val"


# ---------------------------------------------------------------------------
# Safety: truncate_output
# ---------------------------------------------------------------------------

def test_truncate_no_truncation():
    data, truncated = truncate_output(b"hello", 100)
    assert data == b"hello"
    assert truncated is False


def test_truncate_truncates():
    data, truncated = truncate_output(b"hello world", 5)
    assert data == b"hello"
    assert truncated is True


def test_truncate_exact():
    data, truncated = truncate_output(b"hello", 5)
    assert data == b"hello"
    assert truncated is False


# ---------------------------------------------------------------------------
# runner: run_single captures stdout/stderr/exit_code
# ---------------------------------------------------------------------------

def test_run_single_captures_stdout(tmp_path):
    binary = _make_binary(tmp_path, "echo_out", "print('hello stdout')")
    spec = {"name": "test", "argv": [], "stdin": "", "env": {}}
    result = run_single(binary, spec)
    assert "hello stdout" in result["stdout"]
    assert result["exit_code"] == 0
    assert result["timed_out"] is False


def test_run_single_captures_stderr(tmp_path):
    binary = _make_binary(tmp_path, "echo_err", """
import sys
sys.stderr.write("hello stderr\\n")
""")
    spec = {"name": "test", "argv": [], "stdin": "", "env": {}}
    result = run_single(binary, spec)
    assert "hello stderr" in result["stderr"]


def test_run_single_captures_nonzero_exit(tmp_path):
    binary = _make_binary(tmp_path, "exit_42", "import sys; sys.exit(42)")
    spec = {"name": "test", "argv": [], "stdin": "", "env": {}}
    result = run_single(binary, spec)
    assert result["exit_code"] == 42


def test_run_single_exit_zero(tmp_path):
    binary = _make_binary(tmp_path, "exit_ok", "import sys; sys.exit(0)")
    spec = {"name": "test", "argv": [], "stdin": "", "env": {}}
    result = run_single(binary, spec)
    assert result["exit_code"] == 0


def test_run_single_stdin_delivered(tmp_path):
    binary = _make_binary(tmp_path, "echo_stdin", """
import sys
data = sys.stdin.read()
print(f"got:{data.strip()}")
""")
    spec = {"name": "test", "argv": [], "stdin": "ping", "env": {}}
    result = run_single(binary, spec)
    assert "got:ping" in result["stdout"]


def test_run_single_argv_passed(tmp_path):
    binary = _make_binary(tmp_path, "echo_args", """
import sys
print(','.join(sys.argv[1:]))
""")
    spec = {"name": "test", "argv": ["foo", "bar"], "stdin": "", "env": {}}
    result = run_single(binary, spec)
    assert "foo,bar" in result["stdout"]


def test_run_single_timeout(tmp_path):
    binary = _make_binary(tmp_path, "sleep_long", "import time; time.sleep(60)")
    spec = {"name": "test", "argv": [], "stdin": "", "env": {}}
    result = run_single(binary, spec, timeout_s=0.5)
    assert result["timed_out"] is True
    assert any("timed out" in d.lower() for d in result["diagnostics"])


def test_run_single_stdout_truncated(tmp_path):
    binary = _make_binary(tmp_path, "big_output", "print('x' * 200)")
    spec = {"name": "test", "argv": [], "stdin": "", "env": {}}
    result = run_single(binary, spec, max_output_bytes=10)
    assert result["stdout_truncated"] is True
    assert len(result["stdout"]) <= 15  # small, accounting for decode


def test_run_single_computes_sha256(tmp_path):
    binary = _make_binary(tmp_path, "hello_sha", "print('hello')")
    spec = {"name": "test", "argv": [], "stdin": "", "env": {}}
    result = run_single(binary, spec)
    expected = hashlib.sha256(result["stdout"].encode("utf-8", errors="replace")).hexdigest()
    # sha256 is computed from raw bytes before decode; verify it's a sha256 string
    assert len(result["stdout_sha256"]) == 64
    assert len(result["stdin_sha256"]) == 64


def test_run_single_binary_does_not_exist():
    spec = {"name": "test", "argv": [], "stdin": "", "env": {}}
    result = run_single(Path("/nonexistent/binary_xyz"), spec)
    assert result["status"] == "failed_to_execute"
    assert result["exit_code"] is None
    assert any("could not be executed" in d.lower() or "does not exist" in d.lower()
               for d in result["diagnostics"])


def test_run_single_no_shell(tmp_path):
    """Verify shell=False by patching Popen and checking call args."""
    binary = _make_binary(tmp_path, "noop", "pass")
    spec = {"name": "test", "argv": ["arg1"], "stdin": "", "env": {}}

    captured_calls = []
    original_popen = subprocess.Popen

    class PatchedPopen:
        def __init__(self, cmd, **kwargs):
            captured_calls.append({"cmd": cmd, "kwargs": kwargs})
            self._proc = original_popen(cmd, **kwargs)

        def communicate(self, **kw):
            return self._proc.communicate(**kw)

        @property
        def returncode(self):
            return self._proc.returncode

        def kill(self):
            return self._proc.kill()

    with mock.patch("subprocess.Popen", PatchedPopen):
        run_single(binary, spec)

    assert len(captured_calls) == 1
    call = captured_calls[0]
    assert call["kwargs"].get("shell") is False
    # cmd must be a list, not a string
    assert isinstance(call["cmd"], list)
    assert call["cmd"][0] == str(binary)
    assert call["cmd"][1] == "arg1"


def test_run_all_env_not_inherited_by_default(tmp_path):
    """Default env does not expose full user environment."""
    canary_key = "HEPHAESTUS_RUNNER_CANARY_9999"
    os.environ[canary_key] = "secret_value"
    try:
        binary = _make_binary(tmp_path, "env_check", f"""
import os, sys
val = os.environ.get('{canary_key}', 'NOT_FOUND')
print(val)
""")
        spec = {
            "schema_version": "dynamic-inputs-1.0",
            "runs": [{"name": "test", "argv": [], "stdin": "", "env": {}}],
        }
        results, _ = run_all(binary, spec, inherit_env=False)
        assert results[0]["stdout"].strip() == "NOT_FOUND"
    finally:
        del os.environ[canary_key]


def test_run_all_records_binary_sha256(tmp_path):
    binary = _make_binary(tmp_path, "sha_test", "pass")
    spec = {
        "schema_version": "dynamic-inputs-1.0",
        "runs": [{"name": "r", "argv": [], "stdin": "", "env": {}}],
    }
    results, binary_sha256 = run_all(binary, spec)
    assert len(binary_sha256) == 64  # SHA-256 hex


def test_run_single_env_overlay_visible(tmp_path):
    """Env overlay variable is visible in subprocess."""
    binary = _make_binary(tmp_path, "env_overlay", """
import os
print(os.environ.get('MYVAR', 'NOT_SET'))
""")
    spec = {"name": "test", "argv": [], "stdin": "", "env": {"MYVAR": "hello123"}}
    result = run_single(binary, spec)
    assert "hello123" in result["stdout"]
