# Hephaestus Quality Gate — Phase 6.4

This document describes the design, execution, schemas, and scoring rules for the static Quality Gate introduced in Phase 6.4.

---

## Core Purpose

The Quality Gate acts as a readability readiness gate that answers:
```text
Are the current decompiler artifacts safe and useful enough to feed into Phase 7 readable reconstruction?
```

It compiles a gate report (`quality_gate.json` and optionally `quality_gate.md`) evaluating:
- Missing required outputs or schemas
- Static validation safety errors
- Traceability coverage statistics
- Mathematical risk and readability scores

This prevents Phase 7 static readability reconstruction from attempting to clean up or beautify broken or unsafe outputs.

> [!IMPORTANT]
> **Read-Only Gate**: The Quality Gate is strictly read-only. It does not modify code outputs or improve `recovered.c`. It only assesses correctness and produces hint flags to guide Phase 7.

---

## Subcommand Execution

Run the quality gate manually on a directory of output artifacts:

```bash
python3 main.py quality-gate --out-dir artifacts --markdown
```

### Options
- `--out-dir DIR`: Directory containing Hephaestus output artifacts (defaults to `artifacts`).
- `--markdown`: Generates a human-readable `quality_gate.md` file.
- `--json`: Outputs a compact single-line JSON summary to stdout.
- `--strict`: Promotes strict warning conditions to gate failure.

### Standalone Exit Codes
- `0`: Status is `ready` or `review` (safe to proceed, review warnings).
- `1`: Status is `blocked` (safety/policy errors or missing critical files, do not proceed).
- `2`: Internal crash or CLI usage error.

---

## E2E Pipeline Integration

Run the quality gate automatically at the end of the `run-all` compiler pipeline:

```bash
python3 main.py run-all ./t --ghidra --radare2 --out-dir artifacts --clean --quality-gate
```

If `--quality-gate` is passed, the runner automatically schedules `build_evidence_index`, `validate`, `build_trace_report`, and `quality_gate` stages sequentially after source reconstruction.

---

## Scoring Formulas

Scores are calculated using simple deterministic formulas:

1. **`evidence_coverage_score`**:
   `evidence_backed_statements / statements_total * 100` (defaults to `0` if statements are 0).
2. **`traceability_score`**:
   `statements_with_known_confidence / statements_total * 100` where known labels include `evidence_backed`, `generated_scaffold`, `syntax_adapter`, and `commentary_only`.
3. **`validation_health_score`**:
   `100 - (25 * validation_errors) - (5 * validation_warnings)`, clamped to `[0, 100]`.
4. **`risk_score`**:
   Starts at `0`. Adds:
   - `30` if validation status failed
   - `10` if validation status warning
   - `20` if `unknown_statement_ratio > 0.15`
   - `10` if `true_unsupported_statements > 0`
   - `10` if `high_attention_lines > 0`
   - `10` if `unattached validation findings > 0`
   Clamped to `[0, 100]`.
5. **`readability_readiness_score`**:
   `0.35 * evidence_coverage_score + 0.30 * traceability_score + 0.25 * validation_health_score + 0.10 * (100 - risk_score)`, rounded to 2 decimals.

---

## Decision Logic

The gate status evaluates to exactly one of three values:

- **`blocked`**: Proceeding to Phase 7 is disabled. Triggered if required files are missing, validator findings in safety categories (`condition_safety`, `c_safety`, `helper_consistency`, `schema`, `artifact_presence`, `read_only_integrity`) have error severity, schema versions are invalid, condition expressions recovered are non-zero, watched files were mutated during pipeline run, or `clang_syntax` errors are greater than 0.
- **`review`**: Proceeding is allowed, but manual inspection is recommended and downstream outputs (`recovered_readable.c`) should be flagged as lower confidence. Triggered if validator status is warning, strict validation failed due to non-hard policy errors (e.g., strict accounting mismatches), unknown statement ratio > 15%, true unsupported > 0, high attention lines > 0, unattached findings exist, readability readiness score < 70, risk score > 40, or `clang_syntax` warnings only (errors == 0).
- **`ready`**: Safe to proceed. Triggered if all conditions are healthy.

### Clang Syntax Check Rules
- **Compiler syntax errors** (`errors > 0`) produce **blocked** status.
- **Compiler warnings only** (`errors == 0` and `warnings > 0`) produce **review** status.
- **Strict validation failures** do not automatically block Phase 7 unless they correspond to a hard blocker category.
