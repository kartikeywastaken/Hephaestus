# -*- coding: utf-8 -*-
"""
Clang Diagnostics Checker Utilities
"""

from __future__ import annotations
import shutil
import subprocess
from pathlib import Path

def clang_available() -> bool:
    """Check if the clang executable is available in the system path."""
    return shutil.which("clang") is not None

def run_clang_syntax_check(c_path: Path) -> dict:
    """Perform syntax-only clang diagnostics compilation check on C file."""
    if not clang_available():
        return {
            "attempted": False,
            "status": "skipped",
            "errors": 0,
            "warnings": 0,
            "diagnostics": []
        }
    try:
        res = subprocess.run(
            ["clang", "-fsyntax-only", "-ffreestanding", str(c_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        errors = 0
        warnings = 0
        diagnostics = []
        for line in res.stderr.splitlines():
            diagnostics.append(line)
            if ": error:" in line:
                errors += 1
            elif ": warning:" in line:
                warnings += 1
        status = "ok" if res.returncode == 0 and errors == 0 else "failed"
        return {
            "attempted": True,
            "status": status,
            "errors": errors,
            "warnings": warnings,
            "diagnostics": diagnostics
        }
    except Exception as e:
        return {
            "attempted": False,
            "status": "error",
            "errors": 0,
            "warnings": 0,
            "diagnostics": [str(e)]
        }
