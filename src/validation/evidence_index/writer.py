# -*- coding: utf-8 -*-
"""
Evidence Index Serialization Writer
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any

def write_evidence_index(payload: Dict[str, Any], out_dir: Path) -> Path:
    """Write the evidence index dict to out_dir/evidence_index.json."""
    output_file = out_dir / "evidence_index.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return output_file
