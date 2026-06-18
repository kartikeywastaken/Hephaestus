# Stress Testing Harness

To guarantee stability, Hephaestus executes adversarial stress tests across randomized synthetically-generated ARM64 C programs.

## Testing Profiles

- **small**: Compiles and tests a small set of simple functions. Recommended for quick development smoke tests.
- **hard**: Compiles and runs the full adversarial torture test suite, stressing all arithmetic, paired load/store, conditional branches, and stack accesses.

## Execution

To execute:
```bash
python3 main.py stress-test --profile small --out-dir artifacts/stress/small --clean
```

## Stress Invariants

During execution, the stress harness compiles the generated `recovered.c` using `clang -fsyntax-only` and checks:
1. **Compilation Safety**: No syntax errors (warnings are allowed).
2. **Safety checks**: Preserves metrics under `stress_report.json` with schema version `stress-1.0`.
3. **Condition limits**: `condition_expressions_recovered` must remain `0`.
4. **Unsupported Invalid**: Unsupported instruction lists must not hide invalid mnemonics.
