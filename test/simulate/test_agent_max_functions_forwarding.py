# -*- coding: utf-8 -*-
"""
Tests for --max-functions forwarding and enforcement across CLI layers.
"""
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from src.agent.cli import run_agent_debate_cli
from src.agent.debate import run_debate


SIMPLE_SOURCE_RECON = {
    "functions": [
        {
            "name": "main",
            "entry_point": "0x1000",
            "signature": "int main(int argc, char **argv)",
            "calls": [],
            "loops": 0,
            "conditions": 0,
        },
        {
            "name": "helper",
            "entry_point": "0x2000",
            "signature": "void helper(void)",
            "calls": [],
            "loops": 0,
            "conditions": 0,
        },
        {
            "name": "compute",
            "entry_point": "0x3000",
            "signature": "int compute(int x)",
            "calls": [],
            "loops": 0,
            "conditions": 0,
        },
    ]
}

SIMPLE_C = "int main(int argc, char **argv) {\n    return 0;\n}\n"

FAKE_COMPLETE_RESULT = {
    "function": "main",
    "facts": {
        "calls": [], "loops": 0, "conditions": 0,
        "returns_value": True, "constants": [],
        "layout_candidates": [], "dynamic_observations_present": False,
        "global_behavior_refs": [],
    },
    "evidence_refs": [{"kind": "static", "source": "a.json", "detail": "has main"}],
    "uncertainties": ["source variable names are unknown"],
    "dynamic_behavior": [],
    "limitations": ["dynamic evidence only covers provided inputs"],
    "hypotheses": [],
    "suggested_names": [],
    "suggested_structs": [],
    "critic_findings": [],
    "rejected_suggestions": [],
    "summary": {
        "text": "Appears to handle command-line input.",
        "confidence": "low",
        "evidence_level": "static_evidence",
        "critic_status": "accept",
        "requires_human_approval": True,
    },
    "suggestions": [],
    "rejected": [],
    "_provider_diagnostics": {
        "provider": "ollama",
        "model": "llama3.3:70b",
        "json_repair": "direct",
        "duration_ms": 50,
        "parse_status": "ok",
    },
}


def _fake_complete_json(*, system_prompt, user_payload, schema_name):
    return FAKE_COMPLETE_RESULT


@pytest.fixture
def out_dir():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        (p / "source_reconstruction.json").write_text(
            json.dumps(SIMPLE_SOURCE_RECON), encoding="utf-8"
        )
        (p / "recovered.c").write_text(SIMPLE_C, encoding="utf-8")
        (p / "recovered_readable.c").write_text(SIMPLE_C, encoding="utf-8")
        (p / "behavior_model.json").write_text(
            json.dumps({"functions": [], "global_behavior": []}), encoding="utf-8"
        )
        yield p


class TestMaxFunctionsEnforcement:
    """Verify --max-functions limits provider calls to the exact count."""

    def test_debate_max_functions_1_calls_provider_once(self):
        """run_debate with max_functions=1 should call provider for exactly 1 function."""
        provider = MagicMock()
        provider.complete_json.side_effect = _fake_complete_json

        packets = [
            {"function": "main"},
            {"function": "helper"},
            {"function": "compute"},
        ]

        records, suggestions = run_debate(
            packets, provider, max_functions=1,
        )
        assert len(records) == 1
        assert records[0]["function"] == "main"
        # 5 LLM agent calls per function (evidence, dynamic, recon, critic, finalizer)
        assert provider.complete_json.call_count == 5

    def test_debate_max_functions_2_calls_provider_twice(self):
        provider = MagicMock()
        provider.complete_json.side_effect = _fake_complete_json

        packets = [
            {"function": "main"},
            {"function": "helper"},
            {"function": "compute"},
        ]

        records, _ = run_debate(packets, provider, max_functions=2)
        assert len(records) == 2
        assert provider.complete_json.call_count == 10  # 5 * 2

    def test_packet_builder_builds_all_while_debate_selects_subset(self, out_dir):
        """Packet builder may build all packets; debate limits them."""
        avail = {
            "available": True, "host": "http://localhost:11434",
            "model": "llama3.3:70b", "error": None, "suggestion": None,
        }
        with patch("src.agent.providers.ollama.OllamaProvider.check_available",
                   return_value=avail), \
             patch("src.agent.providers.ollama.OllamaProvider.complete_json",
                   side_effect=_fake_complete_json) as mock_complete:
            rc = run_agent_debate_cli([
                "--out-dir", str(out_dir),
                "--provider", "ollama",
                "--max-functions", "1",
            ])
        assert rc == 0
        # Only 1 function debated → 5 LLM calls
        assert mock_complete.call_count == 5

    def test_library_functions_skipped_not_counted(self):
        """Library functions are skipped and do not consume max_functions slots."""
        provider = MagicMock()
        provider.complete_json.side_effect = _fake_complete_json

        packets = [
            {"function": "printf"},   # library — skip
            {"function": "strlen"},   # library — skip
            {"function": "_main"},    # user — debate
            {"function": "_score_packet"},  # user — debate
        ]

        records, _ = run_debate(packets, provider, max_functions=1)
        # Only 1 user function debated (max_functions=1), libraries skipped
        assert len(records) == 1
        assert records[0]["function"] == "_main"
        assert provider.complete_json.call_count == 5

    def test_cli_prints_correct_function_count(self, out_dir, capsys):
        """CLI output should show actual debatable count, not total loaded."""
        avail = {
            "available": True, "host": "http://localhost:11434",
            "model": "llama3.3:70b", "error": None, "suggestion": None,
        }
        with patch("src.agent.providers.ollama.OllamaProvider.check_available",
                   return_value=avail), \
             patch("src.agent.providers.ollama.OllamaProvider.complete_json",
                   side_effect=_fake_complete_json):
            rc = run_agent_debate_cli([
                "--out-dir", str(out_dir),
                "--provider", "ollama",
                "--max-functions", "1",
            ])
        assert rc == 0
        captured = capsys.readouterr()
        assert "functions=1" in captured.out
