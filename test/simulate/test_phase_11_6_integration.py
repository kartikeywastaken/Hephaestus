# -*- coding: utf-8 -*-
"""
Phase 11.6 Integration & Acceptance Tests.
"""

import json
import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.pipeline.reconstruct_cli import run_reconstruct_cli
from src.pipeline.runner import run_pipeline
from src.agent.context_optimizer import optimize_agent_packets
from src.agent.library_filter import filter_debatable_packets
from main import handle_run_all_cli


class TestPhase11_6Integration:

    def test_reconstruct_no_dynamic_inputs_auto_generates(self):
        """1. reconstruct with no --dynamic-inputs auto-generates dynamic inputs."""
        with patch("src.pipeline.runner.run_pipeline") as mock_run, \
             patch("src.agent.providers.groq.resolve_groq_api_key", return_value="mock_key"), \
             patch("os.path.exists", return_value=True):
            
            mock_run.return_value = {"status": "ok"}
            argv = ["./t", "--out-dir", "test_artifacts"]
            code = run_reconstruct_cli(argv)

            assert code == 0
            mock_run.assert_called_once()
            kwargs = mock_run.call_args[1]
            assert kwargs["auto_inputs"] is True
            assert kwargs["adaptive_dynamic"] is True

    def test_adaptive_dynamic_artifacts_written(self):
        """2. Adaptive dynamic artifacts are written when adaptive_dynamic is run."""
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            
            # Setup initial dynamic_runs.json
            initial_runs = {
                "binary_sha256": "mock_sha",
                "runs": [
                    {
                        "name": "case_0",
                        "argv": [],
                        "exit_code": 0,
                        "stdout_sha256": "stdout_hash_1",
                        "stderr_sha256": "stderr_hash_1",
                        "timed_out": False,
                        "signal": None
                    },
                    {
                        "name": "case_1",
                        "argv": ["1"],
                        "exit_code": 1,
                        "stdout_sha256": "stdout_hash_2",
                        "stderr_hash_2": "stderr_hash_2",
                        "timed_out": False,
                        "signal": None
                    }
                ]
            }
            with open(out_dir / "dynamic_runs.json", "w", encoding="utf-8") as f:
                json.dump(initial_runs, f)

            # Create mock recovered files for safety checks
            with open(out_dir / "recovered.c", "w") as f:
                f.write("int main() { return 0; }")
            with open(out_dir / "recovered_readable.c", "w") as f:
                f.write("int main() { return 0; }")

            # Mock run_all to return empty results but prevent subprocessing
            with patch("src.dynamic.runner.run_all", return_value=([], "mock_sha")):
                manifest = {"status": "ok", "final_outputs": {}, "errors": []}
                # Run the runner.py pipeline block manually or via run_pipeline
                # Let's run run_pipeline with skip_static=True, stop_after="adaptive_dynamic"
                from src.pipeline.runner import run_pipeline
                res = run_pipeline(
                    binary_path="./t",
                    out_dir=str(out_dir),
                    clean=False,
                    skip_static=True,
                    stop_after="adaptive_dynamic",
                    dynamic=False, # skip initial dynamic to only test adaptive_dynamic stage loading
                    adaptive_dynamic=True,
                    dynamic_max_adaptive_inputs=5,
                    dynamic_mutation_rounds=1,
                )

                assert res["status"] in ("ok", "partial")
                # Verify that all 4 artifacts are written
                assert (out_dir / "adaptive_inputs.json").exists()
                assert (out_dir / "adaptive_dynamic_runs.json").exists()
                assert (out_dir / "input_influence_report.json").exists()
                assert (out_dir / "dynamic_exploration_report.json").exists()

    def test_compact_packet_artifacts_written(self):
        """3. Compact packet artifacts are written."""
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            
            # Write a mock packet
            packets_dir = out_dir / "agent_packets"
            packets_dir.mkdir(parents=True)
            mock_packet = {
                "function": "test_func",
                "address": "0x1000",
                "signature": "void test_func()",
                "basic_blocks": 5,
                "edges": 4,
                "recovered_slice": "void test_func() { int a = 1; }",
                "calls": ["printf"],
                "called_by": ["main"]
            }
            with open(packets_dir / "test_func.json", "w") as f:
                json.dump(mock_packet, f)

            optimize_agent_packets(out_dir, packet_mode="compact")

            assert (out_dir / "agent_packet_optimization_report.json").exists()
            assert (out_dir / "agent_packets_compact" / "test_func.json").exists()
            
            # Check content
            with open(out_dir / "agent_packets_compact" / "test_func.json", "r") as f:
                compact_data = json.load(f)
            assert compact_data["packet_mode"] == "compact"
            assert compact_data["function"] == "test_func"

    def test_groq_mode_defaults_to_compact(self):
        """4. Groq mode defaults to compact packet mode."""
        with patch("src.pipeline.runner.run_pipeline") as mock_run, \
             patch("src.agent.providers.groq.resolve_groq_api_key", return_value="mock_key"), \
             patch("os.path.exists", return_value=True):
            
            mock_run.return_value = {"status": "ok"}
            argv = ["./t", "--provider", "groq"]
            code = run_reconstruct_cli(argv)

            assert code == 0
            kwargs = mock_run.call_args[1]
            assert kwargs["packet_mode"] == "compact"

    def test_max_functions_enforcement(self):
        """5. --max-functions 1 causes only one function to be debated/forwarded."""
        with patch("src.pipeline.runner.run_pipeline") as mock_run, \
             patch("src.agent.providers.groq.resolve_groq_api_key", return_value="mock_key"), \
             patch("os.path.exists", return_value=True):
            
            mock_run.return_value = {"status": "ok"}
            argv = ["./t", "--max-functions", "1"]
            code = run_reconstruct_cli(argv)

            assert code == 0
            kwargs = mock_run.call_args[1]
            assert kwargs["agent_max_functions"] == 1
            assert kwargs["source_max_functions"] == 1

    def test_library_functions_skipped(self):
        """6. Library functions are skipped by the filter and not debated."""
        # Setup mock packets: one library function, one user function
        packets = [
            {"function": "printf", "signature": "int printf(const char*, ...)", "basic_blocks": 1},
            {"function": "my_custom_func", "signature": "void my_custom_func()", "basic_blocks": 12}
        ]
        
        target, skipped = filter_debatable_packets(packets, max_functions=None)
        assert len(target) == 1
        assert target[0]["function"] == "my_custom_func"
        assert len(skipped) == 1
        assert skipped[0]["function"] == "printf"

    def test_oversized_packets_shrunk_below_budget(self):
        """7. Oversized packets are shrunk below budget."""
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            packets_dir = out_dir / "agent_packets"
            packets_dir.mkdir(parents=True)
            
            # Generate a massive packet by creating very large source_slice and xref lists
            huge_source = "/* " + ("A" * 20000) + " */"
            mock_packet = {
                "function": "huge_func",
                "signature": "void huge_func()",
                "recovered_slice": huge_source,
                "calls": ["f" + str(i) for i in range(100)],
                "called_by": ["g" + str(i) for i in range(100)],
                "evidence": ["evidence_" + str(i) for i in range(100)]
            }
            with open(packets_dir / "huge_func.json", "w") as f:
                json.dump(mock_packet, f)

            optimize_agent_packets(out_dir, packet_mode="compact", max_packet_chars=8000)

            # Check that the compact packet size is below 8000 chars
            compact_file = out_dir / "agent_packets_compact" / "huge_func.json"
            assert compact_file.exists()
            with open(compact_file, "r") as f:
                content = f.read()
            assert len(content) <= 8000

    def test_does_not_modify_conservative_artifacts(self):
        """8. Phase 11.6 does not modify conservative artifacts (recovered.c)."""
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            
            # Write initial recovered.c
            c_file = out_dir / "recovered.c"
            c_file.write_text("int original() { return 42; }\n")
            
            # Build mock packets and run optimizer/explorer
            # Make sure optimize_agent_packets or explorer doesn't modify it
            optimize_agent_packets(out_dir, packet_mode="compact")
            
            # The recovered.c should be identical
            assert c_file.read_text() == "int original() { return 42; }\n"

    def test_default_run_all_behavior_backward_compatible(self):
        """9. Default run-all behavior remains backward compatible (auto_inputs=False, adaptive_dynamic=False)."""
        # Patch run_pipeline in handle_run_all_cli
        with patch("src.pipeline.runner.run_pipeline") as mock_run, \
             patch("sys.argv", ["main.py", "run-all", "./t", "--ghidra"]):
            
            mock_run.return_value = {"status": "ok"}
            try:
                handle_run_all_cli()
            except SystemExit as e:
                assert e.code == 0

            mock_run.assert_called_once()
            kwargs = mock_run.call_args[1]
            # Verify they default to False in run-all
            assert kwargs["auto_inputs"] is False
            assert kwargs["adaptive_dynamic"] is False
