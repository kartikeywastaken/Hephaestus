# -*- coding: utf-8 -*-
"""
Phase 5.2: Lowered Statement Model
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LoweredStatement:
    address: str | None
    kind: str
    text: str
    source_instruction: dict[str, Any] | None = None
    lowered: bool = True
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "kind": self.kind,
            "text": self.text,
            "source_instruction": self.source_instruction,
            "lowered": self.lowered,
            "warnings": self.warnings,
        }
