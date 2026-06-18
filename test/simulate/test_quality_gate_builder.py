# -*- coding: utf-8 -*-
"""
Tests for Quality Gate Builder
"""

from __future__ import annotations
import json
import tempfile
from pathlib import Path
from src.validation.quality_gate.builder import build_quality_gate_payload

def test_builder_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        
        # Write dummy required files
        recon_data = {
            "schema_version": "5.7.2",
            "summary": {
                "condition_expressions_recovered": 0
            }
        }
        
        c_content = "int main() { return 0; }"
        
        val_data = {
            "schema_version": "validation-1.0",
            "status": "ok",
            "findings": [],
            "summary": {
                "errors": 0,
                "warnings": 0
            }
        }
        
        ev_data = {
            "schema_version": "evidence-index-1.0"
        }
        
        trace_data = {
            "schema_version": "trace-report-1.0",
            "summary": {
                "functions_total": 1,
                "statements_total": 10,
                "evidence_backed_statements": 8,
                "high_attention_lines": 0,
                "generated_scaffold_statements": 1,
                "commentary_only_statements": 0
            },
            "category_summary": {
                "executable_lowered": 8,
                "true_unsupported": 0,
                "comment_lowered": 0,
                "syntax_adapter": 1,
                "declaration": 1
            },
            "confidence_summary": {
                "evidence_backed": 8,
                "generated_scaffold": 1,
                "syntax_adapter": 1,
                "unknown": 0
            },
            "global_statements": [],
            "functions": [
                {
                    "c_name": "main",
                    "statements": [
                        {
                            "category": "declaration",
                            "statement_text": "u64 stack_val = 0;"
                        }
                    ]
                }
            ],
            "unattached_validation_findings": []
        }
        
        with open(out_dir / "source_reconstruction.json", "w") as f:
            json.dump(recon_data, f)
        with open(out_dir / "recovered.c", "w") as f:
            f.write(c_content)
        with open(out_dir / "validation_report.json", "w") as f:
            json.dump(val_data, f)
        with open(out_dir / "evidence_index.json", "w") as f:
            json.dump(ev_data, f)
        with open(out_dir / "trace_report.json", "w") as f:
            json.dump(trace_data, f)
            
        payload = build_quality_gate_payload(out_dir)
        
        assert payload["schema_version"] == "quality-gate-1.0"
        assert payload["status"] == "ready"
        assert payload["decision"]["safe_to_use_for_phase7"] is True
        assert payload["scores"]["evidence_coverage_score"] == 80.0
        assert payload["summary"]["statements_total"] == 10
        assert payload["summary"]["unknown_statements"] == 0
        assert payload["phase7_hints"]["predicate_recovery_recommended"] is True # syntax_adapter = 1
        assert payload["phase7_hints"]["local_variable_recovery_recommended"] is True # stack_ in decl text
