# -*- coding: utf-8 -*-
"""
Tests for Phase 5.3 Structured Control-Flow Emission.
"""

from __future__ import annotations

import pytest
from src.ir.source.models import (
    ReconstructedFunction,
    SourceReconstructionArtifact,
    SCHEMA_VERSION,
)
from src.ir.source.control_emitter import (
    emit_regions_to_c,
    analyze_control_flow_regions,
    collect_blocks_from_region,
)
from src.ir.source.c_emitter import emit_recovered_c
import tempfile
import os


# Mock helper classes for statements
class MockStatement:
    def __init__(self, text: str, block_id: str | None = None):
        self.text = text
        self.source_instruction = {"block_id": block_id} if block_id else None


class TestControlFlowEmission:

    def test_1_sequence_emits_blocks_in_order(self):
        regions = [
            {
                "type": "sequence",
                "children": [
                    {"type": "block", "id": "0x1000"},
                    {"type": "block", "id": "0x1008"},
                ]
            }
        ]
        lowered_blocks = {
            "0x1000": [MockStatement("tmp_x8 = 1;", "0x1000")],
            "0x1008": [MockStatement("tmp_x9 = 2;", "0x1008")],
        }

        lines, stats = emit_regions_to_c(regions, lowered_blocks, indent=1)

        body = "\n".join(lines)
        assert "/* block 0x1000 */" in body
        assert "tmp_x8 = 1;" in body
        assert "/* block 0x1008 */" in body
        assert "tmp_x9 = 2;" in body
        
        # Verify sequence nodes keep order
        idx_1000 = body.index("block 0x1000")
        idx_1008 = body.index("block 0x1008")
        assert idx_1000 < idx_1008

    def test_2_loop_emits_conservative_while(self):
        regions = [
            {
                "type": "loop",
                "kind": "while_like",
                "header_block": "0x1000",
                "body": {"type": "block", "id": "0x1004"},
                "exit_blocks": ["0x1008"],
            }
        ]
        lowered_blocks = {
            "0x1000": [MockStatement("tmp_w8 = 0;", "0x1000")],
            "0x1004": [MockStatement("tmp_w8 = tmp_w8 + 1;", "0x1004")],
        }

        lines, stats = emit_regions_to_c(regions, lowered_blocks, indent=1)
        body = "\n".join(lines)

        assert "while (/* condition unknown: loop header 0x1000 */) {" in body
        assert "tmp_w8 = tmp_w8 + 1;" in body
        
        # Must not contain fabricated conditions
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("while (") or stripped.startswith("if ("):
                assert "condition unknown" in stripped
                assert "tmp_" not in stripped
                assert "arg" not in stripped
                assert "stack_" not in stripped

    def test_3_if_emits_conservative_condition(self):
        regions = [
            {
                "type": "if",
                "condition_block": "0x2000",
                "then_branch": {"type": "block", "id": "0x2004"},
                "merge_block": "0x2008",
            }
        ]
        lowered_blocks = {
            "0x2000": [MockStatement("/* condition eval */", "0x2000")],
            "0x2004": [MockStatement("tmp_w9 = 42;", "0x2004")],
        }

        lines, stats = emit_regions_to_c(regions, lowered_blocks, indent=1)
        body = "\n".join(lines)

        assert "if (/* condition unknown: block 0x2000 */) {" in body
        assert "tmp_w9 = 42;" in body

    def test_4_if_else_emits_conservative_branches(self):
        regions = [
            {
                "type": "if_else",
                "condition_block": "0x3000",
                "then_branch": {"type": "block", "id": "0x3004"},
                "else_branch": {"type": "block", "id": "0x3008"},
                "merge_block": "0x300c",
            }
        ]
        lowered_blocks = {
            "0x3000": [],
            "0x3004": [MockStatement("tmp_w8 = 1;", "0x3004")],
            "0x3008": [MockStatement("tmp_w8 = 2;", "0x3008")],
        }

        lines, stats = emit_regions_to_c(regions, lowered_blocks, indent=1)
        body = "\n".join(lines)

        assert "if (/* condition unknown: block 0x3000 */) {" in body
        assert "} else {" in body
        assert "tmp_w8 = 1;" in body
        assert "tmp_w8 = 2;" in body

    def test_5_unstructured_fallback_sorts_blocks_deterministically(self):
        regions = [
            {
                "type": "unstructured",
                "reason": "irreducible CFG shape",
                "children": [
                    {"type": "block", "id": "0x2000"},
                    {"type": "block", "id": "0x1000"},
                    {"type": "block", "id": "block_B"},
                    {"type": "block", "id": "block_A"},
                ]
            }
        ]
        lowered_blocks = {
            "0x1000": [MockStatement("tmp_x8 = 10;", "0x1000")],
            "0x2000": [MockStatement("tmp_x8 = 20;", "0x2000")],
            "block_A": [MockStatement("tmp_x8 = 30;", "block_A")],
            "block_B": [MockStatement("tmp_x8 = 40;", "block_B")],
        }

        lines, stats = emit_regions_to_c(regions, lowered_blocks, indent=1)
        body = "\n".join(lines)

        assert "/* unstructured region begin */" in body
        assert "/* reason: irreducible CFG shape */" in body
        
        # Verify deterministic ordering: addresses first numerically, then non-address lexical
        idx_1000 = body.index("block 0x1000")
        idx_2000 = body.index("block 0x2000")
        idx_A = body.index("block block_A")
        idx_B = body.index("block block_B")
        
        assert idx_1000 < idx_2000
        assert idx_2000 < idx_A
        assert idx_A < idx_B

    def test_a_reconstructor_does_not_generate_c(self):
        # Assert analyze_control_flow_regions() parses metrics without requiring lowered statements/C formatting
        regions = [
            {
                "type": "loop",
                "kind": "while_like",
                "header_block": "0x1000",
                "body": {
                    "type": "if_else",
                    "condition_block": "0x1004",
                    "then_branch": {"type": "block", "id": "0x1008"},
                    "else_branch": {"type": "block", "id": "0x100c"},
                    "merge_block": "0x1010"
                },
                "exit_blocks": ["0x1014"]
            }
        ]
        
        stats = analyze_control_flow_regions(regions)
        
        assert stats["loops_emitted"] == 1
        assert stats["if_else_constructs_emitted"] == 1
        assert stats["if_constructs_emitted"] == 0
        assert stats["structured_constructs_emitted"] == 2
        assert stats["regions_total"] == 4  # loop, if_else, then-block, else-block analyzed (header is metadata)
        assert stats["duplicate_blocks_skipped"] == 0
        assert stats["condition_expressions_recovered"] == 0

    def test_b_duplicate_block_reference_is_commented(self):
        # Block 0x1000 is referenced twice
        regions = [
            {
                "type": "sequence",
                "children": [
                    {"type": "block", "id": "0x1000"},
                    {"type": "block", "id": "0x1000"},
                ]
            }
        ]
        lowered_blocks = {
            "0x1000": [MockStatement("tmp_x8 = 1;", "0x1000")]
        }

        lines, stats = emit_regions_to_c(regions, lowered_blocks, indent=1, seen_blocks=set())
        body = "\n".join(lines)

        assert "/* block 0x1000 */" in body
        assert "tmp_x8 = 1;" in body
        assert "/* block 0x1000 already emitted; duplicate reference skipped */" in body
        assert stats["duplicate_blocks_skipped"] == 1

    def test_c_explicit_break_continue_only(self):
        regions = [
            {
                "type": "sequence",
                "children": [
                    {"type": "break", "target": "0x2000"},
                    {"type": "continue", "target": "0x1000"},
                ]
            }
        ]
        lowered_blocks = {}

        lines, stats = emit_regions_to_c(regions, lowered_blocks, indent=1)
        body = "\n".join(lines)

        assert "break; /* break edge to 0x2000 */" in body
        assert "continue; /* continue edge to loop header 0x1000 */" in body

    def test_d_unknown_region_fallback(self):
        regions = [
            {
                "type": "future_region_type",
                "children": [
                    {"type": "block", "id": "0x1000"}
                ]
            }
        ]
        lowered_blocks = {
            "0x1000": [MockStatement("tmp_x8 = 1;", "0x1000")]
        }

        lines, stats = emit_regions_to_c(regions, lowered_blocks, indent=1)
        body = "\n".join(lines)

        assert "/* unsupported region type: future_region_type */" in body
        assert "/* preserving contained blocks conservatively */" in body
        assert "/* block 0x1000 */" in body
        assert "tmp_x8 = 1;" in body

    def test_e_condition_line_safety(self):
        regions = [
            {
                "type": "loop",
                "kind": "while_like",
                "header_block": "0x1000",
                "body": {"type": "if", "condition_block": "0x1004", "then_branch": {"type": "block", "id": "0x1008"}, "merge_block": "0x100c"},
                "exit_blocks": ["0x100c"]
            }
        ]
        lowered_blocks = {
            "0x1000": [MockStatement("tmp_w8 = stack_m4;", "0x1000")],
            "0x1004": [MockStatement("tmp_w8 = tmp_w8 + 1;", "0x1004")],
            "0x1008": [MockStatement("tmp_w9 = tmp_w8;", "0x1008")],
        }

        lines, stats = emit_regions_to_c(regions, lowered_blocks, indent=1)
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("while (") or stripped.startswith("if ("):
                assert "condition unknown" in stripped
                assert "tmp_" not in stripped
                assert "arg" not in stripped
                assert "stack_" not in stripped

    def test_f_no_referenced_block_is_silently_dropped(self):
        regions = [
            {
                "type": "loop",
                "kind": "while_like",
                "header_block": "0x1000",
                "body": {
                    "type": "sequence",
                    "children": [
                        {"type": "block", "id": "0x1004"},
                        {
                            "type": "if_else",
                            "condition_block": "0x1004",
                            "then_branch": {"type": "block", "id": "0x1008"},
                            "else_branch": {"type": "block", "id": "0x1000"},  # duplicate
                            "merge_block": "0x100c"
                        }
                    ]
                },
                "exit_blocks": ["0x100c"]
            }
        ]
        lowered_blocks = {
            "0x1000": [MockStatement("/* stmt 0x1000 */", "0x1000")],
            "0x1004": [MockStatement("/* stmt 0x1004 */", "0x1004")],
            "0x1008": [MockStatement("/* stmt 0x1008 */", "0x1008")],
        }

        referenced_blocks = collect_blocks_from_region(regions[0])
        assert "0x1000" in referenced_blocks
        assert "0x1004" in referenced_blocks
        assert "0x1008" in referenced_blocks

        lines, stats = emit_regions_to_c(regions, lowered_blocks, indent=1, seen_blocks=set())
        body = "\n".join(lines)

        for b_id in ["0x1000", "0x1004", "0x1008"]:
            # Check either block statement exists or skip comment exists
            first_emit = f"/* block {b_id} */"
            dup_emit = f"/* block {b_id} already emitted; duplicate reference skipped */"
            assert (first_emit in body) or (dup_emit in body)

    def test_9_summary_metrics_validation(self):
        fn = ReconstructedFunction(
            name="fn1",
            canonical_name="fn1",
            c_name="fn1",
            entry_point="0x1000",
            structured_regions=[
                {"type": "loop", "kind": "while_like", "header_block": "0x1000", "body": {"type": "block", "id": "0x1004"}, "exit_blocks": []}
            ]
        )
        # Verify models schema version matches
        artifact = SourceReconstructionArtifact(schema_version=SCHEMA_VERSION, functions=[fn])
        assert artifact.schema_version == "5.3.0"
        
        # Populate function stats (mock reconstructor behavior)
        fn.control_flow = analyze_control_flow_regions(fn.structured_regions)
        assert fn.control_flow["loops_emitted"] == 1
        assert fn.control_flow["condition_expressions_recovered"] == 0

    def test_10_old_test3_integration_simulation(self):
        # Simulate phase52_control.c structure
        regions = [
            {
                "type": "loop",
                "kind": "while_like",
                "header_block": "0x1000",
                "body": {
                    "type": "if_else",
                    "condition_block": "0x1004",
                    "then_branch": {"type": "block", "id": "0x1008"},
                    "else_branch": {"type": "block", "id": "0x100c"},
                    "merge_block": "0x1010"
                },
                "exit_blocks": ["0x1010"]
            }
        ]
        
        # Lowered statements contain indexed memory operations
        lowered_blocks = {
            "0x1000": [MockStatement("stack_m8 = tmp_x0;", "0x1000")],
            "0x1004": [MockStatement("tmp_w8 = tmp_w8 + 1;", "0x1004")],
            "0x1008": [MockStatement("*(u32 *)(tmp_x9 + (tmp_x10 << 2)) = tmp_w8; /* str w8,[x9, x10, LSL #0x2] */", "0x1008")],
            "0x100c": [MockStatement("tmp_w8 = stack_m8;", "0x100c")]
        }

        fn = ReconstructedFunction(
            name="weird_loop",
            canonical_name="weird_loop",
            c_name="weird_loop",
            entry_point="0x1000",
            structured_regions=regions,
            lowered_blocks=lowered_blocks,
            lowered_statements=[stmt for block in lowered_blocks.values() for stmt in block]
        )

        artifact = SourceReconstructionArtifact(functions=[fn])
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".c", delete=False) as f:
            path = f.name
        try:
            emit_recovered_c(artifact, path)
            with open(path, "r") as f:
                content = f.read()
            
            # Assert loop and branch shape
            assert "while (/* condition unknown: loop header 0x1000 */)" in content
            assert "if (/* condition unknown: block 0x1004 */)" in content
            assert "*(u32 *)(tmp_x9 + (tmp_x10 << 2)) = tmp_w8;" in content
            
            # Assert no fabricated semantic keywords
            assert "->" not in content
            assert "struct " not in content
            
            # Assert no bracket syntax leaked outside comment
            for line in content.splitlines():
                stripped = line.strip()
                expr = stripped.split("/*", 1)[0].strip()
                assert not expr.startswith("[")
        finally:
            os.unlink(path)
