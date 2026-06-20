# Hephaestus Phase 7 — Human-Readable C Output

Phase 7 introduces **static readability reconstruction** for Hephaestus, generating a best-effort, human-readable C file `recovered_readable.c` and associated reports.

## Hephaestus Phase 7.1 — Static Predicate Recovery

Phase 7.1 focuses on replacing unreadable `HEPHAESTUS_UNKNOWN_COND("...")` condition adapters with statically inferred C boolean expressions when disassembly evidence is local and straightforward (e.g. CBZ, CBNZ, TBZ, TBNZ, and CMP branches).

## Hephaestus Phase 7.2 — Static Readable Symbol and Local Promotion

Phase 7.2 performs deterministic symbol promotion to clean up low-level variable names in `recovered_readable.c` without semantic guessing.

### Naming Policy
1. **Stack Slots**:
   - Promoted to `local_mN` (for negative frame pointer offsets) and `local_N` (for positive stack pointer offsets) to preserve decimal offsets as evidence.
   - Example: `stack_m16 -> local_m16`, `stack_24 -> local_24`.
2. **Parameters**:
   - Promoted to `param_0`, `param_1`, etc., only when backed by parameter metadata in `source_reconstruction.json` or `type_recovery.json`.
3. **Temporaries**:
   - Remain unchanged as `tmp_*` by default to preserve register traceability.
   - If `--promote-temps` is enabled, they are promoted globally to `temp_*` (e.g., `tmp_w8 -> temp_w8`, `tmp_sp -> temp_sp`).
4. **Function Names**:
   - Placeholder names like `call_0xABC` or `func_1000` are renamed to their canonical symbols (e.g. `printf`) only if mapping is explicitly backed by reconstruction metadata and has no conflicts.

### Hephaestus Phase 7.2.1 & 7.2.2 — Hardening & Guardrails
- **Phase 7.2.1**: Emits stability warnings for missing declarations, cleans up forward declarations, and rolls back all readability adjustments if `clang -fsyntax-only` fails.
- **Phase 7.2.2**: Adds signature normalization guardrails for hosted `main` signature validation.

---

## Hephaestus Phase 7.3 — Static Expression Simplification

Phase 7.3 introduces a token-safe expression simplification pass. Simplifications are conservative, evidence-preserving, and clang-gated (failures roll back to Phase 7.2.1).

### Simplification Rules
1. **Category A — Identity Arithmetic**: Simplifies arithmetic operations with numeric zero or one identity values (e.g., `x + 0 -> x`, `x * 1 -> x`).
2. **Category B — Redundant Parentheses**: Removes single-wrap redundant parentheses around a simple operand (e.g., `(x) -> x`), excluding C cast type keywords.
3. **Category C — RHS Context Gating**: Gates expression simplification strictly to the RHS of simple assignment statements to prevent modifying control flow predicates, return expressions, pointer dereferences, array indices, or macro structures.
4. **Category D — Copy-Op-Store Fold**: Folds three-line register-to-stack copy-modify-store sequences into direct operations (e.g. `tmp = local; tmp = tmp + 1; local = tmp; -> local = local + 1;`) with strict width checks and usage boundaries.

---

## Hephaestus Phase 7.3.1 — Expression Simplification Hardening

Phase 7.3.1 refactors Phase 7.3 into a clean three-module architecture and adds four new categories of expression simplification:

### Architecture
- `src/readability/expression_models.py`: Data structures (`RuleResult`, `ExprSimplification`, `ExprSimplificationStats`).
- `src/readability/expression_rules.py`: Separate, modular functions for each simplification category.
- `src/readability/expression_simplification.py`: Pipeline orchestrator and token-scanning driver.

### Hardened Categories
1. **Category E — Self-Assignment Removal**: Trivial assignments are removed entirely and replaced with an evidence comment (e.g., `tmp_w8 = tmp_w8; -> /* self-assignment removed */`).
2. **Category F — Double Parentheses Collapse**: Collapses exactly two levels of redundant wrapping parentheses around simple operands (e.g., `((x)) -> x`), excluding cast contexts.
3. **Category G — Temp Copy Roundtrip**: Consecutive two-line roundtrip copy sequences are folded and replaced with an evidence comment (e.g., `tmp = local; local = tmp; -> /* temp copy roundtrip removed ... */`), subject to usage guards.
4. **Category H — Mask-Cast**: Flag-gated same-type double casts from the known safe width-preserving set (`u8`/`u16`/`u32`/`u64`) are collapsed to identity (e.g., `x = (u32)(u32)x; -> x = x;`).

---


## Standalone Subcommand

You can run readability recovery on any decompiler outputs directory containing `recovered.c` using:

```bash
python3 main.py build-readable --out-dir artifacts [FLAGS]
```

### CLI Options

- `--out-dir DIR`: Specify target directory (default: `artifacts`).
- `--json`: Print clean JSON summary to stdout (suppresses noise).
- `--markdown`: Generate `readability_report.md` along with the JSON report.
- `--require-quality-gate`: Fail the command if `quality_gate.json` is missing.
- `--ignore-quality-gate`: Bypass Quality Gate checks.
- `--promote-symbols`: Enable Phase 7.2 symbol promotion (default enabled).
- `--no-promote-symbols`: Disable Phase 7.2 symbol promotion (fallback to Phase 7.1 behavior).
- `--promote-temps`: Enable temporary registers style promotion (default disabled).
- `--simplify-expressions`: Enable Phase 7.3 expression simplification (default enabled).
- `--no-simplify-expressions`: Disable all Phase 7.3 expression simplification.
- `--no-copy-op-store-simplification`: Disable Category D (copy-op-store) only.
- `--enable-mask-cast-simplification`: Enable Category H (mask-cast) simplification (default disabled).

---

## E2E Pipeline Integration

You can execute readability recovery as part of the E2E `run-all` pipeline by passing the `--readable` flag:

```bash
python3 main.py run-all ./t \
  --ghidra \
  --radare2 \
  --out-dir artifacts \
  --clean \
  --validate \
  --trace-report \
  --readable
```

Pass E2E options:
- `--no-promote-symbols` to run Phase 7.1 predicate recovery only.
- `--promote-temps` to promote temporary register names globally.

---

## Outputs

- **`recovered_readable.c`**: Emitted C file containing predicate recoveries and symbol promotions. Renames are token-safe and respect comments, string literals, and character literals.
- **`readability_report.json`**: Conforms to schema `readability-1.3` when expression simplification is enabled, documenting promotions, skipped promotions (due to name collisions or conflicts), and expression simplification counts/records.
- **`readability_report.md`**: Human-readable Markdown summary including expression simplification tables and status.

