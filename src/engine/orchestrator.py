# -*- coding: utf-8 -*-
"""
Extraction Pipeline Orchestrator
Aggregates, compiles, and saves outputs across multiple distinct extraction runners.
"""

import os
import time
from typing import Dict, Any, List, Optional
from src.engine.base import BaseExtractor, ExtractorError
from src.engine.ghidra import GhidraExtractor
from src.engine.radare2 import Radare2Extractor
from src.engine.trace import TraceExtractor

class PipelineOrchestrator:
    """
    Coordinates simultaneous or sequential analytical extractions.
    Ensures safe, structured serialization across all discrete jobs.
    """

    def __init__(self, binary_path: str, output_directory: str, config: Optional[Dict[str, Any]] = None):
        self.binary_path = binary_path
        self.output_directory = output_directory
        self.config = config or {}
        os.makedirs(output_directory, exist_ok=True)

    def execute_all(self, run_ghidra: bool = True, run_radare2: bool = True, run_trace: bool = True) -> Dict[str, Any]:
        """
        Executes active extraction components and forms a consolidated system manifest.
        """
        from src.utils.run_logging import append_run_log
        results = {}
        errors = []

        if run_ghidra:
            ghidra_out_path = os.path.join(self.output_directory, "ghidra_extraction.json")
            append_run_log(self.output_directory, "ORCHESTRATION", "Pipeline stage started: Ghidra Extraction")
            try:
                ghidra_extractor = GhidraExtractor(self.binary_path, ghidra_out_path, self.config)
                results["ghidra"] = ghidra_extractor.extract()
                append_run_log(self.output_directory, "ORCHESTRATION", f"Pipeline stage completed: Ghidra Extraction\nArtifact written: {ghidra_out_path}")
            except Exception as e:
                errors.append(f"Ghidra extraction pipeline failed: {e}")
                append_run_log(self.output_directory, "ORCHESTRATION", f"Extractor failure: Ghidra extraction pipeline failed: {e}")

        if run_radare2:
            radare2_out_path = os.path.join(self.output_directory, "radare2_extraction.json")
            append_run_log(self.output_directory, "ORCHESTRATION", "Pipeline stage started: Radare2 Extraction")
            try:
                radare2_extractor = Radare2Extractor(self.binary_path, radare2_out_path, self.config)
                results["radare2"] = radare2_extractor.extract()
                append_run_log(self.output_directory, "ORCHESTRATION", f"Pipeline stage completed: Radare2 Extraction\nArtifact written: {radare2_out_path}")
            except Exception as e:
                errors.append(f"Radare2 extraction pipeline failed: {e}")
                append_run_log(self.output_directory, "ORCHESTRATION", f"Extractor failure: Radare2 extraction pipeline failed: {e}")

        if run_trace:
            trace_out_path = os.path.join(self.output_directory, "trace_extraction.json")
            append_run_log(self.output_directory, "ORCHESTRATION", "Pipeline stage started: Trace Extraction")
            try:
                trace_extractor = TraceExtractor(self.binary_path, trace_out_path, self.config)
                results["trace"] = trace_extractor.extract()
                append_run_log(self.output_directory, "ORCHESTRATION", f"Pipeline stage completed: Trace Extraction\nArtifact written: {trace_out_path}")
            except Exception as e:
                errors.append(f"Trace extraction parser failed: {e}")
                append_run_log(self.output_directory, "ORCHESTRATION", f"Extractor failure: Trace extraction parser failed: {e}")

        manifest = {
            "orchestrated_at": time.strftime("%Y-%m-%dT%H:%M:%S-07:00"),
            "binary_profiled": self.binary_path,
            "jobs": results,
            "errors": errors,
            "total_jobs_run": len(results),
            "status": "partial_success" if errors and results else "success" if results else "failed"
        }

        manifest_path = os.path.join(self.output_directory, "orchestration_manifest.json")
        try:
            import json
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            append_run_log(self.output_directory, "ORCHESTRATION", f"Artifact written: {manifest_path}")
        except Exception as e:
            errors.append(f"Orchestration manifest failed to commit: {e}")
            append_run_log(self.output_directory, "ORCHESTRATION", f"Warning: Orchestration manifest failed to commit: {e}")

        return manifest
