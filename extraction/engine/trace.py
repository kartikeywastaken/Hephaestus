# -*- coding: utf-8 -*-
"""
Dynamic Trace Extractor Implementation
Processes x64dbg trace logs, instruction registers, and dynamic program execution.
"""

import os
from typing import Dict, Any, List, Optional
from extraction.engine.base import BaseExtractor, ExtractorError

class TraceExtractor(BaseExtractor):
    """
    Subsystem responsible for parsing sequential execution logs to find hot spots,
    executed jumps, and reconstruct dynamic loops.
    """

    def validate_environment(self) -> bool:
        """Verifies access to trace file and correct parsing logic."""
        if not self.binary_path or not os.path.exists(self.binary_path):
            raise ExtractorError(f"Dynamic trace file or binary target does not exist on disk: {self.binary_path}")
        return True

    def extract(self) -> Dict[str, Any]:
        """Runs execution trace parsing, identifying loops and execution flow."""
        self.validate_environment()

        try:
            raw_data = self._parse_trace_file()
            envelope = self.generate_envelope(raw_data, "Dynamic Trace Parser (x64dbg / dynamic)")
            self.save_artifact(envelope)
            return envelope
        except Exception as e:
            self.logger.error(f"Execution trace parse error: {e}")
            raise ExtractorError(f"Trace engine failed to compile deterministic sequences: {e}")

    def _parse_trace_file(self) -> Dict[str, Any]:
        """
        Parses trace files to compile sequential execute lists, branches, and register scopes.
        Supports standard text logs and detects loops via cycle analysis.
        """
        import json

        # Check if target is a binary executable or a text trace log
        with open(self.binary_path, "rb") as f:
            header = f.read(4)

        is_binary = any(header.startswith(sig) for sig in [b"\x7fELF", b"MZ", b"\xca\xfe\xba\xbe", b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf"])

        if is_binary:
            raise ExtractorError(
                "Dynamic binary instruction tracing cannot be run directly on raw executables "
                "without debugger privileges. Please provide a compiled x64dbg/gdb trace log file "
                "or configure a tracer in the environment."
            )

        instructions = []
        loops_detected = []
        dynamic_cfg_nodes = {}

        with open(self.binary_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith(";"):
                    continue

                # Parse lines like "address | instruction | registers" or "address: instruction"
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2:
                    eip = parts[0]
                    assembly = parts[1]
                    registers = {}
                    if len(parts) >= 3:
                        reg_parts = parts[2].split(",")
                        for rp in reg_parts:
                            if "=" in rp:
                                rk, rv = rp.split("=", 1)
                                registers[rk.strip()] = rv.strip()
                else:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        eip = parts[0].strip()
                        assembly = parts[1].strip()
                        registers = {}
                    else:
                        continue

                inst_entry = {"eip": eip, "assembly": assembly, "registers": registers}
                instructions.append(inst_entry)
                dynamic_cfg_nodes[eip] = dynamic_cfg_nodes.get(eip, 0) + 1

        # Heuristic cycle detector for loop detection
        visited_addresses = [inst["eip"] for inst in instructions]
        for i, addr in enumerate(visited_addresses):
            if visited_addresses.count(addr) > 1:
                try:
                    next_idx = visited_addresses.index(addr, i + 1)
                    loop_body = visited_addresses[i:next_idx]
                    if loop_body:
                        loop_entry = {
                            "loop_header": addr,
                            "loop_latches": [visited_addresses[next_idx - 1]],
                            "iteration_count": visited_addresses.count(addr)
                        }
                        if loop_entry not in loops_detected:
                            loops_detected.append(loop_entry)
                except ValueError:
                    pass

        cfg_nodes_list = [{"id": eip, "execution_count": count} for eip, count in dynamic_cfg_nodes.items()]

        return {
            "instructions_executed": instructions,
            "loops_detected": loops_detected,
            "dynamic_cfg_nodes": cfg_nodes_list,
            "trace_provenance": f"Real Trace Log Parser: {os.path.basename(self.binary_path)}"
        }
