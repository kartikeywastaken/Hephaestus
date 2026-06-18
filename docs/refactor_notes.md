# Refactoring and Stabilization Notes (Phase 5.9)

Phase 5.9 is a maintenance and stabilization phase. Decompiler behavior is strictly behavior-locked, with zero updates to decompiler capabilities.

## Code Partitioning Goals

1. **Pipeline Definitions**: Centralize stages order and output dependencies in `stage_defs.py`.
2. **Clang Diagnostics Separation**: Centralize Clang execution paths to avoid repeating compilation checker code across `stress.py` and `checks.py`.
3. **C Emitter Decomposition**: Extract name sanitization, source summary calculations, and macro/typedef adapters definitions out of `c_emitter.py` and `reconstructor.py`.
4. **ARM64 Lowerer Split**: Separate the large single lowerer file `arm64.py` into distinct sub-modules inside `arm64_parts/` package (registers, operands, memory, conditions, arithmetic, load/store, paired, branches, calls, unsupported).
