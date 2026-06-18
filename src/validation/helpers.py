# -*- coding: utf-8 -*-
"""
Helper Consistency Checks
"""

from __future__ import annotations
import re
from src.validation.models import ValidationArtifacts
from src.validation.report import add_check, add_finding
from src.pipeline.checks import strip_c_comments, strip_c_strings

def check_helpers(artifacts: ValidationArtifacts, report: dict) -> None:
    """Validate helper functions presence, call definitions, and metrics."""
    strict = report.get("strict", False)
    
    if artifacts.recovered_c is None:
        for name in ("unknown_cond_helper_consistent", "cset_helper_consistent", "reserved_helpers_not_declared_as_call_helpers"):
            add_check(report=report, name=name, status="skipped", severity="error", message="Skipped: recovered.c not loaded.")
        return
        
    raw_text = artifacts.recovered_c
    executable_raw = strip_c_comments(raw_text)
    executable = strip_c_strings(executable_raw)
    
    # 1. Define helper definition search patterns
    has_unknown_cond_def = bool(re.search(r"\bstatic\s+int\s+HEPHAESTUS_UNKNOWN_COND\b", raw_text))
    has_cset_def = bool(re.search(r"\bstatic\s+u64\s+HEPHAESTUS_CSET\b", raw_text))
    
    # 2. Count helper calls (excluding the definition itself)
    # We search in executable for call matches like: HEPHAESTUS_UNKNOWN_COND(...) or HEPHAESTUS_UNKNOWN_COND ( ... )
    unknown_cond_total_matches = len(re.findall(r"\bHEPHAESTUS_UNKNOWN_COND\b", executable))
    # If definition exists in executable, decrement usage count by 1 (since definition uses the identifier)
    unknown_cond_def_matches_in_exec = len(re.findall(r"\bHEPHAESTUS_UNKNOWN_COND\b", strip_c_strings(strip_c_comments(
        "static int HEPHAESTUS_UNKNOWN_COND" if has_unknown_cond_def else ""
    ))))
    unknown_cond_usage_count = max(0, unknown_cond_total_matches - unknown_cond_def_matches_in_exec)
    
    cset_total_matches = len(re.findall(r"\bHEPHAESTUS_CSET\b", executable))
    cset_def_matches_in_exec = len(re.findall(r"\bHEPHAESTUS_CSET\b", strip_c_strings(strip_c_comments(
        "static u64 HEPHAESTUS_CSET" if has_cset_def else ""
    ))))
    cset_usage_count = max(0, cset_total_matches - cset_def_matches_in_exec)
    
    # 3. Check: unknown_cond_helper_consistent
    unknown_cond_consistent = True
    if unknown_cond_usage_count > 0 and not has_unknown_cond_def:
        unknown_cond_consistent = False
        add_finding(
            report=report,
            finding_id="VAL-HELP-001",
            severity="error",
            category="helper_consistency",
            title="Missing HEPHAESTUS_UNKNOWN_COND definition",
            message=f"HEPHAESTUS_UNKNOWN_COND is used {unknown_cond_usage_count} times, but its static definition is missing.",
            artifact="recovered.c",
            recommendation="Emit the 'static int HEPHAESTUS_UNKNOWN_COND' adapter definition."
        )
        
    add_check(
        report=report,
        name="unknown_cond_helper_consistent",
        status="ok" if unknown_cond_consistent else "failed",
        severity="error",
        message="HEPHAESTUS_UNKNOWN_COND helper is consistent." if unknown_cond_consistent else "HEPHAESTUS_UNKNOWN_COND helper definition missing but used."
    )
    
    # 4. Check: cset_helper_consistent
    cset_consistent = True
    if cset_usage_count > 0 and not has_cset_def:
        cset_consistent = False
        add_finding(
            report=report,
            finding_id="VAL-HELP-002",
            severity="error",
            category="helper_consistency",
            title="Missing HEPHAESTUS_CSET definition",
            message=f"HEPHAESTUS_CSET is used {cset_usage_count} times, but its static definition is missing.",
            artifact="recovered.c",
            recommendation="Emit the 'static u64 HEPHAESTUS_CSET' adapter definition."
        )
        
    add_check(
        report=report,
        name="cset_helper_consistent",
        status="ok" if cset_consistent else "failed",
        severity="error",
        message="HEPHAESTUS_CSET helper is consistent." if cset_consistent else "HEPHAESTUS_CSET helper definition missing but used."
    )
    
    # 5. Check: reserved_helpers_not_declared_as_call_helpers
    # Forbidden call_ prefix helpers in C declarations or definition names
    has_call_unknown_cond = bool(re.search(r"\bcall_HEPHAESTUS_UNKNOWN_COND\b", executable))
    has_call_cset = bool(re.search(r"\bcall_HEPHAESTUS_CSET\b", executable))
    call_helpers_safe = not (has_call_unknown_cond or has_call_cset)
    
    if not call_helpers_safe:
        add_finding(
            report=report,
            finding_id="VAL-HELP-003",
            severity="error",
            category="helper_consistency",
            title="Reserved helper declared as call helper",
            message="Found call_HEPHAESTUS_UNKNOWN_COND or call_HEPHAESTUS_CSET declaration/call.",
            artifact="recovered.c",
            evidence={"call_HEPHAESTUS_UNKNOWN_COND": has_call_unknown_cond, "call_HEPHAESTUS_CSET": has_call_cset},
            recommendation="Do not emit call_ prefix declarations for reserved internal syntax helpers."
        )
        
    add_check(
        report=report,
        name="reserved_helpers_not_declared_as_call_helpers",
        status="ok" if call_helpers_safe else "failed",
        severity="error",
        message="Reserved helpers are not declared with call_ prefix." if call_helpers_safe else "Found reserved helpers declared with call_ prefix."
    )
    
    # 6. Check metric consistency if summary is available
    if artifacts.source_reconstruction is not None:
        summary = artifacts.source_reconstruction.get("summary", {})
        
        # unknown_condition_helpers_emitted metric check
        emitted_metric = summary.get("unknown_condition_helpers_emitted", 0)
        expected_metric = 1 if has_unknown_cond_def else 0
        if emitted_metric != expected_metric:
            sev = "error" if strict else "warning"
            add_finding(
                report=report,
                finding_id="VAL-HELP-004",
                severity=sev,
                category="helper_consistency",
                title="unknown_condition_helpers_emitted metric mismatch",
                message=f"Metadata report emitted={emitted_metric}, but actual presence was {expected_metric}.",
                artifact="source_reconstruction.json",
                evidence={"observed": emitted_metric, "expected": expected_metric}
            )
            if strict:
                report["findings"][-1]["strict_promoted"] = True
                
        # cset_helper_emitted metric check
        cset_metric = summary.get("cset_helper_emitted", 0)
        expected_cset_metric = 1 if has_cset_def else 0
        if cset_metric != expected_cset_metric:
            sev = "error" if strict else "warning"
            add_finding(
                report=report,
                finding_id="VAL-HELP-005",
                severity=sev,
                category="helper_consistency",
                title="cset_helper_emitted metric mismatch",
                message=f"Metadata report emitted={cset_metric}, but actual presence was {expected_cset_metric}.",
                artifact="source_reconstruction.json",
                evidence={"observed": cset_metric, "expected": expected_cset_metric}
            )
            if strict:
                report["findings"][-1]["strict_promoted"] = True
