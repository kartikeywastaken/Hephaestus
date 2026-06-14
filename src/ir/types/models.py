# -*- coding: utf-8 -*-
"""
Phase 4A: Type Recovery Data Models

Defines the canonical model classes used by the Phase 4A signature and
variable recovery backbone. All models support deterministic to_dict()
serialization.

No C source code is emitted here. No type propagation is performed here.
Uncertainty is preserved explicitly using confidence scores.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict


# ---------------------------------------------------------------------------
# Supported type name constants
# ---------------------------------------------------------------------------
TYPE_UNKNOWN          = "unknown"
TYPE_VOID             = "void"
TYPE_BOOL             = "bool"
TYPE_INT8             = "int8"
TYPE_UINT8            = "uint8"
TYPE_INT16            = "int16"
TYPE_UINT16           = "uint16"
TYPE_INT32            = "int32"
TYPE_UINT32           = "uint32"
TYPE_INT64            = "int64"
TYPE_UINT64           = "uint64"
TYPE_POINTER          = "pointer"
TYPE_STRUCT_CANDIDATE = "struct_candidate"
TYPE_FUNCTION_POINTER = "function_pointer"

# Valid storage kinds
STORAGE_STACK    = "stack"
STORAGE_REGISTER = "register"
STORAGE_GLOBAL   = "global"
STORAGE_UNKNOWN  = "unknown"

# Valid variable category kinds
CATEGORY_PARAMETER         = "parameter"
CATEGORY_LOCAL             = "local"
CATEGORY_TEMPORARY         = "temporary"
CATEGORY_UNKNOWN_STACK_SLOT = "unknown_stack_slot"

# Valid function kind values
FUNCTION_KIND_LIBRARY    = "library"
FUNCTION_KIND_ENTRYPOINT = "entrypoint"
FUNCTION_KIND_USER       = "user"
FUNCTION_KIND_UNKNOWN    = "unknown"


# ---------------------------------------------------------------------------
# RecoveredType
# ---------------------------------------------------------------------------

@dataclass
class RecoveredType:
    """
    Represents a single recovered type annotation with confidence and provenance.

    Attributes
    ----------
    type_name  : One of the supported Phase 4A type name constants.
    confidence : 0.0–1.0 confidence score for this type annotation.
    source     : Human-readable provenance string describing why this type was inferred.
    notes      : Free-form evidence notes list.
    """
    type_name: str = TYPE_UNKNOWN
    confidence: float = 0.2
    source: str = "fallback"
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type_name,
            "confidence": round(self.confidence, 4),
            "source": self.source,
            "notes": list(self.notes),
        }

    @staticmethod
    def unknown(source: str = "fallback", notes: Optional[List[str]] = None) -> "RecoveredType":
        """Convenience factory for the unknown/fallback type."""
        return RecoveredType(
            type_name=TYPE_UNKNOWN,
            confidence=0.2,
            source=source,
            notes=notes or [],
        )


# ---------------------------------------------------------------------------
# RecoveredVariable
# ---------------------------------------------------------------------------

@dataclass
class RecoveredVariable:
    """
    Represents a single recovered variable (local, parameter, temporary, etc.)
    with classification metadata.

    Attributes
    ----------
    name           : Variable name as recovered from the IR.
    storage        : Where the variable lives (stack, register, global, unknown).
    category       : Semantic category (parameter, local, temporary, unknown_stack_slot).
    recovered_type : The best recovered type annotation.
    offset_bytes   : Stack/memory offset in bytes, or None if unknown.
    size_bytes     : Size of the variable in bytes, or None if unknown.
    source         : Provenance describing where this variable came from.
    confidence     : Confidence in the variable classification.
    notes          : Free-form evidence notes.
    """
    name: str = "unknown"
    storage: str = STORAGE_STACK
    category: str = CATEGORY_UNKNOWN_STACK_SLOT
    recovered_type: RecoveredType = field(default_factory=RecoveredType.unknown)
    offset_bytes: Optional[int] = None
    size_bytes: Optional[int] = None
    source: str = "unified_ir"
    confidence: float = 0.2
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "storage": self.storage,
            "category": self.category,
            "type": self.recovered_type.to_dict(),
            "offset_bytes": self.offset_bytes,
            "size_bytes": self.size_bytes,
            "source": self.source,
            "confidence": round(self.confidence, 4),
            "notes": list(self.notes),
        }


# ---------------------------------------------------------------------------
# RecoveredParameter
# ---------------------------------------------------------------------------

@dataclass
class RecoveredParameter:
    """
    Represents a single recovered function parameter.

    Attributes
    ----------
    name           : Parameter name as recovered or inferred.
    index          : Zero-based parameter position.
    recovered_type : The best recovered type annotation.
    source         : Provenance describing how this parameter was recovered.
    confidence     : Confidence in the parameter recovery.
    notes          : Free-form evidence notes.
    """
    name: str = "param"
    index: int = 0
    recovered_type: RecoveredType = field(default_factory=RecoveredType.unknown)
    source: str = "fallback"
    confidence: float = 0.2
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "index": self.index,
            "type": self.recovered_type.to_dict(),
            "source": self.source,
            "confidence": round(self.confidence, 4),
            "notes": list(self.notes),
        }


# ---------------------------------------------------------------------------
# RecoveredSignature
# ---------------------------------------------------------------------------

@dataclass
class RecoveredSignature:
    """
    Represents a recovered function signature skeleton.

    Attributes
    ----------
    return_type : The recovered return type.
    parameters  : Ordered list of recovered parameters.
    variadic    : Whether this is a variadic function.
    confidence  : Confidence in the overall signature.
    source      : Provenance of the signature recovery.
    notes       : Free-form evidence notes.
    """
    return_type: RecoveredType = field(default_factory=RecoveredType.unknown)
    parameters: List[RecoveredParameter] = field(default_factory=list)
    variadic: bool = False
    confidence: float = 0.2
    source: str = "fallback_unknown_signature"
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "return_type": self.return_type.to_dict(),
            "parameters": [p.to_dict() for p in self.parameters],
            "variadic": self.variadic,
            "confidence": round(self.confidence, 4),
            "source": self.source,
            "notes": list(self.notes),
        }


# ---------------------------------------------------------------------------
# RecoveredFunctionSemantics
# ---------------------------------------------------------------------------

@dataclass
class RecoveredFunctionSemantics:
    """
    The complete Phase 4A semantic record for a single function.

    Attributes
    ----------
    name           : Canonical function name.
    entry_point    : Normalized entry-point address string.
    function_kind  : library | entrypoint | user | unknown
    signature      : The recovered signature skeleton.
    variables      : All recovered variables (parameters + locals + temporaries).
    evidence       : List of evidence notes attached to this function.
    confidence     : Overall function-level confidence.
    """
    name: str = "unknown_function"
    entry_point: str = "unknown"
    function_kind: str = FUNCTION_KIND_UNKNOWN
    signature: RecoveredSignature = field(default_factory=RecoveredSignature)
    variables: List[RecoveredVariable] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "entry_point": self.entry_point,
            "function_kind": self.function_kind,
            "signature": self.signature.to_dict(),
            "variables": [v.to_dict() for v in self.variables],
            "evidence": list(self.evidence),
            "confidence": round(self.confidence, 4),
        }


# ---------------------------------------------------------------------------
# Phase 4B: Refined records
# ---------------------------------------------------------------------------

@dataclass
class RefinedVariableRecord:
    """
    A single variable after Phase 4B constraint-based type refinement.

    Attributes
    ----------
    name                : Variable name.
    refined_type        : The type after applying constraints (may equal Phase 4A type).
    constraints_applied : Number of constraints that changed this variable's type.
    phase4a_type        : The original Phase 4A type_name before refinement.
    """
    name: str = "unknown"
    refined_type: RecoveredType = field(default_factory=RecoveredType.unknown)
    constraints_applied: int = 0
    phase4a_type: str = TYPE_UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "refined_type": self.refined_type.to_dict(),
            "constraints_applied": self.constraints_applied,
            "phase4a_type": self.phase4a_type,
        }


@dataclass
class RefinedFunctionRecord:
    """
    The complete Phase 4B refinement record for a single function.

    Attributes
    ----------
    name                     : Canonical function name.
    entry_point              : Normalized entry-point address string.
    function_kind            : library | entrypoint | user | unknown
    refined_signature        : Signature after Phase 4B parameter refinement.
    variables                : All refined variable records.
    total_constraints_applied: Sum of constraints that changed any type.
    confidence               : Overall function-level confidence after refinement.
    evidence                 : List of evidence notes.
    """
    name: str = "unknown_function"
    entry_point: str = "unknown"
    function_kind: str = FUNCTION_KIND_UNKNOWN
    refined_signature: RecoveredSignature = field(default_factory=RecoveredSignature)
    variables: List[RefinedVariableRecord] = field(default_factory=list)
    total_constraints_applied: int = 0
    confidence: float = 0.2
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "entry_point": self.entry_point,
            "function_kind": self.function_kind,
            "refined_signature": self.refined_signature.to_dict(),
            "variables": [v.to_dict() for v in self.variables],
            "total_constraints_applied": self.total_constraints_applied,
            "confidence": round(self.confidence, 4),
            "evidence": list(self.evidence),
        }
