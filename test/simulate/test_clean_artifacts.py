# -*- coding: utf-8 -*-
"""
Tests for clean-artifacts Safe Cleanup Utility
"""

from __future__ import annotations
import tempfile
import pytest
from pathlib import Path

from src.pipeline.clean_artifacts import clean_artifacts


def test_clean_artifacts_refuses_without_flags():
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td)
        with pytest.raises(ValueError, match="Must specify either --dry-run or --yes"):
            clean_artifacts(out_dir, dry_run=False, yes=False)


def test_clean_artifacts_dry_run_vs_yes():
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td)

        # Create known files
        rec = out_dir / "recovered.c"
        rec.write_text("int x;", encoding="utf-8")

        work = out_dir / ".work"
        work.mkdir()
        (work / "dummy.json").write_text("{}", encoding="utf-8")

        # Create protected user files
        env = out_dir / ".env"
        env.write_text("KEY=val", encoding="utf-8")
        notes = out_dir / "notes.txt"
        notes.write_text("my notes", encoding="utf-8")
        exp = out_dir / "experiment.c"
        exp.write_text("int y;", encoding="utf-8")

        # 1. Dry run
        res = clean_artifacts(out_dir, dry_run=True, yes=False)
        assert "recovered.c" in res["files_deleted"]
        assert ".work" in res["dirs_deleted"]
        assert ".env" in res["skipped"] or "notes.txt" in res["skipped"]

        # Dry run must delete NOTHING
        assert rec.exists()
        assert work.exists()
        assert env.exists()
        assert notes.exists()
        assert exp.exists()

        # 2. Yes run (actual deletion)
        res_yes = clean_artifacts(out_dir, dry_run=False, yes=True)
        assert "recovered.c" in res_yes["files_deleted"]
        assert ".work" in res_yes["dirs_deleted"]

        # Generated outputs must be deleted
        assert not rec.exists()
        assert not work.exists()

        # Protected user files must survive
        assert env.exists()
        assert notes.exists()
        assert exp.exists()
