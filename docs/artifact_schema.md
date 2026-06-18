# Artifact Schema Definitions

Hephaestus uses standard JSON structures to store state between stages. This ensures reproducibility and strict decoupling of extraction, analysis, and source generation.

## Schema Registry

| Artifact Filename | Phase / Stage | Version Identifier | Purpose |
|---|---|---|---|
| `unified_ir.json` | assembly | `2.0.0` | Normalizes extractors data into functions, blocks, instructions. |
| `type_recovery.json` | recover_semantics | `4A.1.0` | Initial inferred parameter names, types, and variables. |
| `semantic_recovery.json` | refine_semantics | `4B.1.0` | Constrained parameter names and ABI bindings list. |
| `layout_recovery.json` | recover_layouts | `4C.1.0` | Offset-to-size observation lists for memory. |
| `phase4_semantics.json` | finalize_semantics | `4D.1.0` | Unified semantics and variable list for code generation. |
| `source_reconstruction.json` | reconstruct_source | `5.7.2` | Lowered functions, block sequences, and summary statistics. |
| `recovered.c` | reconstruct_source | (executable C code) | Valid syntax representation of recovered binary functions. |
| `pipeline_manifest.json` | pipeline | `pipeline-1.0` | Pipeline execution times, outputs, and status. |
| `stress_report.json` | stress-test | `stress-1.0` | Compilation, correctness, and decompiler status for stress binaries. |
