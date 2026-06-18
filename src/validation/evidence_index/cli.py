# -*- coding: utf-8 -*-
"""
Evidence Index CLI command
"""

from __future__ import annotations
import argparse
import sys
import hashlib
import json
from pathlib import Path

from src.validation.evidence_index.builder import build_index_payload
from src.validation.evidence_index.writer import write_evidence_index

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

def run_build_evidence_index_cli(args_list: list[str]) -> int:
    """Run evidence index builder CLI command, returning exit code."""
    parser = argparse.ArgumentParser(description="Build statement-level evidence index.")
    parser.add_argument("--out-dir", default="artifacts", help="Directory with reconstructed artifacts.")
    parser.add_argument("--json", action="store_true", help="Print compact JSON summary to stdout.")
    
    try:
        args = parser.parse_args(args_list)
    except SystemExit:
        return 2
        
    out_dir = Path(args.out_dir)
    recon_path = out_dir / "source_reconstruction.json"
    c_path = out_dir / "recovered.c"
    
    if not recon_path.exists() or not c_path.exists():
        if args.json:
            print(json.dumps({
                "status": "error",
                "message": "Required inputs source_reconstruction.json or recovered.c missing."
            }))
        else:
            print(f"[evidence-index] error: missing input source_reconstruction.json or recovered.c", file=sys.stderr)
        return 1
        
    # Get initial hashes for read-only verification
    recon_hash_before = get_file_hash(recon_path)
    c_hash_before = get_file_hash(c_path)
    
    try:
        payload = build_index_payload(out_dir)
    except Exception as e:
        if args.json:
            print(json.dumps({"status": "error", "message": f"Builder failed: {e}"}))
        else:
            print(f"[evidence-index] builder failed: {e}", file=sys.stderr)
        return 2
        
    # Verify input hashes remain unchanged
    recon_hash_after = get_file_hash(recon_path)
    c_hash_after = get_file_hash(c_path)
    
    if recon_hash_before != recon_hash_after or c_hash_before != c_hash_after:
        if args.json:
            print(json.dumps({"status": "error", "message": "Input artifacts modified during build!"}))
        else:
            print("[evidence-index] error: input artifacts modified during build!", file=sys.stderr)
        return 2
        
    try:
        report_file = write_evidence_index(payload, out_dir)
    except Exception as e:
        if args.json:
            print(json.dumps({"status": "error", "message": f"Failed to write index: {e}"}))
        else:
            print(f"[evidence-index] failed to write index file: {e}", file=sys.stderr)
        return 2
        
    summary = payload["summary"]
    statements_total = summary["statements_total"]
    true_unsupported = summary["true_unsupported_statements"]
    comment_lowered = summary["comment_lowered_statements"]
    unknown = summary["unknown_statement_category"]
    
    if args.json:
        out_summary = {
            "status": "ok",
            "statements_total": statements_total,
            "true_unsupported": true_unsupported,
            "comment_lowered": comment_lowered,
            "unknown": unknown,
            "report": str(report_file)
        }
        print(json.dumps(out_summary))
    else:
        print(
            f"[evidence-index] built evidence_index.json "
            f"statements={statements_total} unknown={unknown} "
            f"true_unsupported={true_unsupported} comment_lowered={comment_lowered}"
        )
        
    return 0
