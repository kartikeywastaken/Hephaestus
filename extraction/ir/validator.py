# -*- coding: utf-8 -*-
"""
Unified IR Schema Validation Module.
Performs precise model checks to confirm standard structure matches Phase 2 specifications.
"""

import json
from typing import Dict, Any, Tuple

class IRValidator:
    """
    Validates Unified Evidence IR payloads against the expected structural properties.
    """
    
    @staticmethod
    def validate_payload(payload: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates JSON schema payload structures programmatically.
        Returns (success: bool, msg: str)
        """
        # 1. Root structure
        if not isinstance(payload, dict):
            return False, "IR paylaod must be a root dict JSON object"
            
        required_root_keys = ["schema_version", "provenance", "data"]
        for key in required_root_keys:
            if key not in payload:
                return False, f"Missing required root key: '{key}'"

        # 2. Version validation
        schema_version = payload.get("schema_version")
        if schema_version != "2.0.0":
            return False, f"Unsupported schema version: '{schema_version}'. Expected '2.0.0'."

        # 3. Provenance validations
        prov = payload["provenance"]
        if not isinstance(prov, dict):
            return False, "provenance block must be a JSON dict"
        if "binary_path" not in prov:
            return False, "provenance must specify 'binary_path'"

        # 4. Core keys within Data Block
        data = payload["data"]
        if not isinstance(data, dict):
            return False, "data block must be a JSON dict"

        required_data_keys = [
            "functions", "call_graph", "symbols", "imports", 
            "exports", "strings", "constants", "dynamic_observations"
        ]
        for key in required_data_keys:
            if key not in data:
                return False, f"Missing required evidence key in data: '{key}'"

        # 5. Functions validation depth
        functions = data["functions"]
        if not isinstance(functions, list):
            return False, "data.functions must be a JSON array list"

        for idx, func in enumerate(functions):
            if not isinstance(func, dict):
                return False, f"Function index {idx} in functions must be an object"
            for f_key in ["name", "entry_point", "size_bytes", "basic_blocks"]:
                if f_key not in func:
                    return False, f"Function index {idx} (name: {func.get('name', 'unknown')}) missing required property '{f_key}'"
            
            # Check Basic Blocks structure
            bbs = func["basic_blocks"]
            if not isinstance(bbs, list):
                return False, f"basic_blocks in function '{func['name']}' must be a list"
            for bb_idx, bb in enumerate(bbs):
                if not isinstance(bb, dict):
                    return False, f"Basic block {bb_idx} in function '{func['name']}' must be an object"
                for bb_key in ["id", "instructions", "memory_accesses", "edges"]:
                    if bb_key not in bb:
                        return False, f"Basic block {bb_idx} in function '{func['name']}' missing required column '{bb_key}'"

        # 6. Call Graph validations
        cg = data["call_graph"]
        if not isinstance(cg, dict):
            return False, "data.call_graph must be a dictionary object"
        for cg_key in ["nodes", "edges"]:
            if cg_key not in cg:
                return False, f"call_graph dictionary missing container attribute '{cg_key}'"

        # 7. Check symbol list format
        if not isinstance(data["symbols"], list):
            return False, "symbols must be a JSON array"

        return True, "Payload structural schema constraints evaluated successfully."
