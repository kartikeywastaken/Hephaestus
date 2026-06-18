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
- **`readability_report.json`**: Conforms to schema `readability-1.1` when symbol promotion is enabled, documenting promotions, skipped promotions (due to name collisions or conflicts), and statistics.
- **`readability_report.md`**: Human-readable Markdown summary.

