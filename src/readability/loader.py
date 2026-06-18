# -*- coding: utf-8 -*-
"""
Readability Loader and Hash Verification Watchdog
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger("readability.loader")

def calculate_sha256(filepath: Path) -> Optional[str]:
    """Calculate the SHA-256 hash of a file if it exists, returning None otherwise."""
    if not filepath.exists() or not filepath.is_file():
        return None
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        logger.warning(f"Failed to hash {filepath}: {e}")
        return None

class HashWatchdog:
    """Watchdog to verify that no input artifacts are modified during readable code generation."""
    def __init__(self, out_dir: Path):
        self.out_dir = out_dir
        self.watch_files = [
            "recovered.c",
            "source_reconstruction.json",
            "evidence_index.json",
            "trace_report.json",
            "validation_report.json",
            "quality_gate.json",
            "unified_ir.json",
            "phase4_semantics.json",
            "layout_recovery.json",
            "type_recovery.json",
        ]
        self.initial_hashes: Dict[str, Optional[str]] = {}
        self.capture_hashes()

    def capture_hashes(self) -> None:
        """Capture hashes of watched files."""
        for name in self.watch_files:
            path = self.out_dir / name
            self.initial_hashes[name] = calculate_sha256(path)

    def verify_hashes(self) -> bool:
        """Verify if any watched file hash has changed. Returns True if all unchanged."""
        for name, initial_hash in self.initial_hashes.items():
            path = self.out_dir / name
            current_hash = calculate_sha256(path)
            if current_hash != initial_hash:
                logger.error(f"Input file violation: Hash of {name} changed from {initial_hash} to {current_hash}")
                return False
        return True

def load_readability_inputs(out_dir: Path) -> Tuple[str, Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], List[str]]:
    """
    Loads all inputs for readability recovery.
    Returns:
        recovered_c: content of recovered.c (string)
        source_recon: parsed source_reconstruction.json (dict or empty dict)
        evidence_idx: parsed evidence_index.json (dict or empty dict)
        trace_rep: parsed trace_report.json (dict or empty dict)
        qg_data: parsed quality_gate.json (dict or empty dict)
        unified_ir: parsed unified_ir.json (dict or empty dict)
        layout_recon: parsed layout_recovery.json (dict or empty dict)
        type_recon: parsed type_recovery.json (dict or empty dict)
        phase4_sem: parsed phase4_semantics.json (dict or empty dict)
        warnings: list of warnings for missing recommended artifacts (list of strings)
    Raises:
        FileNotFoundError: if recovered.c is missing
    """
    warnings = []
    
    recovered_c_path = out_dir / "recovered.c"
    if not recovered_c_path.exists():
        raise FileNotFoundError(f"Required artifact 'recovered.c' is missing at {recovered_c_path}")
        
    try:
        with open(recovered_c_path, "r", encoding="utf-8") as f:
            recovered_c = f.read()
    except Exception as e:
        raise OSError(f"Failed to read 'recovered.c': {e}")
        
    # Helper to load optional json
    def load_optional_json(filename: str) -> Dict[str, Any]:
        path = out_dir / filename
        if not path.exists():
            warnings.append(f"Recommended artifact '{filename}' is missing.")
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            warnings.append(f"Recommended artifact '{filename}' could not be parsed: {e}")
            return {}

    source_recon = load_optional_json("source_reconstruction.json")
    evidence_idx = load_optional_json("evidence_index.json")
    trace_rep = load_optional_json("trace_report.json")
    qg_data = load_optional_json("quality_gate.json")
    unified_ir = load_optional_json("unified_ir.json")
    layout_recon = load_optional_json("layout_recovery.json")
    type_recon = load_optional_json("type_recovery.json")
    phase4_sem = load_optional_json("phase4_semantics.json")
    
    # We also check for validation_report.json to record in watchdog if present
    validation_rep_path = out_dir / "validation_report.json"
    if not validation_rep_path.exists():
        warnings.append("Recommended artifact 'validation_report.json' is missing.")
        
    return recovered_c, source_recon, evidence_idx, trace_rep, qg_data, unified_ir, layout_recon, type_recon, phase4_sem, warnings
