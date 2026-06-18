# -*- coding: utf-8 -*-
"""
Validation CLI Subcommand
"""

from __future__ import annotations
import argparse
import sys
import logging
import hashlib
from pathlib import Path
from src.validation.loader import load_validation_artifacts
from src.validation.report import new_report, write_report
from src.validation.checks import run_all_validation_checks

class ValidateConsoleFormatter(logging.Formatter):
    """Custom logging formatter that adds [validate] prefix only to non-indented lines."""
    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        if formatted.startswith(" ") or formatted.startswith("\t"):
            return formatted
        return f"[validate] {formatted}"

def run_validate_cli(args_list: list[str]) -> int:
    """Run standalone validation subcommand, return exit code."""
    parser = argparse.ArgumentParser(description="Static Validation and Evidence Consistency Checks.")
    parser.add_argument("--out-dir", default="artifacts", help="Artifact directory to validate.")
    parser.add_argument("--strict", action="store_true", help="Promote selected warnings to errors.")
    parser.add_argument("--no-clang", action="store_true", help="Skip Clang syntax check.")
    parser.add_argument("--json", action="store_true", help="Print compact JSON summary to stdout.")
    parser.add_argument("--require-evidence-index", action="store_true", help="Fail validation if evidence_index.json is missing.")
    parser.add_argument("--require-trace-report", action="store_true", help="Fail validation if trace_report.json is missing.")

    
    try:
        args = parser.parse_args(args_list)
    except SystemExit as e:
        return 2

        
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_file = out_dir / "validation.log"
    
    # Setup local logger
    logger = logging.getLogger("validation")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False
    
    # File Handler
    fh = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
    
    # Console Stream Handler (only if not writing raw json summary to stdout)
    if not args.json:
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(logging.INFO)
        sh.setFormatter(ValidateConsoleFormatter("%(message)s"))
        logger.addHandler(sh)
        
    logger.info("Starting static validation on out-dir: %s", out_dir)
    
    recon_path = out_dir / "source_reconstruction.json"
    c_path = out_dir / "recovered.c"
    
    # 1. Record hashes before validation
    recon_hash_before = get_file_hash(recon_path)
    c_hash_before = get_file_hash(c_path)
    
    # 2. Load artifacts
    try:
        artifacts = load_validation_artifacts(out_dir)
        report = new_report(out_dir, args.strict)
        if artifacts.trace_report is not None:
            report["trace_report"] = "trace_report.json"
    except Exception as e:
        logger.exception("Failed to load artifacts or initialize report: %s", e)
        return 2
        
    # 3. Execute all validation checks
    try:
        try:
            run_all_validation_checks(
                artifacts,
                report,
                no_clang=args.no_clang,
                require_evidence_index=args.require_evidence_index,
                require_trace_report=args.require_trace_report
            )
        except TypeError as te:
            if "require_trace_report" in str(te) or "require_evidence_index" in str(te):
                run_all_validation_checks(artifacts, report, no_clang=args.no_clang)
            else:
                raise te
    except Exception as e:



        logger.exception("Validator execution crashed: %s", e)
        return 2
        
    # 4. Verify hashes after validation to guarantee read-only behavior
    recon_hash_after = get_file_hash(recon_path)
    c_hash_after = get_file_hash(c_path)
    
    if recon_hash_before != recon_hash_after or c_hash_before != c_hash_after:
        logger.error("Guards violated: validation engine modified input artifacts!")
        return 2
        
    # 5. Write report to validation_report.json
    try:
        report_file = write_report(report, out_dir)
    except Exception as e:
        logger.exception("Failed to write validation report: %s", e)
        return 2
        
    summary = report["summary"]
    status = report["status"]
    errors = summary["errors"]
    warnings = summary["warnings"]
    checks_total = summary["checks_total"]
    checks_ok = summary["checks_ok"]
    
    # 6. Report outputs
    if args.json:
        import json
        summary_out = {
            "status": status,
            "errors": errors,
            "warnings": warnings,
            "checks_total": checks_total,
            "report": str(report_file)
        }
        print(json.dumps(summary_out))
    else:
        logger.info(
            "status=%s errors=%d warnings=%d checks=%d/%d",
            status, errors, warnings, checks_ok, checks_total
        )
        if status in ("warning", "failed") and report.get("findings"):
            logger.info("top findings:")
            # Sort findings: errors first, then warnings, then info
            findings = list(report["findings"])
            severity_order = {"error": 0, "failed": 0, "warning": 1, "info": 2}
            findings.sort(key=lambda x: severity_order.get(x.get("severity"), 99))
            
            for f in findings[:3]:
                logger.info("  %s %s %s", f.get("severity"), f.get("id"), f.get("title"))
                logger.info("    %s", f.get("message"))
        logger.info("report written to %s", report_file)
        
    if status == "failed":
        return 1
    return 0

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
