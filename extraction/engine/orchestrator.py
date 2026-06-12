# -*- coding: utf-8 -*-
"""
Extraction Pipeline Orchestrator
Aggregates, compiles, and saves outputs across multiple distinct extraction runners.
"""

import os
import time
from typing import Dict, Any, List, Optional
from extraction.engine.base import BaseExtractor, ExtractorError
from extraction.engine.ghidra import GhidraExtractor
from extraction.engine.ida import IDAExtractor
from extraction.engine.trace import TraceExtractor

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

    def execute_all(self, run_ghidra: bool = True, run_ida: bool = True, run_trace: bool = True) -> Dict[str, Any]:
        """
        Executes active extraction components and forms a consolidated system manifest.
        """
        results = {}
        errors = []

        if run_ghidra:
            ghidra_out_path = os.path.join(self.output_directory, "ghidra_extraction.json")
            try:
                ghidra_extractor = GhidraExtractor(self.binary_path, ghidra_out_path, self.config)
                results["ghidra"] = ghidra_extractor.extract()
            except Exception as e:
                errors.append(f"Ghidra extraction pipeline failed: {e}")

        if run_ida:
            ida_out_path = os.path.join(self.output_directory, "ida_extraction.json")
            try:
                ida_extractor = IDAExtractor(self.binary_path, ida_out_path, self.config)
                results["ida"] = ida_extractor.extract()
            except Exception as e:
                errors.append(f"IDA extraction pipeline failed: {e}")

        if run_trace:
            trace_out_path = os.path.join(self.output_directory, "trace_extraction.json")
            try:
                trace_extractor = TraceExtractor(self.binary_path, trace_out_path, self.config)
                results["trace"] = trace_extractor.extract()
            except Exception as e:
                errors.append(f"Trace extraction parser failed: {e}")

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
        except Exception as e:
            errors.append(f"Orchestration manifest failed to commit: {e}")

        return manifest
