# -*- coding: utf-8 -*-
"""
Stress Test Generator and Harness
"""

from __future__ import annotations
import json
import random
import shutil
import subprocess
from pathlib import Path
from typing import Any

from src.pipeline.runner import run_pipeline
from src.pipeline.checks import run_artifact_checks
from src.pipeline.clang import clang_available, run_clang_syntax_check

def generate_stress_c(profile: str, out_path: Path, seed: int = 1337) -> dict:
    """Generate deterministic C stress input based on seed and profile."""
    random.seed(seed)
    
    if profile == "small":
        num_funcs = random.randint(20, 35)
    elif profile == "medium":
        num_funcs = random.randint(100, 150)
    elif profile == "hard":
        num_funcs = random.randint(300, 400)
    elif profile == "brutal":
        num_funcs = random.randint(600, 800)
    else:
        raise ValueError(f"Unknown stress profile: {profile}")
        
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    lines = []
    lines.append("#include <stdio.h>")
    lines.append("#include <stdint.h>")
    lines.append("#include <stdlib.h>")
    lines.append("")
    
    lines.append("typedef uint64_t (*fptr_t)(uint64_t, uint64_t);")
    lines.append("")
    
    signatures = []
    for i in range(num_funcs):
        name = f"stress_fn_{i}"
        num_args = random.choice([2, 4, 8])
        args = [f"uint64_t a{j}" for j in range(num_args)]
        signatures.append((name, args))
        
    two_arg_funcs = [name for name, args in signatures if len(args) == 2]

    for name, args in signatures:
        lines.append(f"uint64_t {name}({', '.join(args)});")
    lines.append("")
    
    lines.append("static fptr_t fptr_table[4];")
    lines.append("")
    
    for i, (name, args) in enumerate(signatures):
        lines.append(f"uint64_t {name}({', '.join(args)})")
        lines.append("{")
        lines.append("    volatile uint64_t sink = 0;")
        lines.append("    volatile uint32_t stack_arr[8] = {1, 2, 3, 4, 5, 6, 7, 8};")
        lines.append("    uint64_t div_u = a0 / (a1 ? a1 : 1);")
        lines.append("    int64_t div_s = ((int64_t)a0) / (((int64_t)a1) ? ((int64_t)a1) : 1);")
        lines.append("")
        
        body_parts = []
        
        # 1. Division feature
        body_parts.append(
            "    // signed and unsigned division\n"
            "    sink += div_u + div_s;"
        )
        
        # 2. Nested loops
        body_parts.append(
            "    // nested loops\n"
            "    uint64_t loop_sum = 0;\n"
            "    for (int idx1 = 0; idx1 < 3; idx1++) {\n"
            "        for (int idx2 = 0; idx2 < 2; idx2++) {\n"
            "            loop_sum += idx1 * idx2 + stack_arr[idx1 + idx2];\n"
            "        }\n"
            "    }\n"
            "    sink += loop_sum;"
        )
        
        # 3. if/else
        body_parts.append(
            "    // if/else\n"
            "    if (a0 > a1) {\n"
            "        sink += a0 - a1;\n"
            "    } else if (a0 == a1) {\n"
            "        sink += 42;\n"
            "    } else {\n"
            "        sink += a1 - a0;\n"
            "    }"
        )
        
        # 4. Switch-like control flow
        body_parts.append(
            "    // switch-like control flow\n"
            "    switch (a0 % 4) {\n"
            "        case 0: sink += 100; break;\n"
            "        case 1: sink += 200; break;\n"
            "        case 2: sink += 300; break;\n"
            "        default: sink += 400; break;\n"
            "    }"
        )
        
        # 5. Shifted/extended arithmetic
        body_parts.append(
            "    // shifted/extended arithmetic\n"
            "    uint64_t shift_val = a0 + (a1 << 3);\n"
            "    uint64_t ext_val = (uint64_t)(int8_t)(a0 & 0xFF);\n"
            "    sink += shift_val + ext_val;"
        )
        
        # 6. Direct calls
        if i > 0:
            target_idx = random.randint(0, i - 1)
            target_name, target_args = signatures[target_idx]
            passed_args = []
            for _ in range(len(target_args)):
                passed_args.append(random.choice(["a0", "a1", "sink", "10", "div_u"]))
            body_parts.append(
                "    // direct call\n"
                f"    sink += {target_name}({', '.join(passed_args)});"
            )
            
        # 7. Indirect calls
        if i % 5 == 0 and len(two_arg_funcs) > 0:
            limit = min(len(two_arg_funcs), 4)
            body_parts.append(
                "    // indirect call via function pointer\n"
                "    if (fptr_table[0]) {\n"
                f"        sink += fptr_table[a0 % {limit}](a1, a0);\n"
                "    }"
            )
            
        # 8. Printf calls
        if i % 7 == 0:
            body_parts.append(
                "    // printf call\n"
                f'    printf("Stress log: {name} sink=%llu\\n", (unsigned long long)sink);'
            )
            
        random.shuffle(body_parts)
        for part in body_parts:
            lines.append(part)
            lines.append("")
            
        lines.append("    return sink;")
        lines.append("}")
        lines.append("")
        
    lines.append("int main(int argc, char **argv)")
    lines.append("{")
    lines.append("    (void)argc; (void)argv;")
    lines.append("    // Initialize fptr table")
    for idx in range(min(len(two_arg_funcs), 4)):
        lines.append(f"    fptr_table[{idx}] = (fptr_t){two_arg_funcs[idx]};")
    lines.append("    uint64_t total = 0;")
    for idx in range(min(num_funcs, 5)):
        name, args = signatures[idx]
        passed = ", ".join(["10"] * len(args))
        lines.append(f"    total += {name}({passed});")
    lines.append('    printf("Total stress result: %llu\\n", (unsigned long long)total);')
    lines.append("    return 0;")
    lines.append("}")
    lines.append("")
    
    content = "\n".join(lines)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    loc = len(content.splitlines())
    return {
        "profile": profile,
        "seed": seed,
        "source_path": str(out_path),
        "loc": loc,
        "features": [
            "loops",
            "function_pointers",
            "stack_arrays",
            "division",
            "abi_pressure"
        ]
    }

def compile_stress_source(source_path: Path, binary_path: Path) -> dict:
    """Compile generated stress source with clang -O0 -g."""
    if not clang_available():
        return {
            "path": str(binary_path),
            "compiled": False,
            "compile_error": "clang command not found"
        }
    try:
        res = subprocess.run(
            ["clang", "-O0", "-g", str(source_path), "-o", str(binary_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if res.returncode == 0:
            return {
                "path": str(binary_path),
                "compiled": True,
                "compile_error": None
            }
        else:
            return {
                "path": str(binary_path),
                "compiled": False,
                "compile_error": res.stderr
            }
    except Exception as e:
        return {
            "path": str(binary_path),
            "compiled": False,
            "compile_error": str(e)
        }

# (run_clang_syntax_check is now imported from src.pipeline.clang)

def run_stress_test(
    profile: str,
    out_dir: str,
    clean: bool = False,
    seed: int = 1337,
) -> dict:
    """Execute complete stress test suite from generation to decompiler structuring checks."""
    out_dir_path = Path(out_dir).resolve()
    
    if clean:
        from src.utils.artifacts import clean_known_artifacts
        clean_known_artifacts(out_dir_path)
        
    out_dir_path.mkdir(parents=True, exist_ok=True)
    
    input_dir = out_dir_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    
    source_path = input_dir / f"stress_{profile}.c"
    binary_path = input_dir / f"stress_{profile}_bin"
    
    # 1. Generate deterministically
    source_info = generate_stress_c(profile, source_path, seed)
    
    # 2. Compile
    binary_info = compile_stress_source(source_path, binary_path)
    
    # Defaults in case of early compile failure
    pipeline_info = {"status": "skipped", "manifest": None}
    checks_info = {}
    metrics_info = {}
    diagnostics_info = {
        "clang_syntax_check_attempted": False,
        "clang_syntax_check_status": "skipped",
        "clang_syntax_errors": 0,
        "clang_syntax_warnings": 0
    }
    status = "failed"
    
    if binary_info["compiled"]:
        # 3. Run runner pipeline
        manifest = run_pipeline(
            binary_path=str(binary_path),
            out_dir=str(out_dir_path),
            use_ghidra=False,
            use_radare2=True,
            clean=False
        )
        
        pipeline_info["status"] = manifest.get("status", "failed")
        pipeline_info["manifest"] = "pipeline_manifest.json"
        
        # 4. Invariant checks
        checks_info = run_artifact_checks(out_dir_path)
        
        # 5. Clang syntax diagnostic checks
        recovered_c = out_dir_path / "recovered.c"
        clang_res = run_clang_syntax_check(recovered_c)
        if "attempted" in clang_res:
            diagnostics_info = {
                "clang_syntax_check_attempted": clang_res["attempted"],
                "clang_syntax_check_status": clang_res["status"],
                "clang_syntax_errors": clang_res["errors"],
                "clang_syntax_warnings": clang_res["warnings"]
            }
        else:
            diagnostics_info = clang_res
        
        # 6. Extract summary metrics
        metrics_info = manifest.get("summary", {})
        
        # Determine overall stress run status
        pipeline_ok = manifest.get("status") == "ok"
        syntax_ok = diagnostics_info.get("clang_syntax_errors", 0) == 0
        invariants_ok = checks_info.get("condition_expressions_recovered_zero", False) and checks_info.get("recovered_c_nonempty", False)
        
        if pipeline_ok and syntax_ok and invariants_ok:
            status = "ok"
            
    report = {
        "schema_version": "stress-1.0",
        "phase": "5.8",
        "profile": profile,
        "seed": seed,
        "status": status,
        "source": {
            "path": f"input/stress_{profile}.c",
            "loc": source_info["loc"],
            "features": source_info["features"]
        },
        "binary": binary_info,
        "pipeline": pipeline_info,
        "artifact_checks": checks_info,
        "metrics": metrics_info,
        "diagnostics": diagnostics_info
    }
    
    report_path = out_dir_path / "stress_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    return report
