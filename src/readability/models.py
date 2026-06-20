# -*- coding: utf-8 -*-
"""
Readability Models and Schema Constants
"""

from typing import Dict, List, Any, Optional

SCHEMA_VERSION = "readability-1.3"
PHASE = "7.3"

# Branch Mappings
BRANCH_MAP = {
    "b.eq": "==",
    "b.ne": "!=",
    "b.lt": "<",
    "b.le": "<=",
    "b.gt": ">",
    "b.ge": ">=",
    "b.lo": "<",
    "b.cc": "<",
    "b.ls": "<=",
    "b.hi": ">",
    "b.hs": ">=",
    "b.cs": ">=",
}

UNSIGNED_BRANCHES = {"b.lo", "b.cc", "b.ls", "b.hi", "b.hs", "b.cs"}
