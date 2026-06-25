# Running Binary Reconstruction and Structuring Pipelines

This document lists the commands to compile, extract, and analyze real binaries using the Binary Reconstruction Platform.

---

## Quickstart

### Compile target program
```bash
clang -O0 -g t.c -o t
```

### Run Full Pipeline
```bash
python3 main.py run-all ./t \
  --ghidra \
  --radare2 \
  --out-dir artifacts \
  --clean
```

### Run Stress Tests
```bash
python3 main.py stress-test \
  --profile hard \
  --out-dir artifacts/stress/hard \
  --clean
```

---

## 1. Compilation (Preparing Target Binaries)

To preserve the natural control-flow structures of the binary without compiler optimizations, compile with `-O0`:

```bash
# Compile on macOS (creates test_case_bin)
clang -O0 test_case.c -o test_case_bin

# Alternatively, using gcc
gcc -O0 test_case.c -o test_case_bin
```

---

## 2. Feature Extraction and Unified IR Generation (Phases 1 & 2)

Extract function representations, symbols, basic blocks, and CFG transitions from the binary, and export them into the canonical Unified IR format.

### Run with Radare2 only:
```bash
python3 main.py ./test_case_bin --radare2 --export-ir
```

### Run with Ghidra only:
```bash
python3 main.py ./test_case_bin --ghidra --export-ir
```

### Run with both Ghidra and Radare2 (Recommended for Merged Context):
This command merges extractor graphs, resolves symbol aliases, and builds canonical CFGs:
```bash
python3 main.py ./test_case_bin --ghidra --radare2 --export-ir
```

### Specify a Custom Output Folder:
To write extraction files to a custom folder (e.g., `artifact_23/`):
```bash
python3 main.py ./test_case_bin --ghidra --radare2 --export-ir --out-dir artifact_23
```

---

## 3. CFG Dominance and Structuring Tree Analysis (Phase 3)

Run the Phase 3A analysis backbone (dominators, post-dominators, back-edges) and the Phase 3B region structuring engine (sequence reduction, if/else detection, unstructured fallbacks):

### Run Structuring Pass on the default output folder (`artifacts/`):
```bash
python3 main.py analyze-cfg
```

### Run Structuring Pass on a custom output folder (e.g., `artifact_23/`):
```bash
python3 main.py --analyze-cfg --out-dir artifact_23
```

---

## 4. Semantic & Signature Recovery (Phase 4A)

Recover conservative function signatures, parameter models, and variable layouts from the Canonical Unified IR:

### Run semantic type recovery on the default folder (`artifacts/`):
```bash
python3 main.py recover-semantics
```

### Run semantic type recovery on a custom folder (e.g., `artifact_23/`):
```bash
python3 main.py recover-semantics --out-dir artifact_23
```

---

## 5. Type Constraint Refinement (Phase 4B)

Refines Phase 4A recovered types using real instruction-level evidence extracted
from the Unified IR basic blocks. Emits `semantic_recovery.json` with a
conservative, constraint-backed type map.

**Prerequisite**: `recover-semantics` must be run first (produces `type_recovery.json`).

### Run on the default folder (`artifacts/`):
```bash
python3 main.py refine-semantics
```

### Run on a custom folder (e.g., `artifact_23/`):
```bash
python3 main.py refine-semantics --out-dir artifact_23
```

The command prints a summary:
```
============================================================
          PHASE 4B: TYPE CONSTRAINT REFINEMENT
============================================================
Functions processed:              <N>
Total constraints applied:        <N>
Functions with no instr evidence: <N>
------------------------------------------------------------
Output: artifacts/semantic_recovery.json
============================================================
```

> **Note**: If no real instructions were extracted (e.g., Ghidra/Radare2 were not
> run), Phase 4B gracefully no-ops — it preserves Phase 4A types verbatim with
> `constraints_applied = 0`. This is a valid conservative outcome.

---

## 6. Conservative Data Layout Recovery (Phase 4C)

Recovers conservative memory access patterns from the Unified IR. Classifies
accesses by base register into scalar, array-like, record-like, or pointer-like
layout candidates. Does not emit structs or field names.

**Prerequisite**: `recover-semantics` must be run first (produces `type_recovery.json`).

### Run on the default folder (`artifacts/`):
```bash
python3 main.py recover-layouts
```

### Run on a custom folder (e.g., `artifact_23/`):
```bash
python3 main.py recover-layouts --out-dir artifact_23
```

---

## 7. Final Phase 4 Semantic Artifact Merger (Phase 4D)

Merges `type_recovery.json`, `semantic_recovery.json` (optional), and
`layout_recovery.json` (optional) into a single `phase4_semantics.json`
artifact for Phase 5 handoff.

Phase 4D does not infer new types, emit structs, or compute confidence scores.
It only summarizes and merges evidence that already exists.

**Prerequisite**: `recover-semantics` must be run first.

### Run on the default folder (`artifacts/`):
```bash
python3 main.py finalize-semantics
```

### Run on a custom folder (e.g., `artifact_23/`):
```bash
python3 main.py finalize-semantics --out-dir artifact_23
```

The command prints a summary:
```
============================================================
      PHASE 4D: FINAL SEMANTIC ARTIFACT MERGER
============================================================
Phase 4D semantic finalization complete
Functions finalized:         <N>
Functions with refinement:   <N>
Layout candidates attached:  <N>
Unbound memory accesses:     <N>
Constraints applied:         <N>
============================================================
Output: artifacts/phase4_semantics.json
============================================================
```

---

## 8. Full Phase 4 Workflow

```bash
python3 main.py ./target_binary --ghidra --radare2 --export-ir
python3 main.py analyze-cfg --out-dir artifacts
python3 main.py recover-semantics --out-dir artifacts
python3 main.py refine-semantics --out-dir artifacts
python3 main.py recover-layouts --out-dir artifacts
python3 main.py finalize-semantics --out-dir artifacts
```

---

## 9. Phase 5.6: Source Reconstruction & Declarations Stabilization

Reconstruct conservative C skeleton, emit real structured control flow, annotate condition header comments with branch evidence, and declare all pseudo-registers, stack slots, and global call target helpers:

```bash
python3 main.py reconstruct-source --out-dir artifacts
```

This reads:
- `unified_ir.json` (required)
- `structuring_regions.json` (required)
- `phase4_semantics.json` (required)
- `layout_recovery.json` (optional)

And writes:
- `source_reconstruction.json` — Structured source reconstruction artifact (schema 5.7.2)
- `recovered.c` — Conservative C function skeletons with structured control flow, return/call refinements, branch predicate annotations, pseudo declarations, and syntax-safe condition adapters.

The command prints a summary:
```
============================================================
      PHASE 5.7: SYNTAX-SAFE UNKNOWN CONDITION ADAPTER
============================================================
Functions reconstructed:          <N>
  Structured:                     <N>
  Partially structured:           <N>
  Unstructured:                   <N>
  Missing:                        <N>
Functions with warnings:          <N>
Functions with region structures: <N>
Functions with semantic evidence: <N>
Functions with layout evidence:   <N>
Functions with param-layout ev:   <N>
Unstructured regions total:       <N>
Instructions total:               <N>
Instructions lowered:             <N>
Instructions commented:           <N>
Lowering coverage percent:        <N>%
Control-flow regions:             <N>
Control-flow constructs:          <N>
  Loops:                          <N>
  If:                             <N>
  If-Else:                        <N>
  Switch:                         <N>
  Fallback/Unstructured:          <N>
  Duplicate blocks skipped:       <N>
Condition expressions recovered:  <N>
Return sites total:               <N>
  With value:                     <N>
  Unknown:                        <N>
  Funcs with recovered returns:   <N>
Call sites total:                 <N>
  Direct:                         <N>
  Indirect:                       <N>
  With arguments:                 <N>
  Arguments recovered:            <N>
  Arguments unknown:              <N>
Condition sites total:            <N>
  With evidence:                  <N>
  Unknown:                        <N>
  Annotations recovered:          <N>
  Inverted polarity:              <N>
  Ambiguous sites:                <N>
Declarations total:               <N>
  Pseudo registers:               <N>
  Pseudo stack slots:             <N>
  Call helpers:                   <N>
  Funcs with declarations:        <N>
Compile shape warnings total:     <N>
Condition adapters inserted:      <N>
  Evidence adapters:              <N>
  Unknown adapters:               <N>
  Helper function emitted:        <N>
============================================================
Output: artifacts/source_reconstruction.json
Output: artifacts/recovered.c
============================================================
```

---

## 10. Full Pipeline Workflow (Phase 1–5.7)

```bash
python3 main.py ./t --ghidra --radare2 --export-ir
python3 main.py analyze-cfg --out-dir artifacts
python3 main.py recover-semantics --out-dir artifacts
python3 main.py refine-semantics --out-dir artifacts
python3 main.py recover-layouts --out-dir artifacts
python3 main.py finalize-semantics --out-dir artifacts
python3 main.py reconstruct-source --out-dir artifacts
```

---

## 11. Output Artifacts Generated

After running the commands above, the output folder will contain:
- `radare2_extraction.json` — Raw Radare2 analysis output.
- `ghidra_extraction.json` — Raw Ghidra headless analysis output.
- `unified_ir.json` — Merged, canonical Unified IR representation (Phase 2).
- `structuring_analysis.json` — Dominator, post-dominator, and back-edge report (Phase 3A).
- `structuring_regions.json` — Structured control-flow region tree serialization (Phase 3B).
- `type_recovery.json` — Phase 4A recovered function signatures and variables mapping.
- `semantic_recovery.json` — Phase 4B constraint-refined type records per function.
- `layout_recovery.json` — Phase 4C conservative memory layout candidates.
- `phase4_semantics.json` — Phase 4D final merged semantic artifact for Phase 5 handoff.
- `source_reconstruction.json` — Phase 5.7 source reconstruction artifact (schema 5.7.2).
- `recovered.c` — Phase 5.7 conservative C function skeletons.
- `pipeline_manifest.json` — Execution manifest showing timings, stages, outputs, and metrics.
- `stress_report.json` — Stress run-level report containing invariant check results and compilation diagnostics.

---

## 12. One-Shot End-to-End Execution (Phase 5.8)

Instead of running each phase manually, you can execute the entire Hephaestus decompiler pipeline from binary extraction to source reconstruction with a single command:

```bash
python3 main.py run-all ./target_binary --ghidra --radare2 --out-dir artifacts --clean
```

### Options:
- `--ghidra`: Run the Ghidra headless extractor.
- `--radare2`: Run the Radare2 extractor.
- `--out-dir DIR`: Directory where all generated intermediate and final artifacts are saved (defaults to `artifacts`).
- `--clean`: Safely delete previously generated Hephaestus artifacts in the output directory before running.
- `--no-source`: Stop after final semantics merger (`phase4_semantics.json`), skipping source reconstruction and `recovered.c` generation.
- `--stop-after STAGE`: Execute up to and including the specified stage (e.g., `extract`, `analyze_cfg`, `recover_semantics`, `refine_semantics`, `recover_layouts`, `finalize_semantics`, `reconstruct_source`).
- `--continue-on-error`: Log errors and continue processing subsequent stages on non-fatal failures.

Running `run-all` generates all individual stage outputs and a final `pipeline_manifest.json` under the output directory summarizing metrics and timings.

---

## 13. Deterministic Stress Testing & Invariant Verification (Phase 5.8)

To evaluate decompiler correctness, robustness, and lowering coverage, run the automated stress harness subcommand:

```bash
python3 main.py stress-test --profile hard --out-dir artifacts/stress/hard --clean
```

### Options:
- `--profile {small,medium,hard,brutal}`: Size and complexity scale of the generated C stress program.
- `--out-dir DIR`: Output folder to write generated C source, compiled binary, intermediate artifacts, and reports.
- `--clean`: Clean output directory before executing.
- `--seed SEED`: Seed value for deterministic C generation (defaults to `1337`).

The harness:
1. **Generates** a deterministic C source program using the specified seed and profile.
2. **Compiles** it with `clang -O0 -g`.
3. **Runs** the Hephaestus `run-all` pipeline using Radare2.
4. **Performs** validation check routines checking safety invariants (no phantom pointers, no structures fabrication, zero condition expressions recovered, syntax-safe adapters consistency, etc.).
5. **Checks** syntax validity of the output `recovered.c` using `clang -fsyntax-only`.
6. **Writes** a comprehensive `stress_report.json` report containing execution logs, metrics, and diagnostics.

---

## 14. Static Validation & Evidence Consistency Checks (Phase 6.1)

To evaluate whether the generated decompiler outputs are internally consistent, policy-compliant, and syntax-safe without modifying the output files, run the standalone validator:

```bash
python3 main.py validate --out-dir artifacts --strict
```

### Options:
- `--out-dir DIR`: Directory containing Hephaestus output artifacts (defaults to `artifacts`).
- `--strict`: Promotes missing recommended files, schema mismatches, helper metrics mismatches, and large unsupported comments mismatches to errors.
- `--no-clang`: Skip running `clang -fsyntax-only` check.
- `--json`: Prints a compact single-line JSON summary to stdout.

### Report Inspection:
You can inspect the generated validation report in a human-readable format:
```bash
python3 scripts/inspect_validation_report.py artifacts/validation_report.json
```

### Integrated Validation:
Run validation checks automatically at the end of `run-all`:
```bash
python3 main.py run-all ./target_binary --ghidra --radare2 --out-dir artifacts --clean --validate
```

To fail the pipeline execution (exit non-zero) if validation checks return errors:
```bash
python3 main.py run-all ./target_binary --ghidra --radare2 --out-dir artifacts --clean --validate-strict
```

---

## 15. Statement-Level Evidence Traceability & Indexing (Phase 6.2)

To generate a statement-level evidence index detailing the classification of emitted C code lines, run the `build-evidence-index` subcommand:

```bash
python3 main.py build-evidence-index --out-dir artifacts
```

### Options:
- `--out-dir DIR`: Directory containing Hephaestus output artifacts (defaults to `artifacts`).
- `--json`: Prints a compact single-line JSON summary to stdout.

### Integrated Evidence Indexing:
Run evidence indexing automatically at the end of `run-all` before validation:
```bash
python3 main.py run-all ./target_binary --ghidra --radare2 --out-dir artifacts --clean --evidence-index
```
Note: If `--validate` or `--validate-strict` is used in `run-all`, the evidence index is built automatically.

---

## 16. Evidence Trace Reports and Validation Explainability (Phase 6.3)

To generate a human-readable and machine-readable trace report correlating statements to confidence categories and validation findings, run the `build-trace-report` subcommand:

```bash
python3 main.py build-trace-report --out-dir artifacts --markdown
```

### Options:
- `--out-dir DIR`: Directory containing Hephaestus output artifacts (defaults to `artifacts`).
- `--markdown`: Generate a human-readable trace summary to `trace_report.md`.
- `--json`: Prints a compact single-line JSON summary to stdout.
- `--require-validation`: Fail if `validation_report.json` is missing.
- `--no-require-evidence-index`: Do not fail if `evidence_index.json` is missing.

### Integrated Trace Reporting:
Run trace report generation automatically at the end of `run-all`:
```bash
python3 main.py run-all ./target_binary --ghidra --radare2 --out-dir artifacts --clean --trace-report
```
To enforce that the validation phase requires the presence of a trace report:
```bash
python3 main.py run-all ./target_binary --ghidra --radare2 --out-dir artifacts --clean --validate --trace-report --require-trace-report
```

---

## 17. Readability Readiness Quality Gate (Phase 6.4)

Evaluate decompiler output readiness for Phase 7 readability transformations using scoring and safety decision logic.

```bash
python3 main.py quality-gate --out-dir artifacts --markdown
```

### Options:
- `--out-dir DIR`: Directory containing Hephaestus output artifacts (defaults to `artifacts`).
- `--markdown`: Generate human-readable quality summary to `quality_gate.md`.
- `--json`: Prints a compact single-line JSON summary to stdout.
- `--strict`: Enforce strict decision criteria.

### Standalone Exit Codes:
- `0`: Status is `ready` or `review` (safe to proceed).
  - **`ready`**: Safe to proceed.
  - **`review`**: Compiler warnings only or validation warnings present. Phase 7 may proceed, but the output `recovered_readable.c` should be marked as lower confidence or requiring manual review.
- `1`: Status is `blocked` (do not proceed). Triggered by compilation/syntax errors, missing critical files, validation safety/policy errors, non-zero condition expressions recovered, or hash mutations.
- `2`: Internal CLI usage error or crash.

> **Note on Blocker Invariance**: Strict validation policy failures (like strict accounting mismatches) do not automatically block Phase 7 unless they correspond to a hard blocker category.

### Integrated Quality Gate:
Run quality gate checks automatically at the end of `run-all`:
```bash
python3 main.py run-all ./target_binary --ghidra --radare2 --out-dir artifacts --clean --quality-gate
```

---

## Phase 7.1 — Human-Readable C Output

Phase 7.1 introduces a best-effort, human-readable decompilation skeleton `recovered_readable.c` that replaces simple `HEPHAESTUS_UNKNOWN_COND` adapters with statically inferred C boolean expressions.

### Standalone CLI Command
```bash
python3 main.py build-readable --out-dir artifacts --markdown
```

### Options:
- `--out-dir DIR`: Directory containing output artifacts (defaults to `artifacts`).
- `--markdown`: Generates human-readable summary report to `readability_report.md`.
- `--json`: Prints a compact single-line JSON summary to stdout.
- `--require-quality-gate`: Aborts and fails if `quality_gate.json` is missing.
- `--ignore-quality-gate`: Force proceed even if quality gate is blocked or missing (records warning).
- `--allow-review`: Accepted for compatibility (review is allowed by default).

### Standalone Exit Codes:
- `0`: Built successfully.
- `1`: Blocked by quality gate, required file missing, input hash mutated, or clang syntax error.
- `2`: Internal CLI usage error or crash.

### Integrated Pipeline:
Generate the readable skeleton automatically at the end of the decompiler pipeline:
```bash
python3 main.py run-all ./target_binary --ghidra --radare2 --out-dir artifacts --clean --readable
```

---

## One-Command Reconstruction Orchestrator (Phase 11.5)

To run the complete reconstruction pipeline all the way from target binary parsing through static extraction, dynamic tracing, static-dynamic fusion, multi-agent debate, and agent-assisted source generation (`recovered_agent.c`) in one go:

```bash
python3 main.py reconstruct ./target_binary \
  --out-dir artifacts/full_run \
  --provider groq \
  --model llama-3.3-70b-versatile \
  --dynamic-inputs ./tests/inputs.json \
  --max-functions 5 \
  --clean
```

### Options:
- `binary_path` (positional): Path to the target binary or trace file.
- `--out-dir DIR`: Output directory for generated JSON and C artifacts (defaults to `artifacts`).
- `--provider {ollama,groq}`: LLM provider (defaults to `groq`).
- `--model MODEL`: Model name (overrides the provider's default model).
- `--api-key-env ENV_NAME`: Custom environment variable name to load the Groq API key from.
- `--ollama-host URL` / `--groq-host URL`: Custom host URL override for the selected LLM provider.
- `--dynamic-inputs PATH`: Path to a JSON file containing dynamic inputs/arguments to run against the binary.
- `--dynamic-timeout-s FLOAT`: Timeout in seconds for each dynamic trace execution (defaults to `5.0`).
- `--dynamic-max-output-bytes INT`: Maximum stdout/stderr output bytes captured per execution.
- `--max-functions INT`: Maximum number of functions to analyze, debate, and generate (defaults to `1`).
- `--function NAME`: Run analysis and generation only for a specific function by name.
- `--allow-human-suggestions`: Incorporate human-approved suggestions (from the `agent_suggestions.json` review status) when emitting the final agent C source code.
- `--overwrite`: Overwrite existing output C source files.
- `--clean`: Clean the output directory before running.
- `--json`: Output final manifest as a JSON object on stdout (logs are redirected to stderr).

### Debug / Skip Flags:
If you need to run specific downstream phases of the orchestrator using already generated artifacts, use the skip flags:
- `--skip-static`: Assume static artifacts exist and skip static extraction/analysis.
- `--skip-dynamic`: Skip dynamic behavior capture.
- `--skip-fusion`: Skip static-dynamic behavior fusion.
- `--skip-agent-debate`: Skip multi-agent debate (requires an existing `agent_suggestions.json`).
- `--skip-agent-source`: Skip generating `recovered_agent.c`.

---

## Phase 11.6 — Adaptive Dynamic Exploration + Compact LLM Context

Phase 11.6 introduces advanced features to enhance dynamic testing sensitivity and manage large LLM prompts to prevent payload size errors on Groq.

### 1. Automatic Dynamic Input Generation
When running `reconstruct` without providing an explicit `--dynamic-inputs` file, the orchestrator automatically generates a diverse, safe test suite of default test cases (`dynamic_inputs.generated.json`).
- Enable/disable: `--auto-inputs` (enabled by default on `reconstruct`) or `--no-auto-inputs`.
- Limits: `--dynamic-max-generated-inputs INT` (defaults to `20`).

### 2. Adaptive Dynamic Exploration
After the initial execution pass, Hephaestus analyzes outputs, exit codes, and string sensitivities. It deterministically mutates inputs to explore code behavior in a second pass.
- Enable/disable: `--adaptive-dynamic` (enabled by default on `reconstruct`) or `--no-adaptive-dynamic`.
- Rounds: `--dynamic-mutation-rounds INT` (defaults to `2`).
- Max adaptive runs: `--dynamic-max-adaptive-inputs INT` (defaults to `30`).
- Generated artifacts:
  - `adaptive_inputs.json` (the list of mutated inputs)
  - `adaptive_dynamic_runs.json` (execution results)
  - `input_influence_report.json` (sensitivities: argv, exit codes, stdout)
  - `dynamic_exploration_report.json` (exploration run stats)

### 3. Compact LLM Context Optimizer
To fit within Groq context windows, LLM packets are compressed, stripping redundant elements (such as raw instructions, PLT stubs, and repeats) and keeping vital indicators.
- Mode: `--packet-mode {compact,full}` (defaults to `compact` for both groq and ollama).
- Size constraints: `--max-packet-chars INT` (defaults to `16000`).
- Evidence limit: `--max-evidence-items INT` (defaults to `20`).
- Generated artifacts:
  - `agent_packets_compact/` (optimized packets directory)
  - `agent_packet_optimization_report.json` (size delta and dropped field logs)

### 4. Provider Error Handling & Retries
Specific handlers intercept 413 Payload Too Large and 429 Rate Limit responses.
- Retry on 413: `--retry-on-413` (defaults to `True`) or `--no-retry-on-413` (progressive downsizing occurs on retry).
- Wait on 429: `--wait-on-429` (default: `False`).
- Retries count: `--max-provider-retries INT` (default: `1`).




