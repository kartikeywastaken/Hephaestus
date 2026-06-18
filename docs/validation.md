# Hephaestus Validation System — Phase 6.1

This document describes the static validation, artifact consistency, and safety policy checking layer introduced in Phase 6.1.

## Core Principles

> [!IMPORTANT]
> - **Validation is read-only**: The validator will calculate hashes of input files before and after execution to guarantee that no modifications or repairs are performed on decompiler source code outputs.
> - **No Repair**: The validation layer identifies inconsistencies and violations but does **not** attempt to repair them.
> - **No Semantic Equivalence Claims**: The validation layer checks syntax safety and conservative policy invariants. It does **not** prove semantic correctness or equivalence to original source behavior.

---

## Standalone Subcommand

Validate a generated output directory:

```bash
python3 main.py validate --out-dir artifacts
```

### Options

- `--out-dir DIR`: Path to output artifacts (default: `artifacts`).
- `--strict`: Enable strict mode, promoting recommended missing files, schema version mismatches, and certain warnings (like cset/ldp commented warnings) to hard errors, failing the overall report status.
- `--no-clang`: Skip executing the system's `clang -fsyntax-only` check.
- `--json`: Output a compact single-line JSON summary to `stdout` instead of regular logs.
- `--require-evidence-index`: Fail validation if `evidence_index.json` is missing.

---

## E2E Pipeline Integration

Run validation automatically at the end of the `run-all` compiler pipeline:

```bash
python3 main.py run-all ./t --ghidra --radare2 --out-dir artifacts --clean --validate
```

To fail the pipeline execution when static checks fail:

```bash
python3 main.py run-all ./t --ghidra --radare2 --out-dir artifacts --clean --validate-strict
```

---

## Check Categories

All checks fall into the following modules:

1. **Schema Check (`schemas.py`)**: Validates schema versions of input artifacts.
2. **Summary Metrics (`metrics.py`)**: Checks instruction totals, mathematical bounds, non-negativity, and condition expression zeros.
3. **C Safety (`c_safety.py`)**: Strips comments and checks for structural safety invariants (`struct`, `->`, empty conditions, raw ARM memory leaks, fake flags, and forbidden `tmp_`/`arg`/`stack_` conditions).
4. **Helper Consistency (`helpers.py`)**: Verifies correct usage and definitions for internal helpers `HEPHAESTUS_UNKNOWN_COND` and `HEPHAESTUS_CSET`.
5. **Evidence Checks (`evidence.py`)**: Validates consistency between metadata summary and function-level direct/indirect call and return site logs.
6. **Evidence Index Checks (`checks.py`)**: Validates presence, schema-version `evidence-index-1.0`, summary key sums, precise unsupported instruction accounting, and checks for unknown categories in `evidence_index.json`.
7. **Pipeline Manifest (`manifest_checks.py`)**: Checks stage ordering sequence and checks stage outputs on disk.
8. **Clang syntax check (`clang_check.py`)**: Performs compilation verification on `recovered.c`.


---

## Report Schema (`validation_report.json`)

The report conforms to schema version `validation-1.0`.

```json
{
  "schema_version": "validation-1.0",
  "phase": "6.1",
  "status": "ok",
  "strict": false,
  "out_dir": "artifacts",
  "started_at": "2026-06-18T00:00:00Z",
  "finished_at": "2026-06-18T00:00:01Z",
  "input_artifacts": {
    "pipeline_manifest": "pipeline_manifest.json",
    "unified_ir": "unified_ir.json",
    "phase4_semantics": "phase4_semantics.json",
    "source_reconstruction": "source_reconstruction.json",
    "recovered_c": "recovered.c"
  },
  "checks": {
    "required_artifacts_present": {
      "status": "ok",
      "severity": "error",
      "message": "All required artifacts are present.",
      "details": {}
    }
  },
  "findings": [],
  "summary": {
    "errors": 0,
    "warnings": 0,
    "info": 0,
    "checks_total": 0,
    "checks_ok": 0,
    "checks_failed": 0,
    "strict_failures": 0
  }
}

---

## Default vs Strict Mode

The validation system supports two modes of execution depending on the severity of policy enforcement:

### Default Mode
In default mode, the validator reports non-fatal evidence discrepancies, missing recommended artifacts (e.g., intermediate semantics files), and compiler warnings as `warning`. The subcommand returns exit code `0`.

> [!NOTE]
> A warning status does not mean the recovered output is wrong. It means the validator found non-fatal missing evidence, approximate accounting mismatch, or an optional check that could not be completed.

### Strict Mode
In strict mode, the validator promotes recommended missing artifacts, schema version mismatches, and approximate evidence-accounting mismatches to `failed` errors. The subcommand returns exit code `1`.

> [!NOTE]
> A failed strict validation does not automatically mean the recovered output is semantically wrong. It means strict validation policy found an error-level artifact, schema, safety, or evidence-consistency issue.
> 
> A failed strict validation is a policy failure, not a proof of incorrect reconstruction.

---

## Resolution of VAL-EVID-008 (Phase 6.2 Statement-Level Traceability)

In Phase 6.1, strict validation could fail due to **`VAL-EVID-008` (Unsupported comment accounting mismatch)**. This was caused by an approximate evidence-accounting discrepancy because Phase 6.1 could not distinguish true unsupported instructions from conservative comment-lowered statements.

In Phase 6.2, this approximate check is resolved and bypassed when a statement-level `evidence_index.json` is present. The evidence index explicitly categorizes C lines into 13 primary categories, distinguishing:
- truly unsupported instructions (`true_unsupported`)
- conservative comment-lowered instructions (`comment_lowered`)
- branch evidence comments (`branch_evidence`)
- syntax adapter comments (`syntax_adapter`)
- helper comments/definitions (`helper`)

This enables a precise validation check (`evidence_index_unsupported_accounting`) to verify that the `true_unsupported` count matches `unsupported_instruction_kinds` perfectly, without false positives.

