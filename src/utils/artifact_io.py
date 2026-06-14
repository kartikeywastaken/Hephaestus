# -*- coding: utf-8 -*-
"""
Centralized Artifact IO Utilities

Provides shared helpers for JSON artifact reading, writing, and provenance path
normalization used across all Phase 4 emitters and the main CLI.

Design rules:
- write_json_artifact always uses indent=2, ensure_ascii=False.
- write_json_artifact creates parent directories automatically.
- load_json_artifact returns the parsed dict or raises with a clear message.
- normalize_provenance_path normalizes to relative POSIX inside output_dir,
  absolute POSIX otherwise, or None for empty/None inputs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def normalize_provenance_path(
    path: Optional[str],
    output_dir: Path,
) -> Optional[str]:
    """
    Normalize a provenance path to be relative to *output_dir* when inside it,
    or absolute otherwise.  Always returns a POSIX path string or None.

    Parameters
    ----------
    path       : Raw file path string, or None.
    output_dir : The resolved output directory (parent of the artifact file).

    Returns
    -------
    str or None
        POSIX path string, or None if input is None/empty.
    """
    if not path:
        return None
    abs_path = Path(path).resolve()
    abs_out_dir = output_dir.resolve()
    try:
        relative = abs_path.relative_to(abs_out_dir)
        return relative.as_posix()
    except ValueError:
        return abs_path.as_posix()


def load_json_artifact(path: str) -> Dict[str, Any]:
    """
    Load and parse a JSON artifact from disk.

    Parameters
    ----------
    path : Absolute or relative path to the JSON file.

    Returns
    -------
    dict
        Parsed JSON content.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If the file cannot be decoded as JSON.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Artifact not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to decode JSON from {path}: {exc}") from exc


def write_json_artifact(path: str, data: Any) -> None:
    """
    Write a JSON artifact to disk with deterministic formatting.

    Creates parent directories automatically.  Uses indent=2 and
    ensure_ascii=False for human-readable, Unicode-safe output.

    Parameters
    ----------
    path : Absolute or relative path for the output file.
    data : JSON-serializable data (usually a dict).
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
