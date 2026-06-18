# -*- coding: utf-8 -*-
"""
Quality Gate JSON Writer
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any

def write_quality_gate(payload: Dict[str, Any], out_dir: Path) -> Path:
    """Write quality_gate.json report."""
    target = out_dir / "quality_gate.json"
    with open(target, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return target
