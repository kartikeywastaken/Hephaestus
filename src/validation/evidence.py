# -*- coding: utf-8 -*-
"""
Evidence Consistency Checks
"""

from __future__ import annotations
import re
from src.validation.models import ValidationArtifacts
from src.validation.report import add_check, add_finding

def check_evidence(artifacts: ValidationArtifacts, report: dict) -> None:
    """Run all evidence consistency checks between source summary and text artifacts."""
    strict = report.get("strict", False)
    
    # Pre-check: If source_reconstruction.json is missing, skip all metadata checks.
    if artifacts.source_reconstruction is None:
        for name in ("function_count_consistency", "lowered_statement_evidence", "unsupported_accounting", "callsite_consistency", "return_consistency"):
            add_check(report=report, name=name, status="skipped", severity="warning", message="Skipped: source_reconstruction.json not loaded.")
        return
        
    recon = artifacts.source_reconstruction
    summary = recon.get("summary", {})
    funcs = recon.get("data", {}).get("functions", [])
    if not funcs and "functions" in recon:
        funcs = recon.get("functions", [])
        
    # -------------------------------------------------------------------------
    # 1. Function Count Consistency
    # -------------------------------------------------------------------------
    fn_status = "ok"
    total_fns = summary.get("functions_total")
    emitted_fns = summary.get("functions_emitted")
    missing_fns = summary.get("functions_missing")
    
    if total_fns is None or emitted_fns is None or missing_fns is None:
        fn_status = "warning"
        add_finding(
            report=report,
            finding_id="VAL-EVID-001",
            severity="warning",
            category="evidence_consistency",
            title="Missing function summary metrics",
            message="Reconstruction summary is missing functions_total, functions_emitted, or functions_missing.",
            artifact="source_reconstruction.json"
        )
    else:
        if total_fns != len(funcs):
            fn_status = "warning"
            add_finding(
                report=report,
                finding_id="VAL-EVID-002",
                severity="warning",
                category="evidence_consistency",
                title="Function count mismatch",
                message=f"summary.functions_total ({total_fns}) does not match functions list length ({len(funcs)}).",
                artifact="source_reconstruction.json",
                evidence={"summary_total": total_fns, "list_len": len(funcs)}
            )
        if emitted_fns > total_fns:
            fn_status = "warning"
            add_finding(
                report=report,
                finding_id="VAL-EVID-003",
                severity="warning",
                category="evidence_consistency",
                title="Invalid emitted functions count",
                message=f"summary.functions_emitted ({emitted_fns}) is greater than functions_total ({total_fns}).",
                artifact="source_reconstruction.json",
                evidence={"emitted": emitted_fns, "total": total_fns}
            )
        if missing_fns < 0:
            fn_status = "warning"
            add_finding(
                report=report,
                finding_id="VAL-EVID-004",
                severity="warning",
                category="evidence_consistency",
                title="Negative missing functions count",
                message=f"summary.functions_missing is negative ({missing_fns}).",
                artifact="source_reconstruction.json"
            )
            
    add_check(
        report=report,
        name="function_count_consistency",
        status=fn_status,
        severity="warning",
        message="Function counts are consistent." if fn_status == "ok" else "Function counts metadata check has warnings."
    )
    
    # -------------------------------------------------------------------------
    # 2. Lowered Statement Evidence
    # -------------------------------------------------------------------------
    stmt_status = "ok"
    total_statements_checked = 0
    total_provenance_valid = 0
    has_statements = False
    
    for f in funcs:
        lowered_stmts = f.get("lowered_statements") or []
        if lowered_stmts:
            has_statements = True
            for stmt in lowered_stmts:
                # We skip checks for helper/declaration lines
                kind = stmt.get("kind")
                if kind in ("declaration", "helper"):
                    continue
                total_statements_checked += 1
                
                # Check provenance
                ins = stmt.get("source_instruction")
                addr = stmt.get("address")
                
                if not ins or not addr or not kind:
                    stmt_status = "warning"
                    add_finding(
                        report=report,
                        finding_id="VAL-EVID-005",
                        severity="warning",
                        category="evidence_consistency",
                        title="Missing statement level provenance",
                        message=f"Lowered statement of kind '{kind}' at address '{addr}' has missing provenance.",
                        artifact="source_reconstruction.json",
                        location={"function": f.get("name"), "block_id": None, "address": addr, "line": None}
                    )
                else:
                    # Check consistency: statement address matches source instruction address
                    ins_addr = ins.get("address")
                    if ins_addr and ins_addr != addr:
                        stmt_status = "warning"
                        add_finding(
                            report=report,
                            finding_id="VAL-EVID-006",
                            severity="warning",
                            category="evidence_consistency",
                            title="Statement address mismatch",
                            message=f"Statement address '{addr}' does not match source instruction address '{ins_addr}'.",
                            artifact="source_reconstruction.json",
                            location={"function": f.get("name"), "block_id": ins.get("block_id"), "address": addr, "line": None},
                            evidence={"statement_address": addr, "instruction_address": ins_addr}
                        )
                    else:
                        total_provenance_valid += 1
                        
    if not has_statements:
        stmt_status = "warning"
        add_finding(
            report=report,
            finding_id="VAL-EVID-007",
            severity="warning",
            category="evidence_consistency",
            title="Statement-level provenance unavailable",
            message="statement-level provenance not available in artifact; skipped lowered evidence check",
            artifact="source_reconstruction.json"
        )
        
    add_check(
        report=report,
        name="lowered_statement_evidence",
        status=stmt_status,
        severity="warning",
        message="Lowered statement evidence is consistent." if stmt_status == "ok" else "Statement evidence validation has warnings/skipped."
    )
    
    # -------------------------------------------------------------------------
    # 3. Unsupported Accounting
    # -------------------------------------------------------------------------
    unsupported_status = "ok"
    if artifacts.evidence_index is not None:
        add_check(
            report=report,
            name="unsupported_accounting",
            status="ok",
            severity="warning",
            message="Bypassed: precise evidence_index.json is present."
        )
    elif artifacts.recovered_c is not None:
        unsupported_comment_count = len(re.findall(r"\bunsupported\b", artifacts.recovered_c, re.IGNORECASE))
        
        unsupported_kinds = summary.get("unsupported_instruction_kinds", {})
        sum_unsupported_kinds = sum(unsupported_kinds.values()) if isinstance(unsupported_kinds, dict) else 0
        
        if unsupported_comment_count != sum_unsupported_kinds:
            diff = abs(unsupported_comment_count - sum_unsupported_kinds)
            # Large mismatch check
            limit = max(3, int(0.25 * sum_unsupported_kinds))
            is_large = diff > limit
            
            severity = "warning"
            if is_large and strict:
                severity = "error"
                unsupported_status = "failed"
            elif unsupported_status == "ok":
                unsupported_status = "warning"
                
            add_finding(
                report=report,
                finding_id="VAL-EVID-008",
                severity=severity,
                category="unsupported_accounting",
                title="Unsupported comment accounting mismatch",
                message="recovered.c contains unsupported-style comments that do not exactly match unsupported_instruction_kinds. This can happen when conservative comment-lowered instructions are emitted as comments but are not classified as unknown/unsupported instructions in the summary.",
                artifact="recovered.c",
                evidence={
                    "unsupported_comments_in_recovered_c": unsupported_comment_count,
                    "unsupported_instruction_kinds_total": sum_unsupported_kinds,
                    "unsupported_instruction_kinds": unsupported_kinds,
                    "difference": diff,
                    "accounting_note": "unsupported comments and unsupported_instruction_kinds are approximate Phase 6.1 accounting categories"
                },
                recommendation="Keep the finding visible. Phase 6.2 should introduce statement-level evidence categories to distinguish true unsupported instructions from conservative comment-lowered instructions."
            )
            if is_large and strict:
                report["findings"][-1]["strict_promoted"] = True
                
        add_check(
            report=report,
            name="unsupported_accounting",
            status=unsupported_status,
            severity="warning",
            message="Unsupported instruction accounting is consistent." if unsupported_status == "ok" else "Unsupported instruction accounting mismatch found."
        )

    
    # -------------------------------------------------------------------------
    # 4. Call Site Consistency
    # -------------------------------------------------------------------------
    callsite_status = "ok"
    c_total = summary.get("call_sites_total", 0)
    c_direct = summary.get("direct_calls", 0)
    c_indirect = summary.get("indirect_calls", 0)
    c_args = summary.get("calls_with_arguments", 0)
    c_unknown = summary.get("call_arguments_unknown", 0)
    
    # Check 4.1 summary stats
    if c_total < (c_direct + c_indirect):
        callsite_status = "warning"
        add_finding(
            report=report,
            finding_id="VAL-EVID-009",
            severity="warning",
            category="callsite_consistency",
            title="Invalid total call sites count",
            message=f"call_sites_total ({c_total}) is less than direct_calls ({c_direct}) + indirect_calls ({c_indirect}).",
            artifact="source_reconstruction.json",
            evidence={"total": c_total, "direct": c_direct, "indirect": c_indirect}
        )
    if c_args > c_total:
        callsite_status = "warning"
        add_finding(
            report=report,
            finding_id="VAL-EVID-010",
            severity="warning",
            category="callsite_consistency",
            title="Invalid call sites with arguments count",
            message=f"calls_with_arguments ({c_args}) is greater than call_sites_total ({c_total}).",
            artifact="source_reconstruction.json",
            evidence={"args_count": c_args, "total": c_total}
        )
    if c_unknown < 0:
        callsite_status = "warning"
        add_finding(
            report=report,
            finding_id="VAL-EVID-011",
            severity="warning",
            category="callsite_consistency",
            title="Negative unknown call arguments count",
            message=f"call_arguments_unknown is negative ({c_unknown}).",
            artifact="source_reconstruction.json"
        )
        
    # Check 4.2 detailed call sites
    has_detailed_call = False
    for f in funcs:
        cr = f.get("callsite_refinement", {})
        sites = cr.get("sites", [])
        if sites:
            has_detailed_call = True
            for site in sites:
                block_id = site.get("block_id")
                addr = site.get("address")
                orig_text = site.get("original_text")
                kind = site.get("kind")
                target = site.get("target")
                refined_text = site.get("refined_text")
                
                # Check: refined call should have block_id/address or original_text
                if not (block_id or addr) and not orig_text:
                    callsite_status = "warning"
                    add_finding(
                        report=report,
                        finding_id="VAL-EVID-012",
                        severity="warning",
                        category="callsite_consistency",
                        title="Missing metadata for call site",
                        message=f"Call site lacks block_id/address and original_text.",
                        artifact="source_reconstruction.json"
                    )
                    
                # Check: indirect calls should not become fake direct call helpers
                if kind == "indirect":
                    # If target is register like x8, that's fine.
                    # Target should not look like call_0x... or function name unless register.
                    if target and not re.match(r"^(?:tmp_)?(?:[xw]\d+|sp|wzr|xzr|pc|lr)$", target, re.IGNORECASE):
                        callsite_status = "warning"
                        add_finding(
                            report=report,
                            finding_id="VAL-EVID-013",
                            severity="warning",
                            category="callsite_consistency",
                            title="Indirect call resolved to direct function name without evidence",
                            message=f"Indirect call site target resolved to function target '{target}' instead of register.",
                            artifact="source_reconstruction.json",
                            evidence={"target": target, "kind": kind}
                        )
                    # refined_text should not be direct call helper
                    if refined_text and re.search(r"\bcall_[a-zA-Z0-9_]+\s*\(", refined_text) and "indirect call" not in refined_text:
                        callsite_status = "warning"
                        add_finding(
                            report=report,
                            finding_id="VAL-EVID-014",
                            severity="warning",
                            category="callsite_consistency",
                            title="Indirect call emitted as direct call statement",
                            message=f"Indirect call site refined text contains direct call helper syntax: '{refined_text}'.",
                            artifact="source_reconstruction.json",
                            evidence={"refined_text": refined_text}
                        )
                        
    if not has_detailed_call:
        if callsite_status == "ok":
            callsite_status = "warning"
        add_finding(
            report=report,
            finding_id="VAL-EVID-015",
            severity="warning",
            category="callsite_consistency",
            title="Detailed call site evidence missing",
            message="Detailed callsite_refinement.sites list is empty or missing.",
            artifact="source_reconstruction.json"
        )
        
    add_check(
        report=report,
        name="callsite_consistency",
        status=callsite_status,
        severity="warning",
        message="Call site consistency is valid." if callsite_status == "ok" else "Call site validation has warnings/missing evidence."
    )
    
    # -------------------------------------------------------------------------
    # 5. Return Site Consistency
    # -------------------------------------------------------------------------
    return_status = "ok"
    r_total = summary.get("return_sites_total", 0)
    r_val = summary.get("return_sites_with_value", 0)
    r_unknown = summary.get("return_sites_unknown", 0)
    r_fns = summary.get("functions_with_recovered_return_value", 0)
    
    # Check 5.1 summary stats
    if r_val > r_total:
        return_status = "warning"
        add_finding(
            report=report,
            finding_id="VAL-EVID-016",
            severity="warning",
            category="return_consistency",
            title="Invalid return sites with value count",
            message=f"return_sites_with_value ({r_val}) is greater than return_sites_total ({r_total}).",
            artifact="source_reconstruction.json",
            evidence={"val": r_val, "total": r_total}
        )
    if r_unknown > r_total:
        return_status = "warning"
        add_finding(
            report=report,
            finding_id="VAL-EVID-017",
            severity="warning",
            category="return_consistency",
            title="Invalid unknown return sites count",
            message=f"return_sites_unknown ({r_unknown}) is greater than return_sites_total ({r_total}).",
            artifact="source_reconstruction.json",
            evidence={"unknown": r_unknown, "total": r_total}
        )
    if r_fns > len(funcs):
        return_status = "warning"
        add_finding(
            report=report,
            finding_id="VAL-EVID-018",
            severity="warning",
            category="return_consistency",
            title="Invalid functions with recovered return value count",
            message=f"functions_with_recovered_return_value ({r_fns}) exceeds total functions count ({len(funcs)}).",
            artifact="source_reconstruction.json",
            evidence={"recovered_fns": r_fns, "total_fns": len(funcs)}
        )
        
    # Check 5.2 detailed return sites
    has_detailed_ret = False
    for f in funcs:
        rr = f.get("return_recovery", {})
        sites = rr.get("sites", [])
        if sites:
            has_detailed_ret = True
            for site in sites:
                expr = site.get("expression")
                kind = site.get("expression_kind")
                reg = site.get("register")
                
                # Check: return expression should come from ABI return register evidence or documented fallback
                if kind == "register":
                    # expression should match tmp_w0 or tmp_x0 or tmp_<reg>
                    if expr not in ("tmp_w0", "tmp_x0") and (reg and expr != f"tmp_{reg}"):
                        return_status = "warning"
                        add_finding(
                            report=report,
                            finding_id="VAL-EVID-019",
                            severity="warning",
                            category="return_consistency",
                            title="Invalid return register expression",
                            message=f"Return site with kind 'register' uses unexpected expression '{expr}' (expected tmp_w0, tmp_x0, or tmp_{reg}).",
                            artifact="source_reconstruction.json",
                            evidence={"expression": expr, "register": reg}
                        )
                elif kind == "constant":
                    # expression should be integer/hex representation
                    if not expr or not re.match(r"^-?\d+$|^0x[0-9a-fA-F]+$", str(expr)):
                        return_status = "warning"
                        add_finding(
                            report=report,
                            finding_id="VAL-EVID-020",
                            severity="warning",
                            category="return_consistency",
                            title="Invalid return constant expression",
                            message=f"Return site with kind 'constant' has non-constant expression '{expr}'.",
                            artifact="source_reconstruction.json",
                            evidence={"expression": expr}
                        )
                elif kind in ("void", "unknown"):
                    if expr is not None:
                        return_status = "warning"
                        add_finding(
                            report=report,
                            finding_id="VAL-EVID-021",
                            severity="warning",
                            category="return_consistency",
                            title="Unexpected expression for void/unknown return",
                            message=f"Return site with kind '{kind}' has expression '{expr}', expected None.",
                            artifact="source_reconstruction.json",
                            evidence={"expression": expr}
                        )
                        
    if not has_detailed_ret:
        if return_status == "ok":
            return_status = "warning"
        add_finding(
            report=report,
            finding_id="VAL-EVID-022",
            severity="warning",
            category="return_consistency",
            title="Detailed return site evidence missing",
            message="Detailed return_recovery.sites list is empty or missing.",
            artifact="source_reconstruction.json"
        )
        
    add_check(
        report=report,
        name="return_consistency",
        status=return_status,
        severity="warning",
        message="Return site consistency is valid." if return_status == "ok" else "Return site validation has warnings/missing evidence."
    )
