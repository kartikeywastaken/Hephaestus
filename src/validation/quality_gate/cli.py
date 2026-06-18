# -*- coding: utf-8 -*-
"""
Quality Gate CLI Command Handler
"""

from __future__ import annotations
import argparse
import sys
import hashlib
import json
from pathlib import Path

from src.validation.quality_gate.builder import build_quality_gate_payload
from src.validation.quality_gate.writer import write_quality_gate
from src.validation.quality_gate.markdown import write_quality_markdown

def get_file_hash(path: Path) -> str | None:
    """Compute sha256 hash of a file if it exists."""
    if not path.exists():
        return None
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def run_quality_gate_cli(args_list: list[str]) -> int:
    """Run quality gate CLI command, returning exit code."""
    parser = argparse.ArgumentParser(description="Evaluate Hephaestus Quality Gate.")
    parser.add_argument("--out-dir", default="artifacts", help="Directory containing reconstructed artifacts.")
    parser.add_argument("--markdown", action="store_true", help="Generate human-readable quality_gate.md.")
    parser.add_argument("--json", action="store_true", help="Print compact JSON summary to stdout.")
    parser.add_argument("--strict", action="store_true", help="Enforce strict decision criteria.")
    
    try:
        args = parser.parse_args(args_list)
    except SystemExit:
        return 2
        
    out_dir = Path(args.out_dir)
    
    # Files to watch for read-only hash changes
    files_to_watch = [
        "recovered.c",
        "source_reconstruction.json",
        "evidence_index.json",
        "trace_report.json",
        "validation_report.json"
    ]
    
    hashes_before = {}
    for name in files_to_watch:
        hashes_before[name] = get_file_hash(out_dir / name)
        
    try:
        # Build first pass payload
        payload = build_quality_gate_payload(out_dir, strict=args.strict, hash_check_failed=False)
    except Exception as e:
        if args.json:
            print(json.dumps({"status": "error", "message": f"Builder crash: {e}"}))
        else:
            print(f"[quality-gate] error: builder crashed: {e}", file=sys.stderr)
        return 2
        
    # Verify input hashes remain unchanged
    hashes_after = {}
    hash_check_failed = False
    for name in files_to_watch:
        hashes_after[name] = get_file_hash(out_dir / name)
        if hashes_before[name] != hashes_after[name]:
            hash_check_failed = True
            
    if hash_check_failed:
        # Re-build payload with blocked status set to True
        try:
            payload = build_quality_gate_payload(out_dir, strict=args.strict, hash_check_failed=True)
        except Exception:
            pass
            
    try:
        write_quality_gate(payload, out_dir)
        if args.markdown:
            write_quality_markdown(payload, out_dir)
    except Exception as e:
        if args.json:
            print(json.dumps({"status": "error", "message": f"Failed to write quality gate outputs: {e}"}))
        else:
            print(f"[quality-gate] error: failed to write outputs: {e}", file=sys.stderr)
        return 2
        
    status = payload.get("status", "blocked")
    scores = payload.get("scores", {})
    readiness = scores.get("readability_readiness_score", 0.0)
    risk = scores.get("risk_score", 0.0)
    decision = payload.get("decision", {})
    
    if args.json:
        out_summary = {
            "status": status,
            "safe_to_use_for_phase7": decision.get("safe_to_use_for_phase7", False),
            "requires_review": decision.get("requires_review", False),
            "readability_readiness_score": readiness,
            "risk_score": risk,
            "report": str(out_dir / "quality_gate.json")
        }
        print(json.dumps(out_summary))
    else:
        print(
            f"[quality-gate] status={status} readiness_score={readiness:.2f} risk_score={risk:.2f}"
        )
        if status == "blocked":
            print("[quality-gate] Blocking issues:", file=sys.stderr)
            for issue in payload.get("blocking_issues", []):
                if isinstance(issue, dict):
                    print(f"  - {issue.get('title', 'Issue')} (ID: {issue.get('id', 'unknown')}): {issue.get('message', '')}", file=sys.stderr)
                else:
                    print(f"  - {issue}", file=sys.stderr)
        elif status == "review":
            print("[quality-gate] Warnings:", file=sys.stderr)
            for warning in payload.get("warnings", []):
                if isinstance(warning, dict):
                    print(f"  - {warning.get('title', 'Warning')} (ID: {warning.get('id', 'unknown')}): {warning.get('message', '')}", file=sys.stderr)
                else:
                    print(f"  - {warning}", file=sys.stderr)
                
    if status == "blocked":
        return 1
    return 0
