# -*- coding: utf-8 -*-
"""
Tests for reconstruct CLI (Phase 11.5).
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

from src.pipeline.reconstruct_cli import run_reconstruct_cli


def test_reconstruct_defaults_and_forwarding():
    """Verify reconstruct default arguments and pipeline forwarding."""
    # We patch run_pipeline to check what is passed to it
    with patch("src.pipeline.runner.run_pipeline") as mock_run, \
         patch("src.pipeline.reconstruct_cli.load_default_env_files") as mock_load_env, \
         patch("src.agent.providers.groq.resolve_groq_api_key") as mock_resolve_key, \
         patch("os.path.exists", return_value=True):
        
        mock_run.return_value = {"status": "ok"}
        mock_resolve_key.return_value = "mock_key"

        argv = ["./t", "--out-dir", "test_artifacts"]
        code = run_reconstruct_cli(argv)

        assert code == 0
        mock_load_env.assert_called_once()
        mock_resolve_key.assert_called_once_with(explicit_key=None, api_key_env=None)
        
        # Verify run_pipeline parameters
        mock_run.assert_called_once()
        kwargs = mock_run.call_args[1]

        # Check default wiring
        assert kwargs["binary_path"] == "./t"
        assert kwargs["out_dir"] == "test_artifacts"
        assert kwargs["use_ghidra"] is True
        assert kwargs["use_radare2"] is True
        assert kwargs["validate"] is True
        assert kwargs["evidence_index"] is True
        assert kwargs["trace_report"] is True
        assert kwargs["quality_gate"] is True
        assert kwargs["readable"] is True
        assert kwargs["dynamic"] is True
        assert kwargs["fuse_behavior"] is True
        assert kwargs["agent_debate"] is True
        assert kwargs["generate_agent_source"] is True
        assert kwargs["agent_provider"] == "groq"
        assert kwargs["agent_model"] == "llama-3.3-70b-versatile"
        assert kwargs["source_provider"] == "groq"
        assert kwargs["source_model"] == "llama-3.3-70b-versatile"
        assert kwargs["agent_max_functions"] == 1
        assert kwargs["source_max_functions"] == 1
        assert kwargs["overwrite_agent_source"] is False


def test_reconstruct_skips():
    """Verify skip flags correctly disable pipeline options."""
    with patch("src.pipeline.runner.run_pipeline") as mock_run, \
         patch("src.agent.providers.groq.resolve_groq_api_key") as mock_resolve_key, \
         patch("os.path.exists", return_value=True):
        
        mock_run.return_value = {"status": "ok"}
        mock_resolve_key.return_value = "mock_key"

        argv = [
            "./t",
            "--skip-static",
            "--skip-dynamic",
            "--skip-fusion",
            "--skip-agent-debate",
            "--skip-agent-source"
        ]
        code = run_reconstruct_cli(argv)
        assert code == 0

        kwargs = mock_run.call_args[1]
        assert kwargs["use_ghidra"] is False
        assert kwargs["use_radare2"] is False
        assert kwargs["skip_static"] is True
        assert kwargs["dynamic"] is False
        assert kwargs["fuse_behavior"] is False
        assert kwargs["agent_debate"] is False
        assert kwargs["generate_agent_source"] is False


def test_reconstruct_provider_ollama_no_key():
    """Verify ollama provider does not require/validate api key."""
    with patch("src.pipeline.runner.run_pipeline") as mock_run, \
         patch("src.agent.providers.groq.resolve_groq_api_key") as mock_resolve_key, \
         patch("os.path.exists", return_value=True):
        
        mock_run.return_value = {"status": "ok"}
        
        argv = ["./t", "--provider", "ollama"]
        code = run_reconstruct_cli(argv)
        assert code == 0

        mock_resolve_key.assert_not_called()
        kwargs = mock_run.call_args[1]
        assert kwargs["agent_provider"] == "ollama"
        assert kwargs["source_provider"] == "ollama"


def test_reconstruct_api_key_error_exits():
    """Verify missing Groq API key exits with code 1."""
    from src.agent.providers.groq import GroqApiKeyMissingError

    with patch("src.agent.providers.groq.resolve_groq_api_key", side_effect=GroqApiKeyMissingError("Missing")), \
         patch("os.path.exists", return_value=True):
        
        argv = ["./t", "--provider", "groq"]
        code = run_reconstruct_cli(argv)
        assert code == 1


def test_reconstruct_skip_debate_check_suggestions():
    """Verify that skip-agent-debate checks for agent_suggestions.json if not skipping source."""
    with patch("os.path.exists", return_value=True), \
         patch("src.agent.providers.groq.resolve_groq_api_key", return_value="mock"), \
         patch("pathlib.Path.exists") as mock_path_exists:
        
        # Simulate missing agent_suggestions.json
        mock_path_exists.return_value = False

        argv = ["./t", "--skip-agent-debate"]
        code = run_reconstruct_cli(argv)
        assert code == 1
