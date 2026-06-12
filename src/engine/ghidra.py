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

        # Use temporary project directory within workspace
        project_dir = os.path.join(os.path.dirname(self.output_path), "ghidra_temp_proj")
        os.makedirs(project_dir, exist_ok=True)
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

            self.logger.info(f"Executing Ghidra subprocess: {' '.join(cmd)}")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if result.returncode != 0:
                raise ExtractorError(f"Ghidra execution failed (code {result.returncode}). Stderr: {result.stderr}")

            if not os.path.exists(temp_json_path) or os.path.getsize(temp_json_path) == 0:
                raise ExtractorError("Ghidra analysis finished but output JSON was not written or is empty.")

            with open(temp_json_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            # Extract internal data structure if present
            if "data" in raw_data:
                return raw_data["data"]
            return raw_data

        finally:
            # Clean up the temporary project directory and JSON file
            if os.path.exists(project_dir):
                import shutil
                shutil.rmtree(project_dir, ignore_errors=True)
            if os.path.exists(temp_json_path):
                os.unlink(temp_json_path)
