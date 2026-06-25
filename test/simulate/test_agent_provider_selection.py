# -*- coding: utf-8 -*-
"""
Tests for provider selection logic in agent CLI and both provider factories.
No real API calls. Monkeypatches HTTP.
"""
import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.agent.cli import run_agent_debate_cli, run_build_agent_packets_cli


# ── Helpers ───────────────────────────────────────────────────────────────────

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


def _write_artifacts(out_dir: Path):
    (out_dir / "source_reconstruction.json").write_text(
        json.dumps(SIMPLE_SOURCE_RECON), encoding="utf-8"
    )
    (out_dir / "recovered.c").write_text(SIMPLE_C, encoding="utf-8")
    (out_dir / "recovered_readable.c").write_text(SIMPLE_C, encoding="utf-8")
    (out_dir / "behavior_model.json").write_text(
        json.dumps({"functions": [], "global_behavior": []}), encoding="utf-8"
    )


@pytest.fixture
def out_dir():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        _write_artifacts(p)
        yield p


# ── Shared fake complete_json (module-level, no self) ─────────────────────────

def _fake_complete_json_groq(*, system_prompt, user_payload, schema_name):
    return {
        "function": "main",
        "facts": {
            "calls": [], "loops": 0, "conditions": 0,
            "returns_value": True, "constants": [],
            "layout_candidates": [], "dynamic_observations_present": False,
            "global_behavior_refs": [],
        },
        "evidence_refs": [{"kind": "static", "source": "a.json", "detail": "x"}],
        "uncertainties": [],
        "dynamic_behavior": [],
        "limitations": ["dynamic evidence only covers provided inputs"],
        "hypotheses": [],
        "suggested_names": [],
        "suggested_structs": [],
        "critic_findings": [],
        "rejected_suggestions": [],
        "summary": {
            "text": "Appears to handle input.",
            "confidence": "low",
            "evidence_level": "static_evidence",
            "critic_status": "accept",
            "requires_human_approval": True,
        },
        "suggestions": [],
        "rejected": [],
        "_provider_diagnostics": {
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "json_repair": "direct",
            "duration_ms": 100,
            "parse_status": "ok",
        },
    }


# ── Provider = unsupported → fail cleanly ─────────────────────────────────────

class TestProviderValidation:
    def test_invalid_provider_fails_with_exit_1(self, out_dir, capsys):
        # argparse choices enforcement: should fail before even loading provider
        rc = run_agent_debate_cli([
            "--out-dir", str(out_dir),
            "--provider", "magic_cloud",
        ])
        # argparse will exit(2) on invalid choice
        assert rc != 0

    def test_ollama_provider_does_not_require_api_key(self, out_dir, monkeypatch):
        # Ensure no GROQ keys in env
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("HEPHAESTUS_GROQ_API_KEY", raising=False)

        unavail = {
            "available": False,
            "host": "http://localhost:11434",
            "model": "llama3.3:70b",
            "error": "Ollama not running",
            "suggestion": "Run ollama serve",
        }
        with patch("src.agent.providers.ollama.OllamaProvider.check_available",
                   return_value=unavail):
            rc = run_agent_debate_cli([
                "--out-dir", str(out_dir),
                "--provider", "ollama",
                "--max-functions", "0",
            ])
        # Should fail due to unavailable, but NOT due to key error
        assert rc == 1

    def test_groq_provider_requires_api_key(self, out_dir, monkeypatch):
        # Remove env vars first
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("HEPHAESTUS_GROQ_API_KEY", raising=False)
        # Suppress .env.local loader so the real key cannot be re-injected
        # by the CLI startup call to load_default_env_files().
        with patch("src.utils.env_loader.load_default_env_files", return_value=None):
            rc = run_agent_debate_cli([
                "--out-dir", str(out_dir),
                "--provider", "groq",
            ])
        assert rc == 1

    def test_groq_reads_groq_api_key_env(self, out_dir, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "sk-test-key")

        unavail = {
            "available": False,
            "host": "https://api.groq.com/openai/v1",
            "model": "llama-3.3-70b-versatile",
            "error": "Groq model not found",
            "suggestion": "Check model name",
        }
        with patch("src.agent.providers.groq.GroqProvider.check_available",
                   return_value=unavail):
            rc = run_agent_debate_cli([
                "--out-dir", str(out_dir),
                "--provider", "groq",
                "--max-functions", "0",
            ])
        assert rc == 1

    def test_groq_reads_hephaestus_groq_api_key_fallback(self, out_dir, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.setenv("HEPHAESTUS_GROQ_API_KEY", "sk-hep-test")

        unavail = {
            "available": False,
            "host": "https://api.groq.com/openai/v1",
            "model": "llama-3.3-70b-versatile",
            "error": "Network error",
            "suggestion": None,
        }
        with patch("src.agent.providers.groq.GroqProvider.check_available",
                   return_value=unavail):
            rc = run_agent_debate_cli([
                "--out-dir", str(out_dir),
                "--provider", "groq",
                "--max-functions", "0",
            ])
        assert rc == 1

    def test_api_key_env_flag_custom_var(self, out_dir, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("HEPHAESTUS_GROQ_API_KEY", raising=False)
        monkeypatch.setenv("MY_CUSTOM_GROQ_KEY", "sk-custom-var")

        unavail = {
            "available": False,
            "host": "https://api.groq.com/openai/v1",
            "model": "llama-3.3-70b-versatile",
            "error": "test",
            "suggestion": None,
        }
        with patch("src.agent.providers.groq.GroqProvider.check_available",
                   return_value=unavail):
            rc = run_agent_debate_cli([
                "--out-dir", str(out_dir),
                "--provider", "groq",
                "--api-key-env", "MY_CUSTOM_GROQ_KEY",
                "--max-functions", "0",
            ])
        assert rc == 1


# ── API key not in reports ─────────────────────────────────────────────────────

class TestApiKeyNotInReports:
    def test_api_key_absent_from_debate_report(self, out_dir, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "sk-do-not-leak")
        avail = {"available": True, "host": "x", "model": "m", "error": None, "suggestion": None}

        with patch("src.agent.providers.groq.GroqProvider.check_available", return_value=avail), \
             patch("src.agent.providers.groq.GroqProvider.complete_json",
                   side_effect=_fake_complete_json_groq):
            run_agent_debate_cli([
                "--out-dir", str(out_dir),
                "--provider", "groq",
                "--model", "llama-3.3-70b-versatile",
                "--max-functions", "1",
            ])

        debate_path = out_dir / "agent_debate_report.json"
        suggestions_path = out_dir / "agent_suggestions.json"

        if debate_path.exists():
            report_text = debate_path.read_text()
            assert "sk-do-not-leak" not in report_text
            assert "Bearer" not in report_text

        if suggestions_path.exists():
            sug_text = suggestions_path.read_text()
            assert "sk-do-not-leak" not in sug_text

    def test_report_records_provider_and_model_not_key(self, out_dir, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "sk-private")
        avail = {"available": True, "host": "x", "model": "m", "error": None, "suggestion": None}

        with patch("src.agent.providers.groq.GroqProvider.check_available", return_value=avail), \
             patch("src.agent.providers.groq.GroqProvider.complete_json",
                   side_effect=_fake_complete_json_groq):
            run_agent_debate_cli([
                "--out-dir", str(out_dir),
                "--provider", "groq",
                "--model", "llama-3.3-70b-versatile",
                "--max-functions", "1",
            ])

        debate_path = out_dir / "agent_debate_report.json"
        if debate_path.exists():
            report = json.loads(debate_path.read_text())
            assert report["provider"] == "groq"
            assert report["model"] == "llama-3.3-70b-versatile"
            assert "sk-private" not in json.dumps(report)


# ── build-agent-packets smoke ──────────────────────────────────────────────────

class TestBuildAgentPacketsCli:
    def test_creates_agent_packets_dir(self, out_dir):
        rc = run_build_agent_packets_cli(["--out-dir", str(out_dir)])
        assert rc == 0
        assert (out_dir / "agent_packets").is_dir()

    def test_writes_manifest(self, out_dir):
        rc = run_build_agent_packets_cli(["--out-dir", str(out_dir)])
        assert rc == 0
        assert (out_dir / "agent_packet_manifest.json").exists()

    def test_manifest_has_correct_schema(self, out_dir):
        run_build_agent_packets_cli(["--out-dir", str(out_dir)])
        manifest = json.loads((out_dir / "agent_packet_manifest.json").read_text())
        assert manifest["schema_version"] == "agent-packet-manifest-1.0"
        assert manifest["packets_written"] >= 1

    def test_does_not_modify_recovered_c(self, out_dir):
        original = (out_dir / "recovered.c").read_text()
        run_build_agent_packets_cli(["--out-dir", str(out_dir)])
        assert (out_dir / "recovered.c").read_text() == original

    def test_does_not_modify_recovered_readable_c(self, out_dir):
        original = (out_dir / "recovered_readable.c").read_text()
        run_build_agent_packets_cli(["--out-dir", str(out_dir)])
        assert (out_dir / "recovered_readable.c").read_text() == original
