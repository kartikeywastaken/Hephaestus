# -*- coding: utf-8 -*-
"""
Real Groq integration tests.

Requires:
  HEPHAESTUS_RUN_GROQ_TESTS=1
  GROQ_API_KEY=<your_key>  (or HEPHAESTUS_GROQ_API_KEY)

Skip unless env var is set.
"""
import json
import os
import pytest
import tempfile
from pathlib import Path

pytestmark = pytest.mark.skipif(
    os.environ.get("HEPHAESTUS_RUN_GROQ_TESTS") != "1",
    reason="Set HEPHAESTUS_RUN_GROQ_TESTS=1 and GROQ_API_KEY=... to run real Groq tests."
)

from src.agent.providers.groq import GroqProvider, resolve_groq_api_key
from src.agent.models import DEFAULT_OLLAMA_MODEL

GROQ_MODEL = os.environ.get("HEPHAESTUS_AGENT_MODEL", "llama-3.3-70b-versatile")


@pytest.fixture
def groq_api_key():
    return resolve_groq_api_key()


@pytest.fixture
def provider(groq_api_key) -> GroqProvider:
    return GroqProvider(
        api_key=groq_api_key,
        model=GROQ_MODEL,
        timeout_s=120,
        temperature=0.0,
    )


class TestGroqProviderIntegration:
    def test_check_available_returns_true(self, provider):
        result = provider.check_available()
        assert result["available"] is True, (
            f"Groq unavailable: {result.get('error')}. "
            f"Hint: {result.get('suggestion')}"
        )

    def test_complete_json_returns_dict(self, provider):
        result = provider.complete_json(
            system_prompt="Return only valid JSON with key 'status' set to 'ok'.",
            user_payload={"task": "Return {\"status\": \"ok\"}"},
            schema_name="test_basic",
        )
        assert isinstance(result, dict)

    def test_complete_json_sends_json_object_format(self, provider):
        result = provider.complete_json(
            system_prompt="Return only valid JSON.",
            user_payload={"task": "Return {\"ok\": true}"},
            schema_name="test_format",
        )
        diag = result.get("_provider_diagnostics", {})
        assert diag.get("parse_status") == "ok"

    def test_provider_diagnostics_present(self, provider):
        result = provider.complete_json(
            system_prompt="Return only valid JSON.",
            user_payload={"task": "Return {\"ok\": true}"},
            schema_name="test_diag",
        )
        diag = result["_provider_diagnostics"]
        assert diag["provider"] == "groq"
        assert diag["model"] == GROQ_MODEL
        assert "duration_ms" in diag

    def test_api_key_not_in_response(self, provider, groq_api_key):
        result = provider.complete_json(
            system_prompt="Return only valid JSON.",
            user_payload={"task": "Return {\"ok\": true}"},
            schema_name="test_key_leak",
        )
        result_str = json.dumps(result)
        assert groq_api_key not in result_str


class TestGroqDebateIntegration:
    def test_full_debate_with_groq(self, groq_api_key):
        from src.agent.cli import run_agent_debate_cli, run_build_agent_packets_cli
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            sr = {
                "functions": [
                    {
                        "name": "main",
                        "entry_point": "0x1000",
                        "signature": "int main(int argc, char **argv)",
                        "calls": [],
                        "loops": 0,
                        "conditions": 1,
                    }
                ]
            }
            c = "int main(int argc, char **argv) {\n    if (argc > 1) return 1;\n    return 0;\n}\n"
            (p / "source_reconstruction.json").write_text(json.dumps(sr))
            (p / "recovered.c").write_text(c)
            (p / "recovered_readable.c").write_text(c)
            (p / "behavior_model.json").write_text(
                json.dumps({"functions": [], "global_behavior": []})
            )

            run_build_agent_packets_cli(["--out-dir", str(p)])
            rc = run_agent_debate_cli([
                "--out-dir", str(p),
                "--provider", "groq",
                "--model", GROQ_MODEL,
                "--max-functions", "1",
                "--timeout-s", "60",
            ])
            assert rc == 0
            assert (p / "agent_debate_report.json").exists()
            report = json.loads((p / "agent_debate_report.json").read_text())
            assert report["provider"] == "groq"
            assert groq_api_key not in json.dumps(report)
            assert not (p / "recovered_agent.c").exists()
