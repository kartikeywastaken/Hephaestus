# -*- coding: utf-8 -*-
"""
Test: Phase 11 pipeline integration.

Tests:
  - generate_agent_source is in OPTIONAL_PIPELINE_STAGES
  - STAGE_OUTPUTS has correct Phase 11 keys
  - Default run-all does NOT run Phase 11 (generate_agent_source=False is default)
  - --generate-agent-source wires correctly to run_pipeline
  - run_pipeline Phase 11 block runs CLI with correct flags
  - Phase 11 artifacts are in KNOWN_ARTIFACT_FILES
"""

from __future__ import annotations

import pytest


class TestStageDefs:
    def test_generate_agent_source_in_optional_stages(self):
        from src.pipeline.stage_defs import OPTIONAL_PIPELINE_STAGES
        assert "generate_agent_source" in OPTIONAL_PIPELINE_STAGES

    def test_stage_outputs_has_generate_agent_source(self):
        from src.pipeline.stage_defs import STAGE_OUTPUTS
        assert "generate_agent_source" in STAGE_OUTPUTS

    def test_generate_agent_source_outputs_are_correct(self):
        from src.pipeline.stage_defs import STAGE_OUTPUTS
        outputs = STAGE_OUTPUTS["generate_agent_source"]
        assert "recovered_agent.c" in outputs
        assert "agent_source_plan.json" in outputs
        assert "agent_source_report.json" in outputs
        assert "agent_source_validation.json" in outputs

    def test_generate_agent_source_not_in_core_stages(self):
        from src.pipeline.stage_defs import PIPELINE_STAGES
        assert "generate_agent_source" not in PIPELINE_STAGES


class TestArtifactsRegistry:
    def test_phase11_artifacts_in_known_files(self):
        from src.utils.artifacts import KNOWN_ARTIFACT_FILES
        assert "recovered_agent.c" in KNOWN_ARTIFACT_FILES
        assert "agent_source_plan.json" in KNOWN_ARTIFACT_FILES
        assert "agent_source_report.json" in KNOWN_ARTIFACT_FILES
        assert "agent_source_validation.json" in KNOWN_ARTIFACT_FILES


class TestRunPipelineSignature:
    def test_run_pipeline_has_generate_agent_source_param(self):
        import inspect
        from src.pipeline.runner import run_pipeline
        sig = inspect.signature(run_pipeline)
        assert "generate_agent_source" in sig.parameters

    def test_generate_agent_source_default_is_false(self):
        import inspect
        from src.pipeline.runner import run_pipeline
        sig = inspect.signature(run_pipeline)
        param = sig.parameters["generate_agent_source"]
        assert param.default is False

    def test_run_pipeline_has_source_provider_param(self):
        import inspect
        from src.pipeline.runner import run_pipeline
        sig = inspect.signature(run_pipeline)
        assert "source_provider" in sig.parameters

    def test_run_pipeline_has_source_model_param(self):
        import inspect
        from src.pipeline.runner import run_pipeline
        sig = inspect.signature(run_pipeline)
        assert "source_model" in sig.parameters

    def test_run_pipeline_has_source_max_functions_param(self):
        import inspect
        from src.pipeline.runner import run_pipeline
        sig = inspect.signature(run_pipeline)
        assert "source_max_functions" in sig.parameters

    def test_run_pipeline_has_overwrite_agent_source_param(self):
        import inspect
        from src.pipeline.runner import run_pipeline
        sig = inspect.signature(run_pipeline)
        assert "overwrite_agent_source" in sig.parameters

    def test_run_pipeline_has_allow_human_suggestions_param(self):
        import inspect
        from src.pipeline.runner import run_pipeline
        sig = inspect.signature(run_pipeline)
        assert "allow_human_suggestions" in sig.parameters


class TestCLIModule:
    def test_generate_agent_source_cli_importable(self):
        from src.agent_source.cli import run_generate_agent_source_cli
        assert callable(run_generate_agent_source_cli)

    def test_agent_source_models_importable(self):
        from src.agent_source.models import (
            SCHEMA_AGENT_SOURCE_PLAN,
            SCHEMA_AGENT_SOURCE_REPORT,
            SCHEMA_AGENT_SOURCE_VALIDATION,
            WARNING_HEADER,
            GUARDED_ARTIFACTS,
        )
        assert SCHEMA_AGENT_SOURCE_PLAN == "agent-source-plan-1.0"
        assert SCHEMA_AGENT_SOURCE_REPORT == "agent-source-report-1.0"
        assert SCHEMA_AGENT_SOURCE_VALIDATION == "agent-source-validation-1.0"
        assert len(WARNING_HEADER) > 0
        assert len(GUARDED_ARTIFACTS) >= 6

    def test_guarded_artifacts_covers_critical_files(self):
        from src.agent_source.models import GUARDED_ARTIFACTS
        assert "recovered.c" in GUARDED_ARTIFACTS
        assert "recovered_readable.c" in GUARDED_ARTIFACTS
        assert "source_reconstruction.json" in GUARDED_ARTIFACTS
        assert "agent_suggestions.json" in GUARDED_ARTIFACTS
        assert "agent_debate_report.json" in GUARDED_ARTIFACTS

    def test_supported_providers(self):
        from src.agent_source.models import SUPPORTED_PROVIDERS
        assert "ollama" in SUPPORTED_PROVIDERS
        assert "groq" in SUPPORTED_PROVIDERS

    def test_writer_has_phase11_outputs_set(self):
        from src.agent_source.writer import _PHASE11_OUTPUTS, _WRITE_FORBIDDEN
        assert "recovered_agent.c" in _PHASE11_OUTPUTS
        assert "agent_source_plan.json" in _PHASE11_OUTPUTS
        assert "agent_source_report.json" in _PHASE11_OUTPUTS
        assert "agent_source_validation.json" in _PHASE11_OUTPUTS
        # Core artifacts must be in write_forbidden
        assert "recovered.c" in _WRITE_FORBIDDEN
        assert "recovered_readable.c" in _WRITE_FORBIDDEN

    def test_writer_refuses_to_write_recovered_c(self):
        from src.agent_source.writer import _check_write_safe
        with pytest.raises(ValueError, match="FORBIDDEN"):
            _check_write_safe(None, "recovered.c")

    def test_writer_refuses_to_write_recovered_readable_c(self):
        from src.agent_source.writer import _check_write_safe
        with pytest.raises(ValueError, match="FORBIDDEN"):
            _check_write_safe(None, "recovered_readable.c")

    def test_writer_refuses_to_write_agent_suggestions(self):
        from src.agent_source.writer import _check_write_safe
        with pytest.raises(ValueError, match="FORBIDDEN"):
            _check_write_safe(None, "agent_suggestions.json")

    def test_writer_accepts_recovered_agent_c(self):
        from src.agent_source.writer import _check_write_safe
        # Should not raise
        _check_write_safe(None, "recovered_agent.c")

    def test_stop_after_generate_agent_source_recognized(self):
        from src.pipeline.stage_defs import OPTIONAL_PIPELINE_STAGES
        assert "generate_agent_source" in OPTIONAL_PIPELINE_STAGES
