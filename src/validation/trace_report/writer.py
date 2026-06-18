# -*- coding: utf-8 -*-
"""
Trace Report Writer
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any

def write_trace_report(payload: Dict[str, Any], out_dir: Path) -> Path:
    """Serialize trace report to trace_report.json."""
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / "trace_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return report_file
