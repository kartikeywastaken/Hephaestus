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
    parser.add_argument("--no-compile-shape-fix", action="store_true", dest="no_compile_shape_fix", default=False, help="Disable Phase 7.2.1 compile-shape hardening patch.")
    parser.add_argument("--strict-readable-clang", action="store_true", dest="strict_readable_clang", default=False, help="Enforce that clang syntax warnings cause a non-ok status.")
    parser.add_argument("--simplify-expressions", action="store_true", dest="simplify_expressions", default=True, help="Enable Phase 7.3 expression simplification (default).")
    parser.add_argument("--no-simplify-expressions", action="store_false", dest="simplify_expressions", help="Disable Phase 7.3 expression simplification.")
    parser.add_argument("--no-copy-op-store-simplification", action="store_true", dest="no_copy_op_store_simplification", default=False, help="Disable copy-op-store category of expression simplification.")
    parser.add_argument("--enable-mask-cast-simplification", action="store_true", dest="enable_mask_cast_simplification", default=False, help="Enable Phase 7.3.1 mask-cast simplification (disabled by default).")

    
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
                                        
    # 4.B Step: Collect declared identifiers in the original functions of recovered_c
    from src.readability.symbol_promotion import parse_c_into_functions
    from src.readability.compile_shape import collect_declared_identifiers, validate_predicate_condition
    
    orig_blocks = parse_c_into_functions(recovered_c)
    declared_by_func = {}
    for ob in orig_blocks:
        if ob["type"] == "function":
            declared_by_func[ob["name"]] = collect_declared_identifiers(ob)

    # 5. Step: Scan candidate sites and recover predicates
    candidates = extract_candidate_sites(recovered_c)
    
    sites = []
    skipped_sites = []
    emitter_mapping = {}
    
    # We collect missing registers that were safely validated to declare them later
    added_decls_from_predicates = {} # func_name -> list of register names
    predicates_skipped_due_to_undeclared_identifiers = 0
    
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
            fn_name = cand["function"]
            declared_ids = declared_by_func.get(fn_name, set())
            
            is_safe = True
            missing_ids = []
            if not args.no_compile_shape_fix:
                is_safe, missing_ids = validate_predicate_condition(
                    replacement_condition,
                    declared_ids,
                    promote_temps_active=args.promote_temps
                )
                
            if not is_safe:
                status = "skipped"
                reason = "undeclared predicate identifier"
                predicates_skipped_due_to_undeclared_identifiers += 1
                skipped_sites.append({
                    "site_id": site_id,
                    "function": cand["function"],
                    "line_number": cand["line_number"],
                    "kind": cand["kind"],
                    "original_condition": cand["original_condition"],
                    "status": "skipped",
                    "reason": reason,
                    "confidence": "unsafe",
                    "evidence": {
                        "raw_evidence": unescaped_adapter
                    },
                    "missing_identifiers": missing_ids
                })
                continue
            else:
                if missing_ids:
                    # Filter duplicate additions
                    func_miss = added_decls_from_predicates.setdefault(fn_name, [])
                    for m_id in missing_ids:
                        if m_id not in func_miss:
                            func_miss.append(m_id)
                    declared_ids.update(missing_ids)
                    
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
    function_promotions = {}
    original_types_by_func = {}
    
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
        function_promotions = getattr(promo_engine, "function_promotions", {})
        original_types_by_func = getattr(promo_engine, "original_types_by_func", {})
    else:
        from src.readability.compile_shape import collect_original_declaration_types
        for ob in orig_blocks:
            if ob["type"] == "function":
                original_types_by_func[ob["name"]] = collect_original_declaration_types(ob)
                
    # Phase 7.2.1 Compile-Shape Hardening post-processing
    compile_shape_items = []
    compile_shape_stats = {
        "missing_predicate_declarations_added": 0,
        "scratch_declarations_added": 0,
        "predicates_skipped_due_to_undeclared_identifiers": predicates_skipped_due_to_undeclared_identifiers,
        "forward_declarations_removed": 0,
        "forward_declaration_conflicts_resolved": 0,
        "function_symbol_promotions_skipped_for_collision": 0,
        "abi_scratch_declarations_added": 0,
        "abi_scratch_declarations_inherited": 0
    }
    
    if args.promote_symbols and symbol_promotion_data:
        for sk in symbol_promotion_data.get("skipped_promotions", []):
            if sk.get("reason") == "global function collision":
                compile_shape_stats["function_symbol_promotions_skipped_for_collision"] += 1
                compile_shape_items.append({
                    "kind": "function_symbol_promotion_skipped_for_collision",
                    "function": "global",
                    "old_name": sk.get("old_name"),
                    "proposed_new_name": sk.get("proposed_new_name"),
                    "reason": "global function collision"
                })
                
    if not args.no_compile_shape_fix:
        from src.readability.compile_shape import harden_compile_shape_functions, dedupe_and_resolve_forward_declarations
        
        # 1. Dedupe and resolve conflicting forward declarations (Fix 3)
        readable_c, resolved_items, resolved_stats = dedupe_and_resolve_forward_declarations(readable_c)
        compile_shape_items.extend(resolved_items)
        compile_shape_stats["forward_declarations_removed"] += resolved_stats["forward_declarations_removed"]
        compile_shape_stats["forward_declaration_conflicts_resolved"] += resolved_stats["forward_declaration_conflicts_resolved"]
        compile_shape_stats["duplicate_main_definitions_renamed"] = resolved_stats.get("duplicate_main_definitions_renamed", 0) + source_recon.get("summary", {}).get("duplicate_main_functions_renamed", 0)
        compile_shape_stats["main_forward_declarations_normalized"] = resolved_stats.get("main_forward_declarations_normalized", 0)
        
        # 2. Harden local declarations (Fix 1 & Fix 2)
        readable_c, added_items, added_stats = harden_compile_shape_functions(
            readable_c,
            promote_temps_active=args.promote_temps,
            function_promotions=function_promotions,
            original_types_by_func=original_types_by_func,
            added_decls_from_predicates=added_decls_from_predicates
        )
        compile_shape_items.extend(added_items)
        compile_shape_stats["missing_predicate_declarations_added"] += added_stats["missing_predicate_declarations_added"]
        compile_shape_stats["scratch_declarations_added"] += added_stats["scratch_declarations_added"]
        compile_shape_stats["main_abi_bridge_declarations_added"] = added_stats.get("main_abi_bridge_declarations_added", 0) + source_recon.get("summary", {}).get("main_abi_bridges_inserted", 0)
        compile_shape_stats["abi_scratch_declarations_added"] += added_stats.get("abi_scratch_declarations_added", 0)
        compile_shape_stats["abi_scratch_declarations_inherited"] = source_recon.get("summary", {}).get("abi_scratch_declarations_inserted", 0)
        
    expression_simplification_enabled = getattr(args, "simplify_expressions", True) and args.promote_symbols
    expression_simplification_data = None
    expression_simplifications = []
    skipped_expression_simplifications = []

    if expression_simplification_enabled:
        from src.readability.expression_simplification import simplify_expressions, build_expression_simplification_report_data
        
        enable_copy_op_store = not getattr(args, "no_copy_op_store_simplification", False)
        pre_simplification_c = readable_c
        
        # Determine skipped categories for reporting
        if not enable_copy_op_store:
            skipped_expression_simplifications.append({
                "category": "copy_op_store",
                "status": "disabled",
                "reason": "disabled by --no-copy-op-store-simplification"
            })
            
        enable_mask_cast = getattr(args, "enable_mask_cast_simplification", False)

        try:
            # Step 6: Run expression simplification
            simplified_c, simplifications, skipped_list, expr_stats = simplify_expressions(
                readable_c,
                enable_copy_op_store=enable_copy_op_store,
                enable_mask_cast=enable_mask_cast,
            )
            expression_simplifications = [
                {
                    "site_id": s.site_id,
                    "function": s.function,
                    "line_number": s.line_number,
                    "category": s.category,
                    "old_text": s.old_text,
                    "new_text": s.new_text,
                    "reason": s.reason
                }
                for s in simplifications
            ]
            
            # Step 7: Final compile-shape safety pass (post-simplification)
            if not args.no_compile_shape_fix:
                from src.readability.compile_shape import harden_compile_shape_functions
                simplified_c, post_added_items, post_added_stats = harden_compile_shape_functions(
                    simplified_c,
                    promote_temps_active=args.promote_temps,
                    function_promotions=function_promotions,
                    original_types_by_func=original_types_by_func,
                    added_decls_from_predicates=added_decls_from_predicates
                )
                compile_shape_items.extend(post_added_items)
                compile_shape_stats["missing_predicate_declarations_added"] += post_added_stats["missing_predicate_declarations_added"]
                compile_shape_stats["scratch_declarations_added"] += post_added_stats["scratch_declarations_added"]
                compile_shape_stats["main_abi_bridge_declarations_added"] += post_added_stats.get("main_abi_bridge_declarations_added", 0)
                compile_shape_stats["abi_scratch_declarations_added"] += post_added_stats.get("abi_scratch_declarations_added", 0)
            
            # Write simplified output temporarily to path for validation check
            readable_c_path = out_dir / "recovered_readable.c"
            try:
                with open(readable_c_path, "w", encoding="utf-8") as f:
                    f.write(simplified_c)
            except Exception as e:
                logger.error("Failed to write temporary recovered_readable.c: %s", e)
                
            # Clang gate validation
            clang_ok = True
            if clang_available():
                res = run_clang_syntax_check(readable_c_path)
                if res.get("status") == "failed":
                    clang_ok = False
                    logger.warning("Clang syntax check failed on simplified C. Rolling back expression simplification.")
            
            if not clang_ok:
                # Rollback!
                readable_c = pre_simplification_c
                # Append rollback status for each category to skipped list
                _all_cats = [
                    "identity_arithmetic", "redundant_parentheses",
                    "self_assignment", "double_parentheses",
                    "temp_copy_roundtrip", "copy_op_store",
                ]
                if enable_mask_cast:
                    _all_cats.append("mask_cast")
                for cat in _all_cats:
                    if cat == "copy_op_store" and not enable_copy_op_store:
                        continue
                    skipped_expression_simplifications.append({
                        "category": cat,
                        "status": "rolled_back",
                        "reason": "clang syntax check failed after simplification"
                    })
                    
                expression_simplification_data = build_expression_simplification_report_data(
                    [], [], expr_stats, enabled=True, status="rolled_back"
                )
                expression_simplification_data["category_statuses"] = skipped_expression_simplifications
            else:
                # Simplification succeeded!
                readable_c = simplified_c
                expression_simplification_data = build_expression_simplification_report_data(
                    simplifications, skipped_list, expr_stats, enabled=True, status="ok"
                )
                expression_simplification_data["category_statuses"] = skipped_expression_simplifications
                
        except Exception as e:
            logger.exception("Expression simplification crashed: %s", e)
            readable_c = pre_simplification_c
            _all_cats = [
                "identity_arithmetic", "redundant_parentheses",
                "self_assignment", "double_parentheses",
                "temp_copy_roundtrip", "copy_op_store",
            ]
            if enable_mask_cast:
                _all_cats.append("mask_cast")
            for cat in _all_cats:
                if cat == "copy_op_store" and not enable_copy_op_store:
                    continue
                skipped_expression_simplifications.append({
                    "category": cat,
                    "status": "rolled_back",
                    "reason": f"simplification engine exception: {e}"
                })
            from src.readability.expression_simplification import ExprSimplificationStats
            expression_simplification_data = build_expression_simplification_report_data(
                [], [], ExprSimplificationStats(), enabled=True, status="rolled_back"
            )
            expression_simplification_data["category_statuses"] = skipped_expression_simplifications
    else:
        # Simplification disabled
        _disabled_cats = [
            "identity_arithmetic", "redundant_parentheses",
            "self_assignment", "double_parentheses",
            "temp_copy_roundtrip", "copy_op_store",
        ]
        skipped_expression_simplifications = [
            {
                "category": cat,
                "status": "disabled",
                "reason": "disabled by --no-simplify-expressions"
            }
            for cat in _disabled_cats
        ]

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
                if args.strict_readable_clang:
                    clang_syntax_status = "failed"
                    diagnostics.append(f"Clang syntax check failed on recovered_readable.c with {res.get('warnings')} warnings (strict mode).")
                else:
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
        symbol_promotion_data=symbol_promotion_data,
        compile_shape_enabled=not args.no_compile_shape_fix,
        compile_shape_data={"stats": compile_shape_stats, "items": compile_shape_items},
        expression_simplification_enabled=expression_simplification_enabled,
        expression_simplification_data=expression_simplification_data,
        expression_simplifications=expression_simplifications,
        skipped_expression_simplifications=skipped_expression_simplifications
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
