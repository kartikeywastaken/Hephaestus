# Hephaestus Evidence Trace Reports — Phase 6.3

This document details the architecture, schemas, and usage of decompiler trace reports introduced in Phase 6.3.

---

## Core Purpose

Decompiled C lines produced by Hephaestus are the result of multi-phase transformations, combining structured C constructs, pseudo registers declarations, type refinements, syntax-safety fallback adapters, and inline comments.

The Trace Report correlates:
- **emitted source lines** of `recovered.c`
- **confidence categories** (derived from instruction provenance and compiler layout evidence)
- **validation findings** (mapping errors/warnings back to the exact code statement)

This provides complete line-by-line auditability and validation explainability for downstream systems and human auditors.

---

## Standalone Subcommand

Build a trace report for a generated output directory containing reconstructed artifacts:

```bash
python3 main.py build-trace-report --out-dir artifacts --markdown
```

### Options
- `--out-dir DIR`: Path to output artifacts (default: `artifacts`).
- `--markdown`: Generate a human-readable summary file `trace_report.md`.
- `--json`: Output a compact single-line JSON summary to stdout.
- `--require-validation`: Fail if `validation_report.json` is missing.
- `--no-require-evidence-index`: Do not fail if `evidence_index.json` is missing.

---

## E2E Pipeline Integration

Run trace report generation automatically at the end of the `run-all` compiler pipeline:

```bash
python3 main.py run-all ./target_binary --ghidra --radare2 --out-dir artifacts --clean --trace-report
```

---

## Statement Classification & Explanation Rules

Emitted C statements are categorized into 13 primary categories. Each combination of statement category and confidence tier maps to a deterministic short explanation:

| Category | Confidence Tier | Short Explanation |
| :--- | :--- | :--- |
| `executable_lowered` | `evidence_backed` | Executable lowered statement backed by instruction evidence. |
| `executable_lowered` | *(other)* | Executable lowered statement without detailed instruction provenance in the current artifacts. |
| `true_unsupported` | *(any)* | Instruction was not lowered and is preserved as an unsupported statement/comment. |
| `comment_lowered` | *(any)* | Recognized instruction or event preserved as conservative commentary rather than executable C semantics. |
| `branch_evidence` | *(any)* | Control-flow evidence preserved as a comment; no executable condition was recovered. |
| `syntax_adapter` | *(any)* | Syntax adapter emitted to keep recovered C compilable without inventing semantics. |
| `helper` | *(any)* | Generated helper used by syntax adapters; not recovered source logic. |
| `declaration` | *(any)* | Generated pseudo declaration for recovered temporaries, stack slots, helpers, or typedefs. |
| `call` | *(any)* | Call statement or indirect-call evidence derived from call-site recovery/lowering. |
| `return` | *(any)* | Return statement/comment derived from ABI return recovery or conservative fallback. |
| `control_flow_scaffold` | *(any)* | Generated control-flow scaffold preserving structured regions without inventing high-level conditions. |
| `function_signature` | *(any)* | Generated function signature derived from recovered symbol/type metadata. |
| `empty_function_scaffold`| *(any)* | Generated empty-function scaffold for a function with no recovered body evidence. |

---

## Prioritized Attention Selector

Each statement is assigned an **Attention Level** calculated using prioritized rules:
1. **`error`**: Assigned if any validation finding with severity `error` or `failed` is attached to the statement.
2. **`warning`**: Assigned if any validation finding with severity `warning` is attached, or if category/confidence is `unknown`, or if the category is `true_unsupported`.
3. **`info`**: Assigned if the category is `comment_lowered`, `branch_evidence`, or `syntax_adapter` (representing conservative or scaffold commentary).
4. **`none`**: Default level for fully verified, lowered executable statements, helper definitions, and declarations.

---

## Findings Matching Algorithm

The trace builder correlates validation findings to statements by applying a priority-based matching algorithm:
1. **Line number exact**: Match a finding to a statement sharing the exact line number on `recovered.c`.
2. **Statement ID exact**: Match a finding to a statement sharing the exact `statement_id`.
3. **Function + Block ID**: Match a finding to the statement inside the specified function matching the instruction block ID.
4. **Function + Instruction Address**: Match a finding to the statement inside the specified function matching the instruction absolute memory address.
5. **Category Fallback**: If a finding mentions a function name only, attach it to the `function_signature` statement of that function.
6. **Unattached Findings**: Any findings that cannot be matched to a statement are collected in `unattached_validation_findings`.

---

## Output Artifact Schema (`trace_report.json`)

The report payload conforms to the schema `trace-report-1.0`:

```json
{
  "schema_version": "trace-report-1.0",
  "phase": "6.3",
  "generated_at": "2026-06-18T00:00:00Z",
  "input_artifacts": {
    "source_reconstruction": "source_reconstruction.json",
    "recovered_c": "recovered.c",
    "evidence_index": "evidence_index.json",
    "validation_report": "validation_report.json"
  },
  "status": "warning",
  "summary": {
    "functions_total": 0,
    "statements_total": 0,
    "evidence_backed_statements": 0,
    "generated_scaffold_statements": 0,
    "syntax_adapter_statements": 0,
    "commentary_only_statements": 0,
    "unknown_confidence_statements": 0,
    "validation_findings_total": 0,
    "validation_errors": 0,
    "validation_warnings": 0,
    "high_attention_lines": 0
  },
  "category_summary": {},
  "confidence_summary": {},
  "functions": [
    {
      "name": "main",
      "c_name": "main",
      "entry_point": "0x1000",
      "statements_total": 0,
      "category_summary": {},
      "confidence_summary": {},
      "statements": [
        {
          "statement_id": "stmt_000001",
          "line_number": 12,
          "category": "executable_lowered",
          "confidence": "evidence_backed",
          "statement_text": "x = x + 1;",
          "attention_level": "none",
          "validation_findings": [],
          "short_explanation": "Executable lowered statement backed by instruction evidence.",
          "evidence": {
            "block_id": "block_0",
            "instruction_address": "0x1000",
            "instruction_mnemonic": "add",
            "raw_instruction": "add x0, x0, #1",
            "evidence_sources": []
          },
          "notes": []
        }
      ],
      "attention_items": []
    }
  ],
  "global_statements": [],
  "validation_findings_by_category": {},
  "unattached_validation_findings": [],
  "diagnostics": []
}
```

---

## Downstream Consumption: Phase 6.4 Quality Gate

The `trace_report.json` is a primary input consumed by the Phase 6.4 Quality Gate to determine readability readiness for Phase 7:
1. **Critical Safety Check**: If `trace_report.json` is missing or contains an invalid schema, the Quality Gate evaluates to `blocked`.
2. **Readiness & Traceability Scoring**: The Quality Gate computes:
   - **`evidence_coverage_score`**: Checks statements marked as `evidence_backed`.
   - **`traceability_score`**: Checks statements that have known confidence labels (`evidence_backed`, `generated_scaffold`, `syntax_adapter`, `commentary_only`).
3. **Risk Scoring**: The `risk_score` increases (+10 each) if the trace report contains `true_unsupported_statements > 0`, `high_attention_lines > 0`, or `unattached_validation_findings > 0`.
4. **Gate Status Escalation**: If the trace report reveals any `true_unsupported_statements > 0`, `high_attention_lines > 0`, or if there are `unattached_validation_findings`, the Quality Gate escalates the final status to `review` (if not already `blocked`).

