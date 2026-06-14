# -*- coding: utf-8 -*-
"""
Radare2 Extraction Implementation
Coordinates r2pipe analysis dispatches, symbols and CFG extraction, and JSON output formatting.
"""

import os
import time
from typing import Any, Dict, List, Optional
from src.engine.base import BaseExtractor, ExtractorError, execute_with_retry
from src.ir.instructions.validation import validate_instruction, is_fabricated_placeholder

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

    def __init__(self, binary_path: str, output_path: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(binary_path, output_path, config)
        self.radare2_log_messages = []

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

        self.radare2_log_messages = []
        self.radare2_log_messages.append(f"Binary path: {os.path.abspath(self.binary_path)}")

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
            self.radare2_log_messages.append("Command executed: aaa")
            r2.cmd("aaa")

            # Query binary info
            try:
                self.radare2_log_messages.append("Command executed: ij")
                info_raw = r2.cmdj("ij") or {}
                bin_info = info_raw.get("bin", {})
                arch = bin_info.get("arch", "")
                bits = bin_info.get("bits", 0)
                self.logger.info(f"Radare2 binary info: arch={arch}, bits={bits}")
                self.radare2_log_messages.append(f"Binary info: arch={arch}, bits={bits}")
            except Exception as e:
                self.logger.warning(f"Failed to get binary info (ij): {e}")
                self.radare2_log_messages.append(f"WARNING: Failed to get binary info (ij): {e}")
                arch, bits = "", 0

            # Extract functions
            try:
                self.radare2_log_messages.append("Command executed: aflj")
                functions_raw = r2.cmdj("aflj") or []
            except Exception as e:
                self.logger.warning(f"Failed to get functions list (aflj): {e}")
                self.radare2_log_messages.append(f"WARNING: Failed to get functions list (aflj): {e}")
                functions_raw = []
            self.logger.info(f"aflj returned {len(functions_raw)} functions")
            self.radare2_log_messages.append(f"aflj returned {len(functions_raw)} functions")
            if functions_raw:
                self.logger.debug(f"First aflj function object: {functions_raw[0]}")

            # Extract symbols
            try:
                self.radare2_log_messages.append("Command executed: isj")
                symbols_raw = r2.cmdj("isj") or []
            except Exception as e:
                self.logger.warning(f"Failed to get symbols list (isj): {e}")
                self.radare2_log_messages.append(f"WARNING: Failed to get symbols list (isj): {e}")
                symbols_raw = []
            self.logger.info(f"isj returned {len(symbols_raw)} symbols")
            self.radare2_log_messages.append(f"isj returned {len(symbols_raw)} symbols")

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
                    self.radare2_log_messages.append("WARNING: Function object discarded: empty/missing name field")
                    discarded_missing_name += 1
                    continue
                
                offset = func.get("addr") or func.get("offset")
                if offset is None:
                    self.logger.warning(f"Function {raw_func_name} discarded: missing address/offset")
                    self.radare2_log_messages.append(f"WARNING: Function {raw_func_name} discarded: missing address/offset")
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
                        cmd_str = f"afvj @ {func_ea}"
                        self.radare2_log_messages.append(f"Command executed: {cmd_str}")
                        afv_vars = r2.cmdj(cmd_str) or {}
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
                        self.radare2_log_messages.append(f"WARNING: Failed to run afvj for {func_name}: {e}")

                # CFG Nodes & Edges
                cfg_nodes = []
                cfg_edges = []
                try:
                    cmd_str = f"afbj @ {func_ea}"
                    self.radare2_log_messages.append(f"Command executed: {cmd_str}")
                    blocks = r2.cmdj(cmd_str) or []
                    self.logger.info(f"Function {func_name} basic blocks (CFG nodes) count: {len(blocks)}")
                    self.radare2_log_messages.append(f"Function {func_name} basic blocks count: {len(blocks)}")
                    for block in blocks:
                        addr = block.get("addr")
                        if addr is None:
                            continue
                        
                        block_id = hex(addr)
                        ninstr = block.get("ninstr", 0)
                        size = block.get("size", 0)

                        # Extract real instructions for this block (Amendment 1: range-filtered)
                        block_instructions = self._extract_block_instructions(
                            r2, addr, size, "radare2", ninstr=ninstr
                        )

                        cfg_nodes.append({
                            "id": block_id,
                            "size": size,
                            "instructions_count": len(block_instructions),
                            "estimated_instructions_count": ninstr,
                            "instructions": block_instructions,
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
                    self.radare2_log_messages.append(f"WARNING: Failed to extract CFG for {func_name}: {e}")

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
                    cmd_str = f"axffj @ {func_ea}"
                    self.radare2_log_messages.append(f"Command executed: {cmd_str}")
                    refs = r2.cmdj(cmd_str) or []
                    self.logger.info(f"axffj for {func_name} at {func_ea} returned {len(refs)} references")
                    self.radare2_log_messages.append(f"axffj for {func_name} at {func_ea} returned {len(refs)} references")
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
                    self.radare2_log_messages.append(f"WARNING: Failed to get callers/callees (axffj) for {func_name}: {e}")

            if discarded_missing_name > 0:
                self.logger.info(f"Discarded {discarded_missing_name} functions due to missing name")
                self.radare2_log_messages.append(f"Discarded {discarded_missing_name} functions due to missing name")
            if discarded_missing_offset > 0:
                self.logger.info(f"Discarded {discarded_missing_offset} functions due to missing address/offset")
                self.radare2_log_messages.append(f"Discarded {discarded_missing_offset} functions due to missing address/offset")

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
            self.radare2_log_messages.append(f"Recovered {len(call_edges)} call edges")

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

            # Write all Radare2 log messages to run.log
            from src.utils.run_logging import append_run_log
            append_run_log(os.path.dirname(self.output_path), "RADARE2", "\n".join(self.radare2_log_messages))

            from src.ir.utils.addressing import normalize_extractor_payload
            return normalize_extractor_payload(data)

        except Exception as e:
            # Append Radare2 execution error to run.log
            err_msg = f"Radare2 execution failed: {e}\n"
            if hasattr(self, "radare2_log_messages"):
                err_msg = "\n".join(self.radare2_log_messages) + f"\n\nERROR: Radare2 execution failed: {e}\n"
            from src.utils.run_logging import append_run_log
            append_run_log(os.path.dirname(self.output_path), "RADARE2", err_msg)
            raise ExtractorError(f"Radare2 execution failed: {e}")

    def _extract_block_instructions(
        self,
        r2: Any,
        block_addr_int: int,
        block_size: int,
        source: str,
        ninstr: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Extract and validate instructions for a single basic block using aoj, pdj, or pDj.

        Amendment 1 — Range filter:
            Any instruction whose address falls outside
            [block_addr_int, block_addr_int + block_size) is discarded.

        Amendment 3 — Missing opcode normalization:
            If opcode is absent, the first token of disasm is used.
        """
        if block_size <= 0:
            return []

        # Tweak 2: Calculate estimated instruction count
        estimated_ninstr = ninstr if ninstr and ninstr > 0 else max(1, block_size // 4)

        raw_instrs = None
        command_used = ""

        # Tweak 1: Prioritized commands (aoj -> pdj -> pDj)
        # 1. Try aoj (structured operands)
        try:
            command_used = f"aoj {estimated_ninstr} @ {block_addr_int}"
            self.radare2_log_messages.append(f"Command executed: {command_used}")
            raw_instrs = r2.cmdj(command_used)
        except Exception as e:
            self.logger.debug("aoj failed for block 0x%x: %s", block_addr_int, e)
            self.radare2_log_messages.append(f"ERROR: aoj failed for block 0x{block_addr_int:x}: {e}")

        # 2. Try pdj (disassembly JSON by instruction count)
        if not raw_instrs or not isinstance(raw_instrs, list):
            self.radare2_log_messages.append(f"FALLBACK: aoj failed or returned empty for block 0x{block_addr_int:x}. Trying pdj...")
            try:
                command_used = f"pdj {estimated_ninstr} @ {block_addr_int}"
                self.radare2_log_messages.append(f"Command executed: {command_used}")
                raw_instrs = r2.cmdj(command_used)
            except Exception as e:
                self.logger.debug("pdj failed for block 0x%x: %s", block_addr_int, e)
                self.radare2_log_messages.append(f"ERROR: pdj failed for block 0x{block_addr_int:x}: {e}")

        # 3. Try pDj (disassembly JSON by byte count)
        if not raw_instrs or not isinstance(raw_instrs, list):
            self.radare2_log_messages.append(f"FALLBACK: pdj failed or returned empty for block 0x{block_addr_int:x}. Trying pDj...")
            try:
                command_used = f"pDj {block_size} @ {block_addr_int}"
                self.radare2_log_messages.append(f"Command executed: {command_used}")
                raw_instrs = r2.cmdj(command_used)
            except Exception as e:
                self.logger.debug("pDj failed for block 0x%x: %s", block_addr_int, e)
                self.radare2_log_messages.append(f"ERROR: pDj failed for block 0x{block_addr_int:x}: {e}")

        if not raw_instrs or not isinstance(raw_instrs, list):
            return []

        block_end = block_addr_int + block_size
        validated: List[Dict[str, Any]] = []
        before_range_filter_count = len(raw_instrs)
        raw_addresses: List[str] = []

        for ri in raw_instrs:
            if not isinstance(ri, dict):
                continue

            # Tweak 3: Address handling (offset or addr or address)
            addr_val = ri.get("offset") or ri.get("addr") or ri.get("address")
            if addr_val is None:
                continue
            from src.ir.utils.addressing import address_to_int, normalize_address
            offset_int = address_to_int(addr_val)
            if offset_int is None:
                continue

            # Normalize address to lowercase hex string '0x...'
            norm_addr = normalize_address(addr_val)
            raw_addresses.append(norm_addr)

            # Tweak 6: Range filtering
            if offset_int < block_addr_int or offset_int >= block_end:
                self.logger.debug(
                    "Discarding out-of-range instruction at 0x%x (block 0x%x-0x%x)",
                    offset_int, block_addr_int, block_end,
                )
                continue

            # Build canonical instruction dict
            disasm = ri.get("disasm") or ri.get("text") or ""
            
            # Tweak 4: Opcode/mnemonic extraction precedence
            mnemonic = ri.get("mnemonic")
            raw = ri.get("disasm") or ri.get("opcode") or ""
            
            def get_first_token(s: str) -> str:
                if not s:
                    return ""
                parts = s.strip().split()
                return parts[0].lower() if parts else ""

            opcode_field = mnemonic or get_first_token(raw) or ri.get("type") or "unknown"

            operands = self._parse_r2_operands(ri, disasm)

            instr: Dict[str, Any] = {
                "address": norm_addr,
                "mnemonic": opcode_field.lower(),
                "opcode": opcode_field.lower(),
                "operands": operands,
                "size_bytes": ri.get("size"),
                "raw": disasm,
                "source": source,
            }

            # Guard: reject fabricated placeholders
            if is_fabricated_placeholder(instr):
                self.logger.error(
                    "Fabricated placeholder detected in r2 instruction at %s; rejected.",
                    norm_addr,
                )
                self.radare2_log_messages.append(f"ERROR: Fabricated placeholder detected in r2 instruction at {norm_addr}; rejected.")
                continue

            # Validate schema
            if validate_instruction(instr):
                validated.append(instr)
            else:
                self.logger.debug(
                    "Invalid instruction at %s skipped: %r", norm_addr, instr
                )
                self.radare2_log_messages.append(f"WARNING: Invalid instruction at {norm_addr} skipped.")

        # Tweak 6: range filter logging
        self.logger.info(
            "Radare2 Instruction Extraction Report:\n"
            "  Command used: %s\n"
            "  Block range: 0x%x - 0x%x\n"
            "  Instructions before range filter: %d\n"
            "  Instructions after range filter: %d\n"
            "  First few instruction addresses: %s",
            command_used, block_addr_int, block_end,
            before_range_filter_count, len(validated),
            raw_addresses[:5]
        )
        self.radare2_log_messages.append(
            f"Instruction Extraction Report for block 0x{block_addr_int:x}:\n"
            f"  Command used: {command_used}\n"
            f"  Block range: 0x{block_addr_int:x} - 0x{block_end:x}\n"
            f"  Instructions before range filter: {before_range_filter_count}\n"
            f"  Instructions after range filter: {len(validated)}\n"
            f"  First few instruction addresses: {raw_addresses[:5]}"
        )

        if before_range_filter_count > 0 and not validated:
            self.logger.warning(
                "Command '%s' returned %d instructions, but range filtering (0x%x - 0x%x) removed all of them! Raw addresses: %s",
                command_used, before_range_filter_count, block_addr_int, block_end, raw_addresses
            )
            self.radare2_log_messages.append(
                f"WARNING: Command '{command_used}' returned {before_range_filter_count} instructions, "
                f"but range filtering (0x{block_addr_int:x} - 0x{block_end:x}) removed all of them! Raw addresses: {raw_addresses}"
            )

        # Sort by normalized address
        from src.ir.utils.addressing import address_to_int
        validated.sort(key=lambda i: address_to_int(i.get("address")) or 0)
        return validated

    def _parse_r2_operands(self, ri: Dict[str, Any], disasm: str) -> List[Dict[str, Any]]:
        """
        Convert Radare2 opex operands to the canonical operand schema.

        Falls back to a single ``unknown`` operand from the disasm operand
        portion if structured operands are unavailable.
        """
        opex = ri.get("opex") or {}
        r2_ops = opex.get("operands") if isinstance(opex, dict) else None

        if isinstance(r2_ops, list) and r2_ops:
            result = []
            for op in r2_ops:
                if not isinstance(op, dict):
                    result.append({"kind": "unknown", "raw": str(op)})
                    continue
                op_type = op.get("type", "")
                if op_type == "reg":
                    result.append({"kind": "register", "value": op.get("value", "")})
                elif op_type == "imm":
                    result.append({"kind": "immediate", "value": op.get("value", 0)})
                elif op_type == "mem":
                    # Tweak 5: accept fields base, reg, disp, offset, delta, imm
                    base_val = op.get("base") or op.get("reg") or ""
                    offset_val = op.get("disp") or op.get("offset") or op.get("delta") or op.get("imm") or 0
                    result.append({
                        "kind": "memory",
                        "base": str(base_val),
                        "offset": offset_val,
                        "size_bytes": op.get("size"),
                    })
                else:
                    # If it's something else, represent as unknown but preserve raw
                    raw_val = op.get("value") or op.get("raw") or str(op)
                    result.append({"kind": "unknown", "raw": str(raw_val)})
            return result

        # Fallback: extract operand text portion from disasm
        parts = disasm.strip().split(None, 1)
        if len(parts) > 1 and parts[1].strip():
            return [{"kind": "unknown", "raw": parts[1].strip()}]
        return []
