# -*- coding: utf-8 -*-
"""
Phase 2: Unified Evidence Model (IR)
Defines high-fidelity, deterministic models representing static disassembly and dynamic trace.
"""

from typing import Dict, List, Any, Optional

class UnifiedIR:
    """
    Unified Intermediate Representation (IR) of the disassembled binary,
    integrating static analysis artifacts and dynamic observations.
    """
    SCHEMA_VERSION = "2.0.0"

    def __init__(self, binary_meta: Dict[str, Any]):
        self.provenance = {
            "binary_path": binary_meta.get("path", ""),
            "sha256": binary_meta.get("sha256", ""),
            "architecture": binary_meta.get("architecture", "x64"),
            "schema_version": self.SCHEMA_VERSION
        }
        self.functions: List[Dict[str, Any]] = []
        self.call_graph: Dict[str, Any] = {"nodes": [], "edges": []}
        self.symbols: List[Dict[str, Any]] = []
        self.imports: List[Dict[str, Any]] = []
        self.exports: List[Dict[str, Any]] = []
        self.strings: List[Dict[str, Any]] = []
        self.constants: List[Dict[str, Any]] = []
        self.dynamic_observations: List[Dict[str, Any]] = []

    def add_function(
        self,
        name: str,
        entry_point: str,
        size_bytes: int,
        calling_convention: str = "unknown",
        signature: str = "void func()",
        confidence: float = 1.0
    ):
        func = {
            "name": name,
            "entry_point": entry_point,
            "size_bytes": size_bytes,
            "calling_convention": calling_convention,
            "signature": signature,
            "confidence": confidence,
            "local_variables": [],
            "stack_variables": [],
            "heap_variables": [],
            "basic_blocks": []
        }
        self.functions.append(func)
        return func

    def add_basic_block(
        self,
        func_entry: str,
        block_id: str,
        size: int,
        instructions: List[str],
        memory_accesses: Optional[List[Dict[str, Any]]] = None,
        edges: Optional[List[Dict[str, Any]]] = None
    ):
        for func in self.functions:
            if func["entry_point"] == func_entry:
                bb = {
                    "id": block_id,
                    "size": size,
                    "instructions": instructions,
                    "memory_accesses": memory_accesses or [],
                    "edges": edges or []
                }
                func["basic_blocks"].append(bb)
                return bb
        return None

    def add_symbol(self, address: str, name: str, sym_type: str, visibility: str = "global"):
        self.symbols.append({
            "address": address,
            "name": name,
            "type": sym_type,
            "visibility": visibility
        })

    def add_string(self, address: str, value: str, length: int):
        self.strings.append({
            "address": address,
            "value": value,
            "length": length
        })

    def add_constant(self, value: Any, width_bits: int, declared_at: str):
        self.constants.append({
            "value": value,
            "width_bits": width_bits,
            "declared_at": declared_at
        })

    def add_import(self, name: str, source_module: str, address: str):
        self.imports.append({
            "name": name,
            "source_module": source_module,
            "address": address
        })

    def add_export(self, name: str, address: str):
        self.exports.append({
            "name": name,
            "address": address
        })

    def add_dynamic_observation(self, timestamp: str, event_type: str, details: Dict[str, Any]):
        self.dynamic_observations.append({
            "timestamp": timestamp,
            "event_type": event_type,
            "details": details
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "provenance": self.provenance,
            "data": {
                "functions": self.functions,
                "call_graph": self.call_graph,
                "symbols": self.symbols,
                "imports": self.imports,
                "exports": self.exports,
                "strings": self.strings,
                "constants": self.constants,
                "dynamic_observations": self.dynamic_observations
            }
        }
