# -*- coding: utf-8 -*-
"""
Validation Report Builder
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def now_iso() -> str:
    """Return current ISO 8601 UTC time string with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def new_report(out_dir: str | Path, strict: bool) -> dict:
    """Initialize a validation report structure."""
    return {
        "schema_version": "validation-1.0",
        "phase": "6.1",
        "status": "ok",
        "strict": strict,
        "out_dir": str(out_dir),
        "started_at": now_iso(),
        "finished_at": None,
        "input_artifacts": {
            "pipeline_manifest": "pipeline_manifest.json",
            "unified_ir": "unified_ir.json",
            "phase4_semantics": "phase4_semantics.json",
            "source_reconstruction": "source_reconstruction.json",
            "recovered_c": "recovered.c"
        },
        "checks": {},
        "findings": [],
        "summary": {
            "errors": 0,
            "warnings": 0,
            "info": 0,
            "checks_total": 0,
            "checks_ok": 0,
            "checks_failed": 0,
            "strict_failures": 0
        }
    }

def add_check(
    report: dict,
    name: str,
    status: str,
    severity: str,
    message: str,
    details: dict | None = None,
) -> None:
    """Add or update a check execution result in the report."""
    report["checks"][name] = {
        "status": status,
        "severity": severity,
        "message": message,
        "details": details or {}
    }

def add_finding(
    report: dict,
    finding_id: str,
    severity: str,
    category: str,
    title: str,
    message: str,
    artifact: str | None = None,
    location: dict | None = None,
    evidence: dict | None = None,
    recommendation: str | None = None,
) -> None:
    """Add a structured validation finding."""
    report["findings"].append({
        "id": finding_id,
        "severity": severity,
        "category": category,
        "title": title,
        "message": message,
        "artifact": artifact,
        "location": location or {
            "function": None,
            "block_id": None,
            "address": None,
            "line": None
        },
        "evidence": evidence or {},
        "recommendation": recommendation
    })

def finalize_report(report: dict) -> dict:
    """Calculate aggregate summary statistics and set final status."""
    report["finished_at"] = now_iso()
    
    findings = report["findings"]
    errors = sum(1 for f in findings if f["severity"] == "error")
    warnings = sum(1 for f in findings if f["severity"] == "warning")
    info = sum(1 for f in findings if f["severity"] == "info")
    
    # Calculate strict failures: count findings that would have been warnings in default mode but are errors.
    # We will identify strict_failures by scanning findings or checks. Let's compute it during checking,
    # or by storing a metadata key 'strict_promoted' in findings. Let's support a 'strict_promoted' flag
    # inside findings or checks details, and count them here!
    strict_failures = sum(1 for f in findings if f.get("strict_promoted", False))
    
    checks = report["checks"]
    checks_total = len(checks)
    checks_ok = sum(1 for c in checks.values() if c["status"] == "ok")
    checks_failed = sum(1 for c in checks.values() if c["status"] == "failed")
    
    # Update summary dict
    report["summary"].update({
        "errors": errors,
        "warnings": warnings,
        "info": info,
        "checks_total": checks_total,
        "checks_ok": checks_ok,
        "checks_failed": checks_failed,
        "strict_failures": strict_failures
    })
    
    # Set final report status
    # ok: no errors
    # warning: warnings exist, but no hard validation errors
    # failed: one or more error-severity checks/findings failed
    if errors > 0 or checks_failed > 0:
        report["status"] = "failed"
    elif warnings > 0:
        report["status"] = "warning"
    else:
        report["status"] = "ok"
        
    return report

def write_report(report: dict, out_dir: str | Path) -> Path:
    """Serialize the finalized validation report to JSON."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    report_file = out_path / "validation_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report_file
