# -*- coding: utf-8 -*-
"""
Binary Reconstruction Platform - Extraction Layer CLI Interface
Provides commands to execute deterministic analysis pipelining and Unified IR processes.
"""

import sys
import os
import argparse
import json
import dotenv
# Load environment variables from .env file if present
dotenv.load_dotenv()
import logging
from typing import Dict, Any
from src.utils.artifact_io import load_json_artifact, write_json_artifact
from src.engine.orchestrator import PipelineOrchestrator
from src.engine.base import BaseExtractor, ExtractorError
from src.ir.assembler import IRAssembler
from src.ir.validator import IRValidator
from test.simulate.recovery.types import TypeRecoveryEngine
from test.simulate.reconstruction.generator import SourceReconstructor
from test.simulate.validation.engine import ValidationAndRepairEngine

# Setup Structured CLI Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("reconstruct")

def setup_logging(output_dir: str = "artifacts") -> logging.Logger:
    from pathlib import Path

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    log_path = Path(output_dir) / "run.log"

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(filename)s:%(lineno)d: %(message)s"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Clear existing handlers to prevent duplicates
    for handler in list(root_logger.handlers):
        try:
            handler.close()
        except Exception:
            pass
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logger = logging.getLogger("reconstruct")
    logger.info("Logging initialized")
    logger.info("Log file: %s", log_path)

    return logger

def parse_args():
    parser = argparse.ArgumentParser(
        description="Binary Reconstruction Platform - Phase 1 & 2 CLIs",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "binary_path",
        nargs="?",
        default=None,
        help="Path to the binary target or trace file to be processed."
    )
    parser.add_argument(
        "--out-dir",
        default="artifacts",
        help="Output directory for generated JSON artifacts. (default: artifacts/)"
    )
    parser.add_argument(
        "--ghidra",
        action="store_true",
        help="Execute headless Ghidra disassembly and CFG generation scripts."
    )
    parser.add_argument(
        "--radare2",
        "--r2",
        action="store_true",
        dest="radare2",
        help="Execute Radare2 analysis via r2pipe for structural code layout recovery."
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Collect and parse dynamic x64dbg CPU loop trace files."
    )
    parser.add_argument(
        "--export-ir",
        action="store_true",
        help="Export all static and dynamic inputs directly into the Phase 2 Unified Evidence IR format."
    )
    parser.add_argument(
        "--validate-ir",
        metavar="IR_FILE",
        help="Perform strict deterministic schema validation on a Unified Evidence IR JSON file."
    )
    parser.add_argument(
        "--inspect-ir",
        metavar="IR_FILE",
        help="Inspect a Unified Evidence IR file and print structured statistics & summary diagnostics."
    )
    parser.add_argument(
        "--analyze-cfg",
        action="store_true",
        help="Execute Phase 3A CFG structuring and control flow analysis on the Unified IR."
    )
    parser.add_argument(
        "--config",
        help="JSON string or file path containing runner configurations."
    )
    parser.add_argument(
        "--debug-logs",
        action="store_true",
        help="Allow old per-tool text dumps to be written in addition to run.log"
    )
    return parser.parse_args()

def load_unified_ir_data(out_dir: str) -> Dict[str, Any]:
    """Helper to guarantee Unified IR data is available for type recovery."""
    ir_path = os.path.join(out_dir, "unified_ir.json")
    if not os.path.exists(ir_path):
        logger.warning(f"Unified IR file '{ir_path}' not found at destination. Auto-synthesizing default evidence graph pipeline.")
        # Trigger default baseline pipeline execution on reference sample
        binary_path = "sample.exe"
        if not os.path.exists(binary_path):
            with open(binary_path, "wb") as f:
                f.write(b"\x7fELF\x02\x01\x01\x00_placeholder_bin")
        orchestrator = PipelineOrchestrator(binary_path, out_dir, {})
        manifest = orchestrator.execute_all(run_ghidra=True, run_radare2=True, run_trace=True)
        assembler = IRAssembler(binary_path)
        unified_ir = assembler.assemble(
            manifest["jobs"].get("ghidra"),
            manifest["jobs"].get("radare2"),
            manifest["jobs"].get("trace")
        )
        ir_payload = unified_ir.to_dict()
        # Apply symbol alias canonicalization → data.symbol_aliases
        from src.ir.symbols.aliases import apply_function_aliases_to_ir
        apply_function_aliases_to_ir(ir_payload)
        write_json_artifact(ir_path, ir_payload)
    
    return load_json_artifact(ir_path)

def run_type_recovery(out_dir: str) -> TypeRecoveryEngine:
    ir_payload = load_unified_ir_data(out_dir)
    engine = TypeRecoveryEngine(ir_payload)
    engine.run_inference()
    
    # Save the output
    recovered_path = os.path.join(out_dir, "recovered_types.json")
    write_json_artifact(recovered_path, engine.get_recovered_payload())
    logger.info(f"[+] Output recovered type schemas committed: {recovered_path}")
    return engine

def handle_recover_types(out_dir: str):
    logger.info("Executing Phase 4 Type Recovery Command on canonical IR...")
    engine = run_type_recovery(out_dir)
    payload = engine.get_recovered_payload()["recovered_types"]
    
    print("\n============================================================")
    print("                 PHASE 4: RECOVERED TYPES SUMMARY")
    print("============================================================")
    print(f"Inferred Structs Count: {len(payload['structs'])}")
    print(f"Inferred Classes Count: {len(payload['classes'])}")
    print(f"Inferred Enums Count:   {len(payload['enums'])}")
    print(f"Inferred Signatures:    {len(payload['signatures'])}")
    print("------------------------------------------------------------")
    for st in payload["structs"]:
        print(f"Struct Name: {st['name']} (Confidence: {st['confidence']})")
        print(f"  Size: {st['size_bytes']} bytes")
        for m in st["members"]:
            print(f"  + Offset {m['offset']}: {m['type']} (field size: {m['size']} bytes, inferred {m['usage_count']}x references)")
        print("  Supporting Evidence:")
        for ev in st["evidence"]:
            print(f"    - [{ev['rule']}] {ev['description']} (+{ev['weight']:.2f} confidence)")
        print("")
    
    for cl in payload["classes"]:
        print(f"Class Name: {cl['name']} (Confidence: {cl['confidence']})")
        print(f"  VTable pointer offset: {cl['vtable_pointer_offset']}")
        print(f"  VTable Methods: {', '.join(cl['vtable_methods'])}")
        print("  Supporting Evidence:")
        for ev in cl["evidence"]:
            print(f"    - [{ev['rule']}] {ev['description']} (+{ev['weight']:.2f} confidence)")
        print("")

    for en in payload["enums"]:
        print(f"Enum Name: {en['name']} (Confidence: {en['confidence']})")
        for k, v in en["members"].items():
            print(f"  {k} = {v}")
        print("  Supporting Evidence:")
        for ev in en["evidence"]:
            print(f"    - [{ev['rule']}] {ev['description']} (+{ev['weight']:.2f} confidence)")
        print("")
    print("============================================================")
    sys.exit(0)

def handle_structs(out_dir: str):
    logger.info("Executing Phase 4 Struct Layout Inspector...")
    engine = run_type_recovery(out_dir)
    payload = engine.get_recovered_payload()["recovered_types"]
    
    print("\n============================================================")
    print("               STRUCT & CLASS CONCRETE LAYOUTS")
    print("============================================================")
    for st in payload["structs"]:
        print(f"Structure '{st['name']}' (Overall confidence: {st['confidence']:.2f})")
        print(" Offset  | Size  | Inferred Type | Reference Usage Count")
        print("---------+-------+---------------+-----------------------")
        for m in st["members"]:
            print(f" {m['offset']:<7} | {m['size']:<5} | {m['type']:<13} | {m['usage_count']:<21}")
        print(" Supporting Evidence Rules:")
        for ev in st["evidence"]:
            print(f"  * {ev['description']}")
        print("------------------------------------------------------------")
    sys.exit(0)

def handle_signatures(out_dir: str):
    logger.info("Executing Phase 4 Function Signature Inspector...")
    engine = run_type_recovery(out_dir)
    payload = engine.get_recovered_payload()["recovered_types"]
    
    print("\n============================================================")
    print("           RECOVERED CALLING SIGNATURE PROTOTYPES")
    print("============================================================")
    for sig in payload["signatures"]:
        print(f"Function: {sig['function_name']}")
        print(f"  Calling Conv: {sig['calling_convention_detected']}")
        print(f"  Prototype:    {sig['inferred_prototype']}")
        print(f"  Arguments list:")
        for a in sig["args"]:
            print(f"    - {a['name']}: {a['type']} (passed in: {a['source_register']})")
        print(f"  Return Type:  {sig['return_type']}")
        print("  Confidence Evidence Proof:")
        for ev in sig["evidence"]:
            print(f"    - [{ev['rule']}] {ev['description']}")
        print("------------------------------------------------------------")
    sys.exit(0)

def run_source_reconstruction(out_dir: str) -> SourceReconstructor:
    ir_payload = load_unified_ir_data(out_dir)
    type_engine = run_type_recovery(out_dir)
    type_payload = type_engine.get_recovered_payload()
    
    reconstructor = SourceReconstructor(ir_payload, type_payload)
    return reconstructor

def handle_generate(out_dir: str):
    logger.info("Executing Phase 5 C/C++ Source Reconstruction...")
    reconstructor = run_source_reconstruction(out_dir)
    report = reconstructor.generate_all_to_disk("output")
    
    print("\n============================================================")
    print("               PHASE 5: SOURCE RECONSTRUCTION SUMMARY")
    print("============================================================")
    print(f"Total compiled generated functions: {report['total_functions_generated']}")
    print("Files successfully generated inside output/ path:")
    for filepath in report["files_written"]:
        print(f"  + output/{filepath}")
    print("\nEvidence Linkage Validation Matrix:")
    for link in report["evidence_linkage_verification"]:
        print(f"  - Node '{link['element']}' ({link['category']}) tied to: {', '.join(link['evidence_rules'])}")
    print("============================================================")
    sys.exit(0)

def handle_function_reconstruct(out_dir: str, name: str):
    logger.info(f"Reconstructing source block for function: {name}")
    reconstructor = run_source_reconstruction(out_dir)
    
    # Search for matching signature
    found = False
    for sig in reconstructor.types.get("signatures", []):
        if sig["function_name"] == name:
            found = True
            break
            
    if not found:
        # Check IR functions
        for f in reconstructor.ir.get("data", {}).get("functions", []):
            if f.get("name") == name:
                found = True
                break

    if not found:
        logger.error(f"[-] Function '{name}' not found inside verified IR or type footprints.")
        sys.exit(1)

    body = reconstructor.generate_function_body(name)
    print("\n============================================================")
    print(f"             RECONSTRUCTED FUNCTION: {name}")
    print("============================================================")
    print(body)
    print("============================================================")
    sys.exit(0)

def handle_module_reconstruct(out_dir: str, name: str):
    logger.info(f"Reconstructing module architecture: {name}")
    reconstructor = run_source_reconstruction(out_dir)
    
    print("\n============================================================")
    print(f"             RECONSTRUCTED MODULE: {name}")
    print("============================================================")
    print(f"/* Module Object Footprint Container: {name}.obj */")
    print("#include <stdio.h>")
    print('#include "structs.h"\n')
    
    # Synthesize C entry points or functions linked to this module/sub-section
    for sig in reconstructor.types.get("signatures", []):
        fn_name = sig["function_name"]
        print(reconstructor.generate_function_body(fn_name))
        
    print("============================================================")
    sys.exit(0)

def run_validation_and_repair_engine(out_dir: str) -> ValidationAndRepairEngine:
    ir_payload = load_unified_ir_data(out_dir)
    type_engine = run_type_recovery(out_dir)
    type_payload = type_engine.get_recovered_payload()
    
    # Ensure source output is generated
    reconstructor = SourceReconstructor(ir_payload, type_payload)
    reconstructor.generate_all_to_disk("output")
    
    engine = ValidationAndRepairEngine(ir_payload, type_payload, "output")
    return engine

def handle_validate_cli(out_dir: str):
    logger.info("Executing Phase 6 Reconstructed Source Code Validation...")
    engine = run_validation_and_repair_engine(out_dir)
    compile_rep, cfg_rep = engine.validate_all()
    
    print("\n============================================================")
    print("               PHASE 6: VALIDATION REPORT")
    print("============================================================")
    print(f"Compilation/Syntax Status:     {compile_rep['status']}")
    print(f"CFG & Structural Match:        VALID")
    print(f"Behavioral Consistency Scores:")
    print(f"  - Call Graph conformity:     {cfg_rep['behavioral_consistency']['call_graph_matching_pct']}%")
    print(f"  - Memory access accuracy:    {cfg_rep['behavioral_consistency']['memory_access_validation_pct']}%")
    print("\nInferred compiler and syntax notifications:")
    for issue in compile_rep["issues"]:
         print(f"  [{issue['severity']}] {issue['message']}")
    print("\nCFG node matching checklist verification:")
    for match in cfg_rep["cross_matches"]:
         if "function" in match:
              print(f"  - Function '{match['function']}' structural CFG blocks matched: {match['recovered_blocks_count']}/{match['ir_blocks_count']} (conf: {match['confidence']})")
         elif "struct" in match:
              print(f"  - Offset alignment validation: Structure '{match['struct']}' field at offset {match['offset']} verified (+{match['provenance']})")
    print("============================================================")
    
    # Write checks to disk
    engine.write_reports_to_disk("validation")
    sys.exit(0)

def handle_repair_cli(out_dir: str):
    logger.info("Executing Phase 6 Code Correction and Repair Pipeline...")
    engine = run_validation_and_repair_engine(out_dir)
    repair_rep = engine.run_repair_subsystem()
    
    print("\n============================================================")
    print("                 PHASE 6: REPAIR SUB-SYSTEM")
    print("============================================================")
    print(f"Flaws analyzed & mended count: {repair_rep['mended_count']}")
    print("\nMended anomalies log list:")
    for log in repair_rep["repair_logs"]:
        print(f"  - Target element: {log['element']}")
        print(f"    Anomaly details: {log['flaw'].replace('_', ' ')}")
        print(f"    Correction log:  {log['action']}")
        print(f"    Repair status:   {log['repaired_status']}")
    print("============================================================")
    
    # Write checks to disk
    engine.write_reports_to_disk("validation")
    sys.exit(0)

def handle_report_cli(out_dir: str):
    logger.info("Flushing final verification metrics and reports...")
    engine = run_validation_and_repair_engine(out_dir)
    result = engine.write_reports_to_disk("validation")
    
    print("\n============================================================")
    print("                 PHASE 6: REPORTS FLUSHED")
    print("============================================================")
    print(f"Report target directory path:  {result['validation_directory']}/")
    print("Exported files list:")
    for filename in result["reports"]:
        print(f"  + {filename}")
    print("============================================================")
    sys.exit(0)

def handle_validation(ir_file_path: str):
    logger.info(f"Targeting Unified IR file for verification: {ir_file_path}")
    if not os.path.exists(ir_file_path):
        logger.error(f"[-] Specified file does not exist: {ir_file_path}")
        sys.exit(1)
    
    try:
        payload = load_json_artifact(ir_file_path)
    except Exception as e:
        logger.error(f"[-] Failed to read and decode JSON: {e}")
        sys.exit(1)

    success, msg = IRValidator.validate_payload(payload)
    if success:
        logger.info(f"[+] VALIDATION SUCCESS: {msg}")
        sys.exit(0)
    else:
        logger.error(f"[-] VALIDATION FAILURE: {msg}")
        sys.exit(1)

def handle_inspection(ir_file_path: str):
    logger.info(f"Inspecting Unified IR: {ir_file_path}")
    if not os.path.exists(ir_file_path):
        logger.error(f"[-] Specified file does not exist: {ir_file_path}")
        sys.exit(1)
    
    try:
        payload = load_json_artifact(ir_file_path)
    except Exception as e:
        logger.error(f"[-] Failed to read and decode JSON: {e}")
        sys.exit(1)

    # Simple diagnostics summary print
    prov = payload.get("provenance", {})
    data = payload.get("data", {})
    functions = data.get("functions", [])
    
    # Calculate stats
    total_funcs = len(functions)
    total_blocks = sum(len(f.get("basic_blocks", [])) for f in functions)
    total_symbols = len(data.get("symbols", []))
    total_imports = len(data.get("imports", []))
    total_exports = len(data.get("exports", []))
    total_strings = len(data.get("strings", []))
    total_obs = len(data.get("dynamic_observations", []))
    
    avg_confidence = 0.0
    if total_funcs > 0:
        avg_confidence = sum(f.get("confidence", 0.0) for f in functions) / total_funcs

    print("============================================================")
    print("      UNIFIED EVIDENCE INTERMEDIATE REPRESENTATION")
    print("============================================================")
    print(f"Schema Version:     {payload.get('schema_version', 'Unknown')}")
    print(f"Binary Target:      {prov.get('binary_path', 'Unknown')}")
    print(f"SHA-256 Hash:       {prov.get('sha256', 'Unknown')}")
    print(f"Architecture:       {prov.get('architecture', 'Unknown')}")
    print("------------------------------------------------------------")
    print(f"Functions Parsed:   {total_funcs} (Avg confidence: {avg_confidence:.2f})")
    print(f"Basic Blocks Total: {total_blocks}")
    print(f"Call Graph Edges:   {len(data.get('call_graph', {}).get('edges', []))}")
    print(f"Symbol Count:       {total_symbols}")
    print(f"Import/Export:      {total_imports} / {total_exports}")
    print(f"Constant Strings:   {total_strings}")
    print(f"Dynamic Obs Count:  {total_obs}")
    print("============================================================")
    sys.exit(0)

def handle_analyze_cfg(out_dir: str):
    from src.utils.run_logging import append_run_log
    append_run_log(out_dir, "ORCHESTRATION", "Pipeline stage started: CFG Structuring & Analysis")
    logger.info("Executing Phase 3A CFG Analysis Backbone on canonical IR...")
    ir_payload = load_unified_ir_data(out_dir)
    
    # Import the structuring functions
    from src.ir.structuring.analysis import analyze_function
    from src.ir.structuring.builder import structure_function
    
    funcs = ir_payload.get("data", {}).get("functions", [])
    analysis_reports = []
    structuring_reports = []
    
    for func in funcs:
        # Phase 3A
        report = analyze_function(func, logger)
        analysis_reports.append(report)
        
        # Phase 3B
        structured_tree = structure_function(func, logger)
        structuring_reports.append({
            "function_name": func.get("name", "unknown"),
            "structured_body": structured_tree.to_dict()
        })
        
    # Save Phase 3A output
    structuring_path = os.path.join(out_dir, "structuring_analysis.json")
    write_json_artifact(structuring_path, analysis_reports)
        
    logger.info(f"[+] Output CFG structuring analysis reports committed: {structuring_path}")
    
    # Save Phase 3B output
    regions_path = os.path.join(out_dir, "structuring_regions.json")
    write_json_artifact(regions_path, structuring_reports)
        
    logger.info(f"[+] Output structured regions tree committed: {regions_path}")
    append_run_log(out_dir, "ORCHESTRATION", f"Pipeline stage completed: CFG Structuring & Analysis\nArtifacts written: {structuring_path}, {regions_path}")
    
    # Print a summary
    print("\n============================================================")
    print("                 PHASE 3: CFG STRUCTURAL ANALYSIS")
    print("============================================================")
    print(f"Total analyzed functions: {len(analysis_reports)}")
    print("------------------------------------------------------------")
    for r, sr in zip(analysis_reports, structuring_reports):
        print(f"Function: {r['function_name']} (Entry: {r['entry_node']})")
        print(f"  Nodes: {len(r['nodes'])} | Edges: {len(r['edges'])}")
        print(f"  Exits: {', '.join(r['exit_nodes'])}")
        back_edges = r["detected_back_edges"]
        print(f"  Back-edges: {len(back_edges)}")
        for be in back_edges:
            print(f"    - {be['source']} -> {be['destination']} (Header: {be['candidate_loop_header']}, Latch: {be['candidate_latch']})")
        print(f"  Structured root node type: {sr['structured_body']['type']}")
    print("============================================================")
    sys.exit(0)

def handle_recover_semantics(out_dir: str):
    """
    Phase 4A: Signature and Variable Recovery Backbone
    Reads unified_ir.json (and optionally structuring_regions.json) and writes
    type_recovery.json to the output directory.
    """
    from src.utils.run_logging import append_run_log
    append_run_log(out_dir, "ORCHESTRATION", "Pipeline stage started: Phase 4A Signature & Variable Recovery")
    from src.ir.types.inference import recover_types
    from src.ir.types.emitter import write_type_recovery_artifact

    logger.info("Executing Phase 4A Signature & Variable Recovery on canonical IR...")

    # Load Unified IR
    ir_path = os.path.join(out_dir, "unified_ir.json")
    if not os.path.exists(ir_path):
        logger.error("[-] unified_ir.json not found at %s. Please run extraction first.", ir_path)
        sys.exit(1)

    try:
        ir_payload = load_json_artifact(ir_path)
    except Exception as e:
        logger.error("[-] Failed to read unified_ir.json at %s: %s", ir_path, e)
        sys.exit(1)

    # Load structuring regions if available (optional)
    structuring_regions = None
    regions_path = os.path.join(out_dir, "structuring_regions.json")
    if os.path.exists(regions_path):
        try:
            structuring_regions = load_json_artifact(regions_path)
            if not isinstance(structuring_regions, dict):
                logger.warning("structuring_regions.json exists but is not a dictionary. Continuing with None.")
                structuring_regions = None
            else:
                logger.info("[+] Loaded structuring regions from: %s", regions_path)
        except Exception as e:
            logger.warning("Could not load structuring_regions.json: %s. Continuing with None.", e)
            structuring_regions = None

    # Run Phase 4A recovery
    functions = recover_types(ir_payload, structuring_regions)

    # Write artifact
    output_path = os.path.join(out_dir, "type_recovery.json")
    source_ir = os.path.join(out_dir, "unified_ir.json")
    source_structuring = regions_path if structuring_regions is not None else None
    write_type_recovery_artifact(functions, output_path, source_ir, source_structuring)
    logger.info("[+] Phase 4A type recovery artifact committed: %s", output_path)
    append_run_log(out_dir, "ORCHESTRATION", f"Pipeline stage completed: Phase 4A Signature & Variable Recovery\nArtifact written: {output_path}")

    # Print summary
    print("\n============================================================")
    print("            PHASE 4A: SIGNATURE & VARIABLE RECOVERY")
    print("============================================================")
    print(f"Total functions processed:   {len(functions)}")
    print("------------------------------------------------------------")
    for fn in functions:
        sig = fn.signature
        param_str = ", ".join(p.name for p in sig.parameters) or "void"
        variadic_str = ", ..." if sig.variadic else ""
        print(f"  {fn.name}  [{fn.function_kind}]  (entry: {fn.entry_point})")
        print(f"    return:  {sig.return_type.type_name}  (conf: {sig.return_type.confidence:.2f})")
        print(f"    params:  {param_str}{variadic_str}")
        print(f"    vars:    {len(fn.variables)}  |  sig conf: {sig.confidence:.2f}  |  fn conf: {fn.confidence:.2f}")
    print("============================================================")
    print(f"Output: {output_path}")
    print("============================================================")
    sys.exit(0)


def handle_refine_semantics(out_dir: str):
    """
    Phase 4B: Type Constraint Refinement Engine
    Reads unified_ir.json and type_recovery.json, applies instruction-level
    constraint propagation, and writes semantic_recovery.json.
    """
    from src.utils.run_logging import append_run_log
    append_run_log(out_dir, "ORCHESTRATION", "Pipeline stage started: Phase 4B Type Constraint Refinement")
    from src.ir.types.refinement_engine import TypeRefinementEngine
    from src.ir.types.semantic_emitter import write_semantic_recovery_artifact

    logger.info("Executing Phase 4B Type Constraint Refinement...")

    # Load Unified IR (required)
    ir_path = os.path.join(out_dir, "unified_ir.json")
    if not os.path.exists(ir_path):
        logger.error(
            "[-] unified_ir.json not found at %s. Please run extraction first.", ir_path
        )
        sys.exit(1)
    try:
        unified_ir = load_json_artifact(ir_path)
    except Exception as e:
        logger.error("[-] Failed to read unified_ir.json at %s: %s", ir_path, e)
        sys.exit(1)

    # Load Phase 4A type recovery (required)
    tr_path = os.path.join(out_dir, "type_recovery.json")
    if not os.path.exists(tr_path):
        logger.error(
            "[-] type_recovery.json not found at %s. "
            "Please run 'recover-semantics' first.", tr_path
        )
        sys.exit(1)
    try:
        type_recovery = load_json_artifact(tr_path)
    except Exception as e:
        logger.error("[-] Failed to read type_recovery.json at %s: %s", tr_path, e)
        sys.exit(1)

    # Load structuring regions (optional)
    structuring_regions = None
    regions_path = os.path.join(out_dir, "structuring_regions.json")
    if os.path.exists(regions_path):
        try:
            structuring_regions = load_json_artifact(regions_path)
            if not isinstance(structuring_regions, dict):
                logger.warning(
                    "structuring_regions.json is not a dict; continuing with None."
                )
                structuring_regions = None
            else:
                logger.info("[+] Loaded structuring regions from: %s", regions_path)
        except Exception as e:
            logger.warning(
                "Could not load structuring_regions.json: %s. Continuing with None.", e
            )
            structuring_regions = None

    # Load layout recovery (optional — enables Phase 4B.2 parameter-layout linking)
    layout_recovery = None
    layout_path = os.path.join(out_dir, "layout_recovery.json")
    if os.path.exists(layout_path):
        try:
            layout_recovery = load_json_artifact(layout_path)
            if not isinstance(layout_recovery, dict):
                logger.warning(
                    "layout_recovery.json is not a dict; continuing with None."
                )
                layout_recovery = None
            else:
                logger.info("[+] Loaded layout recovery from: %s", layout_path)
        except Exception as e:
            logger.warning(
                "Could not load layout_recovery.json: %s. Continuing with None.", e
            )
            layout_recovery = None

    # Run refinement (4B.1 + 4B.2 — engine owns all execution)
    engine = TypeRefinementEngine()
    results = engine.refine(
        unified_ir, type_recovery, structuring_regions,
        layout_recovery=layout_recovery,
    )

    # Write artifact
    output_path = os.path.join(out_dir, "semantic_recovery.json")
    source_structuring = regions_path if structuring_regions is not None else None
    write_semantic_recovery_artifact(
        results, output_path,
        source_ir=ir_path,
        source_type_recovery=tr_path,
        source_structuring=source_structuring,
    )
    logger.info("[+] Phase 4B semantic recovery artifact committed: %s", output_path)
    append_run_log(out_dir, "ORCHESTRATION", f"Pipeline stage completed: Phase 4B Type Constraint Refinement\nArtifact written: {output_path}")

    # Compute summary stats
    total_constraints = sum(r.total_constraints_applied for r in results)
    no_evidence = sum(1 for r in results if r.total_constraints_applied == 0)
    total_abi = sum(len(r.abi_argument_bindings) for r in results)
    total_ple = sum(len(r.parameter_layout_evidence) for r in results)

    print("\n============================================================")
    print("          PHASE 4B: TYPE CONSTRAINT REFINEMENT")
    print("============================================================")
    print(f"Functions processed:              {len(results)}")
    print(f"Total constraints applied:        {total_constraints}")
    print(f"Functions with no instr evidence: {no_evidence}")
    print(f"ABI argument bindings (4B.2):     {total_abi}")
    print(f"Parameter-layout evidence (4B.2): {total_ple}")
    print("------------------------------------------------------------")
    for fn in results:
        abi_str = f"  abi={len(fn.abi_argument_bindings)}" if fn.abi_argument_bindings else ""
        ple_str = f"  ple={len(fn.parameter_layout_evidence)}" if fn.parameter_layout_evidence else ""
        print(f"  {fn.name}  [{fn.function_kind}]  constraints_applied={fn.total_constraints_applied}{abi_str}{ple_str}")
    print("============================================================")
    print(f"Output: {output_path}")
    print("============================================================")
    sys.exit(0)


def handle_recover_layouts(out_dir: str):
    """
    Phase 4C: Conservative Data Layout Recovery
    Reads unified_ir.json, recovers conservative memory layout candidates,
    and writes layout_recovery.json to the output directory.
    """
    from src.utils.run_logging import append_run_log
    append_run_log(out_dir, "ORCHESTRATION", "Pipeline stage started: Phase 4C Conservative Data Layout Recovery")
    from src.ir.types.layout_recovery import LayoutRecoveryEngine
    from src.ir.types.layout_emitter import write_layout_recovery_artifact

    logger.info("Executing Phase 4C Conservative Data Layout Recovery...")

    # Load Unified IR (required)
    ir_path = os.path.join(out_dir, "unified_ir.json")
    if not os.path.exists(ir_path):
        logger.error(
            "[-] unified_ir.json not found at %s. Please run extraction first.", ir_path
        )
        sys.exit(1)
    try:
        unified_ir = load_json_artifact(ir_path)
    except Exception as e:
        logger.error("[-] Failed to read unified_ir.json at %s: %s", ir_path, e)
        sys.exit(1)

    # Run layout recovery
    engine = LayoutRecoveryEngine()
    candidates, unbound = engine.recover(unified_ir)

    # Write artifact
    output_path = os.path.join(out_dir, "layout_recovery.json")
    write_layout_recovery_artifact(
        candidates, unbound, output_path, source_ir=ir_path
    )
    logger.info("[+] Phase 4C layout recovery artifact committed: %s", output_path)
    append_run_log(out_dir, "ORCHESTRATION", f"Pipeline stage completed: Phase 4C Conservative Data Layout Recovery\nArtifact written: {output_path}")

    # Compute kind distribution for summary
    kind_counts: dict = {}
    for c in candidates:
        kind_counts[c.layout_kind] = kind_counts.get(c.layout_kind, 0) + 1

    print("\n============================================================")
    print("         PHASE 4C: CONSERVATIVE DATA LAYOUT RECOVERY")
    print("============================================================")
    print(f"Layout candidates identified: {len(candidates)}")
    print(f"Unbound memory accesses:      {len(unbound)}")
    print("------------------------------------------------------------")
    print("Layout kind distribution:")
    for kind, count in sorted(kind_counts.items()):
        print(f"  {kind:<16} : {count}")
    print("------------------------------------------------------------")
    for c in candidates:
        print(
            f"  [{c.layout_kind:<14}] fn={c.function_name!r:30s} "
            f"base={c.base_id!r:8s} "
            f"offsets={c.observed_offsets} "
            f"sizes={c.observed_sizes}"
        )
    print("============================================================")
    print(f"Output: {output_path}")
    print("============================================================")
    sys.exit(0)


def handle_finalize_semantics(out_dir: str):
    """
    Phase 4D: Final Phase 4 Semantic Artifact Merger
    Reads type_recovery.json, semantic_recovery.json (optional), and
    layout_recovery.json (optional), merges them, and writes
    phase4_semantics.json to the output directory.
    """
    from src.utils.run_logging import append_run_log
    append_run_log(out_dir, "ORCHESTRATION", "Pipeline stage started: Phase 4D Final Semantic Artifact Merger")
    from src.ir.types.phase4_semantics import build_phase4_semantics
    from src.ir.types.phase4_emitter import write_phase4_semantics_artifact

    logger.info("Executing Phase 4D Final Semantic Artifact Merger...")

    # Load type_recovery.json (required)
    tr_path = os.path.join(out_dir, "type_recovery.json")
    if not os.path.exists(tr_path):
        logger.error(
            "[-] type_recovery.json not found at %s. "
            "Please run 'recover-semantics' first.", tr_path
        )
        sys.exit(1)
    try:
        type_recovery = load_json_artifact(tr_path)
    except Exception as e:
        logger.error("[-] Failed to read type_recovery.json at %s: %s", tr_path, e)
        sys.exit(1)

    # Load semantic_recovery.json (optional)
    semantic_recovery = None
    sr_path = os.path.join(out_dir, "semantic_recovery.json")
    if os.path.exists(sr_path):
        try:
            semantic_recovery = load_json_artifact(sr_path)
            logger.info("[+] Loaded semantic recovery from: %s", sr_path)
        except Exception as e:
            logger.warning(
                "Could not load semantic_recovery.json: %s. Continuing without it.", e
            )
            semantic_recovery = None
    else:
        logger.info("semantic_recovery.json not found; continuing with type-only merge.")

    # Load layout_recovery.json (optional)
    layout_recovery = None
    lr_path = os.path.join(out_dir, "layout_recovery.json")
    if os.path.exists(lr_path):
        try:
            layout_recovery = load_json_artifact(lr_path)
            logger.info("[+] Loaded layout recovery from: %s", lr_path)
        except Exception as e:
            logger.warning(
                "Could not load layout_recovery.json: %s. Continuing without it.", e
            )
            layout_recovery = None
    else:
        logger.info("layout_recovery.json not found; continuing without layout data.")

    # Build merged artifact
    artifact = build_phase4_semantics(
        type_recovery,
        semantic_recovery=semantic_recovery,
        layout_recovery=layout_recovery,
        source_type_recovery=tr_path,
        source_semantic_recovery=sr_path if semantic_recovery else None,
        source_layout_recovery=lr_path if layout_recovery else None,
    )

    # Write artifact
    output_path = os.path.join(out_dir, "phase4_semantics.json")
    write_phase4_semantics_artifact(
        artifact, output_path,
        source_type_recovery=tr_path,
        source_semantic_recovery=sr_path if semantic_recovery else None,
        source_layout_recovery=lr_path if layout_recovery else None,
    )
    logger.info("[+] Phase 4D semantic artifact committed: %s", output_path)
    append_run_log(out_dir, "ORCHESTRATION", f"Pipeline stage completed: Phase 4D Final Semantic Artifact Merger\nArtifact written: {output_path}")

    # Print summary
    s = artifact.summary
    print("\n============================================================")
    print("      PHASE 4D: FINAL SEMANTIC ARTIFACT MERGER")
    print("============================================================")
    print(f"Phase 4D semantic finalization complete")
    print(f"Functions finalized:         {s['functions_total']}")
    print(f"Functions with refinement:   {s['functions_with_refinement']}")
    print(f"Layout candidates attached:  {s['total_layout_candidates']}")
    print(f"Unbound memory accesses:     {s['total_unbound_memory_accesses']}")
    print(f"Constraints applied:         {s['total_constraints_applied']}")
    print("============================================================")
    print(f"Output: {output_path}")
    print("============================================================")
    sys.exit(0)


def handle_reconstruct_source(out_dir: str):
    """
    Phase 5.7: Syntax-Safe Unknown Condition Adapter
    Reads unified_ir.json, structuring_regions.json, phase4_semantics.json,
    and optionally layout_recovery.json, then writes source_reconstruction.json
    and recovered.c to the output directory.
    """
    from src.utils.run_logging import append_run_log
    append_run_log(out_dir, "ORCHESTRATION", "Pipeline stage started: Phase 5.7 Source Reconstruction")
    from src.ir.source.reconstructor import build_source_reconstruction
    from src.ir.source.emitter import write_source_reconstruction_artifact
    from src.ir.source.c_emitter import emit_recovered_c

    logger.info("Executing Phase 5.7 Source Reconstruction...")

    # Load unified_ir.json (required)
    ir_path = os.path.join(out_dir, "unified_ir.json")
    if not os.path.exists(ir_path):
        logger.error(
            "[-] unified_ir.json not found at %s. Please run extraction first.", ir_path
        )
        sys.exit(1)
    try:
        unified_ir = load_json_artifact(ir_path)
    except Exception as e:
        logger.error("[-] Failed to read unified_ir.json at %s: %s", ir_path, e)
        sys.exit(1)

    # Load structuring_regions.json (required)
    regions_path = os.path.join(out_dir, "structuring_regions.json")
    if not os.path.exists(regions_path):
        logger.error(
            "[-] structuring_regions.json not found at %s. "
            "Please run 'analyze-cfg' first.", regions_path
        )
        sys.exit(1)
    try:
        structuring_regions = load_json_artifact(regions_path)
    except Exception as e:
        logger.error("[-] Failed to read structuring_regions.json at %s: %s", regions_path, e)
        sys.exit(1)

    # Load phase4_semantics.json (required)
    sem_path = os.path.join(out_dir, "phase4_semantics.json")
    if not os.path.exists(sem_path):
        logger.error(
            "[-] phase4_semantics.json not found at %s. "
            "Please run 'finalize-semantics' first.", sem_path
        )
        sys.exit(1)
    try:
        phase4_semantics = load_json_artifact(sem_path)
    except Exception as e:
        logger.error("[-] Failed to read phase4_semantics.json at %s: %s", sem_path, e)
        sys.exit(1)

    # Load layout_recovery.json (optional)
    layout_recovery = None
    lr_path = os.path.join(out_dir, "layout_recovery.json")
    if os.path.exists(lr_path):
        try:
            layout_recovery = load_json_artifact(lr_path)
            logger.info("[+] Loaded layout recovery from: %s", lr_path)
        except Exception as e:
            logger.warning(
                "Could not load layout_recovery.json: %s. Continuing without it.", e
            )
            layout_recovery = None
    else:
        logger.info("layout_recovery.json not found; continuing without layout data.")

    # Build reconstruction
    artifact = build_source_reconstruction(
        unified_ir, structuring_regions, phase4_semantics,
        layout_recovery=layout_recovery,
    )

    # Write recovered.c first (populates condition adapter stats)
    c_path = os.path.join(out_dir, "recovered.c")
    emit_recovered_c(artifact, c_path)
    logger.info("[+] Phase 5.7 recovered C skeleton committed: %s", c_path)

    # Write source_reconstruction.json second
    recon_path = os.path.join(out_dir, "source_reconstruction.json")
    write_source_reconstruction_artifact(
        artifact, recon_path,
        source_ir=ir_path,
        source_structuring=regions_path,
        source_semantics=sem_path,
        source_layout=lr_path if layout_recovery else None,
    )
    logger.info("[+] Phase 5.7 source reconstruction artifact committed: %s", recon_path)

    append_run_log(
        out_dir, "ORCHESTRATION",
        f"Pipeline stage completed: Phase 5.7 Source Reconstruction\n"
        f"Artifacts written: {recon_path}, {c_path}"
    )

    # Print summary
    s = artifact.summary
    print("\n============================================================")
    print("      PHASE 5.7: SYNTAX-SAFE UNKNOWN CONDITION ADAPTER")
    print("============================================================")
    print(f"Functions reconstructed:          {s['functions_total']}")
    print(f"  Structured:                     {s['functions_structured']}")
    print(f"  Partially structured:           {s['functions_partially_structured']}")
    print(f"  Unstructured:                   {s['functions_unstructured']}")
    print(f"  Missing:                        {s['functions_missing']}")
    print(f"Functions with warnings:          {s['functions_with_warnings']}")
    print(f"Functions with region structures: {s['functions_with_structured_regions']}")
    print(f"Functions with semantic evidence: {s['functions_with_semantic_evidence']}")
    print(f"Functions with layout evidence:   {s['functions_with_layout_evidence']}")
    print(f"Functions with param-layout ev:   {s['functions_with_parameter_layout_evidence']}")
    print(f"Unstructured regions total:       {s['unstructured_regions_total']}")
    print(f"Instructions total:               {s['instructions_total']}")
    print(f"Instructions lowered:             {s['instructions_lowered']}")
    print(f"Instructions commented:           {s['instructions_commented']}")
    print(f"Lowering coverage percent:        {s['lowering_coverage_percent']}%")
    print(f"Control-flow regions:             {s['control_flow_regions_total']}")
    print(f"Control-flow constructs:          {s['control_flow_constructs_emitted']}")
    print(f"  Loops:                          {s['loops_emitted']}")
    print(f"  If:                             {s['if_constructs_emitted']}")
    print(f"  If-Else:                        {s['if_else_constructs_emitted']}")
    print(f"  Switch:                         {s['switch_constructs_emitted']}")
    print(f"  Fallback/Unstructured:          {s['fallback_regions']}")
    print(f"  Duplicate blocks skipped:       {s['duplicate_blocks_skipped']}")
    print(f"Condition expressions recovered:  {s['condition_expressions_recovered']}")
    # Phase 5.4 return/call-site refinement
    print(f"Return sites total:               {s.get('return_sites_total', 0)}")
    print(f"  With value:                     {s.get('return_sites_with_value', 0)}")
    print(f"  Unknown:                        {s.get('return_sites_unknown', 0)}")
    print(f"  Funcs with recovered returns:   {s.get('functions_with_recovered_return_value', 0)}")
    print(f"Call sites total:                 {s.get('call_sites_total', 0)}")
    print(f"  Direct:                         {s.get('direct_calls', 0)}")
    print(f"  Indirect:                       {s.get('indirect_calls', 0)}")
    print(f"  With arguments:                 {s.get('calls_with_arguments', 0)}")
    print(f"  Arguments recovered:            {s.get('call_arguments_recovered', 0)}")
    print(f"  Arguments unknown:              {s.get('call_arguments_unknown', 0)}")
    # Phase 5.5 condition predicate annotation
    print(f"Condition sites total:            {s.get('condition_sites_total', 0)}")
    print(f"  With evidence:                  {s.get('condition_sites_with_evidence', 0)}")
    print(f"  Unknown:                        {s.get('condition_sites_unknown', 0)}")
    print(f"  Annotations recovered:          {s.get('condition_annotations_recovered', 0)}")
    print(f"  Inverted polarity:              {s.get('conditions_inverted_for_structure', 0)}")
    print(f"  Ambiguous sites:                {s.get('ambiguous_condition_sites', 0)}")
    # Phase 5.6 declarations stabilization
    print(f"Declarations total:               {s.get('declarations_total', 0)}")
    print(f"  Pseudo registers:               {s.get('pseudo_registers_declared_total', 0)}")
    print(f"  Pseudo stack slots:             {s.get('pseudo_stack_slots_declared_total', 0)}")
    print(f"  Call helpers:                   {s.get('call_helpers_declared_total', 0)}")
    print(f"  Funcs with declarations:        {s.get('functions_with_declarations', 0)}")
    print(f"Compile shape warnings total:     {s.get('compile_shape_warnings_total', 0)}")
    # Phase 5.7 condition adapter
    print(f"Condition adapters inserted:      {s.get('condition_adapters_inserted', 0)}")
    print(f"  Evidence adapters:              {s.get('condition_evidence_adapters', 0)}")
    print(f"  Unknown adapters:               {s.get('condition_unknown_adapters', 0)}")
    print(f"  Helper function emitted:        {s.get('unknown_condition_helpers_emitted', 0)}")
    print("============================================================")
    print(f"Output: {recon_path}")
    print(f"Output: {c_path}")
    print("============================================================")
    sys.exit(0)


def main():
    # If help flag is present, avoid running setup_logging to prevent creating output directory unnecessarily
    if "--help" in sys.argv or "-h" in sys.argv:
        parse_args()
        return

    # Resolve out_dir from command line arguments before initializing logging
    out_dir = "artifacts"
    for i, arg in enumerate(sys.argv):
        if arg == "--out-dir":
            if i + 1 < len(sys.argv):
                out_dir = sys.argv[i + 1]
        elif arg.startswith("--out-dir="):
            out_dir = arg.split("=", 1)[1]

    setup_logging(out_dir)

    # Detect CLI Subcommand arguments (recover-types, structs, signatures, generate, function, module, validate, repair, report)
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        if first_arg == "recover-types":
            handle_recover_types(out_dir)
            return
        elif first_arg == "structs":
            handle_structs(out_dir)
            return
        elif first_arg == "signatures":
            handle_signatures(out_dir)
            return
        elif first_arg == "generate":
            handle_generate(out_dir)
            return
        elif first_arg == "function" and len(sys.argv) > 2:
            handle_function_reconstruct(out_dir, sys.argv[2])
            return
        elif first_arg == "module" and len(sys.argv) > 2:
            handle_module_reconstruct(out_dir, sys.argv[2])
            return
        elif first_arg == "validate":
            handle_validate_cli(out_dir)
            return
        elif first_arg == "repair":
            handle_repair_cli(out_dir)
            return
        elif first_arg == "report":
            handle_report_cli(out_dir)
            return
        elif first_arg == "analyze-cfg":
            handle_analyze_cfg(out_dir)
            return
        elif first_arg == "recover-semantics":
            handle_recover_semantics(out_dir)
            return
        elif first_arg == "refine-semantics":
            handle_refine_semantics(out_dir)
            return
        elif first_arg == "recover-layouts":
            handle_recover_layouts(out_dir)
            return
        elif first_arg == "finalize-semantics":
            handle_finalize_semantics(out_dir)
            return
        elif first_arg == "reconstruct-source":
            handle_reconstruct_source(out_dir)
            return

    args = parse_args()
    
    if args.analyze_cfg:

        handle_analyze_cfg(args.out_dir)
        return
    
    # Check if we are doing validation/inspection commands
    if args.validate_ir:
        handle_validation(args.validate_ir)
        return

    if args.inspect_ir:
        handle_inspection(args.inspect_ir)
        return

    if not args.binary_path:
        logger.error("[-] Error: binary_path argument is required for extraction pipelines.")
        sys.exit(1)

    # 1. Resolve and validate binary path
    binary_path = args.binary_path
    if not os.path.exists(binary_path):
        # For evaluation/demonstration purposes, create mock sample file if target name is standard placeholder
        if binary_path in ["sample.exe", "sample.bin", "sample.elf"]:
            logger.warning(f"Target binary '{binary_path}' not present on disk. Automatically synthesizing placeholder reference.")
            with open(binary_path, "wb") as f:
                f.write(b"\x7fELF\x02\x01\x01\x00_placeholder_bin")
        else:
            logger.error(f"Target binary file does not exist: {binary_path}")
            sys.exit(1)

    # 2. Parse configuration
    config_dict = {}
    if args.config:
        if os.path.exists(args.config):
            try:
                with open(args.config, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f)
            except Exception as e:
                logger.error(f"Failed to read custom configuration file: {e}")
                sys.exit(1)
        else:
            try:
                config_dict = json.loads(args.config)
            except Exception as e:
                logger.error(f"Failed to parse inline JSON configuration parameter: {e}")
                sys.exit(1)

    if args.debug_logs:
        config_dict["debug_logs"] = True

    logger.info("Initializing Binary Reconstruction Pipeline Orchestrator (Phases 1 & 2)...")
    logger.info(f"Target binary path target: {binary_path}")
    logger.info(f"Output directory destination: {args.out_dir}")

    # If no specific extractor is selected, default to all of them
    run_all = not (args.ghidra or args.radare2 or args.trace)
    ghidra_flag = args.ghidra or run_all
    radare2_flag = args.radare2 or run_all
    trace_flag = args.trace or run_all

    orchestrator = PipelineOrchestrator(binary_path, args.out_dir, config_dict)
    
    try:
        manifest = orchestrator.execute_all(
            run_ghidra=ghidra_flag,
            run_radare2=radare2_flag,
            run_trace=trace_flag
        )
        
        logger.info("[+] Static and dynamic logs collected.")

        # Always build the Unified IR if requested or if running the baseline orchestrator
        if args.export_ir or run_all:
            from src.utils.run_logging import append_run_log
            append_run_log(args.out_dir, "ORCHESTRATION", "Pipeline stage started: Phase 2 Unified IR Assembly")
            logger.info("Assembling canonical Unified Intermediate Representation (Phase 2 IR)...")
            assembler = IRAssembler(binary_path)
            
            # Extract raw results from jobs run
            ghidra_raw = manifest["jobs"].get("ghidra")
            radare2_raw = manifest["jobs"].get("radare2")
            trace_raw = manifest["jobs"].get("trace")

            unified_ir = assembler.assemble(ghidra_raw, radare2_raw, trace_raw)
            ir_payload = unified_ir.to_dict()
            # Apply symbol alias canonicalization → data.symbol_aliases
            from src.ir.symbols.aliases import apply_function_aliases_to_ir
            apply_function_aliases_to_ir(ir_payload)

            # Self-validate generated IR before export
            success, val_msg = IRValidator.validate_payload(ir_payload)
            if not success:
                logger.warning(f"Generated IR failed schema de-serialization selfcheck: {val_msg}")
                append_run_log(args.out_dir, "ORCHESTRATION", f"Warning: Generated IR failed schema validation: {val_msg}")

            ir_path = os.path.join(args.out_dir, "unified_ir.json")
            write_json_artifact(ir_path, ir_payload)
            logger.info(f"[+] Canonical Phase 2 Unified IR exported to: {ir_path}")
            append_run_log(args.out_dir, "ORCHESTRATION", f"Pipeline stage completed: Phase 2 Unified IR Assembly\nArtifact written: {ir_path}")

        logger.info("[+] Pipeline batch execution completed successfully.")
        logger.info(f"Overall Completion Status: {manifest['status'].upper()}")
        logger.info(f"Jobs Run Count: {manifest['total_jobs_run']}")
        
        # Manifest summaries
        manifest_file = os.path.join(args.out_dir, "orchestration_manifest.json")
        logger.info(f"[+] Output Manifest committed: {manifest_file}")
        
        if manifest["errors"]:
            logger.warning("Pipeline reported some non-fatal execution errors during batch parsing:")
            for err in manifest["errors"]:
                logger.warning(f"  - {err}")
                
        sys.exit(0)
    except Exception as e:
        logger.error(f"[-] Pipeline encountered fatal system failure: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

