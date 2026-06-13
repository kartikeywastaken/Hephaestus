# -*- coding: utf-8 -*-
"""
Radare2 Extraction Implementation
Coordinates r2pipe analysis dispatches, symbols and CFG extraction, and JSON output formatting.
"""

import os
import time
from typing import Dict, Any, Optional
from src.engine.base import BaseExtractor, ExtractorError, execute_with_retry

def clean_r2_name(name: str) -> str:
    """Removes common Radare2 prefixes from symbol and function names."""
    if not name:
        return name
    if name.startswith("sym.imp."):
        return name[len("sym.imp."):]
    if name.startswith("sym.fcn."):
        return name[len("sym.fcn."):]
    if name.startswith("sym."):
        return name[len("sym."):]
    if name.startswith("imp."):
        return name[len("imp."):]
    return name

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

            # Query binary info
            try:
                info_raw = r2.cmdj("ij") or {}
                bin_info = info_raw.get("bin", {})
                arch = bin_info.get("arch", "")
                bits = bin_info.get("bits", 0)
                self.logger.info(f"Radare2 binary info: arch={arch}, bits={bits}")
            except Exception as e:
                self.logger.warning(f"Failed to get binary info (ij): {e}")
                arch, bits = "", 0

            # Extract functions
            try:
                functions_raw = r2.cmdj("aflj") or []
            except Exception as e:
                self.logger.warning(f"Failed to get functions list (aflj): {e}")
                functions_raw = []
            self.logger.info(f"aflj returned {len(functions_raw)} functions")
            if functions_raw:
                self.logger.debug(f"First aflj function object: {functions_raw[0]}")

            # Extract symbols
            try:
                symbols_raw = r2.cmdj("isj") or []
            except Exception as e:
                self.logger.warning(f"Failed to get symbols list (isj): {e}")
                symbols_raw = []
            self.logger.info(f"isj returned {len(symbols_raw)} symbols")

            # Parse symbols and build an address-to-name map
            addr_to_symbol: Dict[str, str] = {}
            for sym in symbols_raw:
                name = sym.get("name", "")
                if not name:
                    continue
                vaddr = sym.get("vaddr") or sym.get("offset")
                if vaddr is not None:
                    cleaned_name = clean_r2_name(name)
                    vaddr_hex = hex(vaddr)
                    if vaddr_hex not in addr_to_symbol:
                        addr_to_symbol[vaddr_hex] = cleaned_name
                    else:
                        current = addr_to_symbol[vaddr_hex]
                        if current.startswith("func.") and not cleaned_name.startswith("func."):
                            addr_to_symbol[vaddr_hex] = cleaned_name

            # Structure functions
            functions = []
            call_nodes = set()
            call_edges = []

            discarded_missing_name = 0
            discarded_missing_offset = 0

            for func in functions_raw:
                raw_func_name = func.get("name", "")
                if not raw_func_name:
                    self.logger.warning("Function object discarded: empty/missing name field")
                    discarded_missing_name += 1
                    continue
                
                offset = func.get("addr") or func.get("offset")
                if offset is None:
                    self.logger.warning(f"Function {raw_func_name} discarded: missing address/offset")
                    discarded_missing_offset += 1
                    continue
                
                func_ea = hex(offset)
                func_name = addr_to_symbol.get(func_ea) or clean_r2_name(raw_func_name)
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
                    self.logger.info(f"Function {func_name} basic blocks (CFG nodes) count: {len(blocks)}")
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
                    refs = r2.cmdj(f"axffj @ {func_ea}") or []
                    self.logger.info(f"axffj for {func_name} at {func_ea} returned {len(refs)} references")
                    for ref in refs:
                        if ref.get("type") == "CALL":
                            raw_callee_name = ref.get("name")
                            if raw_callee_name:
                                callee_name = clean_r2_name(raw_callee_name)
                                call_edges.append({
                                    "caller": func_name,
                                    "callee": callee_name
                                })
                                call_nodes.add(callee_name)
                except Exception as e:
                    self.logger.warning(f"Failed to get callers/callees (axffj) for {func_name}: {e}")

            if discarded_missing_name > 0:
                self.logger.info(f"Discarded {discarded_missing_name} functions due to missing name")
            if discarded_missing_offset > 0:
                self.logger.info(f"Discarded {discarded_missing_offset} functions due to missing address/offset")

            # Structure symbols for return
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
                    "name": clean_r2_name(name),
                    "type": "function" if sym_type == "FUNC" else "data",
                    "visibility": "global" if sym_bind in ["GLOBAL", "WEAK"] else "static"
                })

            self.logger.info(f"Recovered {len(call_edges)} call edges")

            data = {
                "provenance": {
                    "tool_name": "Radare2",
                    "arch": arch,
                    "bits": bits
                },
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
