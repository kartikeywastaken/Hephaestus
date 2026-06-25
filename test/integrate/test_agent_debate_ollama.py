# -*- coding: utf-8 -*-
"""
Real Ollama debate integration tests.

Requires:
  HEPHAESTUS_RUN_OLLAMA_TESTS=1
  ollama serve  (running)
  ollama pull llama3.3:70b

Skip unless env var is set.
"""
import json
import os
import pytest
import tempfile
from pathlib import Path

pytestmark = pytest.mark.skipif(
    os.environ.get("HEPHAESTUS_RUN_OLLAMA_TESTS") != "1",
    reason="Set HEPHAESTUS_RUN_OLLAMA_TESTS=1 to run real Ollama debate tests."
)

from src.agent.cli import run_agent_debate_cli, run_build_agent_packets_cli
from src.agent.models import DEFAULT_OLLAMA_HOST, DEFAULT_OLLAMA_MODEL

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
OLLAMA_MODEL = os.environ.get("HEPHAESTUS_AGENT_MODEL", DEFAULT_OLLAMA_MODEL)

SIMPLE_SOURCE_RECON = {
    "functions": [
        {
            "name": "main",
            "entry_point": "0x1000",
            "signature": "int main(int argc, char **argv)",
            "calls": [],
            "loops": 0,
            "conditions": 1,
            "returns_value": True,
            "return_type": "int",
            "params": ["int argc", "char **argv"],
        }
    ]
}
SIMPLE_C = "int main(int argc, char **argv) {\n    if (argc > 1) return 1;\n    return 0;\n}\n"

FORBIDDEN_PHRASES = [
    "definitely equivalent", "semantic equivalence", "exact source",
    "guaranteed", "proven struct", "recovered field name",
    "same behavior as original", "full behavioral equivalence",
]


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


class TestOllamaFullDebate:
    def _build_and_debate(self, out_dir: Path) -> int:
        run_build_agent_packets_cli(["--out-dir", str(out_dir)])
        return run_agent_debate_cli([
            "--out-dir", str(out_dir),
            "--provider", "ollama",
            "--model", OLLAMA_MODEL,
            "--ollama-host", OLLAMA_HOST,
            "--max-functions", "1",
            "--timeout-s", "180",
        ])

    def test_writes_debate_report(self, out_dir):
        self._build_and_debate(out_dir)
        assert (out_dir / "agent_debate_report.json").exists()

    def test_writes_suggestions(self, out_dir):
        self._build_and_debate(out_dir)
        assert (out_dir / "agent_suggestions.json").exists()

    def test_debate_report_schema(self, out_dir):
        self._build_and_debate(out_dir)
        report = json.loads((out_dir / "agent_debate_report.json").read_text())
        assert report["schema_version"] == "agent-debate-1.0"
        assert report["functions_reviewed"] >= 1
        assert report["provider"] in ("ollama",)

    def test_no_recovered_agent_c_emitted(self, out_dir):
        self._build_and_debate(out_dir)
        assert not (out_dir / "recovered_agent.c").exists()

    def test_no_forbidden_phrases_in_reports(self, out_dir):
        self._build_and_debate(out_dir)
        for artifact in ["agent_debate_report.json", "agent_suggestions.json"]:
            path = out_dir / artifact
            if path.exists():
                text = path.read_text().lower()
                for phrase in FORBIDDEN_PHRASES:
                    assert phrase not in text, \
                        f"Forbidden phrase '{phrase}' found in {artifact}"

    def test_static_artifacts_unchanged(self, out_dir):
        original_c = (out_dir / "recovered.c").read_text()
        original_readable = (out_dir / "recovered_readable.c").read_text()
        self._build_and_debate(out_dir)
        assert (out_dir / "recovered.c").read_text() == original_c
        assert (out_dir / "recovered_readable.c").read_text() == original_readable
