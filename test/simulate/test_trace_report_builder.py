# -*- coding: utf-8 -*-
"""
Tests for Trace Report Builder
"""

from __future__ import annotations
import json
import tempfile
from pathlib import Path
from src.validation.trace_report.builder import build_trace_report_payload

def test_build_trace_report_builder_matching_priorities():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        
        # 1. Create a mock evidence index
        evidence_index = {
            "schema_version": "evidence-index-1.0",
            "phase": "6.2",
            "summary": {
                "functions_total": 1,
                "statements_total": 6,
            },
            "global_statements": [
                {
                    "statement_id": "global_000001",
                    "line_number": 10,
                    "category": "helper",
                    "confidence": "evidence_backed",
                    "statement_text": "static int HEPHAESTUS_UNKNOWN_COND(u64 val);"
                }
            ],
            "functions": [
                {
                    "name": "func_test",
                    "c_name": "func_test",
                    "entry_point": "0x1000",
                    "statements": [
                        {
                            "statement_id": "stmt_000001",
                            "line_number": 20,
                            "category": "function_signature",
                            "confidence": "evidence_backed",
                            "statement_text": "int func_test()"
                        },
                        {
                            "statement_id": "stmt_000002",
                            "line_number": 21,
                            "category": "declaration",
                            "confidence": "evidence_backed",
                            "statement_text": "u64 x = 0;"
                        },
                        {
                            "statement_id": "stmt_000003",
                            "line_number": 22,
                            "category": "executable_lowered",
                            "confidence": "evidence_backed",
                            "statement_text": "x = x + 1;",
                            "block_id": "block_0",
                            "instruction_address": "0x1000",
                            "instruction_mnemonic": "add"
                        },
                        {
                            "statement_id": "stmt_000004",
                            "line_number": 23,
                            "category": "true_unsupported",
                            "confidence": "unknown",
                            "statement_text": "/* unsupported instruction: invalid */",
                            "block_id": "block_1",
                            "instruction_address": "0x1004"
                        }
                    ]
                }
            ]
        }
        
        # 2. Create a mock validation report with different finding matching priorities
        validation_report = {
            "schema_version": "1.0",
            "findings": [
                # Match priority 1: Line number exact
                {
                    "finding_id": "FIND_LINE",
                    "severity": "warning",
                    "category": "syntax_safety",
                    "title": "Warning on line 21",
                    "location": {"line": 21}
                },
                # Match priority 2: Statement ID exact
                {
                    "finding_id": "FIND_STMT_ID",
                    "severity": "error",
                    "category": "syntax_safety",
                    "title": "Error on global_000001",
                    "location": {"line": 99}, # Incorrect line, should match by statement_id
                    "statement_id": "global_000001"
                },
                # Match priority 3: function + block_id
                {
                    "finding_id": "FIND_BLOCK",
                    "severity": "warning",
                    "category": "syntax_safety",
                    "title": "Warning on block_1",
                    "location": {"function": "func_test", "block_id": "block_1"}
                },
                # Match priority 4: function + instruction address
                {
                    "finding_id": "FIND_ADDR",
                    "severity": "warning",
                    "category": "syntax_safety",
                    "title": "Warning on address 0x1000",
                    "location": {"function": "func_test", "address": "0x1000"}
                },
                # Match priority 5: category fallback (match function signature line)
                {
                    "finding_id": "FIND_SIG",
                    "severity": "warning",
                    "category": "syntax_safety",
                    "title": "Warning on func_test signature",
                    "location": {"function": "func_test"}
                },
                # Unattached finding (no location, no matching function)
                {
                    "finding_id": "FIND_UNATTACHED",
                    "severity": "error",
                    "category": "syntax_safety",
                    "title": "Unattached finding",
                    "location": {"function": "non_existent_func"}
                }
            ]
        }
        
        # Write files
        with open(out_dir / "evidence_index.json", "w") as f:
            json.dump(evidence_index, f)
        with open(out_dir / "validation_report.json", "w") as f:
            json.dump(validation_report, f)
            
        # Run builder
        payload = build_trace_report_payload(out_dir, require_validation=True, require_evidence_index=True)
        
        assert payload["schema_version"] == "trace-report-1.0"
        assert payload["status"] == "failed" # because of FIND_STMT_ID and FIND_UNATTACHED errors
        
        summary = payload["summary"]
        assert summary["validation_findings_total"] == 6
        assert summary["validation_errors"] == 2
        assert summary["validation_warnings"] == 4
        
        # Verify findings are attached correctly
        # Global statements
        global_stmts = payload["global_statements"]
        assert len(global_stmts) == 1
        assert len(global_stmts[0]["validation_findings"]) == 1
        assert global_stmts[0]["validation_findings"][0]["finding_id"] == "FIND_STMT_ID"
        assert global_stmts[0]["attention_level"] == "error"
        
        # Functions
        funcs = payload["functions"]
        assert len(funcs) == 1
        func = funcs[0]
        stmts = func["statements"]
        
        # stmt_000001: func_test signature -> should match FIND_SIG
        assert stmts[0]["statement_id"] == "stmt_000001"
        assert len(stmts[0]["validation_findings"]) == 1
        assert stmts[0]["validation_findings"][0]["finding_id"] == "FIND_SIG"
        
        # stmt_000002: declaration on line 21 -> should match FIND_LINE
        assert stmts[1]["statement_id"] == "stmt_000002"
        assert len(stmts[1]["validation_findings"]) == 1
        assert stmts[1]["validation_findings"][0]["finding_id"] == "FIND_LINE"
        
        # stmt_000003: executable_lowered with address 0x1000 -> should match FIND_ADDR
        assert stmts[2]["statement_id"] == "stmt_000003"
        assert len(stmts[2]["validation_findings"]) == 1
        assert stmts[2]["validation_findings"][0]["finding_id"] == "FIND_ADDR"
        
        # stmt_000004: true_unsupported on block_1 -> should match FIND_BLOCK
        assert stmts[3]["statement_id"] == "stmt_000004"
        assert len(stmts[3]["validation_findings"]) == 1
        assert stmts[3]["validation_findings"][0]["finding_id"] == "FIND_BLOCK"
        
        # Unattached findings
        unattached = payload["unattached_validation_findings"]
        assert len(unattached) == 1
        assert unattached[0]["finding_id"] == "FIND_UNATTACHED"
