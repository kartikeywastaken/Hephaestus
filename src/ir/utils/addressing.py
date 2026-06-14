# -*- coding: utf-8 -*-
"""
Central Address Normalization Utility
"""

from typing import Any
import re

def normalize_address(value: Any, *, assume_hex_strings: bool = True) -> str | None:
    """
    Standardizes hex/decimal address strings/ints to lowercase hex format with '0x' prefix.
    
    Rules:
    - None -> None
    - Integers -> hex string
    - Existing hex strings starting with 0x/0X -> normalized hex string
    - Bare Ghidra-style hex strings (length >= 6, hex characters only) -> hexadecimal text (not decimal)
    - Small decimal-looking strings (length < 6, digits only) -> decimal-converted hex string
    - Invalid strings -> None
    """
    if value is None:
        return None
    if isinstance(value, int):
        return hex(value).lower()
    
    val_str = str(value).strip()
    if not val_str:
        return None
    
    # Check if it has 0x or 0X prefix
    if val_str.lower().startswith("0x"):
        try:
            return hex(int(val_str, 16)).lower()
        except ValueError:
            return None
            
    # Check if the string consists of only hex characters
    if re.fullmatch(r'[0-9a-fA-F]+', val_str):
        if assume_hex_strings:
            # If length >= 6, treat as hex
            if len(val_str) >= 6:
                try:
                    return hex(int(val_str, 16)).lower()
                except ValueError:
                    return None
            else:
                # Small numeric strings can be treated as decimal only if they are clearly not address-like.
                # If they consist only of decimal digits, treat as base 10.
                if val_str.isdigit():
                    try:
                        return hex(int(val_str, 10)).lower()
                    except ValueError:
                        return None
                else:
                    # Otherwise, treat as hex (e.g. "abc")
                    try:
                        return hex(int(val_str, 16)).lower()
                    except ValueError:
                        return None
        else:
            # If assume_hex_strings is False, treat purely digit strings as decimal
            if val_str.isdigit():
                try:
                    return hex(int(val_str, 10)).lower()
                except ValueError:
                    return None
            else:
                try:
                    return hex(int(val_str, 16)).lower()
                except ValueError:
                    return None
                    
    return None

def address_to_int(value: Any) -> int | None:
    """
    Converts any address format to its integer value using normalize_address.
    """
    norm = normalize_address(value)
    if norm is None:
        return None
    try:
        return int(norm, 16)
    except ValueError:
        return None

def normalize_extractor_payload(data: dict) -> dict:
    """
    Normalizes all target address fields in extractor raw output (functions, symbols, blocks, edges, instructions).
    """
    if not isinstance(data, dict):
        return data
    
    # 1. symbols[*].address
    if "symbols" in data and isinstance(data["symbols"], list):
        for sym in data["symbols"]:
            if isinstance(sym, dict) and "address" in sym:
                sym["address"] = normalize_address(sym["address"])
                
    # 2. functions
    if "functions" in data and isinstance(data["functions"], list):
        for func in data["functions"]:
            if not isinstance(func, dict):
                continue
            if "entry_point" in func:
                func["entry_point"] = normalize_address(func["entry_point"])
                
            # CFG nodes and edges
            cfg = func.get("cfg")
            if isinstance(cfg, dict):
                # nodes
                if "nodes" in cfg and isinstance(cfg["nodes"], list):
                    for node in cfg["nodes"]:
                        if isinstance(node, dict):
                            if "id" in node:
                                node["id"] = normalize_address(node["id"])
                            # instructions[*].address
                            if "instructions" in node and isinstance(node["instructions"], list):
                                for instr in node["instructions"]:
                                    if isinstance(instr, dict) and "address" in instr:
                                        instr["address"] = normalize_address(instr["address"])
                                        # Also check operand names if kind is symbol
                                        for op in instr.get("operands", []):
                                            if isinstance(op, dict) and op.get("kind") == "symbol" and "name" in op:
                                                op["name"] = normalize_address(op["name"])
                # edges
                if "edges" in cfg and isinstance(cfg["edges"], list):
                    for edge in cfg["edges"]:
                        if isinstance(edge, dict):
                            if "source" in edge:
                                edge["source"] = normalize_address(edge["source"])
                            if "target" in edge:
                                edge["target"] = normalize_address(edge["target"])
                                
            # basic_blocks list (fallback schema)
            if "basic_blocks" in func and isinstance(func["basic_blocks"], list):
                for bb in func["basic_blocks"]:
                    if isinstance(bb, dict):
                        if "id" in bb:
                            bb["id"] = normalize_address(bb["id"])
                        # instructions[*].address
                        if "instructions" in bb and isinstance(bb["instructions"], list):
                            for instr in bb["instructions"]:
                                if isinstance(instr, dict) and "address" in instr:
                                    instr["address"] = normalize_address(instr["address"])
                                    for op in instr.get("operands", []):
                                        if isinstance(op, dict) and op.get("kind") == "symbol" and "name" in op:
                                            op["name"] = normalize_address(op["name"])
                        # edges
                        if "edges" in bb and isinstance(bb["edges"], list):
                            for edge in bb["edges"]:
                                if isinstance(edge, dict):
                                    if "source" in edge:
                                        edge["source"] = normalize_address(edge["source"])
                                    if "target" in edge:
                                        edge["target"] = normalize_address(edge["target"])
    
    # 3. call_graph address fields if present
    if "call_graph" in data and isinstance(data["call_graph"], dict):
        cg = data["call_graph"]
        if "nodes" in cg and isinstance(cg["nodes"], list):
            cg["nodes"] = [normalize_address(n) or n for n in cg["nodes"]]
        if "edges" in cg and isinstance(cg["edges"], list):
            for edge in cg["edges"]:
                if isinstance(edge, dict):
                    if "caller" in edge:
                        edge["caller"] = normalize_address(edge["caller"]) or edge["caller"]
                    if "callee" in edge:
                        edge["callee"] = normalize_address(edge["callee"]) or edge["callee"]
                        
    return data
