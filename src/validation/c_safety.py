# -*- coding: utf-8 -*-
"""
C Safety Checks
"""

from __future__ import annotations
import re
from src.validation.models import ValidationArtifacts
from src.validation.report import add_check, add_finding
from src.pipeline.checks import strip_c_comments, strip_c_strings, extract_conditions

def check_c_safety(artifacts: ValidationArtifacts, report: dict) -> None:
    """Verify recovered.c syntax safety invariants on stripped executable code."""
    if artifacts.recovered_c is None:
        add_check(
            report=report,
            name="recovered_c_nonempty",
            status="skipped",
            severity="error",
            message="Skipped: recovered.c not loaded."
        )
        return
        
    raw_text = artifacts.recovered_c
    
    # 1. recovered_c_nonempty
    nonempty = bool(raw_text.strip())
    if not nonempty:
        add_finding(
            report=report,
            finding_id="VAL-CSAF-001",
            severity="error",
            category="c_safety",
            title="Empty recovered C file",
            message="recovered.c is empty or contains only whitespace.",
            artifact="recovered.c"
        )
    add_check(
        report=report,
        name="recovered_c_nonempty",
        status="ok" if nonempty else "failed",
        severity="error",
        message="recovered.c is non-empty." if nonempty else "recovered.c is empty."
    )
    
    if not nonempty:
        return
        
    # Strip comments and string literals
    executable_raw = strip_c_comments(raw_text)
    executable = strip_c_strings(executable_raw)
    
    # 2. no_phantom_0x5f5e
    no_phantom = "0x5f5e" not in executable
    if not no_phantom:
        add_finding(
            report=report,
            finding_id="VAL-CSAF-002",
            severity="error",
            category="c_safety",
            title="Phantom reference detected",
            message="Executable C code contains reference to phantom 0x5f5e address.",
            artifact="recovered.c",
            recommendation="Do not emit hardcoded phantom markers in C output."
        )
    add_check(
        report=report,
        name="no_phantom_0x5f5e",
        status="ok" if no_phantom else "failed",
        severity="error",
        message="No phantom 0x5f5e found in executable code." if no_phantom else "Found phantom 0x5f5e in executable code."
    )
    
    # 3. no_struct_fabrication
    # Check if 'struct' appears as a keyword in the executable code.
    no_struct = not bool(re.search(r"\bstruct\b", executable))
    if not no_struct:
        add_finding(
            report=report,
            finding_id="VAL-CSAF-003",
            severity="error",
            category="c_safety",
            title="Fabricated structure definition detected",
            message="Executable C code contains a 'struct' keyword/definition.",
            artifact="recovered.c",
            recommendation="Do not fabricate structs. Struct/field recovery is forbidden in this phase."
        )
    add_check(
        report=report,
        name="no_struct_fabrication",
        status="ok" if no_struct else "failed",
        severity="error",
        message="No struct definitions in executable code." if no_struct else "Found struct definition in executable code."
    )
    
    # 4. no_arrow_fields_executable
    no_arrow = "->" not in executable
    if not no_arrow:
        add_finding(
            report=report,
            finding_id="VAL-CSAF-004",
            severity="error",
            category="c_safety",
            title="Fabricated arrow field access detected",
            message="Executable C code contains field access operator '->'.",
            artifact="recovered.c",
            recommendation="Do not emit fake field access pointer dereferences."
        )
    add_check(
        report=report,
        name="no_arrow_fields_executable",
        status="ok" if no_arrow else "failed",
        severity="error",
        message="No arrow pointer dereferences in executable code." if no_arrow else "Found arrow operator -> in executable code."
    )
    
    # 5. no_empty_conditions
    conditions = extract_conditions(executable)
    no_empty = True
    for cond in conditions:
        if not cond.strip():
            no_empty = False
            add_finding(
                report=report,
                finding_id="VAL-CSAF-005",
                severity="error",
                category="c_safety",
                title="Empty condition clause",
                message="Found empty condition expression '()' in if/while.",
                artifact="recovered.c",
                recommendation="Empty conditions are forbidden. Use adapter HEPHAESTUS_UNKNOWN_COND if condition is unknown."
            )
            break
            
    # Also double check with regex for empty statements:
    if no_empty and bool(re.search(r"\b(if|while)\s*\(\s*\)", executable)):
        no_empty = False
        add_finding(
            report=report,
            finding_id="VAL-CSAF-005",
            severity="error",
            category="c_safety",
            title="Empty condition clause",
            message="Found empty condition expression in if/while via regex.",
            artifact="recovered.c"
        )
        
    add_check(
        report=report,
        name="no_empty_conditions",
        status="ok" if no_empty else "failed",
        severity="error",
        message="No empty if/while conditions found." if no_empty else "Empty conditions found in if/while."
    )
    
    # 6. no_executable_tmp_conditions
    no_exec_tmp = True
    for cond in conditions:
        cond_stripped = cond.strip()
        # Allow HEPHAESTUS_UNKNOWN_COND adapter
        if re.match(r"^HEPHAESTUS_UNKNOWN_COND\s*\(\s*\".*\"\s*\)$", cond_stripped) or \
           re.match(r"^HEPHAESTUS_UNKNOWN_COND\s*\(\s*\"placeholder\"\s*\)$", cond_stripped):
            continue
        
        # Check if condition contains tmp_, arg, or stack_
        if any(k in cond_stripped for k in ("tmp_", "arg", "stack_")):
            no_exec_tmp = False
            add_finding(
                report=report,
                finding_id="VAL-CSAF-006",
                severity="error",
                category="c_safety",
                title="Fake executable condition detected",
                message=f"Condition '{cond}' contains forbidden variables (tmp_/arg/stack_).",
                artifact="recovered.c",
                evidence={"condition": cond},
                recommendation="Do not emit executable recovered conditions. Use HEPHAESTUS_UNKNOWN_COND adapters."
            )
            break
            
    add_check(
        report=report,
        name="no_executable_tmp_conditions",
        status="ok" if no_exec_tmp else "failed",
        severity="error",
        message="No fake executable conditions (tmp_/arg/stack_) found." if no_exec_tmp else "Fake executable conditions found."
    )
    
    # 7. no_raw_arm_indexed_leak_executable
    # Match patterns like: [x9, x10, LSL #0x2] or [x9,x10,SXTW]
    raw_arm_leak_pattern = r"\[[xw]\d+,\s*[xw]\d+,\s*(?:LSL|SXTW|UXTW|SXTX|UXTX|LSL\s*#)"
    no_raw_leak = not bool(re.search(raw_arm_leak_pattern, executable, re.IGNORECASE))
    if not no_raw_leak:
        add_finding(
            report=report,
            finding_id="VAL-CSAF-007",
            severity="error",
            category="c_safety",
            title="Raw ARM indexed leak in executable code",
            message="Executable C code contains raw bracketed ARM indexing expressions.",
            artifact="recovered.c",
            recommendation="Ensure ARM memory operand lowerer cleans bracket notation from C source."
        )
    add_check(
        report=report,
        name="no_raw_arm_indexed_leak_executable",
        status="ok" if no_raw_leak else "failed",
        severity="error",
        message="No raw ARM indexing leaks in executable code." if no_raw_leak else "Raw ARM indexing leaks found."
    )
    
    # 8. no_fake_flag_variables
    # Forbidden flag variables: tmp_flags_, flag_z, flag_n, flag_c, flag_v
    flag_pattern = r"\btmp_flags_[a-zA-Z0-9_]*\b|\bflag_z\b|\bflag_n\b|\bflag_c\b|\bflag_v\b"
    no_flags = not bool(re.search(flag_pattern, executable))
    if not no_flags:
        add_finding(
            report=report,
            finding_id="VAL-CSAF-008",
            severity="error",
            category="c_safety",
            title="Fake flag variable detected",
            message="Executable C code references flag registers (e.g. tmp_flags_, flag_z, etc.).",
            artifact="recovered.c",
            recommendation="Do not emit fake flag variables. Flags are not modeled in this phase."
        )
    add_check(
        report=report,
        name="no_fake_flag_variables",
        status="ok" if no_flags else "failed",
        severity="error",
        message="No fake flag variables in executable code." if no_flags else "Fake flag variables found in executable code."
    )
