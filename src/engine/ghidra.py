# -*- coding: utf-8 -*-
"""
Ghidra Extraction Implementation
Executes headless analyzers or simulated headless components for Phase 1 deterministic profiling.
"""

import os
from typing import Dict, Any, Optional
from src.engine.base import BaseExtractor, ExtractorError, execute_with_retry

class GhidraExtractor(BaseExtractor):
    """
    Handles connection, execution, and JSON compilation of Ghidra headless analytical pipelines.
    Extracts high-fidelity metadata, symbol indices, and CFG structures.
    """

    def validate_environment(self) -> bool:
        """
        Determines if Ghidra install directories exist.
        """
        ghidra_home = self.config.get("GHIDRA_HOME") or os.environ.get("GHIDRA_HOME")
        if not ghidra_home:
            self.logger.error("GHIDRA_HOME environment variable or config key is not set.")
            return False
        return os.path.exists(ghidra_home)

    def extract(self) -> Dict[str, Any]:
        """
        Main extraction wrapper with integrated deterministic execution error tracking.
        """
        if not self.validate_environment():
            raise ExtractorError("Encountered invalid or corrupt Ghidra analysis path configurations. Please check that GHIDRA_HOME is set.")

        def run_extraction() -> Dict[str, Any]:
            return self._execute_ghidra_analysis()

        raw_data = execute_with_retry(run_extraction, retries=2)
        envelope = self.generate_envelope(raw_data, "Ghidra Headless Analyzer")
        self.save_artifact(envelope)
        return envelope

    def _execute_ghidra_analysis(self) -> Dict[str, Any]:
        """
        Executes a real headless Ghidra analysis using analyzeHeadless.
        """
        import subprocess
        import tempfile
        import json

        ghidra_home = self.config.get("GHIDRA_HOME") or os.environ.get("GHIDRA_HOME")
        analyze_headless = os.path.join(ghidra_home, "support", "analyzeHeadless")
        
        # Handle macOS/Linux vs Windows executable naming
        if not os.path.exists(analyze_headless):
            analyze_headless_bat = os.path.join(ghidra_home, "support", "analyzeHeadless.bat")
            if os.path.exists(analyze_headless_bat):
                analyze_headless = analyze_headless_bat
            else:
                raise ExtractorError(f"analyzeHeadless executable not found in {ghidra_home}/support/")

        # Use a temporary project directory in /tmp to avoid dot-prefixed path
        # segments (e.g. .work/) that Ghidra rejects with:
        #   "Path element starting with '.' is not permitted"
        project_dir = tempfile.mkdtemp(prefix="hephaestus-ghidra-")
        project_name = "temp_ghidra_proj"
        
        script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
        script_name = "GhidraExtractorScript.java"
        
        # Temp file to read the script's output JSON
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_json_path = tf.name

        try:
            cmd = [
                analyze_headless,
                project_dir,
                project_name,
                "-import", os.path.abspath(self.binary_path),
                "-scriptPath", script_dir,
                "-postScript", script_name, temp_json_path,
                "-deleteProject",
                "-overwrite"
            ]

            env = os.environ.copy()
            java_home = self.config.get("JAVA_HOME") or os.environ.get("JAVA_HOME")
            if java_home:
                env["JAVA_HOME"] = java_home
                env["PATH"] = os.path.join(java_home, "bin") + os.pathsep + env.get("PATH", "")

            self.logger.info(f"Executing Ghidra subprocess: {' '.join(cmd)}")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)

            # Append Ghidra execution info to run.log
            ghidra_log_msg = (
                f"Command used: {' '.join(cmd)}\n"
                f"Project directory: {project_dir}\n"
                f"Script path: {os.path.join(script_dir, script_name)}\n"
                f"Output JSON path: {temp_json_path}\n"
                f"Return code: {result.returncode}\n\n"
                f"STDOUT:\n{result.stdout}\n"
                f"STDERR:\n{result.stderr}\n"
            )
            from src.utils.run_logging import append_run_log
            append_run_log(os.path.dirname(self.output_path), "GHIDRA", ghidra_log_msg)

            # Optional Debug Dump Mode
            if self.config.get("debug_logs", False):
                try:
                    out_dir = os.path.dirname(self.output_path)
                    with open(os.path.join(out_dir, "ghidra_stdout.txt"), "w", encoding="utf-8") as f:
                        f.write(result.stdout)
                    with open(os.path.join(out_dir, "ghidra_stderr.txt"), "w", encoding="utf-8") as f:
                        f.write(result.stderr)
                except Exception as e:
                    self.logger.warning(f"Failed to write debug logs: {e}")

            # Include execution logs in errors
            if result.returncode != 0:
                raise ExtractorError(
                    f"Ghidra execution failed (code {result.returncode}).\n"
                    f"Command used: {' '.join(cmd)}\n"
                    f"Stderr: {result.stderr}\n"
                    f"Stdout: {result.stdout}"
                )

            if not os.path.exists(temp_json_path) or os.path.getsize(temp_json_path) == 0:
                raise ExtractorError(
                    f"Ghidra analysis finished but output JSON was not written or is empty.\n"
                    f"Command used: {' '.join(cmd)}\n"
                    f"Expected output path: {temp_json_path}\n"
                    f"Stderr: {result.stderr}\n"
                    f"Stdout: {result.stdout}"
                )

            with open(temp_json_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            from src.ir.utils.addressing import normalize_extractor_payload
            # Extract internal data structure if present
            if "data" in raw_data:
                payload = raw_data["data"]
            else:
                payload = raw_data
            return normalize_extractor_payload(payload)

        finally:
            # Clean up the temporary project directory and JSON file
            if os.path.exists(project_dir):
                import shutil
                shutil.rmtree(project_dir, ignore_errors=True)
            if os.path.exists(temp_json_path):
                os.unlink(temp_json_path)
