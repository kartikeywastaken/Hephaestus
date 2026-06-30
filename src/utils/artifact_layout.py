# -*- coding: utf-8 -*-
"""
Central Artifact Path Layout and Management
"""

from __future__ import annotations
from pathlib import Path

class ArtifactLayout:
    def __init__(self, out_dir: Path | str, mode: str = "flat"):
        self._root = Path(out_dir).resolve()
        self.mode = mode

    @property
    def root(self) -> Path:
        return self._root

    @property
    def work_dir(self) -> Path:
        return self._root / ".work"

    def final_path(self, filename: str) -> Path:
        return self._safe_resolve(self._root, filename)

    def work_path(self, filename: str) -> Path:
        return self._safe_resolve(self.work_dir, filename)

    def _safe_resolve(self, parent: Path, filename: str) -> Path:
        filename_p = Path(filename)
        # Handle absolute path components safely
        if filename_p.is_absolute():
            filename_p = Path(*filename_p.parts[1:])
        resolved = (parent / filename_p).resolve()
        try:
            resolved.relative_to(parent)
        except ValueError:
            raise ValueError(f"Path traversal detected: {filename} attempts to escape {parent}")
        return resolved

    def ensure_dirs(self) -> None:
        if self._root == Path("/").resolve() or self._root == Path.home().resolve():
            raise ValueError("Root or home directory are not allowed as output directory.")
        self._root.mkdir(parents=True, exist_ok=True)
        self.work_dir.mkdir(parents=True, exist_ok=True)
