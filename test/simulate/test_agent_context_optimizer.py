# -*- coding: utf-8 -*-
"""
Tests for src/agent/context_optimizer.py
"""
import json
import pytest
import tempfile
from pathlib import Path

from src.agent.context_optimizer import (
    _build_compact_packet,
    optimize_agent_packets,
    SCHEMA_COMPACT_PACKET,
)


def _big_packet(fn_name: str = "main", extra_chars: int = 0) -> dict:
    """Build a realistic raw packet that's large."""
    return {
        "function": fn_name,
        "address": "0x1000",
        "signature": "int main(int argc, char **argv)",
        "calls": ["printf", "malloc", "helper"],
        "called_by": [],
        "loops": [{"kind": "while", "header": "0x1010", "evidence": "static_cfg"}],
        "conditionals": [{"kind": "if_else", "address": "0x1020"}],
        "constants": [42, 0, 255],
        "strings": ["%d\\n", "hello"],
        "params": [{"name": "argc", "type": "int"}, {"name": "argv", "type": "char**"}],
        "return_type": "int",
        "dynamic_behavior": {"observed": True, "argv_sensitive": True, "stdout_varies": True},
        "recovered_readable_slice": "int main(int argc, char **argv) {\n    return 0;\n}\n",
        "known_uncertainties": ["source names unknown"],
        "forbidden_claims": ["semantic equivalence"],
        "evidence": [{"kind": "static", "detail": "calls printf"}],
        "raw_instructions": "LOTS OF ICKY DISASSEMBLY " * max(100, extra_chars),
        "xrefs": list(range(200)),
    }


def _small_packet(fn_name: str = "tiny") -> dict:
    return {
        "function": fn_name,
        "address": "0x2000",
        "calls": [],
    }


def _library_packet(fn_name: str = "printf") -> dict:
    return {
        "function": fn_name,
        "address": "0x3000",
        "calls": [],
    }


class TestBuildCompactPacket:
    def test_compact_preserves_function_name(self):
        pkt = _big_packet("main")
        compact = _build_compact_packet(pkt)
        assert compact["function"] == "main"
        assert compact["schema_version"] == SCHEMA_COMPACT_PACKET

    def test_compact_preserves_signature(self):
        compact = _build_compact_packet(_big_packet())
        assert compact["signature_guess"] == "int main(int argc, char **argv)"

    def test_compact_preserves_calls(self):
        compact = _build_compact_packet(_big_packet())
        assert "printf" in compact["calls"]

    def test_compact_has_structure_summary(self):
        compact = _build_compact_packet(_big_packet())
        assert "structure_summary" in compact
        assert "basic_blocks" in compact["structure_summary"]

    def test_compact_has_type_summary(self):
        compact = _build_compact_packet(_big_packet())
        assert "type_summary" in compact

    def test_compact_has_dynamic_summary(self):
        compact = _build_compact_packet(_big_packet())
        assert "dynamic_summary" in compact

    def test_compact_has_source_slice(self):
        compact = _build_compact_packet(_big_packet())
        assert "source_slice" in compact

    def test_compact_has_optimization_metadata(self):
        compact = _build_compact_packet(_big_packet())
        assert "optimization" in compact
        opt = compact["optimization"]
        assert "original_chars" in opt
        assert "compact_chars" in opt
        assert opt["compact_chars"] <= opt["original_chars"]

    def test_compact_drops_raw_instructions(self):
        compact = _build_compact_packet(_big_packet())
        assert "raw_instructions" not in compact

    def test_compact_drops_xrefs(self):
        compact = _build_compact_packet(_big_packet())
        assert "xrefs" not in compact

    def test_compact_respects_max_packet_chars(self):
        compact = _build_compact_packet(_big_packet(), max_packet_chars=16000)
        size = len(json.dumps(compact, ensure_ascii=False))
        assert size <= 16000

    def test_compact_very_small_budget_enters_summary_mode(self):
        """With a tiny budget, the optimizer should enter summary-only mode."""
        compact = _build_compact_packet(_big_packet(), max_packet_chars=200)
        assert compact.get("packet_mode") == "summary_only"

    def test_compact_preserves_forbidden_claims(self):
        compact = _build_compact_packet(_big_packet())
        assert "forbidden_claims" in compact
        assert len(compact["forbidden_claims"]) > 0

    def test_compact_no_source_slice_when_disabled(self):
        compact = _build_compact_packet(_big_packet(), include_source_slice=False)
        assert "source_slice" not in compact

    def test_compact_max_evidence_items(self):
        pkt = _big_packet()
        pkt["evidence"] = [{"detail": f"ev_{i}"} for i in range(50)]
        compact = _build_compact_packet(pkt, max_evidence_items=5)
        assert len(compact["top_evidence"]) <= 10  # initial + 5 evidence refs


class TestOptimizeAgentPackets:
    def test_creates_compact_dir_and_packets(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            pdir = out / "agent_packets"
            pdir.mkdir()
            (pdir / "pkt_main.json").write_text(
                json.dumps(_big_packet("main")), encoding="utf-8"
            )
            (pdir / "pkt_helper.json").write_text(
                json.dumps(_small_packet("helper")), encoding="utf-8"
            )

            paths, report = optimize_agent_packets(out)
            assert len(paths) == 2
            assert report["packets_optimized"] == 2
            assert (out / "agent_packets_compact").is_dir()
            assert (out / "agent_packet_optimization_report.json").exists()

    def test_skips_library_functions(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            pdir = out / "agent_packets"
            pdir.mkdir()
            (pdir / "pkt_printf.json").write_text(
                json.dumps(_library_packet("printf")), encoding="utf-8"
            )
            (pdir / "pkt_main.json").write_text(
                json.dumps(_big_packet("main")), encoding="utf-8"
            )

            paths, report = optimize_agent_packets(out)
            assert report["packets_skipped_library"] == 1
            assert report["packets_optimized"] == 1

    def test_full_mode_copies_without_optimization(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            pdir = out / "agent_packets"
            pdir.mkdir()
            raw = _big_packet("main")
            (pdir / "pkt_main.json").write_text(
                json.dumps(raw), encoding="utf-8"
            )

            paths, report = optimize_agent_packets(out, packet_mode="full")
            assert report["packet_mode"] == "full"
            # In full mode, compact_chars == original_chars
            for p in report["packets"]:
                if p["status"] == "full_copy":
                    assert p["compact_chars"] == p["original_chars"]

    def test_no_packets_dir_returns_empty(self):
        with tempfile.TemporaryDirectory() as td:
            paths, report = optimize_agent_packets(Path(td))
            assert len(paths) == 0
            assert report["status"] == "no_packets"

    def test_optimization_report_has_compression_ratio(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            pdir = out / "agent_packets"
            pdir.mkdir()
            (pdir / "pkt_main.json").write_text(
                json.dumps(_big_packet("main")), encoding="utf-8"
            )

            _, report = optimize_agent_packets(out)
            assert "compression_ratio" in report
            assert report["compression_ratio"] <= 1.0
