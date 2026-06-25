# -*- coding: utf-8 -*-
"""
Tests for agent-debate CLI without any real provider calls.
No Ollama or Groq required.
"""
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.agent.cli import run_agent_debate_cli, run_build_agent_packets_cli


SIMPLE_SOURCE_RECON = {
    "functions": [
        {
            "name": "main",
            "entry_point": "0x1000",
            "signature": "int main(int argc, char **argv)",
            "calls": [],
            "loops": 0,
            "conditions": 0,
        }
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


# ── Provider rejection ─────────────────────────────────────────────────────────

class TestProviderRejection:
    def test_unknown_provider_exits_nonzero(self, out_dir):
        rc = run_agent_debate_cli([
            "--out-dir", str(out_dir),
            "--provider", "badprovider",
        ])
        assert rc != 0

    def test_ollama_unavailable_exits_1(self, out_dir):
        unavail = {
            "available": False, "host": "http://localhost:11434",
            "model": "llama3.3:70b", "error": "not running",
            "suggestion": "Start with ollama serve",
        }
        with patch("src.agent.providers.ollama.OllamaProvider.check_available",
                   return_value=unavail):
            rc = run_agent_debate_cli([
                "--out-dir", str(out_dir),
                "--provider", "ollama",
            ])
        assert rc == 1

    def test_groq_missing_key_exits_1(self, out_dir, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("HEPHAESTUS_GROQ_API_KEY", raising=False)
        rc = run_agent_debate_cli([
            "--out-dir", str(out_dir),
            "--provider", "groq",
        ])
        assert rc == 1


# ── Full mock debate run ───────────────────────────────────────────────────────

class TestMockDebateRun:
    def _run_with_mock_ollama(self, out_dir):
        avail = {
            "available": True, "host": "http://localhost:11434",
            "model": "llama3.3:70b", "error": None, "suggestion": None,
        }
        with patch("src.agent.providers.ollama.OllamaProvider.check_available",
                   return_value=avail), \
             patch("src.agent.providers.ollama.OllamaProvider.complete_json",
                   side_effect=_fake_complete_json):
            return run_agent_debate_cli([
                "--out-dir", str(out_dir),
                "--provider", "ollama",
                "--max-functions", "1",
            ])

    def test_debate_produces_report(self, out_dir):
        rc = self._run_with_mock_ollama(out_dir)
        assert rc == 0
        assert (out_dir / "agent_debate_report.json").exists()

    def test_debate_produces_suggestions(self, out_dir):
        rc = self._run_with_mock_ollama(out_dir)
        assert rc == 0
        assert (out_dir / "agent_suggestions.json").exists()

    def test_no_recovered_agent_c_produced(self, out_dir):
        self._run_with_mock_ollama(out_dir)
        assert not (out_dir / "recovered_agent.c").exists()

    def test_debate_does_not_modify_recovered_c(self, out_dir):
        original = (out_dir / "recovered.c").read_text()
        self._run_with_mock_ollama(out_dir)
        assert (out_dir / "recovered.c").read_text() == original

    def test_debate_does_not_modify_recovered_readable_c(self, out_dir):
        original = (out_dir / "recovered_readable.c").read_text()
        self._run_with_mock_ollama(out_dir)
        assert (out_dir / "recovered_readable.c").read_text() == original

    def test_debate_report_schema(self, out_dir):
        self._run_with_mock_ollama(out_dir)
        report = json.loads((out_dir / "agent_debate_report.json").read_text())
        assert report["schema_version"] == "agent-debate-1.0"
        assert report["phase"] == "10.2"
        assert "provider" in report
        assert "model" in report
        assert "functions_reviewed" in report
        assert "suggestions_total" in report

    def test_suggestions_schema(self, out_dir):
        self._run_with_mock_ollama(out_dir)
        sug = json.loads((out_dir / "agent_suggestions.json").read_text())
        assert sug["schema_version"] == "agent-suggestions-1.0"
        assert "suggestions" in sug
        assert isinstance(sug["suggestions"], list)

    def test_no_forbidden_phrases_in_reports(self, out_dir):
        self._run_with_mock_ollama(out_dir)
        forbidden = [
            "definitely equivalent", "semantic equivalence", "exact source",
            "guaranteed", "proven struct", "recovered field name",
            "same behavior as original",
        ]
        for artifact in ["agent_debate_report.json", "agent_suggestions.json"]:
            path = out_dir / artifact
            if path.exists():
                text = path.read_text().lower()
                for phrase in forbidden:
                    assert phrase not in text, \
                        f"Forbidden phrase '{phrase}' found in {artifact}"


# ── Hash guard ─────────────────────────────────────────────────────────────────

class TestHashGuardDebate:
    def test_abort_if_recovered_c_changes_mid_debate(self, out_dir):
        """Simulate artifact mutation after packets built but during debate."""
        avail = {
            "available": True, "host": "http://localhost:11434",
            "model": "llama3.3:70b", "error": None, "suggestion": None,
        }

        call_count = [0]

        def mutating_complete_json(self_inner, *, system_prompt, user_payload, schema_name):
            call_count[0] += 1
            if call_count[0] == 1:
                # Simulate mutation on first agent call
                (out_dir / "recovered.c").write_text("// mutated\n", encoding="utf-8")
            return FAKE_COMPLETE_RESULT

        with patch("src.agent.providers.ollama.OllamaProvider.check_available",
                   return_value=avail), \
             patch("src.agent.providers.ollama.OllamaProvider.complete_json",
                   side_effect=mutating_complete_json):
            rc = run_agent_debate_cli([
                "--out-dir", str(out_dir),
                "--provider", "ollama",
                "--max-functions", "1",
            ])
        # Should exit 2 (safety violation) or at minimum not 0
        assert rc != 0
