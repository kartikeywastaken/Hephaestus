# -*- coding: utf-8 -*-
"""
Artifact Invariant Checks and Correctness Verification
"""

from __future__ import annotations
import re
import json
from pathlib import Path

def strip_c_comments(text: str) -> str:
    """Remove line and block comments from C code."""
    # Pattern to match /* block comments */ or // line comments
    pattern = r"/\*.*?\*/|//.*?$"
    return re.sub(pattern, "", text, flags=re.DOTALL | re.MULTILINE)

def strip_c_strings(text: str) -> str:
    """Replace string literals in C code with a placeholder string."""
    pattern = r'"(?:[^"\\]|\\.)*"'
    return re.sub(pattern, '"placeholder"', text)

def extract_conditions(text: str) -> list[str]:
    """Extract predicates/conditions inside outermost parentheses of if/while statements."""
    conditions = []
    pos = 0
    while True:
        match = re.search(r"\b(if|while)\s*\(", text[pos:])
        if not match:
            break
        start_idx = pos + match.end() - 1  # index of '('
        depth = 0
        end_idx = -1
        for i in range(start_idx, len(text)):
            if text[i] == '(':
                depth += 1
            elif text[i] == ')':
                depth -= 1
                if depth == 0:
                    end_idx = i
                    break
        if end_idx != -1:
            cond_content = text[start_idx+1:end_idx].strip()
            conditions.append(cond_content)
            pos = end_idx + 1
        else:
            pos = start_idx + 1
    return conditions

def check_required_files(out_dir: Path) -> dict:
    """Verify that all required output files exist in the artifact directory."""
    out_dir = Path(out_dir)
    required = [
        "unified_ir.json",
        "structuring_analysis.json",
        "structuring_regions.json",
        "type_recovery.json",
        "phase4_semantics.json",
        "source_reconstruction.json",
        "recovered.c"
    ]
    missing = []
    for f in required:
        if not (out_dir / f).exists():
            missing.append(f)
    return {
        "required_files_present": len(missing) == 0,
        "missing_files": missing
    }

def check_source_reconstruction(out_dir: Path) -> dict:
    """Extract schema version and condition recovery metrics from reconstruction metadata."""
    out_dir = Path(out_dir)
    recon_path = out_dir / "source_reconstruction.json"
    if not recon_path.exists():
        return {
            "source_schema_version": "unknown",
            "condition_expressions_recovered_zero": False
        }
    try:
        with open(recon_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        schema_version = data.get("schema_version", "unknown")
        summary = data.get("summary", {})
        cond_recovered = summary.get("condition_expressions_recovered", -1)
        return {
            "source_schema_version": schema_version,
            "condition_expressions_recovered_zero": (cond_recovered == 0)
        }
    except Exception:
        return {
            "source_schema_version": "unknown",
            "condition_expressions_recovered_zero": False
        }

def check_recovered_c_safety(out_dir: Path) -> dict:
    """Verify syntactic and security properties of the emitted C code skeleton."""
    out_dir = Path(out_dir)
    c_path = out_dir / "recovered.c"
    if not c_path.exists():
        return {
            "recovered_c_nonempty": False,
            "no_phantom_0x5f5e": False,
            "no_struct_fabrication": False,
            "no_arrow_fields_executable": False,
            "no_empty_conditions": False,
            "no_executable_tmp_conditions": False,
            "no_raw_arm_indexed_leak_executable": False,
            "cset_helper_consistent": False
        }
        
    try:
        with open(c_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
    except Exception:
        raw_text = ""
        
    if not raw_text.strip():
        return {
            "recovered_c_nonempty": False,
            "no_phantom_0x5f5e": False,
            "no_struct_fabrication": False,
            "no_arrow_fields_executable": False,
            "no_empty_conditions": False,
            "no_executable_tmp_conditions": False,
            "no_raw_arm_indexed_leak_executable": False,
            "cset_helper_consistent": False
        }
        
    executable_raw = strip_c_comments(raw_text)
    executable = strip_c_strings(executable_raw)
    
    no_phantom = "0x5f5e" not in executable
    no_struct = not bool(re.search(r"\bstruct\b", executable))
    no_arrow = "->" not in executable
    
    conditions = extract_conditions(executable)
    no_empty = True
    no_exec_tmp = True
    
    for cond in conditions:
        if not cond:
            no_empty = False
        # Match HEPHAESTUS_UNKNOWN_COND("...") which becomes HEPHAESTUS_UNKNOWN_COND("placeholder")
        if not re.match(r"^HEPHAESTUS_UNKNOWN_COND\s*\(\s*\".*\"\s*\)$", cond):
            if any(k in cond for k in ["tmp_", "arg", "stack_"]):
                no_exec_tmp = False
            if cond == "":
                no_empty = False
                
    raw_arm_leak_pattern = r"\[[xw][0-9]+,\s*[xw][0-9]+,\s*(?:LSL|SXTW|UXTW|SXTX|UXTX)"
    no_raw_leak = not bool(re.search(raw_arm_leak_pattern, executable, re.IGNORECASE))
    
    has_cset_calls = "HEPHAESTUS_CSET" in executable
    has_cset_def = "HEPHAESTUS_CSET" in raw_text and "static u64 HEPHAESTUS_CSET" in raw_text
    cset_helper_consistent = (not has_cset_calls) or has_cset_def
    
    return {
        "recovered_c_nonempty": True,
        "no_phantom_0x5f5e": no_phantom,
        "no_struct_fabrication": no_struct,
        "no_arrow_fields_executable": no_arrow,
        "no_empty_conditions": no_empty,
        "no_executable_tmp_conditions": no_exec_tmp,
        "no_raw_arm_indexed_leak_executable": no_raw_leak,
        "cset_helper_consistent": cset_helper_consistent
    }

def run_artifact_checks(out_dir: str | Path) -> dict:
    """Run all correctness checks on the artifact output directory."""
    out_dir = Path(out_dir)
    req = check_required_files(out_dir)
    recon = check_source_reconstruction(out_dir)
    safety = check_recovered_c_safety(out_dir)
    
    return {
        "required_files_present": req["required_files_present"],
        "missing_files": req["missing_files"],
        "source_schema_version": recon["source_schema_version"],
        "recovered_c_nonempty": safety["recovered_c_nonempty"],
        "no_phantom_0x5f5e": safety["no_phantom_0x5f5e"],
        "no_struct_fabrication": safety["no_struct_fabrication"],
        "no_arrow_fields_executable": safety["no_arrow_fields_executable"],
        "no_empty_conditions": safety["no_empty_conditions"],
        "no_executable_tmp_conditions": safety["no_executable_tmp_conditions"],
        "no_raw_arm_indexed_leak_executable": safety["no_raw_arm_indexed_leak_executable"],
        "condition_expressions_recovered_zero": recon["condition_expressions_recovered_zero"],
        "cset_helper_consistent": safety["cset_helper_consistent"]
    }
