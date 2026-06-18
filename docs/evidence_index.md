# Hephaestus Statement-Level Evidence Traceability — Phase 6.2

This document describes the statement-level evidence traceability and auditability layer introduced in Phase 6.2.

## Core Principle

> [!IMPORTANT]
> **Auditability and Traceability Focus**: Phase 6.2 improves **auditability and traceability**, not decompilation intelligence.
> - Emitted `recovered.c` and `source_reconstruction.json` remain completely unmodified and behavior-locked.
> - Input file hashes are verified before and after constructing the index to guarantee read-only behavior.
> - A new separate audit artifact, `evidence_index.json` (schema `evidence-index-1.0`), is generated under the output directory.

---

## Standalone Subcommand

Build the statement-level evidence index for a generated output directory:

```bash
python3 main.py build-evidence-index --out-dir artifacts
```

### Options

- `--out-dir DIR`: Path to output artifacts (default: `artifacts`).
- `--json`: Output a compact single-line JSON summary to `stdout` instead of regular logs.

---

## E2E Pipeline Integration

Run evidence index generation automatically before validation at the end of the `run-all` compiler pipeline:

```bash
python3 main.py run-all ./t --ghidra --radare2 --out-dir artifacts --clean --evidence-index
```

If `--validate` or `--validate-strict` is used, the evidence index is built automatically prior to running validation checks:

```bash
python3 main.py run-all ./t --ghidra --radare2 --out-dir artifacts --clean --validate
```

---

## Statement Classification & Priority Precedence

Every line of emitted C code (statement) is parsed, text-normalized, and assigned to **exactly one primary category** based on the following deterministic priority order:

1. **`helper`**: Internal decompiler helper function or macro definitions (e.g. `HEPHAESTUS_UNKNOWN_COND`).
2. **`declaration`**: Typedefs, function prototypes, or conservative pseudo local variable declarations (e.g. `u64 tmp_sp = 0;`).
3. **`function_signature`**: Line containing a function's starting signature (e.g. `int main(void)`).
4. **`empty_function_scaffold`**: Placeholder comment/line for an empty body (e.g. `/* TODO: body reconstruction pending */`).
5. **`syntax_adapter`**: Condition wrapper calls (e.g. `HEPHAESTUS_UNKNOWN_COND(0)` or `HEPHAESTUS_CSET(1)`).
6. **`true_unsupported`**: A conservative comment-lowered statement representing a true decompiler unsupported gap (the parsed mnemonic exists inside the `unsupported_instruction_kinds` list from the reconstruction summary).
7. **`branch_evidence`**: Comments describing branch target address or conditional checks (e.g. `/* branch to 0x100000578 */`).
8. **`call`**: Call statements (e.g. `call_0x10000();` or `/* indirect call */`).
9. **`return`**: Return statements or comments (e.g. `return 0;` or `/* return via x0 */`).
10. **`control_flow_scaffold`**: Compiler structure elements (e.g. `if (`, `}`, `else`).
11. **`comment_lowered`**: Other commented instructions or commentary fallbacks (not classified as true unsupported instructions).
12. **`executable_lowered`**: Ordinary lowered executable statements (ending in `;`).
13. **`unknown`**: Any statement that does not match any of the above categories.

This strict precedence guarantees that the sum of the counts of all 13 categories is exactly equal to `statements_total`.

---

## Validation Checks on Evidence Index

When validation runs:
- If `evidence_index.json` is successfully loaded:
  - The validator replaces the approximate `VAL-EVID-008` unsupported comment accounting check with precise evidence index audits.
  - `VAL-EVID-008` is resolved and bypassed.

The validator runs 5 new checks:
1. **`evidence_index_present`**: Verifies that the evidence index is present.
   - Errors if `--require-evidence-index` is specified and missing.
   - Warnings if `--strict` is active and missing.
2. **`evidence_index_schema_valid`**: Verifies that the schema version is `evidence-index-1.0`.
3. **`evidence_index_summary_valid`**: Verifies that all category counts are non-negative and sum exactly to `statements_total`.
4. **`evidence_index_unsupported_accounting`**: Performs precise accounting verifying that `true_unsupported_statements` matches the sum of `unsupported_instruction_kinds` in the source reconstruction summary.
5. **`evidence_index_unknown_categories`**: Warns (or errors in strict mode) if any statements are classified as `unknown` (`unknown_statement_category > 0`).
