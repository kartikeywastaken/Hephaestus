# -*- coding: utf-8 -*-
"""
Tests for Evidence Index Builder
"""

from __future__ import annotations
import json
import tempfile
from pathlib import Path
from src.validation.evidence_index.builder import build_index_payload

def test_build_index_payload():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        
        # 1. Create a dummy source_reconstruction.json
        recon_data = {
            "schema_version": "5.7.2",
            "summary": {
                "unsupported_instruction_kinds": {"invalid": 1}
            },
            "data": {
                "functions": [
                    {
                        "name": "main",
                        "c_name": "main",
                        "entry_point": "0x1000",
                        "lowered_statements": [
                            {
                                "kind": "executable_lowered",
                                "address": "0x1000",
                                "source_instruction": {
                                    "address": "0x1000",
                                    "block_id": "block_0",
                                    "mnemonic": "add",
                                    "raw": "add x0, x0, #1"
                                }
                            }
                        ]
                    }
                ]
            }
        }
        
        # 2. Create recovered.c with a function body and comments
        c_content = """
static int HEPHAESTUS_UNKNOWN_COND(u64 val);

int main()
{
    /* block 0x1000 */
    u64 tmp_sp = 0;
    tmp_sp = tmp_sp + 1;
    /* unsupported instruction: invalid */
    return 0;
}
"""
        
        with open(out_dir / "source_reconstruction.json", "w") as f:
            json.dump(recon_data, f)
        with open(out_dir / "recovered.c", "w") as f:
            f.write(c_content)
            
        # 3. Build index
        payload = build_index_payload(out_dir)
        
        assert payload["schema_version"] == "evidence-index-1.0"
        assert payload["phase"] == "6.2"
        
        summary = payload["summary"]
        assert summary["functions_total"] == 1
        assert summary["statements_total"] > 0
        
        # Verify category sum matches statements_total
        categories = [
            "executable_lowered_statements",
            "true_unsupported_statements",
            "comment_lowered_statements",
            "branch_evidence_comments",
            "syntax_adapter_statements",
            "helper_statements",
            "declaration_statements",
            "call_statements",
            "return_statements",
            "control_flow_scaffold_statements",
            "function_signature_statements",
            "empty_function_scaffold_statements",
            "unknown_statement_category"
        ]
        category_sum = sum(summary[c] for c in categories)
        assert category_sum == summary["statements_total"]
        
        # Verify specific statement classifications
        assert summary["helper_statements"] == 1 # HEPHAESTUS_UNKNOWN_COND definition
        assert summary["true_unsupported_statements"] == 1 # invalid
        assert summary["return_statements"] == 1 # return 0;
        
        # Verify function details
        funcs = payload["functions"]
        assert len(funcs) == 1
        assert funcs[0]["c_name"] == "main"
        assert len(funcs[0]["statements"]) > 0
