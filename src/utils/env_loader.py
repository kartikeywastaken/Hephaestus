# -*- coding: utf-8 -*-
"""
Environment variable loader from env files.
Does not depend on python-dotenv.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Union


def load_env_file(path: str | Path, *, override: bool = False) -> dict[str, str]:
    """
    Load KEY=VALUE lines from an env file.

    Rules:
    - Ignore blank lines.
    - Ignore lines beginning with #.
    - Support KEY=VALUE.
    - Strip surrounding single or double quotes from VALUE.
    - Do not override existing os.environ values unless override=True.
    - Return dict of loaded keys.
    - Never print secret values.
    """
    path_obj = Path(path)
    if not path_obj.is_file():
        return {}

    loaded = {}
    with open(path_obj, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if "=" in stripped:
                key, val = stripped.split("=", 1)
                key = key.strip()
                val = val.strip()

                # Strip surrounding single or double quotes from VALUE
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]

                loaded[key] = val

    # Do not override existing os.environ values unless override=True.
    for k, v in loaded.items():
        if override or k not in os.environ:
            os.environ[k] = v

    return loaded


def load_default_env_files(root: Path | None = None) -> dict[str, str]:
    """
    Load .env.local first, then .env, if present.
    Existing environment variables win by default.
    """
    if root is None:
        root = Path.cwd()
    else:
        root = Path(root)

    # Load .env.local (higher precedence, loaded first so it populates os.environ)
    local_loaded = load_env_file(root / ".env.local", override=False)
    # Load .env (lower precedence, loaded second, so it doesn't override .env.local/existing env)
    base_loaded = load_env_file(root / ".env", override=False)

    # Merge returned dictionary representing final loaded variables.
    # Since .env.local overrides .env, local_loaded takes precedence.
    merged = {}
    merged.update(base_loaded)
    merged.update(local_loaded)
    return merged
