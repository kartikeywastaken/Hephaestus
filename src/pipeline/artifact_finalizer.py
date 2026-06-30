# -*- coding: utf-8 -*-
"""
Artifact Finalization Layer
"""

from __future__ import annotations
import json
import shutil
import logging
from pathlib import Path

logger = logging.getLogger("reconstruct.finalizer")

def finalize_artifacts(
    out_dir: Path | str,
    *,
    work_dir: Path | str | None = None,
    artifact_mode: str = "flat",
    binary_path: str | None = None,
) -> dict:
    """
    Finalize artifacts:
    1. Read intermediate files from artifacts/.work/
    2. Copy final C outputs to artifacts/
    3. Build hephaestus_report.json
    4. Write hephaestus_report.json to artifacts/
    5. If artifact_mode=flat and finalization succeeds, delete artifacts/.work/
    """
    out_dir = Path(out_dir).resolve()
    if work_dir is None:
        work_dir = out_dir / ".work"
    work_dir = Path(work_dir).resolve()

    # Safely ensure output directory exists
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy final C outputs if they exist in work_dir
    c_files = ["recovered.c", "recovered_readable.c", "recovered_agent.c"]
    for filename in c_files:
        src_path = work_dir / filename
        dst_path = out_dir / filename
        if src_path.exists() and src_path.is_file():
            try:
                shutil.copy2(src_path, dst_path)
            except Exception as e:
                logger.error(f"Failed to copy final output {filename}: {e}")

    # Build files dictionary mapping to loaded JSON data
    def load_json(name: str) -> dict:
        p = work_dir / name
        if p.exists() and p.is_file():
            try:
                with p.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load JSON {name}: {e}")
        return {}

    source_reconstruction = load_json("source_reconstruction.json")
    unified_ir = load_json("unified_ir.json")
    dynamic_runs = load_json("dynamic_runs.json")
    adaptive_dynamic_runs = load_json("adaptive_dynamic_runs.json")
    input_influence_report = load_json("input_influence_report.json")
    dynamic_exploration_report = load_json("dynamic_exploration_report.json")
    behavior_profile = load_json("behavior_profile.json")
    behavior_fusion_report = load_json("behavior_fusion_report.json")
    behavior_model = load_json("behavior_model.json")
    agent_packet_manifest = load_json("agent_packet_manifest.json")
    agent_packet_optimization_report = load_json("agent_packet_optimization_report.json")
    agent_debate_report = load_json("agent_debate_report.json")
    agent_suggestions = load_json("agent_suggestions.json")
    agent_source_report = load_json("agent_source_report.json")
    agent_source_validation = load_json("agent_source_validation.json")
    validation_report = load_json("validation_report.json")
    pipeline_manifest = load_json("pipeline_manifest.json")

    # Compute binary sha256
    binary_sha = None
    binary_filename = "./t"
    if binary_path:
        binary_p = Path(binary_path)
        binary_filename = str(binary_path)
        import hashlib
        if binary_p.exists() and binary_p.is_file():
            h = hashlib.sha256()
            try:
                with binary_p.open("rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        h.update(chunk)
                binary_sha = h.hexdigest()
            except Exception:
                pass

    # Extract static
    static_summary = source_reconstruction.get("summary", {})
    arch = None
    if unified_ir:
        arch = (
            unified_ir.get("provenance", {}).get("architecture")
            or unified_ir.get("metadata", {}).get("architecture")
        )
    static_section = {
        "functions": static_summary.get("functions_total", 0),
        "structured": static_summary.get("functions_structured", 0),
        "partial": static_summary.get("functions_partially_structured", 0),
        "unstructured": static_summary.get("functions_unstructured", 0),
        "architecture": arch
    }

    # Extract dynamic
    initial_cases = dynamic_runs.get("runs", [])
    if not isinstance(initial_cases, list):
        initial_cases = []
    adaptive_cases = adaptive_dynamic_runs.get("runs", [])
    if not isinstance(adaptive_cases, list):
        adaptive_cases = []

    completed = 0
    timeouts = 0
    crashes = 0
    for r in initial_cases + adaptive_cases:
        if r.get("status") == "ok":
            completed += 1
        if r.get("timed_out") or r.get("timeout"):
            timeouts += 1
        if r.get("signal") is not None or r.get("crash") or r.get("exit_code") == -1:
            crashes += 1

    initial_runs_cnt = len(initial_cases) if initial_cases else dynamic_runs.get("runs_total", 0)
    adaptive_runs_cnt = len(adaptive_cases) if adaptive_cases else adaptive_dynamic_runs.get("runs_total", 0)

    argv_sensitive = bool(
        input_influence_report.get("argv_sensitive")
        or behavior_profile.get("summary", {}).get("argv_sensitive")
        or dynamic_exploration_report.get("argv_sensitive")
    )
    stdout_varies = bool(behavior_profile.get("summary", {}).get("stdout_varies", False))
    stderr_varies = bool(behavior_profile.get("summary", {}).get("stderr_varies", False))
    exit_code_varies = bool(
        len(behavior_profile.get("summary", {}).get("distinct_exit_codes", [])) > 1
        or input_influence_report.get("exit_code_varies", False)
    )

    dynamic_section = {
        "initial_runs": initial_runs_cnt,
        "adaptive_runs": adaptive_runs_cnt,
        "runs_completed": completed,
        "timeouts": timeouts,
        "crashes": crashes,
        "argv_sensitive": argv_sensitive,
        "stdout_varies": stdout_varies,
        "stderr_varies": stderr_varies,
        "exit_code_varies": exit_code_varies
    }

    # Extract behavior fusion
    fusion_summary = behavior_model.get("summary", {})
    # has_dynamic: check fusion summary OR direct presence of completed runs
    has_dynamic_from_fusion = bool(fusion_summary.get("functions_with_dynamic_evidence", 0) > 0)
    has_dynamic_from_runs = bool(
        any(r.get("status") == "ok" or r.get("exit_code") is not None for r in initial_cases + adaptive_cases)
        if (initial_cases or adaptive_cases) else False
    )
    has_dynamic = has_dynamic_from_fusion or has_dynamic_from_runs
    fusion_section = {
        "status": behavior_fusion_report.get("status"),
        "functions": fusion_summary.get("functions_total", 0),
        "has_dynamic": has_dynamic,
        "hypotheses": fusion_summary.get("hypotheses_total", 0),
        "global_behavior": fusion_summary.get("global_behavior_observations", 0)
    }

    # Extract agent
    agent_section = {
        "provider": agent_debate_report.get("provider") or agent_packet_optimization_report.get("provider"),
        "model": agent_debate_report.get("model") or agent_packet_optimization_report.get("model"),
        "packet_mode": agent_packet_optimization_report.get("packet_mode"),
        "packets_total": agent_packet_manifest.get("packets_total", 0),
        "packets_optimized": agent_packet_optimization_report.get("packets_optimized", 0),
        "packets_skipped_library": agent_packet_optimization_report.get("packets_skipped_library", 0),
        "total_original_chars": agent_packet_optimization_report.get("total_original_chars", 0),
        "total_compact_chars": agent_packet_optimization_report.get("total_compact_chars", 0),
        "functions_reviewed": agent_debate_report.get("functions_reviewed", 0),
        "functions_failed": agent_debate_report.get("functions_failed", 0),
        "suggestions_total": agent_debate_report.get("suggestions_total", 0)
    }

    # Extract source_generation
    source_gen_section = {
        "functions_generated": agent_source_report.get("functions_generated", 0),
        "functions_copied_unchanged": agent_source_report.get("functions_copied_unchanged", 0),
        "functions_failed": agent_source_report.get("functions_failed", 0),
        "functions_fallback": agent_source_report.get("functions_fallback", 0),
        "metadata_suggestions_ignored": agent_source_report.get("metadata_suggestions_ignored", 0)
    }

    # Extract validation
    agent_val_passed = agent_source_validation.get("validation_passed")
    clang_status = agent_source_validation.get("clang_status")
    val_issues = []
    if agent_source_validation.get("issues"):
        val_issues.extend(agent_source_validation.get("issues"))
    if validation_report.get("findings"):
        for f in validation_report.get("findings", []):
            msg = f.get("message")
            if msg:
                val_issues.append(f"static: {msg}")

    # Scan for forbidden claims in outputs (claim-context phrases only)
    forbidden_patterns = [
        "same behavior as original",
        "semantically equivalent",
        "semantic equivalence proven",
        "exact original variable names",
        "exact original struct field names",
        "guaranteed equivalent",
        "fully equivalent",
        "identical to original",
        "full behavioral equivalence",
    ]
    forbidden_claims_found = []
    seen_lines = set()
    for filename in c_files:
        file_path = out_dir / filename
        if file_path.exists() and file_path.is_file():
            try:
                content = file_path.read_text(encoding="utf-8")
                for line_no, line in enumerate(content.splitlines(), 1):
                    line_lower = line.lower()
                    for pat in forbidden_patterns:
                        if pat in line_lower:
                            entry = f"{filename}:{line_no}: {line.strip()}"
                            if entry not in seen_lines:
                                seen_lines.add(entry)
                                forbidden_claims_found.append(entry)
                            break  # one finding per line
            except Exception:
                pass

    validation_section = {
        "agent_source_validation_passed": agent_val_passed,
        "clang_status": clang_status,
        "forbidden_claims_found": forbidden_claims_found,
        "issues": val_issues
    }

    # Determine status
    pipeline_status = pipeline_manifest.get("status", "ok")
    status = "ok"
    if pipeline_status == "failed" or len(forbidden_claims_found) > 0:
        status = "failed"
    elif (
        agent_val_passed is False
        or clang_status in ("failed", "error")
        or source_gen_section.get("functions_failed", 0) > 0
        or pipeline_status in ("warning", "partial")
    ):
        status = "warning"

    # Diagnostics & Ordering bug detection
    diagnostics = []
    # If recovered_agent.c is absent, explain why
    stages_run = [s.get("name") for s in pipeline_manifest.get("stages", [])]
    if "generate_agent_source" not in stages_run and not (out_dir / "recovered_agent.c").exists():
        diagnostics.append("outputs/recovered_agent.c was not produced because agent source generation was skipped or failed before writing.")

    # Check ordering bug
    suggestions_targeted = []
    for s in agent_suggestions.get("suggestions", []):
        func = s.get("function")
        if func:
            suggestions_targeted.append(func)
    
    copied_unchanged = []
    generated = []
    for r in agent_source_report.get("function_records", []):
        func = r.get("function")
        status_rec = r.get("status")
        if status_rec == "copied_unchanged" or r.get("copied_unchanged", False):
            copied_unchanged.append(func)
        elif status_rec == "generated" or r.get("generated", False):
            generated.append(func)

    bug_detected = False
    for func in suggestions_targeted:
        if func in copied_unchanged and len(generated) > 0 and func not in generated:
            bug_detected = True
            break
    if bug_detected:
        diagnostics.append("Agent source generation target mismatch detected: debate target differs from generated function.")

    # Diagnostic: dynamic runs exist but fusion did not flag has_dynamic
    if has_dynamic_from_runs and not has_dynamic_from_fusion:
        diagnostics.append(
            "Dynamic runs detected in artifacts but behavior_model.json did not report functions_with_dynamic_evidence. "
            "has_dynamic set to true from run artifacts."
        )

    # Build outputs paths relative to out_dir
    outputs_shape = {
        "recovered": "recovered.c" if (out_dir / "recovered.c").exists() else None,
        "readable": "recovered_readable.c" if (out_dir / "recovered_readable.c").exists() else None,
        "agent": "recovered_agent.c" if (out_dir / "recovered_agent.c").exists() else None
    }

    report = {
        "schema_version": "hephaestus-report-1.0",
        "phase": "11.8",
        "status": status,
        "binary": {
            "path": binary_filename,
            "sha256": binary_sha
        },
        "artifact_mode": artifact_mode,
        "outputs": outputs_shape,
        "static": static_section,
        "dynamic": dynamic_section,
        "behavior_fusion": fusion_section,
        "agent": agent_section,
        "source_generation": source_gen_section,
        "validation": validation_section,
        "diagnostics": diagnostics
    }

    # Write report file
    report_path = out_dir / "hephaestus_report.json"
    try:
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
            f.write("\n")
        logger.info(f"Consolidated report written to {report_path}")
    except Exception as e:
        logger.error(f"Failed to write consolidated report: {e}")

    # Delete or preserve .work directory
    if artifact_mode == "flat":
        # Delete only if C outputs were copied and report written successfully
        if report_path.exists() and ((out_dir / "recovered.c").exists() or (out_dir / "recovered_readable.c").exists()):
            try:
                if work_dir.name == ".work" and work_dir.exists():
                    shutil.rmtree(work_dir)
                    logger.info(f"Cleaned up work directory: {work_dir}")
            except Exception as e:
                logger.warning(f"Failed to delete work directory {work_dir}: {e}")
        else:
            logger.warning("Postponing work directory cleanup: missing critical final outputs.")
    else:
        logger.info(f"Preserving work directory: {work_dir} (debug mode)")

    return report
