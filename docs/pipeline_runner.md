# Pipeline Runner and Orchestration

Hephaestus provides a single command-line interface to orchestrate the multi-stage reconstruction pipeline from binary to C source.

## Stage Execution Flow

The stages run sequentially:
1. **extract**: Extract raw metadata using Ghidra and Radare2 subprocesses.
2. **analyze_cfg**: Construct dominator trees and extract structured region trees.
3. **recover_semantics**: Infer local types and signatures.
4. **refine_semantics**: Apply constraint resolution and extract ABI mappings.
5. **recover_layouts**: Infer struct member/offset candidates.
6. **finalize_semantics**: Combine recovered types and signatures.
7. **reconstruct_source**: Run the instruction lowerer and emit `recovered.c`.

## Command CLI Parameters

Run `main.py run-all <binary>`:
- `--ghidra`: Use Ghidra for metadata extraction.
- `--radare2`: Use Radare2 for metadata extraction.
- `--out-dir`: Directory for outputs.
- `--clean`: Clean up existing intermediate artifacts in `out_dir` before starting.
- `--no-source`: Stop execution before the source reconstruction stage.
- `--stop-after`: Execute stages up to and including the specified stage name.
- `--validate`: Run the static validation suite after the reconstruct_source stage.
- `--validate-strict`: Run the strict validation suite after the reconstruct_source stage, marking the pipeline status failed if validation checks return error findings.
