# -*- coding: utf-8 -*-
"""
Tests for src/dynamic/input_spec.py
"""

import pytest
from src.dynamic.input_spec import (
    validate_input_spec,
    load_input_spec,
    resolve_input_spec,
)
from src.dynamic.models import default_input_spec
import json
import tempfile
import os


# ---------------------------------------------------------------------------
# validate_input_spec
# ---------------------------------------------------------------------------

def _valid_spec(**overrides):
    spec = {
        "schema_version": "dynamic-inputs-1.0",
        "runs": [
            {"name": "no_args", "argv": [], "stdin": "", "env": {}},
        ],
    }
    spec.update(overrides)
    return spec


def test_valid_spec_passes():
    errors = validate_input_spec(_valid_spec())
    assert errors == []


def test_valid_spec_three_runs():
    spec = {
        "schema_version": "dynamic-inputs-1.0",
        "runs": [
            {"name": "no_args",   "argv": [],            "stdin": "", "env": {}},
            {"name": "short_arg", "argv": ["hello"],      "stdin": "", "env": {}},
            {"name": "long_arg",  "argv": ["AAAAAAAAAA"], "stdin": "", "env": {}},
        ],
    }
    errors = validate_input_spec(spec)
    assert errors == []


def test_missing_schema_version():
    spec = {"runs": [{"name": "x", "argv": [], "stdin": "", "env": {}}]}
    errors = validate_input_spec(spec)
    assert any("schema_version" in e for e in errors)


def test_empty_runs_list():
    spec = {"schema_version": "dynamic-inputs-1.0", "runs": []}
    errors = validate_input_spec(spec)
    assert any("non-empty" in e for e in errors)


def test_missing_runs_key():
    spec = {"schema_version": "dynamic-inputs-1.0"}
    errors = validate_input_spec(spec)
    assert any("runs" in e for e in errors)


def test_duplicate_run_names():
    spec = {
        "schema_version": "dynamic-inputs-1.0",
        "runs": [
            {"name": "dupe", "argv": [], "stdin": "", "env": {}},
            {"name": "dupe", "argv": ["x"], "stdin": "", "env": {}},
        ],
    }
    errors = validate_input_spec(spec)
    assert any("duplicate" in e for e in errors)


def test_non_list_argv():
    spec = _valid_spec()
    spec["runs"][0]["argv"] = "not_a_list"
    errors = validate_input_spec(spec)
    assert any("argv" in e and "list" in e for e in errors)


def test_non_string_argv_item():
    spec = _valid_spec()
    spec["runs"][0]["argv"] = [42]
    errors = validate_input_spec(spec)
    assert any("argv" in e and "string" in e for e in errors)


def test_non_string_env_value():
    spec = _valid_spec()
    spec["runs"][0]["env"] = {"KEY": 123}
    errors = validate_input_spec(spec)
    assert any("env" in e and "string" in e for e in errors)


def test_null_byte_in_argv():
    spec = _valid_spec()
    spec["runs"][0]["argv"] = ["arg\x00bad"]
    errors = validate_input_spec(spec)
    assert any("null" in e.lower() for e in errors)


def test_null_byte_in_env_value():
    spec = _valid_spec()
    spec["runs"][0]["env"] = {"KEY": "val\x00ue"}
    errors = validate_input_spec(spec)
    assert any("null" in e.lower() for e in errors)


def test_null_byte_in_stdin():
    spec = _valid_spec()
    spec["runs"][0]["stdin"] = "hello\x00world"
    errors = validate_input_spec(spec)
    assert any("null" in e.lower() for e in errors)


def test_run_not_a_dict():
    spec = {
        "schema_version": "dynamic-inputs-1.0",
        "runs": ["not_a_dict"],
    }
    errors = validate_input_spec(spec)
    assert any("dict" in e for e in errors)


# ---------------------------------------------------------------------------
# default_input_spec
# ---------------------------------------------------------------------------

def test_default_spec_valid():
    spec = default_input_spec()
    errors = validate_input_spec(spec)
    assert errors == []


def test_default_spec_has_no_args_run():
    spec = default_input_spec()
    assert len(spec["runs"]) == 1
    assert spec["runs"][0]["name"] == "no_args"
    assert spec["runs"][0]["argv"] == []


# ---------------------------------------------------------------------------
# load_input_spec
# ---------------------------------------------------------------------------

def test_load_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_input_spec("/nonexistent/path/inputs.json")


def test_load_invalid_json_raises(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{bad json", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        load_input_spec(p)


def test_load_invalid_spec_raises(tmp_path):
    p = tmp_path / "spec.json"
    p.write_text(json.dumps({"schema_version": "x", "runs": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="validation failed"):
        load_input_spec(p)


def test_load_valid_spec(tmp_path):
    spec = {
        "schema_version": "dynamic-inputs-1.0",
        "runs": [{"name": "run1", "argv": [], "stdin": "", "env": {}}],
    }
    p = tmp_path / "inputs.json"
    p.write_text(json.dumps(spec), encoding="utf-8")
    loaded = load_input_spec(p)
    assert loaded["runs"][0]["name"] == "run1"


# ---------------------------------------------------------------------------
# resolve_input_spec
# ---------------------------------------------------------------------------

def test_resolve_none_returns_default():
    spec, using_default = resolve_input_spec(None)
    assert using_default is True
    assert spec["runs"][0]["name"] == "no_args"


def test_resolve_path_returns_file(tmp_path):
    spec = {
        "schema_version": "dynamic-inputs-1.0",
        "runs": [{"name": "r", "argv": [], "stdin": "", "env": {}}],
    }
    p = tmp_path / "inputs.json"
    p.write_text(json.dumps(spec), encoding="utf-8")
    loaded, using_default = resolve_input_spec(p)
    assert using_default is False
    assert loaded["runs"][0]["name"] == "r"
