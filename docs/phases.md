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
- **Phase 6 (Future)**: Code validation, behavior repair, and advanced type synthesis.
