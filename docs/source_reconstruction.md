# Source Reconstruction Process

The final stage of the Hephaestus pipeline processes semantic and control-flow information to construct a valid C source skeleton (`recovered.c`).

## Lowering Pipeline

Each instruction from `unified_ir.json` is passed through the ARM64 lowerer:
1. **ABI Mapping**: Maps registers like `x0`, `x1` to function parameters `arg0`, `arg1` if backed by validated ABI binding evidence.
2. **Registers**: Map temporary registers to local pseudovariables (e.g. `tmp_x8`).
3. **Memory Accesses**: Express stack layout offsets conservatively as `stack_0`, `stack_m20` or pointers.
4. **Statements Generation**: Generates standard assignment, store, or call statements.

## Control Flow Synthesis

The structured tree from `structuring_regions.json` is traversed recursively:
- **Sequence nodes** emit statements sequentially.
- **Branch annotations** are preserved as comments to avoid fabricating conditions.
- **Adapter Helpers** are emitted to ensure compilation correctness:
  - `HEPHAESTUS_UNKNOWN_COND`: Preserves original branch evidence syntax in non-executable branches.
  - `HEPHAESTUS_CSET`: Handles ARM64 conditional flags assignment syntax.
