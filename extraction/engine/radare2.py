# -*- coding: utf-8 -*-
"""
Radare2 Extraction Implementation
Coordinates r2pipe analysis dispatches, symbols and CFG extraction, and JSON output formatting.
"""

import os
import time
from typing import Dict, Any, Optional
from extraction.engine.base import BaseExtractor, ExtractorError, execute_with_retry

class Radare2Extractor(BaseExtractor):
    """
    Subsystem managing custom headless Radare2 environments using r2pipe dispatches.
    Converts binary targets to standardized structural JSON schemas.
    """

    def validate_environment(self) -> bool:
        """
        Determines if radare2 is available.
        """
        radare2_path = self.config.get("RADARE2_PATH") or os.environ.get("RADARE2_PATH")
        if radare2_path:
            return os.path.exists(radare2_path)
        
        # Check if radare2 is on PATH using shutil.which
        import shutil
        return shutil.which("radare2") is not None

    def extract(self) -> Dict[str, Any]:
        """Runs the Radare2 extraction pipeline with built-in retry mechanisms."""
        if not self.validate_environment():
            raise ExtractorError("Encountered invalid or missing Radare2 configuration. Please check that radare2 is installed and on PATH.")

        def run_extraction() -> Dict[str, Any]:
            return self._execute_radare2_analysis()

        raw_data = execute_with_retry(run_extraction, retries=2)
        envelope = self.generate_envelope(raw_data, "Radare2 Headless Analyser")
        self.save_artifact(envelope)
        return envelope

    def _execute_radare2_analysis(self) -> Dict[str, Any]:
        """
        Executes Radare2 analysis via r2pipe and collects JSON outputs.
        """
        import r2pipe

        radare2_path = self.config.get("RADARE2_PATH") or os.environ.get("RADARE2_PATH")
        if radare2_path:
            # Prepend directory to PATH so r2pipe can find it
            if os.path.isdir(radare2_path):
                os.environ["PATH"] = radare2_path + os.pathsep + os.environ.get("PATH", "")
            elif os.path.isfile(radare2_path):
                os.environ["PATH"] = os.path.dirname(radare2_path) + os.pathsep + os.environ.get("PATH", "")

        try:
            self.logger.info(f"Opening binary targets for Radare2: {self.binary_path}")
            r2 = r2pipe.open(os.path.abspath(self.binary_path))
            
            # Analyze all (equivalent to aaa)
            self.logger.info("Running Radare2 analyzer auto-analysis (aaa)...")
            r2.cmd("aaa")

            # Extract functions
            try:
                functions_raw = r2.cmdj("aflj") or []
            except Exception as e:
                self.logger.warning(f"Failed to get functions list (aflj): {e}")
                functions_raw = []

            # Extract symbols
            try:
                symbols_raw = r2.cmdj("isj") or []
            except Exception as e:
                self.logger.warning(f"Failed to get symbols list (isj): {e}")
                symbols_raw = []

            # Structure functions
            functions = []
            call_nodes = set()
            call_edges = []

            for func in functions_raw:
                func_name = func.get("name", "")
                if not func_name:
                    continue
                
                offset = func.get("offset")
                if offset is None:
                    continue
                
                func_ea = hex(offset)
                call_nodes.add(func_name)

                # Calling convention
                cc = func.get("cc", "unknown")

                # Local variables
                local_vars = []
                for v in func.get("bpvars", []):
                    if "name" in v:
                        local_vars.append(v["name"])
                for v in func.get("spvars", []):
                    if "name" in v:
                        local_vars.append(v["name"])
                for v in func.get("regvars", []):
                    if "name" in v:
                        local_vars.append(v["name"])

                # If no variables found in aflj, try afvj (Analyze Function Variables JSON)
                if not local_vars:
                    try:
                        afv_vars = r2.cmdj(f"afvj @ {func_ea}") or {}
                        if isinstance(afv_vars, dict):
                            for var_list in afv_vars.values():
                                if isinstance(var_list, list):
                                    for v in var_list:
                                        if isinstance(v, dict) and "name" in v:
                                            local_vars.append(v["name"])
                        elif isinstance(afv_vars, list):
                            for v in afv_vars:
                                if isinstance(v, dict) and "name" in v:
                                    local_vars.append(v["name"])
                    except Exception as e:
                        self.logger.debug(f"Failed to run afvj for {func_name}: {e}")

                # CFG Nodes & Edges
                cfg_nodes = []
                cfg_edges = []
                try:
                    blocks = r2.cmdj(f"afbj @ {func_ea}") or []
                    for block in blocks:
                        addr = block.get("addr")
                        if addr is None:
                            continue
                        
                        block_id = hex(addr)
                        ninstr = block.get("ninstr", 0)
                        size = block.get("size", 0)

                        cfg_nodes.append({
                            "id": block_id,
                            "size": size,
                            "instructions_count": ninstr
                        })

                        jump = block.get("jump")
                        fail = block.get("fail")

                        if jump is not None:
                            jump_hex = hex(jump)
                            if fail is not None:
                                fail_hex = hex(fail)
                                cfg_edges.append({
                                    "source": block_id,
                                    "target": jump_hex,
                                    "type": "conditional"
                                })
                                cfg_edges.append({
                                    "source": block_id,
                                    "target": fail_hex,
                                    "type": "conditional"
                                })
                            else:
                                cfg_edges.append({
                                    "source": block_id,
                                    "target": jump_hex,
                                    "type": "unconditional"
                                })
                        elif fail is not None:
                            fail_hex = hex(fail)
                            cfg_edges.append({
                                    "source": block_id,
                                    "target": fail_hex,
                                    "type": "unconditional"
                                })
                except Exception as e:
                    self.logger.warning(f"Failed to extract CFG for {func_name}: {e}")

                functions.append({
                    "name": func_name,
                    "entry_point": func_ea,
                    "size_bytes": func.get("size", 0),
                    "calling_convention": cc,
                    "local_variables": local_vars,
                    "cfg": {
                        "nodes": cfg_nodes,
                        "edges": cfg_edges
                    }
                })

                # Extract callees / calls inside this function
                try:
                    callees = r2.cmdj(f"afcj @ {func_ea}") or []
                    for callee in callees:
                        if isinstance(callee, str):
                            callee_name = callee
                        elif isinstance(callee, dict) and "name" in callee:
                            callee_name = callee["name"]
                        else:
                            continue
                        call_edges.append({
                            "caller": func_name,
                            "callee": callee_name
                        })
                except Exception as e:
                    self.logger.debug(f"Failed to get callers/callees (afcj) for {func_name}: {e}")

            # Structure symbols
            symbols = []
            for sym in symbols_raw:
                name = sym.get("name", "")
                if not name:
                    continue
                
                vaddr = sym.get("vaddr") or sym.get("offset")
                if vaddr is None:
                    continue

                sym_type = sym.get("type", "").upper()
                sym_bind = sym.get("bind", "").upper()

                symbols.append({
                    "address": hex(vaddr),
                    "name": name,
                    "type": "function" if sym_type == "FUNC" else "data",
                    "visibility": "global" if sym_bind in ["GLOBAL", "WEAK"] else "static"
                })

            data = {
                "functions": functions,
                "symbols": symbols,
                "call_graph": {
                    "nodes": list(call_nodes),
                    "edges": call_edges
                }
            }

            try:
                r2.quit()
            except Exception:
                pass

            return data

        except Exception as e:
            raise ExtractorError(f"Radare2 execution failed: {e}")
