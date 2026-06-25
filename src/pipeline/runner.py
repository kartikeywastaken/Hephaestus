# -*- coding: utf-8 -*-
"""
One-Shot Hephaestus Pipeline Runner
"""

from __future__ import annotations
import os
import json
import time
import logging
from pathlib import Path
from typing import Any

from src.utils.artifact_io import load_json_artifact, write_json_artifact
from src.pipeline.manifest import start_manifest, record_stage, finalize_manifest, write_manifest, now_iso
from src.pipeline.stage_defs import PIPELINE_STAGES

# Pipeline Imports
from src.engine.orchestrator import PipelineOrchestrator
from src.ir.assembler import IRAssembler
from src.ir.validator import IRValidator
from src.ir.symbols.aliases import apply_function_aliases_to_ir
from src.ir.structuring.analysis import analyze_function
from src.ir.structuring.builder import structure_function
from src.ir.types.inference import recover_types
from src.ir.types.emitter import write_type_recovery_artifact
from src.ir.types.refinement_engine import TypeRefinementEngine
from src.ir.types.semantic_emitter import write_semantic_recovery_artifact
from src.ir.types.layout_recovery import LayoutRecoveryEngine
from src.ir.types.layout_emitter import write_layout_recovery_artifact
from src.ir.types.phase4_semantics import build_phase4_semantics
from src.ir.types.phase4_emitter import write_phase4_semantics_artifact
from src.ir.source.reconstructor import build_source_reconstruction
from src.ir.source.emitter import write_source_reconstruction_artifact
from src.ir.source.c_emitter import emit_recovered_c

logger = logging.getLogger("reconstruct")

class PipelineError(Exception):
    """Pipeline execution exception."""
    pass

def run_stage_extract(binary_path: str, out_dir: str, use_ghidra: bool, use_radare2: bool) -> list[str]:
    """Execute Phase 1 Extraction and Phase 2 Unified IR Assembly."""
    if not (use_ghidra or use_radare2):
        raise PipelineError("At least one extractor: --ghidra or --radare2 must be selected")
    
    orchestrator = PipelineOrchestrator(binary_path, out_dir, {})
    manifest = orchestrator.execute_all(
        run_ghidra=use_ghidra,
        run_radare2=use_radare2,
        run_trace=False
    )
    
    if manifest.get("status") == "failed":
        errors_str = "; ".join(manifest.get("errors", []))
        raise PipelineError(f"Extraction failed: {errors_str}")
        
    assembler = IRAssembler(binary_path)
    ghidra_raw = manifest["jobs"].get("ghidra")
    radare2_raw = manifest["jobs"].get("radare2")
    
    unified_ir = assembler.assemble(ghidra_raw, radare2_raw, None)
    ir_payload = unified_ir.to_dict()
    apply_function_aliases_to_ir(ir_payload)
    
    # Self check validation
    success, val_msg = IRValidator.validate_payload(ir_payload)
    if not success:
        logger.warning(f"Generated IR failed schema de-serialization selfcheck: {val_msg}")
        
    ir_path = os.path.join(out_dir, "unified_ir.json")
    write_json_artifact(ir_path, ir_payload)
    
    outputs = ["unified_ir.json"]
    if use_ghidra:
        outputs.append("ghidra_extraction.json")
    if use_radare2:
        outputs.append("radare2_extraction.json")
    return outputs

def run_stage_analyze_cfg(out_dir: str) -> list[str]:
    """Execute Phase 3 CFG Analysis and Region Structuring."""
    ir_path = os.path.join(out_dir, "unified_ir.json")
    if not os.path.exists(ir_path):
        raise PipelineError(f"Missing required input unified_ir.json at {ir_path}")
        
    ir_payload = load_json_artifact(ir_path)
    funcs = ir_payload.get("data", {}).get("functions", [])
    analysis_reports = []
    structuring_reports = []
    
    for func in funcs:
        report = analyze_function(func, logger)
        analysis_reports.append(report)
        
        structured_tree = structure_function(func, logger)
        structuring_reports.append({
            "function_name": func.get("name", "unknown"),
            "structured_body": structured_tree.to_dict()
        })
        
    structuring_path = os.path.join(out_dir, "structuring_analysis.json")
    write_json_artifact(structuring_path, analysis_reports)
    
    regions_path = os.path.join(out_dir, "structuring_regions.json")
    write_json_artifact(regions_path, structuring_reports)
    
    return ["structuring_analysis.json", "structuring_regions.json"]

def run_stage_recover_semantics(out_dir: str) -> list[str]:
    """Execute Phase 4A Signature and Variable Recovery."""
    ir_path = os.path.join(out_dir, "unified_ir.json")
    if not os.path.exists(ir_path):
        raise PipelineError(f"Missing required input unified_ir.json at {ir_path}")
        
    ir_payload = load_json_artifact(ir_path)
    
    structuring_regions = None
    regions_path = os.path.join(out_dir, "structuring_regions.json")
    if os.path.exists(regions_path):
        try:
            structuring_regions = load_json_artifact(regions_path)
            if not isinstance(structuring_regions, list):
                structuring_regions = None
        except Exception:
            structuring_regions = None
            
    functions = recover_types(ir_payload, structuring_regions)
    
    output_path = os.path.join(out_dir, "type_recovery.json")
    write_type_recovery_artifact(functions, output_path, ir_path, regions_path if structuring_regions else None)
    return ["type_recovery.json"]

def run_stage_refine_semantics(out_dir: str) -> list[str]:
    """Execute Phase 4B Type Constraint Refinement."""
    ir_path = os.path.join(out_dir, "unified_ir.json")
    tr_path = os.path.join(out_dir, "type_recovery.json")
    if not os.path.exists(ir_path) or not os.path.exists(tr_path):
        raise PipelineError("Missing required inputs unified_ir.json or type_recovery.json")
        
    unified_ir = load_json_artifact(ir_path)
    type_recovery = load_json_artifact(tr_path)
    
    structuring_regions = None
    regions_path = os.path.join(out_dir, "structuring_regions.json")
    if os.path.exists(regions_path):
        try:
            structuring_regions = load_json_artifact(regions_path)
        except Exception:
            pass
            
    layout_recovery = None
    layout_path = os.path.join(out_dir, "layout_recovery.json")
    if os.path.exists(layout_path):
        try:
            layout_recovery = load_json_artifact(layout_path)
        except Exception:
            pass
            
    engine = TypeRefinementEngine()
    results = engine.refine(
        unified_ir, type_recovery, structuring_regions,
        layout_recovery=layout_recovery,
    )
    
    output_path = os.path.join(out_dir, "semantic_recovery.json")
    write_semantic_recovery_artifact(
        results, output_path,
        source_ir=ir_path,
        source_type_recovery=tr_path,
        source_structuring=regions_path if structuring_regions else None,
    )
    return ["semantic_recovery.json"]

def run_stage_recover_layouts(out_dir: str) -> list[str]:
    """Execute Phase 4C Conservative Data Layout Recovery."""
    ir_path = os.path.join(out_dir, "unified_ir.json")
    if not os.path.exists(ir_path):
        raise PipelineError(f"Missing required input unified_ir.json at {ir_path}")
        
    unified_ir = load_json_artifact(ir_path)
    
    engine = LayoutRecoveryEngine()
    candidates, unbound = engine.recover(unified_ir)
    
    output_path = os.path.join(out_dir, "layout_recovery.json")
    write_layout_recovery_artifact(candidates, unbound, output_path, source_ir=ir_path)
    return ["layout_recovery.json"]

def run_stage_finalize_semantics(out_dir: str) -> list[str]:
    """Execute Phase 4D Semantic Artifact Merger."""
    tr_path = os.path.join(out_dir, "type_recovery.json")
    if not os.path.exists(tr_path):
        raise PipelineError(f"Missing required input type_recovery.json at {tr_path}")
        
    type_recovery = load_json_artifact(tr_path)
    
    semantic_recovery = None
    sr_path = os.path.join(out_dir, "semantic_recovery.json")
    if os.path.exists(sr_path):
        try:
            semantic_recovery = load_json_artifact(sr_path)
        except Exception:
            pass
            
    layout_recovery = None
    lr_path = os.path.join(out_dir, "layout_recovery.json")
    if os.path.exists(lr_path):
        try:
            layout_recovery = load_json_artifact(lr_path)
        except Exception:
            pass
            
    artifact = build_phase4_semantics(
        type_recovery,
        semantic_recovery=semantic_recovery,
        layout_recovery=layout_recovery,
        source_type_recovery=tr_path,
        source_semantic_recovery=sr_path if semantic_recovery else None,
        source_layout_recovery=lr_path if layout_recovery else None,
    )
    
    output_path = os.path.join(out_dir, "phase4_semantics.json")
    write_phase4_semantics_artifact(
        artifact, output_path,
        source_type_recovery=tr_path,
        source_semantic_recovery=sr_path if semantic_recovery else None,
        source_layout_recovery=lr_path if layout_recovery else None,
    )
    return ["phase4_semantics.json"]

def run_stage_reconstruct_source(out_dir: str) -> list[str]:
    """Execute Phase 5 Source Reconstruction."""
    ir_path = os.path.join(out_dir, "unified_ir.json")
    regions_path = os.path.join(out_dir, "structuring_regions.json")
    sem_path = os.path.join(out_dir, "phase4_semantics.json")
    if not os.path.exists(ir_path) or not os.path.exists(regions_path) or not os.path.exists(sem_path):
        raise PipelineError("Missing required inputs unified_ir.json, structuring_regions.json, or phase4_semantics.json")
        
    unified_ir = load_json_artifact(ir_path)
    structuring_regions = load_json_artifact(regions_path)
    phase4_semantics = load_json_artifact(sem_path)
    
    layout_recovery = None
    lr_path = os.path.join(out_dir, "layout_recovery.json")
    if os.path.exists(lr_path):
        try:
            layout_recovery = load_json_artifact(lr_path)
        except Exception:
            pass
            
    artifact = build_source_reconstruction(
        unified_ir, structuring_regions, phase4_semantics,
        layout_recovery=layout_recovery,
    )
    
    c_path = os.path.join(out_dir, "recovered.c")
    emit_recovered_c(artifact, c_path)
    
    recon_path = os.path.join(out_dir, "source_reconstruction.json")
    write_source_reconstruction_artifact(
        artifact, recon_path,
        source_ir=ir_path,
        source_structuring=regions_path,
        source_semantics=sem_path,
        source_layout=lr_path if layout_recovery else None,
    )
    return ["source_reconstruction.json", "recovered.c"]

def run_pipeline(
    binary_path: str,
    out_dir: str = "artifacts",
    use_ghidra: bool = False,
    use_radare2: bool = False,
    clean: bool = False,
    continue_on_error: bool = False,
    no_source: bool = False,
    stop_after: str | None = None,
    validate: bool = False,
    validate_strict: bool = False,
    evidence_index: bool = False,
    require_evidence_index: bool = False,
    trace_report: bool = False,
    require_trace_report: bool = False,
    quality_gate: bool = False,
    readable: bool = False,
    promote_symbols: bool = True,
    promote_temps: bool = False,
    no_compile_shape_fix: bool = False,
    strict_readable_clang: bool = False,
    simplify_expressions: bool = True,
    no_copy_op_store_simplification: bool = False,
    enable_mask_cast_simplification: bool = False,
    # Phase 8 — Dynamic Behavior Capture
    dynamic: bool = False,
    dynamic_inputs: str | None = None,
    dynamic_timeout_s: float = 5.0,
    dynamic_max_output_bytes: int = 1_048_576,
    # Phase 11.6 — Adaptive Dynamic
    auto_inputs: bool = False,
    adaptive_dynamic: bool = False,
    dynamic_mutation_rounds: int = 2,
    dynamic_max_generated_inputs: int = 20,
    dynamic_max_adaptive_inputs: int = 30,
    # Phase 9 — Static-Dynamic Behavior Fusion
    fuse_behavior: bool = False,
    require_dynamic: bool = False,
    # Phase 10 — Agent Orchestration
    agent_debate: bool = False,
    agent_provider: str = "ollama",
    agent_model: str | None = None,
    agent_ollama_host: str | None = None,
    agent_groq_host: str | None = None,
    agent_api_key_env: str | None = None,
    agent_timeout_s: int = 300,
    agent_temperature: float = 0.0,
    agent_num_ctx: int = 8192,
    agent_max_functions: int | None = None,
    # Phase 11.6 — Compact Context
    packet_mode: str = "compact",
    max_packet_chars: int = 16000,
    max_evidence_items: int = 20,
    # Phase 11.6 — Provider Retry
    retry_on_413: bool = True,
    wait_on_429: bool = False,
    max_provider_retries: int = 1,
    # Phase 11 — Agent-Assisted Source Generation
    generate_agent_source: bool = False,
    source_provider: str = "ollama",
    source_model: str | None = None,
    source_max_functions: int = 1,
    source_api_key_env: str | None = None,
    allow_human_suggestions: bool = False,
    overwrite_agent_source: bool = False,
    skip_static: bool = False,
    function: str | None = None,
) -> dict:
    """Run Hephaestus pipeline and return execution manifest."""
    from src.utils.artifacts import ensure_out_dir, clean_known_artifacts
    
    if quality_gate:
        evidence_index = True
        validate = True
        trace_report = True
    from main import setup_logging
    from src.pipeline.stage_defs import OPTIONAL_PIPELINE_STAGES
    
    # Clean previous run artifacts if requested
    if clean:
        clean_known_artifacts(out_dir)
        
    ensure_out_dir(out_dir)
    
    # Consolidate log file
    setup_logging(out_dir)
    logger.info("[run-all] start")
    
    manifest = start_manifest(binary_path, out_dir)
    
    STAGES = PIPELINE_STAGES.copy()
    
    # Include build_evidence_index stage in PIPELINE_STAGES copy if requested
    if (evidence_index or validate or validate_strict or trace_report) and "build_evidence_index" not in STAGES:
        STAGES.append("build_evidence_index")
        
    if stop_after:
        if stop_after not in STAGES and stop_after not in OPTIONAL_PIPELINE_STAGES:
            logger.error(f"[run-all] Invalid stop-after stage name: {stop_after}")
            raise PipelineError(f"Invalid stop-after stage name: {stop_after}")
            
        combined_stages = PIPELINE_STAGES.copy()
        if stop_after == "build_evidence_index" or (evidence_index or validate or validate_strict or trace_report or quality_gate):
            combined_stages.append("build_evidence_index")
        if stop_after == "validate" or (validate or validate_strict or quality_gate):
            combined_stages.append("validate")
        if stop_after == "build_trace_report" or trace_report or quality_gate:
            combined_stages.append("build_trace_report")
        if stop_after == "quality_gate" or quality_gate:
            combined_stages.append("quality_gate")
        if stop_after == "build_readable" or readable:
            combined_stages.append("build_readable")
        if stop_after == "run_dynamic" or dynamic:
            combined_stages.append("run_dynamic")
        if stop_after == "adaptive_dynamic" or adaptive_dynamic:
            combined_stages.append("adaptive_dynamic")
        if stop_after == "fuse_behavior" or fuse_behavior:
            combined_stages.append("fuse_behavior")
        if stop_after == "build_agent_packets" or agent_debate:
            combined_stages.append("build_agent_packets")
        if stop_after == "optimize_agent_context" or agent_debate:
            combined_stages.append("optimize_agent_context")
        if stop_after == "agent_debate" or agent_debate:
            combined_stages.append("agent_debate")
        if stop_after == "generate_agent_source" or generate_agent_source:
            combined_stages.append("generate_agent_source")
            
        if stop_after in combined_stages:
            idx = combined_stages.index(stop_after)
            active_stages = combined_stages[:idx+1]
        else:
            active_stages = combined_stages.copy()
    else:
        active_stages = STAGES.copy()
        
    if no_source:
        if "reconstruct_source" in active_stages:
            active_stages.remove("reconstruct_source")
        if "build_evidence_index" in active_stages:
            active_stages.remove("build_evidence_index")
            
    if skip_static:
        for s in [
            "extract", "analyze_cfg", "recover_semantics", "refine_semantics",
            "recover_layouts", "finalize_semantics", "reconstruct_source"
        ]:
            if s in active_stages:
                active_stages.remove(s)
                
    status = "ok"
    
    for stage in active_stages:
        logger.info(f"[stage {stage}] start")
        started_at = now_iso()
        start_time = time.perf_counter()
        stage_status = "ok"
        outputs = []
        error_msg = None
        
        try:
            if stage == "extract":
                outputs = run_stage_extract(binary_path, out_dir, use_ghidra, use_radare2)
            elif stage == "analyze_cfg":
                outputs = run_stage_analyze_cfg(out_dir)
            elif stage == "recover_semantics":
                outputs = run_stage_recover_semantics(out_dir)
            elif stage == "refine_semantics":
                outputs = run_stage_refine_semantics(out_dir)
            elif stage == "recover_layouts":
                outputs = run_stage_recover_layouts(out_dir)
            elif stage == "finalize_semantics":
                outputs = run_stage_finalize_semantics(out_dir)
            elif stage == "reconstruct_source":
                outputs = run_stage_reconstruct_source(out_dir)
            elif stage == "build_evidence_index":
                from src.validation.evidence_index.builder import build_index_payload
                from src.validation.evidence_index.writer import write_evidence_index
                try:
                    payload = build_index_payload(Path(out_dir))
                    write_evidence_index(payload, Path(out_dir))
                    outputs = ["evidence_index.json"]
                except Exception as e:
                    raise PipelineError(f"Build evidence index failed: {e}")

        except Exception as e:
            stage_status = "failed"
            error_msg = str(e)
            logger.error(f"[stage {stage}] failed: {e}")
            status = "partial" if continue_on_error else "failed"
            
        finished_at = now_iso()
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        
        if stage_status == "ok":
            logger.info(f"[stage {stage}] ok duration_ms={duration_ms}")
            
        record_stage(
            manifest=manifest,
            name=stage,
            status=stage_status,
            outputs=outputs,
            error=error_msg,
            metrics={},
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms
        )
        
        if stage_status == "failed" and not continue_on_error:
            break
            
    # Gather output artifacts paths
    final_outputs = {}
    for key, filename in [
        ("unified_ir", "unified_ir.json"),
        ("phase4_semantics", "phase4_semantics.json"),
        ("source_reconstruction", "source_reconstruction.json"),
        ("recovered_c", "recovered.c")
    ]:
        path = os.path.join(out_dir, filename)
        if os.path.exists(path):
            final_outputs[key] = path
            
    # Add evidence_index if generated
    ev_path = os.path.join(out_dir, "evidence_index.json")
    if os.path.exists(ev_path):
        final_outputs["evidence_index"] = ev_path
            
    # Compile summary statistics
    summary_dict = {
        "source_schema_version": "5.7.2",
        "functions_total": 0,
        "instructions_total": 0,
        "instructions_lowered": 0,
        "instructions_commented": 0,
        "lowering_coverage_percent": 0.0,
        "condition_expressions_recovered": 0,
        "declarations_total": 0,
        "unsupported_instruction_kinds": {}
    }
    
    recon_path = os.path.join(out_dir, "source_reconstruction.json")
    if os.path.exists(recon_path):
        try:
            with open(recon_path, "r", encoding="utf-8") as f:
                recon_data = json.load(f)
            summary_dict["source_schema_version"] = recon_data.get("schema_version", "5.7.2")
            rs = recon_data.get("summary", {})
            for k in [
                "instructions_total", "instructions_lowered",
                "instructions_commented", "condition_expressions_recovered",
                "functions_total", "lowering_coverage_percent", "declarations_total"
            ]:
                # Map functions_total correctly
                summary_key = k
                if k == "functions_total" and "functions_total" not in rs:
                    # fallback to total reconstructed if not present
                    summary_key = "functions_total"
                
                # Check for direct mapping or fallback
                if k in rs:
                    summary_dict[summary_key] = rs[k]
                elif k == "functions_total" and "functions_total" in rs:
                    summary_dict["functions_total"] = rs["functions_total"]
            if "unsupported_instruction_kinds" in rs:
                summary_dict["unsupported_instruction_kinds"] = rs["unsupported_instruction_kinds"]
        except Exception:
            pass
            
    finalize_manifest(manifest, status, summary_dict, final_outputs)
    write_manifest(manifest, out_dir)
    
    # Check validation after pipeline manifest has been written to disk
    if validate or validate_strict:
        logger.info("[run-all] running validation stage")
        started_at = now_iso()
        start_time = time.perf_counter()
        stage_status = "ok"
        error_msg = None
        outputs = []
        
        from src.validation.loader import load_validation_artifacts
        from src.validation.report import new_report, write_report
        from src.validation.checks import run_all_validation_checks
        
        try:
            artifacts = load_validation_artifacts(out_dir)
            report = new_report(out_dir, strict=validate_strict)
            # If trace report is enabled, bypass require-trace-report check on this initial run
            # as the trace report has not been generated yet. It will be verified and link-injected
            # in the post-trace validation update block.
            first_run_require_trace_report = False if trace_report else require_trace_report
            run_all_validation_checks(
                artifacts,
                report,
                require_evidence_index=require_evidence_index,
                require_trace_report=first_run_require_trace_report
            )
            write_report(report, out_dir)
            outputs = ["validation_report.json"]
            
            # Update manifest final outputs
            manifest["final_outputs"]["validation_report"] = os.path.join(out_dir, "validation_report.json")
            if report.get("status") == "failed" and validate_strict:
                logger.error("[run-all] validation failed in strict mode")
                manifest["status"] = "failed"
                status = "failed"
        except Exception as e:
            logger.exception("[run-all] validation check crashed: %s", e)
            stage_status = "failed"
            error_msg = str(e)
            if validate_strict:
                status = "failed"
                manifest["status"] = "failed"
                
        finished_at = now_iso()
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        
        record_stage(
            manifest=manifest,
            name="validate",
            status=stage_status,
            outputs=outputs,
            error=error_msg,
            metrics={},
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms
        )
        write_manifest(manifest, out_dir)
    
    # Check trace report generation after pipeline validation has completed
    if trace_report and (not stop_after or "build_trace_report" in active_stages):
        logger.info("[run-all] running trace report generation stage")
        started_at = now_iso()
        start_time = time.perf_counter()
        stage_status = "ok"
        error_msg = None
        outputs = []
        
        from src.validation.trace_report import build_trace_report
        
        try:
            build_trace_report(
                out_dir=out_dir,
                markdown_mode=True,
                require_validation=False,
                require_evidence_index=require_evidence_index
            )
            
            json_path = os.path.join(out_dir, "trace_report.json")
            md_path = os.path.join(out_dir, "trace_report.md")
            if os.path.exists(json_path):
                outputs.append("trace_report.json")
                manifest["final_outputs"]["trace_report"] = json_path
            if os.path.exists(md_path):
                outputs.append("trace_report.md")
                manifest["final_outputs"]["trace_report_markdown"] = md_path
                
            # If validation is also enabled, re-run validation checks to include the new trace report
            if validate or validate_strict:
                logger.info("[run-all] updating validation report with trace report metadata")
                from src.validation.loader import load_validation_artifacts
                from src.validation.report import new_report, write_report
                from src.validation.checks import run_all_validation_checks
                
                artifacts = load_validation_artifacts(out_dir)
                report = new_report(out_dir, strict=validate_strict)
                if artifacts.trace_report is not None:
                    report["trace_report"] = "trace_report.json"
                run_all_validation_checks(
                    artifacts,
                    report,
                    require_evidence_index=require_evidence_index,
                    require_trace_report=require_trace_report
                )
                write_report(report, out_dir)
                
                # Update manifest outputs and status if strict mode fails now
                manifest["final_outputs"]["validation_report"] = os.path.join(out_dir, "validation_report.json")
                if report.get("status") == "failed" and validate_strict:
                    logger.error("[run-all] validation failed in strict mode after trace report generation")
                    manifest["status"] = "failed"
                    status = "failed"
                
        except Exception as e:
            logger.exception("[run-all] trace report generation crashed: %s", e)
            stage_status = "failed"
            error_msg = str(e)
            status = "failed"
            manifest["status"] = "failed"
            
        finished_at = now_iso()
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        
        record_stage(
            manifest=manifest,
            name="build_trace_report",
            status=stage_status,
            outputs=outputs,
            error=error_msg,
            metrics={},
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms
        )
        write_manifest(manifest, out_dir)

    # Check quality gate after trace report generation has completed
    if quality_gate and (not stop_after or "quality_gate" in active_stages):
        logger.info("[run-all] running quality gate stage")
        started_at = now_iso()
        start_time = time.perf_counter()
        stage_status = "ok"
        error_msg = None
        outputs = []
        
        from src.validation.quality_gate import build_quality_gate
        
        try:
            build_quality_gate(
                out_dir=out_dir,
                markdown_mode=True,
                strict=validate_strict
            )
            
            json_path = os.path.join(out_dir, "quality_gate.json")
            md_path = os.path.join(out_dir, "quality_gate.md")
            if os.path.exists(json_path):
                outputs.append("quality_gate.json")
                manifest["final_outputs"]["quality_gate"] = json_path
                
                # Check status inside quality_gate.json to block pipeline status if blocked
                with open(json_path, "r", encoding="utf-8") as f:
                    qg_data = json.load(f)
                if qg_data.get("status") == "blocked":
                    logger.error("[run-all] quality gate blocked Phase 7 execution")
                    status = "failed"
                    manifest["status"] = "failed"
            if os.path.exists(md_path):
                outputs.append("quality_gate.md")
                manifest["final_outputs"]["quality_gate_markdown"] = md_path
                
        except Exception as e:
            logger.exception("[run-all] quality gate stage crashed: %s", e)
            stage_status = "failed"
            error_msg = str(e)
            status = "failed"
            manifest["status"] = "failed"
            
        finished_at = now_iso()
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        
        record_stage(
            manifest=manifest,
            name="quality_gate",
            status=stage_status,
            outputs=outputs,
            error=error_msg,
            metrics={},
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms
        )
        write_manifest(manifest, out_dir)

    # Check readable generation after quality gate has completed
    if readable and (not stop_after or "build_readable" in active_stages):
        logger.info("[run-all] running build_readable stage")
        started_at = now_iso()
        start_time = time.perf_counter()
        stage_status = "ok"
        error_msg = None
        outputs = []
        
        # Check if quality gate failed/blocked
        qg_blocked = False
        qg_path = os.path.join(out_dir, "quality_gate.json")
        if os.path.exists(qg_path):
            try:
                with open(qg_path, "r", encoding="utf-8") as f:
                    qg_data = json.load(f)
                if qg_data.get("status") == "blocked" or not qg_data.get("decision", {}).get("safe_to_use_for_phase7", True):
                    qg_blocked = True
            except Exception:
                pass
                
        if qg_blocked:
            stage_status = "failed"
            error_msg = "Blocked by quality gate"
            logger.error("[run-all] build_readable blocked by quality gate")
            status = "failed"
            manifest["status"] = "failed"
        else:
            from src.readability.cli import run_build_readable_cli
            argv = ["--out-dir", out_dir, "--markdown"]
            if not promote_symbols:
                argv.append("--no-promote-symbols")
            if promote_temps:
                argv.append("--promote-temps")
            if no_compile_shape_fix:
                argv.append("--no-compile-shape-fix")
            if strict_readable_clang:
                argv.append("--strict-readable-clang")
            if not simplify_expressions:
                argv.append("--no-simplify-expressions")
            if no_copy_op_store_simplification:
                argv.append("--no-copy-op-store-simplification")
            if enable_mask_cast_simplification:
                argv.append("--enable-mask-cast-simplification")
            
            try:
                code = run_build_readable_cli(argv)
                if code != 0:
                    stage_status = "failed"
                    error_msg = f"build-readable CLI returned {code}"
                    status = "failed"
                    manifest["status"] = "failed"
                else:
                    for filename in ["recovered_readable.c", "readability_report.json", "readability_report.md"]:
                        p = os.path.join(out_dir, filename)
                        if os.path.exists(p):
                            outputs.append(filename)
                            # Map keys
                            key = filename.replace(".", "_")
                            manifest["final_outputs"][key] = p
            except Exception as e:
                logger.exception("[run-all] build_readable stage crashed: %s", e)
                stage_status = "failed"
                error_msg = str(e)
                status = "failed"
                manifest["status"] = "failed"
                
        finished_at = now_iso()
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        
        record_stage(
            manifest=manifest,
            name="build_readable",
            status=stage_status,
            outputs=outputs,
            error=error_msg,
            metrics={},
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms
        )
        write_manifest(manifest, out_dir)

    # Phase 8 — Dynamic Behavior Capture
    if dynamic:
        logger.info("[run-all] running run_dynamic stage")
        started_at = now_iso()
        start_time = time.perf_counter()
        stage_status = "ok"
        error_msg = None
        outputs = []

        from src.dynamic.cli import run_dynamic_cli
        argv = [
            binary_path,
            "--out-dir", out_dir,
            "--timeout-s", str(dynamic_timeout_s),
            "--max-output-bytes", str(dynamic_max_output_bytes),
        ]
        if dynamic_inputs:
            argv += ["--inputs", dynamic_inputs]
        if auto_inputs:
            argv.append("--auto-inputs")
            argv += ["--dynamic-max-generated-inputs", str(dynamic_max_generated_inputs)]

        try:
            code = run_dynamic_cli(argv)
            if code == 2:
                stage_status = "failed"
                error_msg = "Safety violation: static artifact was modified during dynamic execution"
                status = "failed"
                manifest["status"] = "failed"
            elif code != 0:
                stage_status = "failed"
                error_msg = f"run-dynamic CLI returned exit code {code}"
                status = "failed"
                manifest["status"] = "failed"
            else:
                for filename in [
                    "dynamic_inputs.resolved.json",
                    "dynamic_runs.json",
                    "behavior_profile.json",
                    "dynamic_report.json",
                ]:
                    p = os.path.join(out_dir, filename)
                    if os.path.exists(p):
                        outputs.append(filename)
                        manifest["final_outputs"][filename.replace(".", "_")] = p
                # Also record dynamic_inputs.generated.json if auto_inputs was used
                if auto_inputs:
                    gen_inputs_path = os.path.join(out_dir, "dynamic_inputs.generated.json")
                    if os.path.exists(gen_inputs_path):
                        outputs.append("dynamic_inputs.generated.json")
                        manifest["final_outputs"]["dynamic_inputs_generated_json"] = gen_inputs_path
        except Exception as e:
            logger.exception("[run-all] run_dynamic stage crashed: %s", e)
            stage_status = "failed"
            error_msg = str(e)
            status = "failed"
            manifest["status"] = "failed"

        finished_at = now_iso()
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        record_stage(
            manifest=manifest,
            name="run_dynamic",
            status=stage_status,
            outputs=outputs,
            error=error_msg,
            metrics={},
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
        )
        write_manifest(manifest, out_dir)

    # Phase 11.6 — Adaptive Dynamic Exploration
    if adaptive_dynamic and (not stop_after or "adaptive_dynamic" in active_stages):
        logger.info("[run-all] running adaptive_dynamic stage")
        started_at = now_iso()
        start_time = time.perf_counter()
        stage_status = "ok"
        error_msg = None
        outputs = []

        def _file_sha256(path: Path) -> str | None:
            import hashlib
            if not path.exists():
                return None
            h = hashlib.sha256()
            try:
                with path.open("rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        h.update(chunk)
                return h.hexdigest()
            except Exception:
                return None

        runs_path = os.path.join(out_dir, "dynamic_runs.json")
        if not os.path.exists(runs_path):
            stage_status = "failed"
            error_msg = f"Missing required input dynamic_runs.json at {runs_path}"
            logger.error(f"[run-all] adaptive_dynamic failed: {error_msg}")
            status = "failed"
            manifest["status"] = "failed"
        else:
            try:
                with open(runs_path, "r", encoding="utf-8") as f:
                    initial_runs_data = json.load(f)

                from src.dynamic.explorer import (
                    generate_adaptive_inputs,
                    build_input_influence_report,
                    build_exploration_report,
                )
                from src.dynamic.input_generator import build_input_spec_from_cases
                from src.dynamic.runner import run_all
                from src.dynamic.safety import SafetyError

                # Safety check read-only guard
                recovered_c = Path(out_dir) / "recovered.c"
                recovered_readable_c = Path(out_dir) / "recovered_readable.c"
                hash_before = {
                    "recovered.c": _file_sha256(recovered_c),
                    "recovered_readable.c": _file_sha256(recovered_readable_c),
                }

                adaptive_cases, explorer_diag = generate_adaptive_inputs(
                    initial_runs_data,
                    max_new_cases=dynamic_max_adaptive_inputs,
                    mutation_rounds=dynamic_mutation_rounds,
                )

                # Write adaptive_inputs.json
                adaptive_spec = build_input_spec_from_cases(
                    adaptive_cases,
                    generated=True,
                    max_cases=dynamic_max_adaptive_inputs,
                )
                adaptive_inputs_path = os.path.join(out_dir, "adaptive_inputs.json")
                with open(adaptive_inputs_path, "w", encoding="utf-8") as f:
                    json.dump(adaptive_spec, f, indent=2)

                adaptive_results = []
                if adaptive_cases:
                    # Run adaptive inputs
                    adaptive_results, _ = run_all(
                        Path(binary_path),
                        adaptive_spec,
                        timeout_s=dynamic_timeout_s,
                        max_output_bytes=dynamic_max_output_bytes,
                        cwd=None,
                        inherit_env=False,
                        fail_fast=False,
                    )

                    # Check read-only guard
                    hash_after = {
                        "recovered.c": _file_sha256(recovered_c),
                        "recovered_readable.c": _file_sha256(recovered_readable_c),
                    }
                    for name, h_before in hash_before.items():
                        h_after_val = hash_after.get(name)
                        if h_before is not None and h_before != h_after_val:
                            raise PipelineError(f"SAFETY VIOLATION: {name} was modified during adaptive execution")

                # Write adaptive_dynamic_runs.json
                from src.dynamic.writer import _now_iso
                binary_sha256 = initial_runs_data.get("binary_sha256", "")
                adaptive_runs_completed = sum(1 for r in adaptive_results if r.get("status") == "ok")
                adaptive_runs_timed_out = sum(1 for r in adaptive_results if r.get("timed_out"))
                adaptive_runs_crashed = sum(1 for r in adaptive_results if r.get("signal") is not None)

                adaptive_runs_payload = {
                    "schema_version": "dynamic-runs-1.0",
                    "phase": "11.6",
                    "generated_at": _now_iso(),
                    "binary_path": str(binary_path),
                    "binary_sha256": binary_sha256,
                    "timeout_s": dynamic_timeout_s,
                    "runs_total": len(adaptive_results),
                    "runs_completed": adaptive_runs_completed,
                    "runs_timed_out": adaptive_runs_timed_out,
                    "runs_crashed": adaptive_runs_crashed,
                    "runs": adaptive_results,
                    "diagnostics": explorer_diag,
                }
                adaptive_runs_path = os.path.join(out_dir, "adaptive_dynamic_runs.json")
                with open(adaptive_runs_path, "w", encoding="utf-8") as f:
                    json.dump(adaptive_runs_payload, f, indent=2)

                # Write input_influence_report.json
                influence_report = build_input_influence_report(initial_runs_data.get("runs", []), adaptive_results)
                influence_path = os.path.join(out_dir, "input_influence_report.json")
                with open(influence_path, "w", encoding="utf-8") as f:
                    json.dump(influence_report, f, indent=2)

                # Write dynamic_exploration_report.json
                exploration_report = build_exploration_report(
                    explorer_diag,
                    initial_run_count=len(initial_runs_data.get("runs", [])),
                    adaptive_run_count=len(adaptive_results),
                    new_cases_count=len(adaptive_cases),
                )
                exploration_path = os.path.join(out_dir, "dynamic_exploration_report.json")
                with open(exploration_path, "w", encoding="utf-8") as f:
                    json.dump(exploration_report, f, indent=2)

                # Add output files to list
                for fn in ["adaptive_inputs.json", "adaptive_dynamic_runs.json", "input_influence_report.json", "dynamic_exploration_report.json"]:
                    p = os.path.join(out_dir, fn)
                    if os.path.exists(p):
                        outputs.append(fn)
                        manifest["final_outputs"][fn.replace(".", "_")] = p

            except Exception as e:
                stage_status = "failed"
                error_msg = str(e)
                logger.error(f"[stage adaptive_dynamic] failed: {e}")
                status = "failed"
                manifest["status"] = "failed"

        finished_at = now_iso()
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        record_stage(
            manifest=manifest,
            name="adaptive_dynamic",
            status=stage_status,
            outputs=outputs,
            error=error_msg,
            metrics={},
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
        )
        write_manifest(manifest, out_dir)

    # Phase 9 — Static-Dynamic Behavior Fusion
    # IMPORTANT: fuse_behavior reads existing artifacts only; it never executes the binary.
    if fuse_behavior:
        logger.info("[run-all] running fuse_behavior stage")
        started_at = now_iso()
        start_time = time.perf_counter()
        stage_status = "ok"
        error_msg = None
        outputs = []

        from src.behavior.cli import run_fuse_behavior_cli
        argv = ["--out-dir", out_dir]
        if require_dynamic:
            argv.append("--require-dynamic")

        try:
            code = run_fuse_behavior_cli(argv)
            if code != 0:
                stage_status = "failed"
                error_msg = f"fuse-behavior CLI returned exit code {code}"
                status = "failed"
                manifest["status"] = "failed"
            else:
                for filename in ["behavior_model.json", "behavior_fusion_report.json"]:
                    p = os.path.join(out_dir, filename)
                    if os.path.exists(p):
                        outputs.append(filename)
                        manifest["final_outputs"][filename.replace(".", "_")] = p
        except Exception as e:
            logger.exception("[run-all] fuse_behavior stage crashed: %s", e)
            stage_status = "failed"
            error_msg = str(e)
            status = "failed"
            manifest["status"] = "failed"

        finished_at = now_iso()
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        record_stage(
            manifest=manifest,
            name="fuse_behavior",
            status=stage_status,
            outputs=outputs,
            error=error_msg,
            metrics={},
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
        )
        write_manifest(manifest, out_dir)

    # Phase 10.1 — Build Agent Packets
    if agent_debate:
        logger.info("[run-all] running build_agent_packets stage")
        started_at = now_iso()
        start_time = time.perf_counter()
        stage_status = "ok"
        error_msg = None
        outputs = []

        from src.agent.cli import run_build_agent_packets_cli
        argv = ["--out-dir", str(out_dir)]

        try:
            code = run_build_agent_packets_cli(argv)
            if code == 2:
                stage_status = "failed"
                error_msg = "Safety violation: input artifact modified during packet build"
                status = "failed"
                manifest["status"] = "failed"
            elif code != 0:
                stage_status = "failed"
                error_msg = f"build-agent-packets returned exit code {code}"
                # Non-fatal: continue to attempt debate if packets partial
            else:
                p = os.path.join(str(out_dir), "agent_packet_manifest.json")
                if os.path.exists(p):
                    outputs.append("agent_packet_manifest.json")
                    manifest["final_outputs"]["agent_packet_manifest_json"] = p
        except Exception as e:
            logger.exception("[run-all] build_agent_packets stage crashed: %s", e)
            stage_status = "failed"
            error_msg = str(e)

        finished_at = now_iso()
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        record_stage(
            manifest=manifest,
            name="build_agent_packets",
            status=stage_status,
            outputs=outputs,
            error=error_msg,
            metrics={},
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
        )
        write_manifest(manifest, out_dir)

    # Phase 11.6 — Compact LLM Context Optimizer
    if (agent_debate or stop_after == "optimize_agent_context") and (not stop_after or "optimize_agent_context" in active_stages):
        logger.info("[run-all] running optimize_agent_context stage")
        started_at = now_iso()
        start_time = time.perf_counter()
        stage_status = "ok"
        error_msg = None
        outputs = []

        from src.agent.context_optimizer import optimize_agent_packets
        try:
            compact_paths, report = optimize_agent_packets(
                Path(out_dir),
                packet_mode=packet_mode,
                max_packet_chars=max_packet_chars,
                max_evidence_items=max_evidence_items,
            )
            p = os.path.join(out_dir, "agent_packet_optimization_report.json")
            if os.path.exists(p):
                outputs.append("agent_packet_optimization_report.json")
                manifest["final_outputs"]["agent_packet_optimization_report_json"] = p
        except Exception as e:
            stage_status = "failed"
            error_msg = str(e)
            logger.error(f"[stage optimize_agent_context] failed: {e}")
            if stop_after == "optimize_agent_context":
                status = "failed"
                manifest["status"] = "failed"

        finished_at = now_iso()
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        record_stage(
            manifest=manifest,
            name="optimize_agent_context",
            status=stage_status,
            outputs=outputs,
            error=error_msg,
            metrics={},
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
        )
        write_manifest(manifest, out_dir)

    # Phase 10.2 — Agent Debate
    if agent_debate:
        logger.info("[run-all] running agent_debate stage")
        started_at = now_iso()
        start_time = time.perf_counter()
        stage_status = "ok"
        error_msg = None
        outputs = []

        from src.agent.cli import run_agent_debate_cli
        argv = [
            "--out-dir", str(out_dir),
            "--provider", agent_provider,
            "--timeout-s", str(agent_timeout_s),
            "--temperature", str(agent_temperature),
            "--num-ctx", str(agent_num_ctx),
            "--packet-mode", packet_mode,
            "--max-packet-chars", str(max_packet_chars),
            "--max-evidence-items", str(max_evidence_items),
            "--max-provider-retries", str(max_provider_retries),
        ]
        if agent_model:
            argv += ["--model", agent_model]
        if agent_ollama_host:
            argv += ["--ollama-host", agent_ollama_host]
        if agent_groq_host:
            argv += ["--groq-host", agent_groq_host]
        if agent_api_key_env:
            argv += ["--api-key-env", agent_api_key_env]
        if agent_max_functions is not None:
            argv += ["--max-functions", str(agent_max_functions)]
        if function:
            argv += ["--function", function]
        if retry_on_413:
            argv.append("--retry-on-413")
        else:
            argv.append("--no-retry-on-413")
        if wait_on_429:
            argv.append("--wait-on-429")

        try:
            code = run_agent_debate_cli(argv)
            if code == 2:
                stage_status = "failed"
                error_msg = "Safety violation: input artifact modified during agent debate"
                status = "failed"
                manifest["status"] = "failed"
            elif code != 0:
                stage_status = "failed"
                error_msg = f"agent-debate returned exit code {code}"
                status = "failed"
                manifest["status"] = "failed"
            else:
                for filename in ["agent_debate_report.json", "agent_suggestions.json"]:
                    p = os.path.join(str(out_dir), filename)
                    if os.path.exists(p):
                        outputs.append(filename)
                        manifest["final_outputs"][filename.replace(".", "_")] = p
        except Exception as e:
            logger.exception("[run-all] agent_debate stage crashed: %s", e)
            stage_status = "failed"
            error_msg = str(e)
            status = "failed"
            manifest["status"] = "failed"

        finished_at = now_iso()
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        record_stage(
            manifest=manifest,
            name="agent_debate",
            status=stage_status,
            outputs=outputs,
            error=error_msg,
            metrics={},
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
        )
        write_manifest(manifest, out_dir)

    # Phase 11 — Agent-Assisted Source Generation
    if generate_agent_source:
        logger.info("[run-all] running generate_agent_source stage")
        started_at = now_iso()
        start_time = time.perf_counter()
        stage_status = "ok"
        error_msg = None
        outputs = []

        from src.agent_source.cli import run_generate_agent_source_cli
        argv = [
            "--out-dir", str(out_dir),
            "--provider", source_provider,
            "--max-functions", str(source_max_functions),
        ]
        if source_model:
            argv += ["--model", source_model]
        if source_api_key_env:
            argv += ["--api-key-env", source_api_key_env]
        if allow_human_suggestions:
            argv.append("--allow-human-suggestions")
        if overwrite_agent_source:
            argv.append("--overwrite")
        if function:
            argv += ["--function", function]

        try:
            code = run_generate_agent_source_cli(argv)
            if code == 2:
                stage_status = "failed"
                error_msg = "Safety violation: guarded artifact modified during Phase 11"
                status = "failed"
                manifest["status"] = "failed"
            elif code != 0:
                stage_status = "failed"
                error_msg = f"generate-agent-source returned exit code {code}"
                status = "failed"
                manifest["status"] = "failed"
            else:
                for filename in [
                    "recovered_agent.c",
                    "agent_source_plan.json",
                    "agent_source_report.json",
                    "agent_source_validation.json",
                ]:
                    p = os.path.join(str(out_dir), filename)
                    if os.path.exists(p):
                        outputs.append(filename)
                        key = filename.replace(".", "_")
                        manifest["final_outputs"][key] = p
        except Exception as e:
            logger.exception("[run-all] generate_agent_source stage crashed: %s", e)
            stage_status = "failed"
            error_msg = str(e)
            status = "failed"
            manifest["status"] = "failed"

        finished_at = now_iso()
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        record_stage(
            manifest=manifest,
            name="generate_agent_source",
            status=stage_status,
            outputs=outputs,
            error=error_msg,
            metrics={},
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
        )
        write_manifest(manifest, out_dir)

    logger.info(f"[run-all] finished status={status}")
    return manifest

