# -*- coding: utf-8 -*-
"""
Tests for Phase 10 pipeline integration.
Verifies stage_defs, artifact registry, runner wiring, and run-all flag defaults.
No Ollama or Groq required.
"""
import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.pipeline.stage_defs import OPTIONAL_PIPELINE_STAGES, STAGE_OUTPUTS
from src.utils.artifacts import (
    KNOWN_ARTIFACT_FILES,
    KNOWN_ARTIFACT_DIRS,
    clean_known_artifacts,
)


# ── Stage definitions ──────────────────────────────────────────────────────────

class TestStageDefs:
    def test_build_agent_packets_in_optional_stages(self):
        assert "build_agent_packets" in OPTIONAL_PIPELINE_STAGES

    def test_agent_debate_in_optional_stages(self):
        assert "agent_debate" in OPTIONAL_PIPELINE_STAGES

    def test_stage_outputs_build_agent_packets(self):
        assert "build_agent_packets" in STAGE_OUTPUTS
        assert "agent_packet_manifest.json" in STAGE_OUTPUTS["build_agent_packets"]

    def test_stage_outputs_agent_debate(self):
        assert "agent_debate" in STAGE_OUTPUTS
        assert "agent_debate_report.json" in STAGE_OUTPUTS["agent_debate"]
        assert "agent_suggestions.json" in STAGE_OUTPUTS["agent_debate"]


# ── Artifact registry ──────────────────────────────────────────────────────────

class TestArtifactRegistry:
    def test_agent_packet_manifest_registered(self):
        assert "agent_packet_manifest.json" in KNOWN_ARTIFACT_FILES

    def test_agent_debate_report_registered(self):
        assert "agent_debate_report.json" in KNOWN_ARTIFACT_FILES

    def test_agent_suggestions_registered(self):
        assert "agent_suggestions.json" in KNOWN_ARTIFACT_FILES

    def test_agent_packets_dir_registered(self):
        assert "agent_packets" in KNOWN_ARTIFACT_DIRS


# ── Clean artifacts ────────────────────────────────────────────────────────────

class TestCleanArtifacts:
    def test_clean_removes_agent_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "agent_packet_manifest.json").write_text("{}", encoding="utf-8")
            (p / "agent_debate_report.json").write_text("{}", encoding="utf-8")
            (p / "agent_suggestions.json").write_text("{}", encoding="utf-8")

            deleted = clean_known_artifacts(p)

            assert "agent_packet_manifest.json" in deleted
            assert "agent_debate_report.json" in deleted
            assert "agent_suggestions.json" in deleted

    def test_clean_removes_agent_packets_dir(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            agent_dir = p / "agent_packets"
            agent_dir.mkdir()
            (agent_dir / "main.json").write_text("{}", encoding="utf-8")

            deleted = clean_known_artifacts(p)

            assert "agent_packets" in deleted
            assert not agent_dir.exists()

    def test_clean_does_not_remove_non_agent_files(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "my_custom_file.txt").write_text("keep", encoding="utf-8")
            (p / "agent_debate_report.json").write_text("{}", encoding="utf-8")

            clean_known_artifacts(p)

            assert (p / "my_custom_file.txt").exists()


# ── Pipeline runner wiring ─────────────────────────────────────────────────────

class TestRunnerWiring:
    def test_run_pipeline_accepts_agent_debate_param(self):
        """run_pipeline should accept agent_debate without TypeError."""
        from src.pipeline.runner import run_pipeline
        import inspect
        sig = inspect.signature(run_pipeline)
        assert "agent_debate" in sig.parameters
        assert "agent_provider" in sig.parameters
        assert "agent_model" in sig.parameters
        assert "agent_api_key_env" in sig.parameters
        assert "agent_groq_host" in sig.parameters
        assert "agent_ollama_host" in sig.parameters
        assert "agent_timeout_s" in sig.parameters
        assert "agent_temperature" in sig.parameters
        assert "agent_max_functions" in sig.parameters

    def test_default_agent_debate_is_false(self):
        from src.pipeline.runner import run_pipeline
        import inspect
        sig = inspect.signature(run_pipeline)
        assert sig.parameters["agent_debate"].default is False


# ── build-agent-packets on partial artifacts ───────────────────────────────────

class TestBuildPacketsPartialArtifacts:
    def test_no_crash_without_behavior_model(self):
        from src.agent.cli import run_build_agent_packets_cli
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            sr = {"functions": [{"name": "main", "calls": []}]}
            (p / "source_reconstruction.json").write_text(json.dumps(sr), encoding="utf-8")
            (p / "recovered.c").write_text("int main(){return 0;}\n", encoding="utf-8")
            (p / "recovered_readable.c").write_text("int main(){return 0;}\n", encoding="utf-8")
            # No behavior_model.json
            rc = run_build_agent_packets_cli(["--out-dir", str(p)])
            assert rc == 0

    def test_fails_gracefully_without_source_recon(self):
        from src.agent.cli import run_build_agent_packets_cli
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            rc = run_build_agent_packets_cli(["--out-dir", str(p)])
            assert rc != 0


# ── Default run-all does not trigger agents ────────────────────────────────────

class TestDefaultRunAllNoAgents:
    def test_build_agent_packets_not_in_default_stages(self):
        """
        Without agent_debate=True, build_agent_packets should not appear
        in the active stage list for a standard run-all.
        """
        from src.pipeline.stage_defs import PIPELINE_STAGES
        assert "build_agent_packets" not in PIPELINE_STAGES

    def test_agent_debate_not_in_default_stages(self):
        from src.pipeline.stage_defs import PIPELINE_STAGES
        assert "agent_debate" not in PIPELINE_STAGES
