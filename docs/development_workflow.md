# Development and Release Workflow

This document describes the branching, tagging, pre-merge testing, and rollback workflows for the Hephaestus project.

## Git Branching Strategy

- **main**: Protected branch representing stable, tested checkpoints. Direct commits and force pushes are strictly prohibited on `main`.
- **feature/fix branches**: Feature/refactor branches are branched off `main` and merged via pull request.
  - Namespace: `feat/` for new phases, `fix/` for bug fixes.

## Stable Checkpoint Tagging

To mark a stable release or phase completion:
```bash
git checkout main
git pull origin main
git tag -a v0.5.8 -m "Stable Phase 5.8 checkpoint"
git push origin v0.5.8
```

## Creating a New Phase Branch

To start work on a new phase:
```bash
git checkout main
git pull origin main
git checkout -b feat/phase5.9-refactor-docs
```

## Pre-Merge Testing Verification

Before merging any pull request, developers must ensure:
1. All local changes are committed.
2. The full unit test suite passes cleanly:
   ```bash
   python3 -m pytest -q
   ```
3. Run-all smoke test passes:
   ```bash
   python3 main.py run-all ./t --ghidra --radare2 --out-dir artifacts/refactor_smoke --clean
   ```

## Rollbacks and Resetting

### Rolling Back to a Stable Tag
If a phase breaks stability, roll back the workspace to the last tagged release:
```bash
git checkout v0.5.8
git checkout -b fix/retry-from-v0.5.8
```

### Dangerous Reset Warning
If you need to discard uncommitted changes or reset local branches:
```bash
# WARNING: This permanently discards all changes. Do not execute without saving.
git reset --hard v0.5.8
```
> [!CAUTION]
> Do NOT use `git push --force` or `git push --force-with-lease` on shared public branches or `main`.
