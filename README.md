# Hephaestus

A CLI-based binary reconstruction platform for extracting low-level analysis data, building a canonical intermediate representation, and recovering structured control flow from raw binary CFGs.

## Overview

Hephaestus is an incremental binary reconstruction pipeline designed to turn noisy analysis output into something structured, testable, and useful for later high-level source reconstruction.

Instead of jumping directly from a binary to fake decompiled source, Hephaestus works in phases:

* collect evidence from multiple analysis backends
* merge and normalize that evidence into a canonical IR
* recover structured control flow from raw CFGs
* preserve hard cases conservatively rather than guessing
* prepare the pipeline for later type recovery and source emission

The current implementation focuses on **evidence-driven extraction**, **IR normalization**, **canonicalization**, **CFG analysis**, **control-flow structuring**, and **safe fallback handling** for difficult graphs.

---

## Current Status

### Completed

* Phase 1: Static extraction pipeline
* Phase 2: Unified IR assembly and canonicalization
* Phase 3A: CFG normalization and graph analysis
* Phase 3B: Sequence and conditional structuring
* Phase 3C: Loop structuring
* Phase 3D: Conservative fallback handling for hard cases

### Next

* Phase 4: Type recovery and signature inference
* Phase 5: Source reconstruction / AST emission
* Phase 6: Validation, compilation, and repair loop

---

## Architecture

The pipeline is organized into staged phases so that each layer can be tested and improved independently.

### Phase 1 — Extraction

Collects structural evidence from analysis backends.

Current backends:

* **Ghidra headless**
* **Radare2**
* optional future dynamic trace sources

Artifacts produced here include:

* functions
* symbols
* CFG nodes and edges
* call graph evidence
* architecture / binary metadata

### Phase 2 — Unified IR

Builds a canonical intermediate representation from extractor output.

Responsibilities:

* merge duplicate function identities
* canonicalize names
* normalize addresses
* deduplicate aliases
* preserve provenance
* reject fabricated placeholder data
* emit evidence-backed IR only

### Phase 3 — CFG Structuring

Recovers higher-level control-flow structure from flat CFGs.

Implemented sub-phases:

* **3A**: CFG normalization, predecessor/successor maps, dominators, post-dominators, back-edge detection
* **3B**: sequence reduction, `if`, and `if/else` recovery
* **3C**: reducible natural loop recovery
* **3D**: conservative fallback for irreducible, fragmented, multi-exit, and switch-like regions

The structuring layer currently emits a structured control-flow tree, not source code.

---

## Design Principles

### 1. Evidence first

Hephaestus only keeps information that can be traced back to extractor evidence. If data is not implemented yet, the correct output is an empty field, not mock content.

### 2. Conservative over clever

Hard control-flow cases fall back explicitly instead of being misrepresented as clean structure.

### 3. Incremental structuring

The pipeline prefers staged graph reduction over monolithic decompilation-style guessing.

### 4. Deterministic output

The same input should produce stable serialization and reproducible artifacts.

### 5. Test-driven iteration

Each stage is stress-tested with synthetic CFGs and real compiled binaries before being considered stable.

---

## Key Features

* Headless multi-backend extraction
* Canonical IR generation
* Address normalization and function canonicalization
* CFG analysis with dominators and post-dominators
* Structured region models:

  * `BlockNode`
  * `SequenceNode`
  * `IfNode`
  * `IfElseNode`
  * `LoopNode`
  * `UnstructuredRegionNode`
* Loop candidate validation and false-positive rejection
* Conservative hard-case classification:

  * irreducible regions
  * fragmented acyclic regions
  * multi-exit loop regions
  * switch-like dispatch regions
* Automatic artifact generation for debugging and validation
* Persisted pipeline logs in `artifacts/`

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
│   │   └── structuring/
│   │       ├── analysis.py
│   │       ├── builder.py
│   │       ├── conditionals.py
│   │       ├── dominators.py
│   │       ├── fallbacks.py
│   │       ├── graph.py
│   │       ├── loops.py
│   │       ├── models.py
│   │       ├── postdominators.py
│   │       └── reducers.py
│   └── scripts/
├── test/
│   └── simulate/
│       └── test_structuring.py
└── artifacts/
```

---

## Example Workflow

### 1. Run extractors and export IR

```bash
python3 main.py ./target_binary --ghidra --radare2 --export-ir
```

### 2. Run CFG analysis / structuring

```bash
python3 main.py analyze-cfg
```

### 3. Inspect generated artifacts

Typical outputs in `artifacts/`:

* `ghidra_extraction.json`
* `radare2_extraction.json`
* `unified_ir.json`
* `structuring_analysis.json`
* `structuring_regions.json`
* `orchestration_manifest.json`
* `run_<timestamp>.log`
* `latest.log`

---

## Structuring Output Model

The current structuring phase emits a control-flow tree rather than source code.

Examples of output node types:

* `block`
* `sequence`
* `if`
* `if_else`
* `loop`
* `unstructured`

This allows Hephaestus to:

* preserve structured regions when possible
* isolate unresolved regions without guessing
* prepare the data for later AST and source generation

---

## Hard Cases Currently Handled Conservatively

Hephaestus does **not** pretend every CFG can be perfectly structured.

Examples of cases intentionally handled conservatively:

* recursion-shaped entry-header cycles
* irreducible cyclic regions
* fragmented acyclic leftovers
* multi-exit loop bodies
* switch-like decision ladders / dispatch trees

These are preserved as explicit fallback regions instead of being flattened into misleading source-like structure.

---

## Validation Strategy

Phase 3 was validated using both:

* synthetic CFG-based unit tests
* compiled C stress binaries

Coverage includes:

* nested loops
* sibling loops
* deeply nested conditionals
* continue-if loop bodies
* multi-exit loops
* endless loops
* recursion-shaped false positives
* switch-like fan-out / decision ladders
* deterministic ordering under shuffled graph inputs

---

## What Hephaestus Is Not

At its current stage, Hephaestus is **not yet**:

* a full decompiler
* a finished source-code emitter
* a perfect solution for every possible CFG
* a substitute for mature reverse engineering suites

Its current role is to provide a **reliable, staged reconstruction backbone** that later phases can build on.

---

## Roadmap

### Phase 4 — Type Recovery

* stack / argument / heap interpretation
* type propagation
* signature inference
* struct / class layout hints

### Phase 5 — Source Reconstruction

* AST construction
* structured code emission
* uncertainty annotations where needed

### Phase 6 — Validation & Repair

* compile generated code
* detect structural mismatches
* feed corrections back into the pipeline

---

## Running Tests

Example:

```bash
python3 -m pytest test/simulate/test_structuring.py -v
```

Or, depending on the test layout:

```bash
python3 -m unittest discover -s test/simulate/
```

---

## Notes

Hephaestus is under active development. The current milestone is a stable Phase 3 control-flow structuring pipeline with conservative fallback handling and evidence-backed IR generation.
