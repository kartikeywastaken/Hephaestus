#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validation Report Inspection Utility
"""

import sys
import json
from pathlib import Path

def inspect_report(report_path: Path):
    if not report_path.exists():
        print(f"Error: Report file not found at {report_path}")
        sys.exit(2)
        
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
    except Exception as e:
        print(f"Error: Failed to parse JSON report: {e}")
        sys.exit(2)
        
    status = report.get("status", "unknown")
    summary = report.get("summary", {})
    errors = summary.get("errors", 0)
    warnings = summary.get("warnings", 0)
    checks_total = summary.get("checks_total", 0)
    checks_ok = summary.get("checks_ok", 0)
    checks_failed = summary.get("checks_failed", 0)
    
    print(f"status: {status}")
    print(f"summary: errors={errors} warnings={warnings} checks={checks_ok}/{checks_total}")
    
    # Print failed/warning checks
    checks = report.get("checks", {})
    non_ok_checks = {k: v for k, v in checks.items() if v.get("status") != "ok"}
    if non_ok_checks:
        print("\nfailed/warning checks:")
        for name, check in non_ok_checks.items():
            c_status = check.get("status", "unknown")
            c_sev = check.get("severity", "unknown")
            c_msg = check.get("message", "")
            c_det = check.get("details", {})
            print(f"  {name} {c_status} {c_sev}")
            print(f"    {c_msg}")
            if c_det:
                import pprint
                det_str = pprint.pformat(c_det, indent=2)
                for line in det_str.splitlines():
                    print(f"    {line}")
                
    # Print findings
    findings = report.get("findings", [])
    if findings:
        print("\nfindings:")
        for f in findings:
            f_sev = f.get("severity", "unknown")
            f_id = f.get("id", "VAL-???")
            f_cat = f.get("category", "unknown")
            f_title = f.get("title", "")
            f_msg = f.get("message", "")
            f_rec = f.get("recommendation", "")
            
            print(f"  {f_sev} {f_id} {f_cat} - {f_title}")
            print(f"    {f_msg}")
            if f_rec:
                print(f"    {f_rec}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/inspect_validation_report.py <path_to_report_json>")
        sys.exit(2)
    inspect_report(Path(sys.argv[1]))

if __name__ == "__main__":
    main()
