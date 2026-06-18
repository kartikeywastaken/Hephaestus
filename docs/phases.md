# Hephaestus Developmental Phases

This document lists the history of developmental milestones for the Hephaestus framework.

## Phase Chronology

- **Phase 1: Binary Extraction Foundations**: Base scripts for Ghidra and Radare2 disassembly extraction.
- **Phase 2: Unified Intermediate Representation**: Normalization of schemas across multiple extraction outputs.
- **Phase 3: Control Flow Graph Analysis**: Basic block structuring, acyclic tree identification, loops detection.
- **Phase 4: Variable & Type Inference**: Basic semantic recovery, parameter matching, signature estimation.
- **Phase 5: Source Reconstruction**: Translating instructions to C statements, handling registers, memory accesses, stack.
  - **Phase 5.7**: Instruction lowering coverage enhancements for ARM64 math and memory instructions.
  - **Phase 5.8**: Integration of run-all orchestrator command, clean artifact folders layout, stress harness.
  - **Phase 5.9**: Refactor and stabilization. Centralizing stages definition, separating helper APIs, and partitioning the ARM64 lowerer.
- **Phase 6: Validation, Indexing, and Gatekeeping**:
  - **Phase 6.1: Static Validation and Evidence Consistency Checks**: Read-only validation checking schema versions, source summary metrics, C safety policy, helper consistency, and manifest correctness.
  - **Phase 6.2: Statement-Level Evidence Traceability**: Categorizes and normalizes emitted code lines in `recovered.c` into 13 primary categories to resolve approximate comment accounting mismatches.
  - **Phase 6.3: Evidence Trace Reports**: Generates machine-readable `trace_report.json` and human-readable `trace_report.md` explaining line-by-line statement classification, confidence levels, and validation findings mapping.
  - **Phase 6.4: Readability Readiness Quality Gate**: Evaluates readiness status (`ready`/`review`/`blocked`) using scoring and blocking rules on coverage, health, traceability, and risk.
- **Phase 7: Static Readability Reconstruction (Future)**: Enhancing C skeleton readability using structured control flow transforms, predicate recovery, and variable binding refinements.
