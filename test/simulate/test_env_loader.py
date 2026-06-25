# -*- coding: utf-8 -*-
"""
Tests for env_loader.py
"""

import os
import tempfile
from pathlib import Path
import pytest

from src.utils.env_loader import load_env_file, load_default_env_files


def test_env_loader_ignores_missing_files():
    res = load_env_file("/nonexistent/file/path/here")
    assert res == {}


def test_env_loader_loads_key_value():
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env.test"
        env_file.write_text("TEST_KEY_ONE=value1\nTEST_KEY_TWO=value2\n", encoding="utf-8")

        # Clean environment before test
        os.environ.pop("TEST_KEY_ONE", None)
        os.environ.pop("TEST_KEY_TWO", None)

        res = load_env_file(env_file)
        assert res == {"TEST_KEY_ONE": "value1", "TEST_KEY_TWO": "value2"}
        assert os.environ.get("TEST_KEY_ONE") == "value1"
        assert os.environ.get("TEST_KEY_TWO") == "value2"

        # Cleanup
        os.environ.pop("TEST_KEY_ONE", None)
        os.environ.pop("TEST_KEY_TWO", None)


def test_env_loader_ignores_comments_and_blank_lines():
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env.test"
        content = (
            "\n"
            "# This is a comment line\n"
            "   # Another indented comment\n"
            "KEY_A=valA\n"
            "\n"
            "KEY_B=valB\n"
        )
        env_file.write_text(content, encoding="utf-8")

        os.environ.pop("KEY_A", None)
        os.environ.pop("KEY_B", None)

        res = load_env_file(env_file)
        assert res == {"KEY_A": "valA", "KEY_B": "valB"}
        assert os.environ.get("KEY_A") == "valA"
        assert os.environ.get("KEY_B") == "valB"

        os.environ.pop("KEY_A", None)
        os.environ.pop("KEY_B", None)


def test_env_loader_strips_quotes():
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env.test"
        content = (
            "KEY_Q1=\"doublequoted\"\n"
            "KEY_Q2='singlequoted'\n"
            "KEY_Q3=noquotes\n"
        )
        env_file.write_text(content, encoding="utf-8")

        os.environ.pop("KEY_Q1", None)
        os.environ.pop("KEY_Q2", None)
        os.environ.pop("KEY_Q3", None)

        res = load_env_file(env_file)
        assert res == {
            "KEY_Q1": "doublequoted",
            "KEY_Q2": "singlequoted",
            "KEY_Q3": "noquotes",
        }
        assert os.environ.get("KEY_Q1") == "doublequoted"
        assert os.environ.get("KEY_Q2") == "singlequoted"
        assert os.environ.get("KEY_Q3") == "noquotes"

        os.environ.pop("KEY_Q1", None)
        os.environ.pop("KEY_Q2", None)
        os.environ.pop("KEY_Q3", None)


def test_env_loader_does_not_override_existing_env_by_default():
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env.test"
        env_file.write_text("EXISTING_KEY=newval\n", encoding="utf-8")

        os.environ["EXISTING_KEY"] = "originalval"

        res = load_env_file(env_file, override=False)
        assert res == {"EXISTING_KEY": "newval"}
        assert os.environ.get("EXISTING_KEY") == "originalval"

        os.environ.pop("EXISTING_KEY", None)


def test_env_loader_can_override_if_requested():
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env.test"
        env_file.write_text("EXISTING_KEY=newval\n", encoding="utf-8")

        os.environ["EXISTING_KEY"] = "originalval"

        res = load_env_file(env_file, override=True)
        assert res == {"EXISTING_KEY": "newval"}
        assert os.environ.get("EXISTING_KEY") == "newval"

        os.environ.pop("EXISTING_KEY", None)


def test_env_loader_never_prints_secret_values(capsys):
    # Verify that loading doesn't write anything containing secrets to stdout/stderr
    with tempfile.TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env.test"
        secret_val = "SuperSecretGroqAPIKey_12345"
        env_file.write_text(f"GROQ_API_KEY={secret_val}\n", encoding="utf-8")

        os.environ.pop("GROQ_API_KEY", None)
        load_env_file(env_file)

        captured = capsys.readouterr()
        assert secret_val not in captured.out
        assert secret_val not in captured.err

        os.environ.pop("GROQ_API_KEY", None)


def test_env_example_exists():
    root = Path(__file__).resolve().parents[2]
    example_file = root / ".env.example"
    assert example_file.is_file()

    # Check for expected contents
    content = example_file.read_text(encoding="utf-8")
    assert "GROQ_API_KEY" in content
    assert "HEPHAESTUS_AGENT_MODEL" in content


def test_gitignore_contains_env_and_env_local():
    root = Path(__file__).resolve().parents[2]
    gitignore_file = root / ".gitignore"
    assert gitignore_file.is_file()

    lines = gitignore_file.read_text(encoding="utf-8").splitlines()
    stripped_lines = [l.strip() for l in lines]
    assert ".env" in stripped_lines
    assert ".env.local" in stripped_lines
