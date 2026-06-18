# -*- coding: utf-8 -*-
"""
Readability CLI Command Handler
"""

import sys
import os
import json
import argparse
import logging
from pathlib import Path
from typing import List

from src.readability.loader import load_readability_inputs, HashWatchdog
from src.readability.predicate_parser import parse_adapter_string, unescape_c_string
from src.readability.predicate_recovery import recover_predicate
from src.readability.readable_emitter import emit_readable_c, extract_candidate_sites
from src.readability.report import build_readability_report, write_readability_report_json, generate_readability_report_md
from src.pipeline.clang import run_clang_syntax_check, clang_available

logger = logging.getLogger("readability.cli")

def run_build_readable_cli(argv: List[str]) -> int:
    """
    Executes build-readable subcommand.
    Returns exit code:
        0 -> success
        1 -> blocked/failure (missing required file, quality gate blocked, hash check mismatch, or clang syntax error)
        2 -> internal error or invalid CLI arguments
    """
    parser = argparse.ArgumentParser(description="Generate best-effort human-readable C from recovered.c.")
    parser.add_argument("--out-dir", default="artifacts", help="Directory containing target artifacts.")
    parser.add_argument("--json", action="store_true", help="Print clean JSON result on stdout.")
    parser.add_argument("--markdown", action="store_true", help="Generate readability_report.md.")
    parser.add_argument("--require-quality-gate", action="store_true", help="Fail if quality_gate.json is missing.")
    parser.add_argument("--allow-review", action="store_true", help="Accepted for compatibility; review is allowed by default.")
    parser.add_argument("--ignore-quality-gate", action="store_true", help="Override quality gate blocks and proceed with warnings.")
    parser.add_argument("--promote-symbols", action="store_true", dest="promote_symbols", default=True, help="Enable Phase 7.2 symbol promotion (default).")
    parser.add_argument("--no-promote-symbols", action="store_false", dest="promote_symbols", help="Disable Phase 7.2 symbol promotion.")
    parser.add_argument("--promote-temps", action="store_true", dest="promote_temps", default=False, help="Enable temporary registers promotion (default disabled).")
    
    try:
        args = parser.parse_args(argv)
    except Exception as e:
        print(f"Error parsing CLI arguments: {e}", file=sys.stderr)
        return 2
        
    out_dir = Path(args.out_dir).resolve()
    
    # Suppress console logging if JSON mode is requested
    if args.json:
        root_logger = logging.getLogger()
        for h in list(root_logger.handlers):
            if isinstance(h, logging.StreamHandler) and (h.stream == sys.stdout or h.stream == sys.stderr):
                root_logger.removeHandler(h)
                
    diagnostics = []
    
    # 1. Step: Watchdog Initial Hashes
    watchdog = HashWatchdog(out_dir)
    
    # 2. Step: Load inputs
    try:
        recovered_c, source_recon, evidence_idx, trace_rep, qg_data, unified_ir, layout_recon, type_recon, phase4_sem, load_warnings = load_readability_inputs(out_dir)
    except FileNotFoundError as e:
        err_msg = str(e)
        logger.error(err_msg)
        if args.json:
            print(json.dumps({"status": "failed", "error": err_msg}))
        else:
            print(f"Error: {err_msg}", file=sys.stderr)
        return 1
    except Exception as e:
        err_msg = f"Loader exception: {e}"
        logger.exception(err_msg)
        if args.json:
            print(json.dumps({"status": "failed", "error": err_msg}))
        else:
            print(f"Error: {err_msg}", file=sys.stderr)
        return 2
        
    # 3. Step: Quality Gate Policy Checks
    quality_gate_status = "ok"
    safe_to_use = True
    
    qg_path = out_dir / "quality_gate.json"
    if not qg_path.exists():
        quality_gate_status = "missing"
        if args.require_quality_gate:
            err_msg = "Quality gate file quality_gate.json is missing and required."
            logger.error(err_msg)
            if args.json:
                print(json.dumps({"status": "failed", "error": err_msg}))
            else:
                print(f"Error: {err_msg}", file=sys.stderr)
            return 1
        else:
            diagnostics.append("quality_gate.json is missing; proceeding with warning.")
    else:
        # quality_gate.json exists
        status = qg_data.get("status", "ok")
        blocked = qg_data.get("decision", {}).get("blocked", False)
        safe_to_use = qg_data.get("decision", {}).get("safe_to_use_for_phase7", True)
        quality_gate_status = status
        
        if args.ignore_quality_gate:
            quality_gate_status = "ignored"
            diagnostics.append("Quality gate checks ignored by command line flag.")
        else:
            if blocked or not safe_to_use:
                err_msg = f"Phase 7 blocked by Quality Gate: status={status}, blocked={blocked}, safe={safe_to_use}"
                logger.error(err_msg)
                if args.json:
                    print(json.dumps({"status": "failed", "error": err_msg}))
                else:
                    print(f"Error: {err_msg}", file=sys.stderr)
                return 1
            elif status == "review":
                diagnostics.append("Quality gate requires review; proceeding with warnings.")
                
    # 4. Step: Build instruction lookup cache
    # We combine source_reconstruction.json and unified_ir.json instructions
    inst_lookup = {}
    if source_recon and "functions" in source_recon:
        for fn in source_recon["functions"]:
            blocks = fn.get("lowered_blocks", {})
            if isinstance(blocks, dict):
                for block_id, insts in blocks.items():
                    if isinstance(insts, list):
                        for inst in insts:
                            if isinstance(inst, dict) and "address" in inst:
                                addr = inst["address"]
                                src_inst = inst.get("source_instruction")
                                if src_inst and isinstance(src_inst, dict):
                                    inst_lookup[addr] = src_inst
                                    
    if unified_ir and isinstance(unified_ir, dict):
        data = unified_ir.get("data", {})
        if isinstance(data, dict):
            funcs = data.get("functions", [])
            if isinstance(funcs, list):
                for fn in funcs:
                    if isinstance(fn, dict):
                        for block in fn.get("basic_blocks", []):
                            if isinstance(block, dict):
                                for inst in block.get("instructions", []):
                                    if isinstance(inst, dict) and "address" in inst:
                                        addr = inst["address"]
                                        if addr not in inst_lookup:
                                            inst_lookup[addr] = inst
                                        
    # 5. Step: Scan candidate sites and recover predicates
    candidates = extract_candidate_sites(recovered_c)
    
    sites = []
    skipped_sites = []
    emitter_mapping = {}
    
    for idx, cand in enumerate(candidates):
        site_id = f"pred_{idx+1:06d}"
        adapter_raw = cand["adapter_raw"]
        unescaped_adapter = unescape_c_string(adapter_raw)
        
        parsed = parse_adapter_string(unescaped_adapter)
        if not parsed:
            skipped_sites.append({
                "site_id": site_id,
                "function": cand["function"],
                "line_number": cand["line_number"],
                "kind": cand["kind"],
                "original_condition": cand["original_condition"],
                "status": "skipped",
                "reason": "unsupported evidence format",
                "confidence": "unsafe",
                "evidence": {
                    "raw_evidence": unescaped_adapter
                }
            })
            continue
            
        status, replacement_condition, reason, notes = recover_predicate(parsed, inst_lookup)
        
        if status == "recovered" and replacement_condition:
            source = parsed["type"]
            if source in ("cmp_branch_direct", "cmp_branch_indirect"):
                source = f"cmp/{parsed['branch_cond']}"
                
            sites.append({
                "site_id": site_id,
                "function": cand["function"],
                "line_number": cand["line_number"],
                "kind": cand["kind"],
                "original_condition": cand["original_condition"],
                "replacement_condition": replacement_condition,
                "source": "cmp_conditional_branch" if parsed["type"] in ("cmp_branch_direct", "cmp_branch_indirect") else parsed["type"],
                "status": "recovered",
                "confidence": "static_simple",
                "evidence": {
                    "raw_evidence": unescaped_adapter
                },
                "notes": notes
            })
            emitter_mapping[cand["line_number"]] = (replacement_condition, source)
        else:
            # skipped
            skipped_sites.append({
                "site_id": site_id,
                "function": cand["function"],
                "line_number": cand["line_number"],
                "kind": cand["kind"],
                "original_condition": cand["original_condition"],
                "status": "skipped",
                "reason": reason or "complex condition",
                "confidence": "unsafe",
                "evidence": {
                    "raw_evidence": unescaped_adapter
                }
            })
            
    # 6. Step: Emit C output
    readable_c = emit_readable_c(recovered_c, emitter_mapping)
    
    symbol_promotion_data = None
    if args.promote_symbols:
        from src.readability.symbol_promotion import SymbolPromotionEngine
        promo_engine = SymbolPromotionEngine(
            source_recon=source_recon,
            type_recovery=type_recon,
            phase4_semantics=phase4_sem,
            layout_recovery=layout_recon,
            promote_temps=args.promote_temps
        )
        readable_c, symbol_promotion_data = promo_engine.run_symbol_promotion(readable_c)
        
    readable_c_path = out_dir / "recovered_readable.c"
    
    try:
        with open(readable_c_path, "w", encoding="utf-8") as f:
            f.write(readable_c)
    except Exception as e:
        err_msg = f"Failed to write recovered_readable.c: {e}"
        logger.error(err_msg)
        if args.json:
            print(json.dumps({"status": "failed", "error": err_msg}))
        else:
            print(f"Error: {err_msg}", file=sys.stderr)
        return 2
        
    # 7. Step: Clang Syntax Check
    clang_syntax_status = "skipped"
    if clang_available():
        res = run_clang_syntax_check(readable_c_path)
        if res.get("status") == "ok":
            if res.get("warnings", 0) > 0:
                clang_syntax_status = "warning"
            else:
                clang_syntax_status = "ok"
        elif res.get("status") == "failed":
            clang_syntax_status = "failed"
            diagnostics.append(f"Clang syntax check failed on recovered_readable.c with {res.get('errors')} errors.")
        else:
            clang_syntax_status = "failed"
    else:
        clang_syntax_status = "unavailable"
        diagnostics.append("Clang is not available; syntax validation skipped.")
        
    # 8. Step: Check Input Hash Guard (Safety)
    if not watchdog.verify_hashes():
        # Clean up readable outputs before failing
        try:
            if readable_c_path.exists():
                readable_c_path.unlink()
            report_json_path = out_dir / "readability_report.json"
            if report_json_path.exists():
                report_json_path.unlink()
            report_md_path = out_dir / "readability_report.md"
            if report_md_path.exists():
                report_md_path.unlink()
        except Exception:
            pass
        err_msg = "Hash Guard mismatch: An input artifact was modified during execution!"
        logger.error(err_msg)
        if args.json:
            print(json.dumps({"status": "failed", "error": err_msg}))
        else:
            print(f"Error: {err_msg}", file=sys.stderr)
        return 1
        
    # 9. Step: Build and write reports
    report = build_readability_report(
        sites=sites,
        skipped_sites=skipped_sites,
        quality_gate_status=quality_gate_status,
        safe_to_use_for_phase7=safe_to_use,
        clang_syntax_status=clang_syntax_status,
        warnings=load_warnings,
        diagnostics=diagnostics,
        promote_symbols_enabled=args.promote_symbols,
        symbol_promotion_data=symbol_promotion_data
    )
    
    write_readability_report_json(report, out_dir)
    
    # Always generate md report if requested, or if we want E2E outputs
    if args.markdown:
        generate_readability_report_md(report, out_dir)
        
    # 10. Step: Terminal Output
    sum_promoted = report["summary"].get("symbols_promoted", 0)
    sum_slots = report["summary"].get("stack_slots_promoted", 0)
    sum_params = report["summary"].get("parameters_promoted", 0)
    sum_temps = report["summary"].get("temps_promoted", 0)
    
    if args.json:
        
        result = {
            "status": report["status"],
            "predicates_recovered": len(sites),
            "symbols_promoted": sum_promoted,
            "stack_slots_promoted": sum_slots,
            "parameters_promoted": sum_params,
            "temps_promoted": sum_temps,
            "output": str(readable_c_path),
            "report": str(out_dir / "readability_report.json")
        }
        print(json.dumps(result))
    else:
        print("Hephaestus Phase 7.2 Readable Reconstruction Complete.")
        print(f"Output File: {readable_c_path}")
        print(f"Report JSON: {out_dir / 'readability_report.json'}")
        if args.markdown:
            print(f"Report Markdown: {out_dir / 'readability_report.md'}")
        print(f"Recovered predicates: {len(sites)}")
        print(f"Skipped condition sites: {len(skipped_sites)}")
        if args.promote_symbols:
            print(f"Promoted symbols: {sum_promoted}")
            print(f"  Stack slots promoted: {sum_slots}")
            print(f"  Parameters promoted: {sum_params}")
            print(f"  Temporaries promoted: {sum_temps}")
        print(f"Global status: {report['status'].upper()}")
        
    if report["status"] == "failed" or clang_syntax_status == "failed":
        return 1
        
    return 0
# A simple entrypoint for main.py mapping
if __name__ == "__main__":
    sys.exit(run_build_readable_cli(sys.argv[1:]))
