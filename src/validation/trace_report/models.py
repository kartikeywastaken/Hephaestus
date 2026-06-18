# -*- coding: utf-8 -*-
"""
Trace Report Data Models
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class TraceStatement:
    statement_id: str
    line_number: int
    category: str
    subcategory: Optional[str]
    confidence: str
    statement_text: str
    short_explanation: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    validation_findings: List[Dict[str, Any]] = field(default_factory=list)
    attention_level: str = "none"
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "statement_id": self.statement_id,
            "line_number": self.line_number,
            "category": self.category,
            "subcategory": self.subcategory,
            "confidence": self.confidence,
            "statement_text": self.statement_text,
            "short_explanation": self.short_explanation,
            "evidence": self.evidence,
            "validation_findings": self.validation_findings,
            "attention_level": self.attention_level,
            "notes": self.notes
        }

@dataclass
class TraceFunction:
    name: str
    c_name: str
    entry_point: Optional[str]
    statements_total: int = 0
    category_summary: Dict[str, int] = field(default_factory=dict)
    confidence_summary: Dict[str, int] = field(default_factory=dict)
    attention_items: List[Dict[str, Any]] = field(default_factory=list)
    statements: List[TraceStatement] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "c_name": self.c_name,
            "entry_point": self.entry_point,
            "statements_total": self.statements_total,
            "category_summary": self.category_summary,
            "confidence_summary": self.confidence_summary,
            "attention_items": self.attention_items,
            "statements": [s.to_dict() for s in self.statements]
        }
