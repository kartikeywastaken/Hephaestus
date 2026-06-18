# -*- coding: utf-8 -*-
"""
Clang Syntax Checking Validation Check
"""

from __future__ import annotations
from src.validation.models import ValidationArtifacts
from src.validation.report import add_check, add_finding
from src.pipeline.clang import run_clang_syntax_check

def check_clang(artifacts: ValidationArtifacts, report: dict, no_clang: bool = False) -> None:
    """Run clang diagnostics syntax compilation check on recovered.c."""
    if no_clang:
        add_check(
            report=report,
            name="clang_syntax_ok",
            status="skipped",
            severity="warning",
            message="Skipped: clang check disabled via CLI.",
            details={"attempted": False, "status": "skipped", "errors": 0, "warnings": 0, "diagnostics": []}
        )
        return
        
    if artifacts.recovered_c is None:
        add_check(
            report=report,
            name="clang_syntax_ok",
            status="skipped",
            severity="warning",
            message="Skipped: recovered.c not loaded.",
            details={"attempted": False, "status": "skipped", "errors": 0, "warnings": 0, "diagnostics": []}
        )
        return
        
    c_path = artifacts.out_dir / "recovered.c"
    res = run_clang_syntax_check(c_path)
    
    if not res.get("attempted", False):
        # Clang compiler is not available on path
        add_check(
            report=report,
            name="clang_syntax_ok",
            status="skipped",
            severity="warning",
            message="Skipped: clang is not available in the system path.",
            details=res
        )
        add_finding(
            report=report,
            finding_id="VAL-CLNG-001",
            severity="warning",
            category="clang_syntax",
            title="Clang compiler unavailable",
            message="Clang compiler was not found on the system path. Syntax checking of recovered.c was skipped.",
            artifact="recovered.c"
        )
        return
        
    errors = res.get("errors", 0)
    warnings = res.get("warnings", 0)
    diagnostics = res.get("diagnostics", [])
    
    if errors > 0:
        add_check(
            report=report,
            name="clang_syntax_ok",
            status="failed",
            severity="error",
            message=f"Clang compilation returned {errors} errors and {warnings} warnings.",
            details=res
        )
        add_finding(
            report=report,
            finding_id="VAL-CLNG-002",
            severity="error",
            category="clang_syntax",
            title="Clang compilation errors detected",
            message=f"Clang syntax check failed with {errors} errors.",
            artifact="recovered.c",
            evidence={"errors": errors, "warnings": warnings, "diagnostics": diagnostics[:10]}
        )
    elif warnings > 0:
        add_check(
            report=report,
            name="clang_syntax_ok",
            status="ok",
            severity="warning",
            message=f"Clang compilation succeeded with {warnings} warnings.",
            details=res
        )
        add_finding(
            report=report,
            finding_id="VAL-CLNG-003",
            severity="warning",
            category="clang_syntax",
            title="Clang compilation warnings detected",
            message=f"Clang syntax check succeeded but produced {warnings} warnings.",
            artifact="recovered.c",
            evidence={"warnings": warnings, "diagnostics": diagnostics[:10]}
        )
    else:
        add_check(
            report=report,
            name="clang_syntax_ok",
            status="ok",
            severity="error",
            message="Clang compilation succeeded with no errors or warnings.",
            details=res
        )
        
    # If the checker itself crashed or failed to run
    if res.get("status") == "error":
        add_check(
            report=report,
            name="clang_syntax_ok",
            status="failed",
            severity="error",
            message="Clang compilation check failed to run correctly.",
            details=res
        )
        add_finding(
            report=report,
            finding_id="VAL-CLNG-004",
            severity="error",
            category="clang_syntax",
            title="Clang diagnostics run crashed",
            message=f"Clang diagnostics checker crashed with: {res.get('diagnostics')}",
            artifact="recovered.c"
        )
