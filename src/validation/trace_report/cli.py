# -*- coding: utf-8 -*-
"""
Trace Report CLI Command Handler
"""

from __future__ import annotations
import argparse
import sys
import hashlib
import json
from pathlib import Path

from src.validation.trace_report.builder import build_trace_report_payload
from src.validation.trace_report.writer import write_trace_report
from src.validation.trace_report.markdown import write_trace_markdown

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

def run_build_trace_report_cli(args_list: list[str]) -> int:
    """Run trace report builder CLI command, returning exit code."""
    parser = argparse.ArgumentParser(description="Build decompiler trace report.")
    parser.add_argument("--out-dir", default="artifacts", help="Directory containing reconstructed artifacts.")
    parser.add_argument("--markdown", action="store_true", help="Generate human-readable trace_report.md.")
    parser.add_argument("--json", action="store_true", help="Print compact JSON summary to stdout.")
    parser.add_argument("--require-validation", action="store_true", help="Fail if validation_report.json is missing.")
    parser.add_argument("--require-evidence-index", action="store_true", default=True, help="Fail if evidence_index.json is missing.")
    parser.add_argument("--no-require-evidence-index", action="store_false", dest="require_evidence_index", help="Do not fail if evidence_index.json is missing.")
    
    try:
        args = parser.parse_args(args_list)
    except SystemExit:
        return 2
        
    out_dir = Path(args.out_dir)
    ev_path = out_dir / "evidence_index.json"
    val_path = out_dir / "validation_report.json"
    recon_path = out_dir / "source_reconstruction.json"
    c_path = out_dir / "recovered.c"
    
    # Check if evidence_index is required and missing
    if args.require_evidence_index and not ev_path.exists():
        if args.json:
            print(json.dumps({"status": "error", "message": "Required evidence_index.json missing."}))
        else:
            print("[trace-report] error: missing required evidence_index.json", file=sys.stderr)
        return 1
        
    # Check if validation_report is required and missing
    if args.require_validation and not val_path.exists():
        if args.json:
            print(json.dumps({"status": "error", "message": "Required validation_report.json missing."}))
        else:
            print("[trace-report] error: missing required validation_report.json", file=sys.stderr)
        return 1
        
    # Capture initial hashes for read-only verification
    hashes_before = {
        "recovered.c": get_file_hash(c_path),
        "source_reconstruction.json": get_file_hash(recon_path),
        "evidence_index.json": get_file_hash(ev_path),
        "validation_report.json": get_file_hash(val_path)
    }
    
    try:
        payload = build_trace_report_payload(
            out_dir,
            require_validation=args.require_validation,
            require_evidence_index=args.require_evidence_index
        )
    except Exception as e:
        if args.json:
            print(json.dumps({"status": "error", "message": f"Builder failed: {e}"}))
        else:
            print(f"[trace-report] builder failed: {e}", file=sys.stderr)
        return 1
        
    # Verify input hashes remain unchanged
    hashes_after = {
        "recovered.c": get_file_hash(c_path),
        "source_reconstruction.json": get_file_hash(recon_path),
        "evidence_index.json": get_file_hash(ev_path),
        "validation_report.json": get_file_hash(val_path)
    }
    
    if hashes_before != hashes_after:
        if args.json:
            print(json.dumps({"status": "error", "message": "Input artifacts modified during trace generation!"}))
        else:
            print("[trace-report] error: input artifacts modified during trace generation!", file=sys.stderr)
        return 2
        
    try:
        report_file = write_trace_report(payload, out_dir)
        if args.markdown:
            write_trace_markdown(payload, out_dir)
    except Exception as e:
        if args.json:
            print(json.dumps({"status": "error", "message": f"Failed to write trace files: {e}"}))
        else:
            print(f"[trace-report] failed to write report files: {e}", file=sys.stderr)
        return 2
        
    summary = payload["summary"]
    statements_total = summary["statements_total"]
    high_attention = summary["high_attention_lines"]
    
    if args.json:
        out_summary = {
            "status": "ok",
            "statements_total": statements_total,
            "high_attention_lines": high_attention,
            "report": str(report_file)
        }
        print(json.dumps(out_summary))
    else:
        print(
            f"[trace-report] built trace_report.json "
            f"statements={statements_total} high_attention={high_attention}"
        )
        if args.markdown:
            print(f"[trace-report] built trace_report.md human summary")
            
    return 0
