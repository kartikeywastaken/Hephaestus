# -*- coding: utf-8 -*-
"""
Trace Report Module Entry Point
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any

from src.validation.trace_report.builder import build_trace_report_payload
from src.validation.trace_report.writer import write_trace_report
from src.validation.trace_report.markdown import write_trace_markdown

def build_trace_report(
    out_dir: str | Path,
    markdown_mode: bool = False,
    require_validation: bool = False,
    require_evidence_index: bool = True
) -> Dict[str, Any]:
    """Orchestrate trace report generation and serialization."""
    out_path = Path(out_dir)
    payload = build_trace_report_payload(
        out_path,
        require_validation=require_validation,
        require_evidence_index=require_evidence_index
    )
    write_trace_report(payload, out_path)
    if markdown_mode:
        write_trace_markdown(payload, out_path)
    return payload
