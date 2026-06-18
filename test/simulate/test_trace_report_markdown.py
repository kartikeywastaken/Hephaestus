# -*- coding: utf-8 -*-
"""
Tests for Trace Report Markdown Generator
"""

from __future__ import annotations
import tempfile
from pathlib import Path
from src.validation.trace_report.markdown import write_trace_markdown

def test_write_trace_markdown():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        
        # Build a dummy payload
        payload = {
            "status": "warning",
            "summary": {
                "functions_total": 2,
                "statements_total": 10,
                "evidence_backed_statements": 5,
                "generated_scaffold_statements": 2,
                "syntax_adapter_statements": 1,
                "commentary_only_statements": 1,
                "unknown_confidence_statements": 1,
                "validation_findings_total": 3,
                "validation_errors": 0,
                "validation_warnings": 3,
                "high_attention_lines": 2
            },
            "category_summary": {
                "executable_lowered": 5,
                "true_unsupported": 1,
                "comment_lowered": 1,
                "syntax_adapter": 1,
                "helper": 1,
                "declaration": 1
            },
            "confidence_summary": {
                "evidence_backed": 5,
                "generated_scaffold": 2,
                "syntax_adapter": 1,
                "commentary_only": 1,
                "unknown": 1
            },
            "global_statements": [
                {
                    "statement_id": "global_000001",
                    "line_number": 1,
                    "category": "helper",
                    "confidence": "evidence_backed",
                    "statement_text": "static int HEPHAESTUS_UNKNOWN_COND(u64 val);",
                    "attention_level": "none",
                    "validation_findings": [],
                    "short_explanation": "Generated helper used by syntax adapters; not recovered source logic."
                }
            ],
            "functions": [
                {
                    "name": "func_a",
                    "c_name": "func_a",
                    "entry_point": "0x1000",
                    "statements_total": 4,
                    "attention_items": [],
                    "category_summary": {"executable_lowered": 3, "declaration": 1},
                    "confidence_summary": {"evidence_backed": 3, "generated_scaffold": 1},
                    "statements": []
                },
                {
                    "name": "func_b",
                    "c_name": "func_b",
                    "entry_point": "0x2000",
                    "statements_total": 5,
                    "attention_items": [
                        {
                            "statement_id": "stmt_000005",
                            "line_number": 15,
                            "category": "true_unsupported",
                            "confidence": "unknown",
                            "statement_text": "/* unsupported instruction: invalid */",
                            "attention_level": "warning",
                            "validation_findings": [
                                {
                                    "id": "VAL-EVID-008",
                                    "title": "Unsupported comment count mismatch",
                                    "severity": "warning"
                                }
                            ],
                            "short_explanation": "Instruction was not lowered and is preserved as an unsupported statement/comment."
                        }
                    ],
                    "category_summary": {"executable_lowered": 2, "true_unsupported": 1, "declaration": 2},
                    "confidence_summary": {"evidence_backed": 2, "unknown": 1, "generated_scaffold": 2},
                    "statements": [
                        {
                            "statement_id": "stmt_000005",
                            "line_number": 15,
                            "category": "true_unsupported",
                            "confidence": "unknown",
                            "statement_text": "/* unsupported instruction: invalid */",
                            "attention_level": "warning",
                            "validation_findings": [
                                {
                                    "id": "VAL-EVID-008",
                                    "title": "Unsupported comment count mismatch",
                                    "severity": "warning"
                                }
                            ],
                            "short_explanation": "Instruction was not lowered and is preserved as an unsupported statement/comment."
                        }
                    ]
                }
            ]
        }
        
        md_file = write_trace_markdown(payload, out_dir)
        
        assert md_file.exists()
        content = md_file.read_text(encoding="utf-8")
        
        # Verify key markdown headers and tables exist
        assert "# Hephaestus Trace Report" in content
        assert "## Summary" in content
        assert "Functions Total | 2" in content
        assert "High-Attention Lines | **2**" in content
        assert "## Validation Status" in content
        assert "Validation Warnings | 3" in content
        assert "## Category Summary" in content
        assert "executable_lowered | 5" in content
        assert "## High Attention Lines" in content
        assert "15 | WARNING | func_b | true_unsupported | `/* unsupported instruction: invalid */` | [VAL-EVID-008] Unsupported comment count mismatch" in content
        assert "## Function Summaries" in content
        assert "func_a | 0x1000 | 4 | 0 |" in content
        assert "func_b | 0x2000 | 5 | 1 |" in content
