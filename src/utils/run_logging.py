# -*- coding: utf-8 -*-
"""
Centralized Run Logging Utility
Provides helper to append formatted sections into the shared run.log file.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

def append_run_log(out_dir: str | Path, section: str, message: str) -> None:
    """
    Appends a formatted section with a timestamp to artifacts/run.log.
    Never throws on failure; prints a warning to stderr or continues.
    """
    try:
        out_path = Path(out_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        log_file = out_path / "run.log"
        
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        # Border format
        border = "=" * 80
        header = f"\n{border}\n[{timestamp}] {section.upper()}\n{border}\n"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(header)
            f.write(message)
            if not message.endswith("\n"):
                f.write("\n")
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to append to run log: {e}\n")
