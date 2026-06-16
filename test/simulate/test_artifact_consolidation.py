# -*- coding: utf-8 -*-
"""
Tests for Artifact Consolidation and Safe Cleanup Utilities
"""

from __future__ import annotations
import os
import pytest
from pathlib import Path
import tempfile
import shutil

from src.utils.artifacts import ensure_out_dir, artifact_path, clean_known_artifacts, KNOWN_ARTIFACT_FILES

def test_ensure_out_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir) / "sub_artifacts"
        assert not out_dir.exists()
        resolved = ensure_out_dir(out_dir)
        assert out_dir.exists()
        assert resolved == out_dir.resolve()

def test_artifact_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        # Check standard known path
        path = artifact_path(out_dir, "recovered.c")
        assert path == out_dir.resolve() / "recovered.c"
        
        # Check unknown name rejection
        with pytest.raises(ValueError, match="Unknown artifact name"):
            artifact_path(out_dir, "unknown_file.txt")
            
        # Check path traversal attempts (even if name matches, traversal should be blocked)
        from src.utils.artifacts import KNOWN_ARTIFACT_FILES
        KNOWN_ARTIFACT_FILES.add("../../outside")
        try:
            with pytest.raises(ValueError, match="Path traversal"):
                artifact_path(out_dir, "../../outside")
        finally:
            KNOWN_ARTIFACT_FILES.remove("../../outside")

def test_clean_known_artifacts():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        
        # Create some known files
        known1 = out_dir / "recovered.c"
        known2 = out_dir / "unified_ir.json"
        known1.write_text("void main() {}", encoding="utf-8")
        known2.write_text("{}", encoding="utf-8")
        
        # Create an unrelated file
        unrelated = out_dir / "user_source.c"
        unrelated.write_text("int x = 10;", encoding="utf-8")
        
        # Create an input binary
        binary = out_dir / "target_bin"
        binary.write_bytes(b"\x00\x01\x02")
        
        # Create a known directory
        known_dir = out_dir / "ghidra_temp_proj"
        known_dir.mkdir()
        (known_dir / "dummy.txt").write_text("dummy", encoding="utf-8")
        
        # Create an unrelated directory
        unrelated_dir = out_dir / "user_dir"
        unrelated_dir.mkdir()
        (unrelated_dir / "dummy2.txt").write_text("dummy2", encoding="utf-8")

        # Run cleanup
        deleted = clean_known_artifacts(out_dir)
        
        # Assert deleted names list
        assert "recovered.c" in deleted
        assert "unified_ir.json" in deleted
        assert "ghidra_temp_proj" in deleted
        assert "user_source.c" not in deleted
        assert "target_bin" not in deleted
        assert "user_dir" not in deleted
        
        # Check files and directories on disk
        assert not known1.exists()
        assert not known2.exists()
        assert not known_dir.exists()
        assert unrelated.exists()
        assert binary.exists()
        assert unrelated_dir.exists()
