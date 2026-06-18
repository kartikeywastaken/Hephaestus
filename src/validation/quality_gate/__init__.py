# -*- coding: utf-8 -*-
"""
Quality Gate Entry Point
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any

from src.validation.quality_gate.builder import build_quality_gate_payload
from src.validation.quality_gate.writer import write_quality_gate
from src.validation.quality_gate.markdown import write_quality_markdown

def build_quality_gate(
    out_dir: str | Path,
    markdown_mode: bool = False,
    strict: bool = False,
    hash_check_failed: bool = False
) -> Dict[str, Any]:
    """Orchestrate quality gate evaluation and serialization."""
    out_path = Path(out_dir)
    payload = build_quality_gate_payload(
        out_path,
        strict=strict,
        hash_check_failed=hash_check_failed
    )
    write_quality_gate(payload, out_path)
    if markdown_mode:
        write_quality_markdown(payload, out_path)
    return payload
