# -*- coding: utf-8 -*-
"""
Evidence Index Data Models
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class StatementEntry:
    statement_id: str
    line_number: int
    text_hash: str
    statement_text: str
    category: str
    confidence: str
    subcategory: Optional[str] = None
    function: Optional[str] = None
    block_id: Optional[str] = None
    instruction_address: Optional[str] = None
    instruction_mnemonic: Optional[str] = None
    raw_instruction: Optional[str] = None
    evidence_sources: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {
            "statement_id": self.statement_id,
            "line_number": self.line_number,
            "text_hash": self.text_hash,
            "statement_text": self.statement_text,
            "category": self.category,
            "subcategory": self.subcategory,
            "function": self.function,
            "block_id": self.block_id,
            "instruction_address": self.instruction_address,
            "instruction_mnemonic": self.instruction_mnemonic,
            "raw_instruction": self.raw_instruction,
            "evidence_sources": self.evidence_sources,
            "confidence": self.confidence,
            "notes": self.notes
        }
        return res

@dataclass
class GlobalStatementEntry:
    statement_id: str
    line_number: int
    text_hash: str
    statement_text: str
    category: str
    confidence: str
    subcategory: Optional[str] = None
    evidence_sources: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {
            "statement_id": self.statement_id,
            "line_number": self.line_number,
            "text_hash": self.text_hash,
            "statement_text": self.statement_text,
            "category": self.category,
            "subcategory": self.subcategory,
            "evidence_sources": self.evidence_sources,
            "confidence": self.confidence,
            "notes": self.notes
        }
        return res

@dataclass
class FunctionIndex:
    name: str
    c_name: str
    entry_point: Optional[str]
    statements: List[StatementEntry] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "c_name": self.c_name,
            "entry_point": self.entry_point,
            "statements": [s.to_dict() for s in self.statements]
        }
