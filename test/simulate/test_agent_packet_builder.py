# -*- coding: utf-8 -*-
"""
Tests for src/agent/packet_builder.py — packet construction and hash guards.
No Ollama or Groq required. No external process execution.
"""
import json
import pytest
from pathlib import Path
import tempfile
import os

from src.agent.packet_builder import (
    build_packet,
    build_all_packets,
    compute_input_hashes,
    verify_input_hashes,
    _extract_function_slice,
)
from src.agent.models import FORBIDDEN_CLAIMS, KNOWN_UNCERTAINTIES


# ── Fixtures ──────────────────────────────────────────────────────────────────

SIMPLE_C = """\
int helper(int x) {
    return x + 1;
}

int main(int argc, char **argv) {
    int result = helper(argc);
    if (result > 1) {
        return 0;
    }
    return 1;
}
"""

FN_RECORD_MAIN = {
    "name": "main",
    "entry_point": "0x1000",
    "signature": "int main(int argc, char **argv)",
    "calls": ["helper"],
    "loops": 0,
    "conditions": 1,
    "returns_value": True,
    "return_type": "int",
    "params": ["int argc", "char **argv"],
    "layout_candidates": [],
}

FN_RECORD_HELPER = {
    "name": "helper",
    "entry_point": "0x0F00",
    "signature": "int helper(int x)",
    "calls": [],
    "loops": 0,
    "conditions": 0,
    "returns_value": True,
    "return_type": "int",
    "params": ["int x"],
    "layout_candidates": [],
}

BEHAVIOR_MODEL = {
    "functions": [
        {
            "function": "main",
            "static_summary": {"calls": ["helper"]},
            "hypotheses": [{"kind": "argv_dependency", "text": "argv sensitive"}],
            "dynamic_links": [],
        }
    ],
    "global_behavior": [{"kind": "crash_observed"}],
}

BEHAVIOR_PROFILE = {
    "binary_path": "/tmp/t",
    "binary_sha256": "abc123",
    "summary": {
        "runs_total": 3,
        "argv_sensitive": True,
        "distinct_exit_codes": [0, 1],
    },
    "observations": [],
}


@pytest.fixture
def tmpdir_path():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


def _write_source_recon(path: Path, functions: list):
    sr = {"functions": functions}
    (path / "source_reconstruction.json").write_text(
        json.dumps(sr), encoding="utf-8"
    )


def _write_recovered_c(path: Path, content: str = SIMPLE_C):
    (path / "recovered.c").write_text(content, encoding="utf-8")


def _write_recovered_readable(path: Path, content: str = SIMPLE_C):
    (path / "recovered_readable.c").write_text(content, encoding="utf-8")


# ── Packet content ────────────────────────────────────────────────────────────

class TestPacketContent:
    def test_packet_contains_forbidden_claims(self, tmpdir_path):
        packet, _ = build_packet(
            FN_RECORD_MAIN,
            tmpdir_path,
            recovered_c=SIMPLE_C,
            recovered_readable_c=SIMPLE_C,
            behavior_model=BEHAVIOR_MODEL,
            behavior_profile=BEHAVIOR_PROFILE,
            evidence_index=None,
            trace_report=None,
            quality_gate=None,
        )
        assert "forbidden_claims" in packet
        assert isinstance(packet["forbidden_claims"], list)
        assert len(packet["forbidden_claims"]) > 0
        # Check against model constants
        for claim in FORBIDDEN_CLAIMS:
            assert claim in packet["forbidden_claims"]

    def test_packet_contains_known_uncertainties(self, tmpdir_path):
        packet, _ = build_packet(
            FN_RECORD_MAIN,
            tmpdir_path,
            recovered_c=SIMPLE_C,
            recovered_readable_c=SIMPLE_C,
            behavior_model=None,
            behavior_profile=None,
            evidence_index=None,
            trace_report=None,
            quality_gate=None,
        )
        assert "known_uncertainties" in packet
        for u in KNOWN_UNCERTAINTIES:
            assert u in packet["known_uncertainties"]

    def test_packet_contains_behavior_model_entry(self, tmpdir_path):
        packet, _ = build_packet(
            FN_RECORD_MAIN,
            tmpdir_path,
            recovered_c=SIMPLE_C,
            recovered_readable_c=SIMPLE_C,
            behavior_model=BEHAVIOR_MODEL,
            behavior_profile=None,
            evidence_index=None,
            trace_report=None,
            quality_gate=None,
        )
        assert "behavior_model_entry" in packet
        assert isinstance(packet["behavior_model_entry"], dict)
        # Should find main's entry
        assert packet["behavior_model_entry"].get("function") == "main"

    def test_packet_contains_global_behavior(self, tmpdir_path):
        packet, _ = build_packet(
            FN_RECORD_MAIN,
            tmpdir_path,
            recovered_c=SIMPLE_C,
            recovered_readable_c=SIMPLE_C,
            behavior_model=BEHAVIOR_MODEL,
            behavior_profile=None,
            evidence_index=None,
            trace_report=None,
            quality_gate=None,
        )
        assert "global_behavior" in packet
        assert isinstance(packet["global_behavior"], list)
        assert len(packet["global_behavior"]) > 0

    def test_packet_contains_dynamic_summary(self, tmpdir_path):
        packet, _ = build_packet(
            FN_RECORD_MAIN,
            tmpdir_path,
            recovered_c=SIMPLE_C,
            recovered_readable_c=SIMPLE_C,
            behavior_model=None,
            behavior_profile=BEHAVIOR_PROFILE,
            evidence_index=None,
            trace_report=None,
            quality_gate=None,
        )
        assert packet["dynamic_summary"]["available"] is True
        assert packet["dynamic_summary"]["argv_sensitive"] is True

    def test_packet_contains_schema_version(self, tmpdir_path):
        packet, _ = build_packet(
            FN_RECORD_MAIN,
            tmpdir_path,
            recovered_c=SIMPLE_C,
            recovered_readable_c=SIMPLE_C,
            behavior_model=None,
            behavior_profile=None,
            evidence_index=None,
            trace_report=None,
            quality_gate=None,
        )
        assert packet["schema_version"] == "agent-packet-1.0"
        assert packet["phase"] == "10.1"

    def test_packet_function_name_set(self, tmpdir_path):
        packet, _ = build_packet(
            FN_RECORD_HELPER,
            tmpdir_path,
            recovered_c=SIMPLE_C,
            recovered_readable_c=SIMPLE_C,
            behavior_model=None,
            behavior_profile=None,
            evidence_index=None,
            trace_report=None,
            quality_gate=None,
        )
        assert packet["function"] == "helper"


# ── build_all_packets ─────────────────────────────────────────────────────────

class TestBuildAllPackets:
    def test_one_packet_per_function(self, tmpdir_path):
        _write_source_recon(tmpdir_path, [FN_RECORD_MAIN, FN_RECORD_HELPER])
        _write_recovered_c(tmpdir_path)
        _write_recovered_readable(tmpdir_path)

        packets, diag, _ = build_all_packets(tmpdir_path)
        assert len(packets) == 2
        fn_names = {p["function"] for p in packets}
        assert "main" in fn_names
        assert "helper" in fn_names

    def test_empty_without_source_recon(self, tmpdir_path):
        packets, diag, _ = build_all_packets(tmpdir_path)
        assert packets == []
        assert any("source_reconstruction" in d for d in diag)

    def test_no_crash_on_missing_recovered_c(self, tmpdir_path):
        _write_source_recon(tmpdir_path, [FN_RECORD_MAIN])
        # Do NOT write recovered.c
        packets, diag, _ = build_all_packets(tmpdir_path)
        assert len(packets) == 1  # built with empty C slices


# ── Token-safe C slicing ──────────────────────────────────────────────────────

class TestTokenSafeSlicer:
    def test_simple_slice(self):
        c = "int foo(int x) {\n    return x;\n}\n"
        result, diag = _extract_function_slice(c, "foo")
        assert "return x" in result
        assert not diag

    def test_brace_in_string_not_counted(self):
        c = 'void bar() {\n    printf("open {\\n");\n}\n'
        result, diag = _extract_function_slice(c, "bar")
        assert 'printf("open {' in result
        assert not diag

    def test_brace_in_block_comment_not_counted(self):
        c = "void baz() {\n    /* { not a real open */\n    return;\n}\n"
        result, diag = _extract_function_slice(c, "baz")
        assert "return" in result
        assert not diag

    def test_brace_in_line_comment_not_counted(self):
        c = "int qux(void) {\n    // { ignore\n    return 0;\n}\n"
        result, diag = _extract_function_slice(c, "qux")
        assert "return 0" in result
        assert not diag

    def test_function_not_found_returns_empty(self):
        c = "int existing(void) { return 1; }\n"
        result, diag = _extract_function_slice(c, "nonexistent")
        assert result == ""
        assert any("not found" in d for d in diag)

    def test_truncation_at_max_lines(self):
        body_lines = "\n".join(f"    x = {i};" for i in range(300))
        c = f"void big(void) {{\n{body_lines}\n}}\n"
        result, diag = _extract_function_slice(c, "big", max_lines=50)
        lines = result.splitlines()
        assert len(lines) <= 52  # 50 + truncation comment
        assert any("truncated" in d for d in diag)

    def test_nested_braces_balanced(self):
        c = "int nested(int x) {\n    if (x) {\n        return 1;\n    }\n    return 0;\n}\n"
        result, diag = _extract_function_slice(c, "nested")
        assert result.count("{") == result.count("}")


# ── Hash guards ───────────────────────────────────────────────────────────────

class TestHashGuards:
    def test_hashes_unchanged_after_build(self, tmpdir_path):
        _write_source_recon(tmpdir_path, [FN_RECORD_MAIN])
        _write_recovered_c(tmpdir_path)
        _write_recovered_readable(tmpdir_path)

        packets, diag, hashes_before = build_all_packets(tmpdir_path)
        changed = verify_input_hashes(tmpdir_path, hashes_before)
        assert changed == [], f"Hashes changed: {changed}"

    def test_detect_modified_artifact(self, tmpdir_path):
        _write_source_recon(tmpdir_path, [FN_RECORD_MAIN])
        _write_recovered_c(tmpdir_path)

        hashes_before = compute_input_hashes(tmpdir_path)

        # Simulate mutation
        (tmpdir_path / "recovered.c").write_text("// modified\n", encoding="utf-8")

        changed = verify_input_hashes(tmpdir_path, hashes_before)
        assert "recovered.c" in changed

    def test_detect_new_artifact_appearance(self, tmpdir_path):
        hashes_before = compute_input_hashes(tmpdir_path)  # all None (missing)

        # Simulate recovered_readable.c appearing mid-run (hash was None before)
        (tmpdir_path / "recovered_readable.c").write_text("new\n", encoding="utf-8")

        changed = verify_input_hashes(tmpdir_path, hashes_before)
        assert "recovered_readable.c" in changed


# ── No crash on bad function record ──────────────────────────────────────────

class TestRobustness:
    def test_malformed_fn_record_does_not_crash(self, tmpdir_path):
        _write_source_recon(tmpdir_path, [{"not_a_name": True}])
        _write_recovered_c(tmpdir_path)
        packets, diag, _ = build_all_packets(tmpdir_path)
        # Should produce one packet with function="unknown"
        assert len(packets) == 1
