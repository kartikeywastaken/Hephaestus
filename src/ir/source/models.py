# -*- coding: utf-8 -*-
"""
Phase 5.1: Source Reconstruction Data Models

Defines the canonical model classes used by the Phase 5.1 source
reconstruction foundation. All models support deterministic to_dict()
serialization.

Core Rule: Missing evidence is acceptable. Fabricated evidence is not.
Phase 5.1 only emits information grounded in existing artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "5.1.0"


# ---------------------------------------------------------------------------
# ReconstructedFunction
# ---------------------------------------------------------------------------

@dataclass
class ReconstructedFunction:
    """
    Reconstructed source representation of a single function.

    Attributes
    ----------
    name           : Original artifact name (from unified_ir.json).
    canonical_name : Alias-canonical name (from symbol_aliases or same as name).
    c_name         : Sanitized C identifier safe for use in recovered.c.
    entry_point    : Normalized hex address string.
    function_kind  : From Phase 4D (library/user/entrypoint/unknown).
    return_type    : From Phase 4D recovered/refined signature, or "u64" default.
    parameters     : From Phase 4D recovered/refined parameters, or synthetic
                     from ABI bindings.
    local_variables: From Phase 4D variables.
    body_status    : One of "structured", "partially_structured",
                     "unstructured", "missing".
    structured_regions : From structuring_regions.json (preserved as-is).
    abi_argument_bindings     : From Phase 4B.2.
    parameter_layout_evidence : From Phase 4B.2.
    layout_candidates         : From Phase 4C/4D.
    instruction_count : Total instructions across all basic blocks.
    basic_block_count : Total basic blocks.
    warnings       : Diagnostic warnings (e.g. "empty_function",
                     "unknown_return_type_defaulted_to_u64").
    evidence_notes : Summarizing what evidence exists for this function.
    """
    name: str = "unknown_function"
    canonical_name: str = "unknown_function"
    c_name: str = "fn_unknown"
    entry_point: str = "unknown"
    function_kind: str = "unknown"
    return_type: str = "u64"
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    local_variables: List[Dict[str, Any]] = field(default_factory=list)
    body_status: str = "missing"
    structured_regions: List[Dict[str, Any]] = field(default_factory=list)
    abi_argument_bindings: List[Dict[str, Any]] = field(default_factory=list)
    parameter_layout_evidence: List[Dict[str, Any]] = field(default_factory=list)
    layout_candidates: List[Dict[str, Any]] = field(default_factory=list)
    instruction_count: int = 0
    basic_block_count: int = 0
    warnings: List[str] = field(default_factory=list)
    evidence_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "canonical_name": self.canonical_name,
            "c_name": self.c_name,
            "entry_point": self.entry_point,
            "function_kind": self.function_kind,
            "return_type": self.return_type,
            "parameters": list(self.parameters),
            "local_variables": list(self.local_variables),
            "body_status": self.body_status,
            "structured_regions": list(self.structured_regions),
            "abi_argument_bindings": list(self.abi_argument_bindings),
            "parameter_layout_evidence": list(self.parameter_layout_evidence),
            "layout_candidates": list(self.layout_candidates),
            "instruction_count": self.instruction_count,
            "basic_block_count": self.basic_block_count,
            "warnings": list(self.warnings),
            "evidence_notes": list(self.evidence_notes),
        }


# ---------------------------------------------------------------------------
# SourceReconstructionArtifact
# ---------------------------------------------------------------------------

@dataclass
class SourceReconstructionArtifact:
    """
    The complete Phase 5.1 output artifact.

    Attributes
    ----------
    schema_version : Always "5.1.0".
    provenance     : Source artifact paths.
    functions      : List of ReconstructedFunction records.
    summary        : Aggregate counters.
    """
    schema_version: str = SCHEMA_VERSION
    provenance: Dict[str, Any] = field(default_factory=dict)
    functions: List[ReconstructedFunction] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=lambda: {
        "functions_total": 0,
        "functions_structured": 0,
        "functions_partially_structured": 0,
        "functions_unstructured": 0,
        "functions_missing": 0,
        "functions_with_warnings": 0,
        "total_parameters": 0,
        "total_abi_bindings": 0,
        "total_parameter_layout_evidence": 0,
        "total_layout_candidates": 0,
        "total_instructions": 0,
    })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "provenance": dict(self.provenance),
            "data": {
                "functions": [f.to_dict() for f in self.functions],
                "summary": dict(self.summary),
            },
        }
