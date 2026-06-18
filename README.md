# Hephaestus

A CLI-based binary reconstruction platform for extracting low-level binary analysis evidence, building a canonical intermediate representation, recovering structured control flow, and performing conservative type-semantic recovery without fabricating unsupported information.

## Overview

Hephaestus is an incremental binary reconstruction pipeline designed to turn noisy reverse-engineering tool output into structured, testable, evidence-backed artifacts.

Instead of jumping directly from a binary to fake decompiled source, Hephaestus works in phases:

* collect evidence from multiple analysis backends
* merge and normalize that evidence into a canonical IR
* recover structured control flow from raw CFGs
* extract real instruction-level evidence
* perform conservative type and semantic recovery
* preserve hard cases explicitly instead of guessing
* prepare the pipeline for later data-layout recovery and source reconstruction

The current implementation focuses on **evidence-driven extraction**, **IR normalization**, **canonicalization**, **CFG analysis**, **control-flow structuring**, **real instruction extraction**, **initial type recovery**, **type-constraint refinement**, **operand-to-variable binding**, and **safe fallback behavior** for difficult or ambiguous cases.

---

## Core Rule

> **Missing evidence is acceptable. Fabricated evidence is not.**

Hephaestus does not insert mock instructions, fake variables, fake types, fake structs, or fake source code. If a phase lacks enough evidence, the correct behavior is to preserve uncertainty explicitly.

---

## Current Status

### Completed

* Phase 1: Static extraction pipeline
* Phase 2: Unified IR assembly and canonicalization
* Phase 3A: CFG normalization and graph analysis
* Phase 3B: Sequence and conditional structuring
* Phase 3C: Loop structuring
* Phase 3D: Conservative fallback handling for hard CFG cases
* Phase 4A: Initial type recovery and signature inference
* Phase 4B: Real instruction extraction and type-constraint refinement
* Phase 4B.1: Conservative operand-to-variable binding
* Phase 4C: Conservative data-layout recovery
* Phase 4D: Final Phase 4 semantic artifact merger
* Phase 5: Conservative source reconstruction (AST emission, `recovered.c` C skeleton)
* Phase 5.8: Artifact consolidation, one-shot pipeline runner, and stress testing harness
* Phase 6.1 - 6.3: Static validator, evidence indexes, and trace reports
* Phase 6.4: Readability readiness quality gate

### Current Test Status

```text
722 passed
1 xfailed
0 failures
```

The adversarial and simulation test suites include cases for instruction validation, assembler stability, CFG structuring, operand binding, type constraints, semantic refinement, layout recovery, artifact merging, integration behavior, regression invariants, manifest generation, safe path utilities, stress generation, and quality gate scores/rules evaluation.

### Next

* Phase 7: Static readability reconstruction

---

## Architecture

The pipeline is organized into staged phases so each layer can be tested and improved independently.

```text
Binary
  ↓
Phase 1: Extraction
  ↓
Phase 2: Unified IR
  ↓
Phase 3: CFG Analysis + Structuring
  ↓
Phase 4A: Initial Type Recovery
  ↓
Phase 4B: Instruction Evidence + Type Refinement
  ↓
Phase 4B.1: Operand Binding
  ↓
Phase 4C: Data Layout Recovery
  ↓
Phase 4D: Semantic Artifact Merger
  ↓
Phase 5+: Source Reconstruction / Validation
```

---

## Phase 1 — Extraction

Phase 1 collects structural and instruction-level evidence from analysis backends.

Current backends:

* **Ghidra headless**
* **Radare2**
* optional future dynamic trace sources

Evidence collected includes:

* functions
* symbols
* CFG nodes and edges
* call graph evidence
* architecture / binary metadata
* real per-basic-block instructions where available

Instruction extraction is conservative. If a backend cannot recover real instructions for a block, Hephaestus emits an empty instruction list rather than inventing instructions.

---

## Phase 2 — Unified IR

Phase 2 builds a canonical intermediate representation from extractor output.

Responsibilities:

* merge duplicate function identities
* canonicalize function names
* normalize addresses
* deduplicate aliases
* preserve provenance
* preserve real instruction evidence
* validate instruction schema
* reject fabricated placeholder data
* emit evidence-backed IR only

The Unified IR stores instructions inside basic blocks:

```json
{
  "id": "0x100000540",
  "size": 24,
  "instructions": [
    {
      "address": "0x100000540",
      "mnemonic": "add",
      "opcode": "add",
      "operands": [
        { "kind": "register", "value": "w8" },
        { "kind": "register", "value": "w8" },
        { "kind": "immediate", "value": 1 }
      ],
      "size_bytes": 4,
      "raw": "add w8, w8, #0x1",
      "source": "radare2"
    }
  ],
  "edges": []
}
```

If instructions are missing, the IR remains valid:

```json
"instructions": []
```

---

## Phase 3 — CFG Structuring

Phase 3 recovers higher-level control-flow structure from flat CFGs.

Implemented sub-phases:

* **3A**: CFG normalization, predecessor/successor maps, dominators, post-dominators, back-edge detection
* **3B**: sequence reduction, `if`, and `if/else` recovery
* **3C**: reducible natural loop recovery
* **3D**: conservative fallback for irreducible, fragmented, multi-exit, and switch-like regions

The structuring layer emits a structured control-flow tree, not C/C++ source code.

### Structured Region Nodes

Current region model includes:

* `BlockNode`
* `SequenceNode`
* `IfNode`
* `IfElseNode`
* `LoopNode`
* `UnstructuredRegionNode`

### Hard CFG Cases

Hephaestus intentionally preserves difficult cases instead of pretending they are cleanly structured.

Examples:

* recursion-shaped entry/header cycles
* irreducible cyclic regions
* fragmented acyclic leftovers
* multi-exit loop bodies
* switch-like decision ladders / dispatch trees
* ambiguous loop regions
* hard break/continue-heavy regions

---

## Phase 4A — Initial Type Recovery

Phase 4A performs initial type and signature recovery from canonical IR evidence.

Responsibilities:

* classify functions
* identify known library signatures
* recover initial function signatures
* classify variables and parameters
* preserve unknowns when evidence is weak
* emit `type_recovery.json`

Phase 4A is conservative. It does not infer structs, emit source code, or pretend unknown variables have precise types.

---

## Phase 4B — Instruction Evidence + Type Constraint Refinement

Phase 4B adds real instruction evidence and a conservative type-constraint system.

Major capabilities:

* real instruction extraction from Ghidra and Radare2
* instruction schema validation
* fabricated-placeholder rejection
* instruction deduplication and sorting
* type constraint collection
* constraint priority resolution
* confidence refinement without lowering Phase 4A confidence
* semantic artifact emission via `semantic_recovery.json`

### Constraint Sources

Current constraint priorities:

| Source           | Priority |
| ---------------- | -------: |
| Known signature  |      100 |
| IR call site     |       80 |
| IR arithmetic    |       60 |
| IR memory access |       60 |
| IR comparison    |       50 |
| Name heuristic   |       20 |

### Conservative Behavior

If no real instruction evidence exists, Phase 4B still succeeds:

```text
constraints_applied = 0
Phase 4A types preserved
semantic_recovery.json emitted
```

This is a valid outcome, not a failure.

---

## Phase 4B.1 — Conservative Operand-to-Variable Binding

Phase 4B.1 bridges low-level instruction operands to Phase 4A variables.

Problem solved:

```text
instruction operand
    ↓
stack slot / register temporary / ABI argument register
    ↓
Phase 4A variable
    ↓
type constraint
```

Supported binding kinds:

* explicit variable operand
* verified stack-slot binding
* basic-block-local register temporary binding
* ABI argument register binding

### Binding Rules

Hephaestus only binds operands when the link is concrete.

Examples of allowed binding:

```text
kind=variable + name exists in Phase 4A index
```

```text
memory operand + stack base + verified unique Phase 4A offset
```

```text
register previously loaded from a verified variable inside the same basic block
```

Examples of rejected binding:

* unknown raw stack-like text
* immediate operands
* non-stack memory bases
* ambiguous stack offsets
* size mismatches
* registers with no prior binding
* register bindings across basic blocks
* printf varargs

### ABI Call Binding

For ARM64, argument registers `x0`–`x7` are used conservatively.

For variadic functions such as `printf`, only the fixed first argument is constrained. Varargs are not inferred.

---

## Instruction Validation

Hephaestus rejects known fabricated placeholder evidence, including old mock values such as:

```text
mov eax
cmp eax
je exit_block
0xDEADBEEF
LoadLibraryA
GetProcAddress
kernel32.dll
0x0045e0c0
0x00401000
```

The validator scans:

* `raw`
* `opcode`
* `mnemonic`
* operand `value`
* operand `name`
* operand `raw`
* operand `base`

Malformed but non-fabricated instructions are skipped safely.

---

## Design Principles

### 1. Evidence first

Hephaestus only keeps information that can be traced back to extractor evidence. If data is not implemented or not recoverable, the correct output is an empty field or explicit uncertainty, not mock content.

### 2. Conservative over clever

Hard or ambiguous cases fall back explicitly instead of being misrepresented as clean structure or precise types.

### 3. Incremental structuring

The pipeline prefers staged graph and semantic reduction over monolithic decompiler-style guessing.

### 4. Deterministic output

The same input should produce stable serialization and reproducible artifacts.

### 5. No fake precision

Types, variables, instructions, fields, and control-flow regions are not invented to make output look complete.

### 6. Test-driven iteration

Each stage is stress-tested with synthetic fixtures, adversarial cases, and compiled binaries before being considered stable.

---

## Key Features

* Headless multi-backend extraction
* Ghidra and Radare2 support
* Real instruction extraction per basic block
* Instruction validation and fabricated-evidence rejection
* Canonical IR generation
* Address normalization and function canonicalization
* CFG analysis with dominators and post-dominators
* Structured region recovery
* Loop candidate validation and false-positive rejection
* Conservative hard-case classification
* Initial type recovery
* Known signature handling
* Type constraint refinement
* Operand-to-variable binding
* ABI call argument binding
* Deterministic artifact generation
* Persisted pipeline logs in `artifacts/`
* Adversarial regression test suite

---

## Project Layout

```text
.
├── main.py
├── src/
│   ├── engine/
│   │   ├── ghidra.py
│   │   └── radare2.py
│   ├── ir/
│   │   ├── assembler.py
│   │   ├── instructions/
│   │   │   ├── __init__.py
│   │   │   └── validation.py
│   │   ├── structuring/
│   │   │   ├── analysis.py
│   │   │   ├── builder.py
│   │   │   ├── conditionals.py
│   │   │   ├── dominators.py
│   │   │   ├── fallbacks.py
│   │   │   ├── graph.py
│   │   │   ├── loops.py
│   │   │   ├── models.py
│   │   │   ├── postdominators.py
│   │   │   └── reducers.py
│   │   └── types/
│   │       ├── bindings.py
│   │       ├── constraints.py
│   │       ├── emitter.py
│   │       ├── models.py
│   │       ├── propagation.py
│   │       ├── refinement_engine.py
│   │       ├── resolver.py
│   │       ├── semantic_emitter.py
│   │       └── signatures.py
│   └── scripts/
│       └── GhidraExtractorScript.java
├── test/
│   └── simulate/
│       ├── test_adversarial_binding.py
│       ├── test_adversarial_cfg_structuring.py
│       ├── test_adversarial_constraints.py
│       ├── test_adversarial_full_pipeline.py
│       ├── test_adversarial_instruction_validation.py
│       ├── test_adversarial_integration.py
│       ├── test_engine.py
│       ├── test_instruction_extraction.py
│       ├── test_ir.py
│       ├── test_operand_binding.py
│       ├── test_regression_invariants.py
│       ├── test_semantic_refinement.py
│       ├── test_structuring.py
│       └── test_type_recovery.py
└── artifacts/
```

---

## Example Workflow

### 1. One-Shot End-to-End Execution (Recommended)

To run the entire decompiler pipeline on a target binary, use the `run-all` subcommand:

```bash
python3 main.py run-all ./target_binary --ghidra --radare2 --out-dir artifacts --clean
```

### 2. Running Individual Phases (Staged Execution)

If you prefer to run the pipeline incrementally:

```bash
# Phase 1 & 2: Run extractors and export IR
python3 main.py ./target_binary --ghidra --radare2 --export-ir

# Phase 3: CFG analysis and structuring
python3 main.py analyze-cfg --out-dir artifacts

# Phase 4A: Type recovery
python3 main.py recover-semantics --out-dir artifacts

# Phase 4B: Type constraint refinement
python3 main.py refine-semantics --out-dir artifacts

# Phase 4C: Data layout recovery
python3 main.py recover-layouts --out-dir artifacts

# Phase 4D: Final semantic merger
python3 main.py finalize-semantics --out-dir artifacts

# Phase 5: Source reconstruction
python3 main.py reconstruct-source --out-dir artifacts
```

### 3. Automated Stress Testing

To run the deterministic stress harness:

```bash
python3 main.py stress-test --profile hard --out-dir artifacts/stress/hard --clean
```

### 4. Inspect generated artifacts

Typical outputs in the output directory:

* `radare2_extraction.json` — Raw Radare2 analysis output.
* `ghidra_extraction.json` — Raw Ghidra headless analysis output.
* `unified_ir.json` — Merged canonical Unified IR representation (Phase 2).
* `structuring_analysis.json` — CFG normalization report (Phase 3A).
* `structuring_regions.json` — Structured control-flow region tree serialization (Phase 3B).
* `type_recovery.json` — Phase 4A initial signature and variable mapping.
* `semantic_recovery.json` — Phase 4B constraint-refined type records.
* `layout_recovery.json` — Phase 4C memory layout candidates.
* `phase4_semantics.json` — Phase 4D final merged semantic evidence.
* `source_reconstruction.json` — Phase 5 source reconstruction summary (schema 5.7.2).
* `recovered.c` — Emitted C skeletons with syntax-safe condition adapters.
* `pipeline_manifest.json` — Execution manifest showing stages, timings, and decompiler summary metrics.
* `run.log` — Consolidated pipeline run execution logs.

---

## Structuring Output Model

The current structuring phase emits a control-flow tree rather than source code.

Output node types include:

* `block`
* `sequence`
* `if`
* `if_else`
* `loop`
* `unstructured`

This allows Hephaestus to:

* preserve structured regions when possible
* isolate unresolved regions without guessing
* prepare data for later AST and source generation

---

## Semantic Recovery Output Model

Phase 4B emits `semantic_recovery.json`.

Example shape:

```json
{
  "schema_version": "4B.0.0",
  "provenance": {
    "phase": "4B",
    "description": "Type constraint refinement engine",
    "source_ir": "unified_ir.json",
    "source_type_recovery": "type_recovery.json",
    "source_structuring": "structuring_regions.json"
  },
  "data": {
    "functions": [
      {
        "name": "_main",
        "entry_point": "0x1000004c0",
        "function_kind": "user",
        "refined_signature": {},
        "variables": [],
        "total_constraints_applied": 0,
        "confidence": 0.2,
        "evidence": [
          "No instruction-level evidence available; Phase 4A types preserved"
        ]
      }
    ]
  }
}
```

`total_constraints_applied = 0` is valid when evidence is insufficient.

---

## Hard Cases Currently Handled Conservatively

Hephaestus does **not** pretend every binary can be perfectly reconstructed.

Examples of cases intentionally handled conservatively:

* recursion-shaped entry/header cycles
* irreducible cyclic regions
* fragmented acyclic leftovers
* multi-exit loop bodies
* switch-like decision ladders / dispatch trees
* ambiguous stack offsets
* conflicting type constraints
* unknown call targets
* unknown raw operands
* unbound register arithmetic
* pointer-like use without layout evidence

These are preserved as uncertainty instead of being flattened into misleading source-like output.

---

## Validation Strategy

The test suite includes:

* synthetic CFG-based unit tests
* synthetic IR and type-recovery fixtures
* adversarial instruction validation tests
* adversarial operand-binding tests
* adversarial type-constraint tests
* full synthetic pipeline stress tests
* optional compiled C integration tests
* regression invariant tests

Current coverage includes:

* nested loops
* sibling loops
* deeply nested conditionals
* continue-if loop bodies
* multi-exit loops
* endless loops
* recursion-shaped false positives
* switch-like fan-out / decision ladders
* deterministic ordering under shuffled graph inputs
* fabricated instruction rejection
* instruction deduplication
* malformed instruction tolerance
* stack-slot ambiguity
* register alias handling
* register clobbering
* call clobbering
* printf vararg safety
* constraint conflict handling
* confidence monotonicity

---

## Running Tests

Run the full suite:

```bash
python3 -m pytest -v
```

Run targeted suites:

```bash
python3 -m pytest test/simulate/test_structuring.py -v
python3 -m pytest test/simulate/test_type_recovery.py -v
python3 -m pytest test/simulate/test_semantic_refinement.py -v
python3 -m pytest test/simulate/test_operand_binding.py -v
python3 -m pytest test/simulate/test_regression_invariants.py -v
```

Current full-suite result:

```text
193 passed, 1 xfailed, 0 failures
```

If using integration markers, register them in `pytest.ini`:

```ini
[pytest]
markers =
    integration: tests that require external tools like clang, radare2, or ghidra
```

---

---

## Safety Policy

Hephaestus operates under a strict safety policy:

> **Missing evidence is acceptable. Fabricated evidence is not.**

- **Allowed outputs**: Pseudo registers (e.g., `tmp_x0`), pseudo stack slots (e.g., `stack_0`), call target helpers (e.g., `call_0x100000abc()`), syntax adapters (`HEPHAESTUS_UNKNOWN_COND`, `HEPHAESTUS_CSET`), unsupported comments, and layout candidates.
- **Forbidden outputs**: Fake source variables, fake structs, fake fields, fake arrays, fake executable conditions, and fake flag variables.

---

## Limitations

- **ARM64-Focused**: Instruction lowering and semantic constraints currently assume ARM64 architecture.
- **Syntax-Safe, Not Semantic Equivalence**: Emitted C code compiles syntax-safely under `clang -fsyntax-only` but is a conservative outline, not a direct semantic equivalent.
- **No Real Condition Recovery**: Control-flow condition expressions are represented as unknown condition helpers rather than executable boolean checks.
- **No Struct/Field/Array Recovery**: Structured types and layout offsets are not dynamically fabricated.
- **Unsupported Instructions Preserved**: Instructions without lowering rules are explicitly emitted as comments.
- **External Dependencies**: Requires Ghidra and Radare2 backends installed and in path for full metadata extraction.

---

## Quickstart

### Compile target program
```bash
clang -O0 -g t.c -o t
```

### Run Full Pipeline with Validation
```bash
python3 main.py run-all ./t \
  --ghidra \
  --radare2 \
  --out-dir artifacts \
  --clean \
  --validate
```

### Run Full Pipeline with Quality Gate
```bash
python3 main.py run-all ./t \
  --ghidra \
  --radare2 \
  --out-dir artifacts \
  --clean \
  --quality-gate
```

### Run Validation Standalone
```bash
python3 main.py validate \
  --out-dir artifacts \
  --strict
```

### Run Quality Gate Standalone
```bash
python3 main.py quality-gate \
  --out-dir artifacts \
  --markdown
```

### Run Stress Tests
To stress test Hephaestus against generated C programs:
```bash
python3 main.py stress-test \
  --profile hard \
  --out-dir artifacts/stress/hard \
  --clean
```

---

## Roadmap

### Phase 6 — Validation & Repair
- **Phase 6.1: Static Validation and Evidence Consistency Checks** (Complete): Add a read-only validator verifying artifact consistency, metrics, helpers, and C safety policy invariants.
- **Phase 6.2: Repair and Feedback Loop** (Future Work): Compile generated C code, capture syntactic mismatches, and feed repairs back into decompiler semantics.

