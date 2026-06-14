# Running Binary Reconstruction and Structuring Pipelines

This document lists the commands to compile, extract, and analyze real binaries using the Binary Reconstruction Platform.

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

## 6. Output Artifacts Generated

After running the commands above, the output folder will contain:
- `radare2_extraction.json` — Raw Radare2 analysis output.
- `ghidra_extraction.json` — Raw Ghidra headless analysis output.
- `unified_ir.json` — Merged, canonical Unified IR representation (Phase 2).
- `structuring_analysis.json` — Dominator, post-dominator, and back-edge report (Phase 3A).
- `structuring_regions.json` — Structured control-flow region tree serialization (Phase 3B).
- `type_recovery.json` — Phase 4A recovered function signatures and variables mapping.
- `semantic_recovery.json` — Phase 4B constraint-refined type records per function.
