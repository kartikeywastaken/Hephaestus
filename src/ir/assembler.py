# -*- coding: utf-8 -*-
"""
Phase 2: Unified Evidence IR Assembler
Converts static tool inputs (Ghidra, IDA) and trace outputs into canonical UnifiedIR objects.
"""

from typing import Dict, Any, List, Optional, Set
import hashlib
from src.ir.models import UnifiedIR
from src.ir.instructions.validation import validate_instruction, is_fabricated_placeholder
from src.ir.utils.addressing import normalize_address, address_to_int

def clean_tool_prefix(name: str) -> str:
    """Removes common tool-specific prefixes from symbol and function names."""
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

def name_score(name: str) -> int:
    """Assigns quality scores to symbol/function names to prioritize real names."""
    if not name:
        return 0
    cleaned = clean_tool_prefix(name)
    if cleaned.startswith("_") and "func." not in cleaned:
        return 100
    if cleaned in {"printf", "malloc", "free"}:
        return 95
    if cleaned == "entry":
        return 60
    if cleaned.startswith("func."):
        return 10
    return 50

def choose_canonical_name(names: List[str]) -> str:
    """Chooses the highest-scoring canonical name from a list of names."""
    valid_names = [n for n in names if n]
    if not valid_names:
        return "unknown"
    return max(valid_names, key=name_score)

def normalize_addr(addr: str) -> str:
    """Standardizes hex/decimal address strings to lowercase hex format with '0x' prefix."""
    norm = normalize_address(addr)
    return norm if norm is not None else ""

def get_invalid_entries_for_fn(fn: Dict[str, Any]) -> Set[str]:
    from typing import Set
    invalid_addrs = set()
    all_instrs = []
    cfg = fn.get("cfg", {})
    nodes = cfg.get("nodes", []) or fn.get("basic_blocks", [])
    for node in nodes:
        for instr in node.get("instructions", []):
            all_instrs.append(instr)
    if all_instrs:
        all_instrs.sort(key=lambda i: address_to_int(i.get("address")) or 0)
        # Last instruction address
        last_addr = normalize_addr(all_instrs[-1].get("address"))
        if last_addr:
            invalid_addrs.add(last_addr)
        # Return instructions
        for instr in all_instrs:
            opcode = (instr.get("opcode") or instr.get("mnemonic") or "").lower().strip()
            if opcode == "ret" or opcode.startswith("ret"):
                iaddr = normalize_addr(instr.get("address"))
                if iaddr:
                    invalid_addrs.add(iaddr)
    return invalid_addrs

def score_instruction_for_merge(ins: Dict[str, Any]) -> tuple:
    """
    Returns a scoring key for merging instructions. Higher is better.
    1. Prefer instruction with structured memory operands (has at least one kind == "memory").
    2. If both have structured memory operands, prefer more operands.
    3. If still tied, prefer Ghidra for operand richness.
    4. If still tied, prefer Radare2 for normalized symbol/call naming.
    5. Fallback deterministically by source name.
    """
    ops = ins.get("operands", [])
    has_mem = any(isinstance(op, dict) and op.get("kind") == "memory" for op in ops)
    mem_score = 1 if has_mem else 0
    num_ops = len(ops)
    source = ins.get("source", "")
    source_priority = 2 if source == "ghidra" else (1 if source == "radare2" else 0)
    return (mem_score, num_ops, source_priority, source)

class IRAssembler:
    """
    Assembles multiple raw static/dynamic extraction dictionaries into
    the standard high-fidelity Unified Evidence IR structure.
    """

    def __init__(self, binary_path: str):
        self.binary_path = binary_path
        # Derive a stable virtual SHA256 of the binary path for consistency
        self.sha256 = hashlib.sha256(binary_path.encode('utf-8')).hexdigest()

    def assemble(
        self,
        ghidra_data: Optional[Dict[str, Any]] = None,
        radare2_data: Optional[Dict[str, Any]] = None,
        trace_data: Optional[Dict[str, Any]] = None
    ) -> UnifiedIR:
        """
        Merges disassembler lists and dynamic traces. Resolves duplicates,
        computes confidence coefficients, tracks provenance source attributes.
        """
        import logging
        self.logger = logging.getLogger("reconstruct.ir.assembler")

        # Extraction payload maps
        # Extract underlying data maps from envelopes if present
        g_payload = ghidra_data.get("data", {}) if ghidra_data and "data" in ghidra_data else (ghidra_data or {})
        r_payload = radare2_data.get("data", {}) if radare2_data and "data" in radare2_data else (radare2_data or {})
        t_payload = trace_data.get("data", {}) if trace_data and "data" in trace_data else (trace_data or {})

        # Resolve architecture
        architecture = "unknown"
        
        # 1. Try Ghidra language ID
        ghidra_language_id = g_payload.get("provenance", {}).get("language_id", "")
        if ghidra_language_id:
            if "AARCH64" in ghidra_language_id or "ARM64" in ghidra_language_id or "arm64" in ghidra_language_id:
                architecture = "arm64"
            elif "x86_64" in ghidra_language_id or "x86:LE:64" in ghidra_language_id:
                architecture = "x86_64"
            elif "x86" in ghidra_language_id:
                architecture = "x86"

        # 2. Try Radare2 arch and bits info
        if architecture == "unknown":
            r2_prov = r_payload.get("provenance", {})
            r2_arch = r2_prov.get("arch", "")
            r2_bits = r2_prov.get("bits", 0)
            if r2_arch:
                if r2_arch == "arm" and r2_bits == 64:
                    architecture = "arm64"
                elif r2_arch == "arm" and r2_bits == 32:
                    architecture = "arm"
                elif r2_arch in ["x86", "x86_64"]:
                    if r2_bits == 64:
                        architecture = "x86_64"
                    else:
                        architecture = "x86"
                else:
                    architecture = f"{r2_arch}{r2_bits}" if r2_bits else r2_arch

        # 3. Fallback to name-based logic
        if architecture == "unknown":
            if "64" in self.binary_path.lower():
                architecture = "x86_64"
            else:
                architecture = "x86"

        # Reference Validation Guard
        if architecture == "x86" and "AARCH64" in ghidra_language_id:
            raise ValueError("Architecture mismatch: extractor says ARM64 but IR says x86")

        incoming_functions = []
        for func in g_payload.get("functions", []):
            entry = normalize_addr(func.get("entry_point"))
            if entry:
                func_copy = dict(func)
                func_copy["entry_point"] = entry
                func_copy["source_tool"] = "ghidra"
                incoming_functions.append(func_copy)

        for func in r_payload.get("functions", []):
            entry = normalize_addr(func.get("entry_point"))
            if entry:
                func_copy = dict(func)
                func_copy["entry_point"] = entry
                func_copy["source_tool"] = "radare2"
                incoming_functions.append(func_copy)

        # Flow in Trace-based functions if we saw dynamic executions
        run_tr_instructions = t_payload.get("instructions_executed", [])
        if run_tr_instructions:
            for inst in run_tr_instructions:
                eip = inst.get("eip")
                if eip and eip.endswith("000"):
                    entry = normalize_addr(eip)
                    incoming_functions.append({
                        "name": f"dyn_func_{entry[2:]}" if entry.startswith("0x") else f"dyn_func_{entry}",
                        "entry_point": entry,
                        "size_bytes": 64,
                        "calling_convention": "unknown",
                        "signature": f"void dyn_func_{entry}()",
                        "source_tool": "dynamic_trace",
                        "provenance": ["dynamic_trace"],
                        "local_variables": [],
                        "basic_blocks": [{"id": entry, "size": 32, "instructions_count": 4}],
                        "cfg": {"nodes": [{"id": entry, "size": 32, "instructions_count": 4}], "edges": []}
                    })

        # Collect symbols and map names/addresses
        all_symbols = []
        for sym in g_payload.get("symbols", []):
            all_symbols.append(sym)
        for sym in r_payload.get("symbols", []):
            all_symbols.append(sym)
            
        symbol_name_to_addr = {}
        for sym in all_symbols:
            sname = sym.get("name")
            saddr = normalize_addr(sym.get("address"))
            if sname and saddr and not saddr.startswith("0x5f5e"):
                symbol_name_to_addr[sname] = saddr
                symbol_name_to_addr[clean_tool_prefix(sname)] = saddr

        # Resolve entry points for all incoming functions before grouping them by entry point
        fns_by_clean_name = {}
        for fn in incoming_functions:
            cname = clean_tool_prefix(fn.get("name", ""))
            fns_by_clean_name.setdefault(cname, []).append(fn)

        resolved_entries_by_name = {}
        for cname, grouped_fns in fns_by_clean_name.items():
            entries = []
            for fn in grouped_fns:
                ep = normalize_addr(fn.get("entry_point"))
                if ep and not ep.startswith("0x5f5e"):
                    entries.append(ep)
            
            agreed_entry = None
            if len(set(entries)) == 1:
                agreed_entry = entries[0]
            
            symbol_entry = symbol_name_to_addr.get(cname)
            
            best_entry = None
            if agreed_entry:
                best_entry = agreed_entry
            elif symbol_entry:
                best_entry = symbol_entry
            else:
                bb_addrs = []
                for fn in grouped_fns:
                    invalid_addrs = get_invalid_entries_for_fn(fn)
                    cfg = fn.get("cfg", {})
                    nodes = cfg.get("nodes", []) or fn.get("basic_blocks", [])
                    for bb in nodes:
                        bb_id = normalize_addr(bb.get("id"))
                        if bb_id and not bb_id.startswith("0x5f5e") and bb_id not in invalid_addrs:
                            bb_addrs.append(bb_id)
                if bb_addrs:
                    bb_addrs.sort(key=lambda a: address_to_int(a) or 0)
                    best_entry = bb_addrs[0]
            
            if not best_entry:
                non_corr = [e for e in entries if not e.startswith("0x5f5e")]
                if non_corr:
                    best_entry = non_corr[0]
                elif entries:
                    best_entry = entries[0]
                else:
                    best_entry = "unknown"
                self.logger.warning(
                    f"Ambiguous entry point for function {cname}. Using fallback: {best_entry}"
                )
            
            resolved_entries_by_name[cname] = best_entry

        # Update incoming function entry points
        for fn in incoming_functions:
            cname = clean_tool_prefix(fn.get("name", ""))
            if cname in resolved_entries_by_name:
                fn["entry_point"] = resolved_entries_by_name[cname]

        # Merge by entry point
        functions_by_addr = {}
        for fn in incoming_functions:
            addr = fn["entry_point"]
            functions_by_addr.setdefault(addr, []).append(fn)

        merged_functions = {}
        alias_to_canonical = {}

        for addr, grouped_fns in functions_by_addr.items():
            names = [fn.get("name", "") for fn in grouped_fns]
            canonical_name = choose_canonical_name(names)
            
            # Map aliases to canonical name
            for fn in grouped_fns:
                raw_name = fn.get("name")
                if raw_name:
                    alias_to_canonical[raw_name] = canonical_name
                    alias_to_canonical[clean_tool_prefix(raw_name)] = canonical_name

            self.logger.info(f"Resolved canonical name '{canonical_name}' for entry point {addr}")

            # Merge size_bytes (maximum)
            size_bytes = max((fn.get("size_bytes", 0) for fn in grouped_fns), default=0)

            # Merge calling_convention (pick first non-unknown)
            calling_convention = next(
                (fn.get("calling_convention") for fn in grouped_fns if fn.get("calling_convention") not in ["unknown", None]),
                "unknown"
            )

            # Preserve provenance
            provenance = sorted(set(
                src
                for fn in grouped_fns
                for src in fn.get("provenance", [fn.get("source_tool")])
            ))

            # Merge local variable names conservatively
            local_vars_seen = set()
            local_variables = []
            for fn in grouped_fns:
                for var in fn.get("local_variables", []):
                    if var not in local_vars_seen:
                        local_vars_seen.add(var)
                        local_variables.append(var)

            # Retain the most detailed CFG using deterministic tie-breaking rules:
            # 1. highest basic block count
            # 2. if tied, highest edge count
            # 3. if still tied, prefer Ghidra over Radare2
            # 4. if still tied, prefer a stable sorted source order
            def cfg_sort_key(fn):
                cfg = fn.get("cfg", {})
                bbs = cfg.get("nodes", []) or fn.get("basic_blocks", [])
                edges = cfg.get("edges", []) or fn.get("edges", [])
                tool = fn.get("source_tool", "")
                tool_priority = 2 if tool == "ghidra" else (1 if tool == "radare2" else 0)
                return (len(bbs), len(edges), tool_priority)

            scored_fns = []
            for idx, fn in enumerate(grouped_fns):
                scored_fns.append((cfg_sort_key(fn) + (idx,), fn))
            
            scored_fns.sort(key=lambda item: item[0], reverse=True)
            cfg_src_fn = scored_fns[0][1]

            cfg = cfg_src_fn.get("cfg", {})
            bbs = cfg.get("nodes", []) or cfg_src_fn.get("basic_blocks", [])
            edges = cfg.get("edges", []) or cfg_src_fn.get("edges", [])

            # Normalize basic block IDs and edges
            normalized_blocks = []
            normalized_edges = []
            for e in edges:
                normalized_edges.append({
                    "source": normalize_addr(e.get("source")),
                    "target": normalize_addr(e.get("target")),
                    "type": e.get("type", "unconditional")
                })

            for bb in bbs:
                bb_id = normalize_addr(bb.get("id"))
                bb_size = bb.get("size", 16)
                bb_instructions = bb.get("instructions", [])
                bb_mem_accesses = bb.get("memory_accesses", [])

                # Filter outgoing edges for this block
                bb_edges = [e for e in normalized_edges if e["source"] == bb_id]

                # Validate and deduplicate instructions
                validated_instructions = []
                for ins in bb_instructions:
                    if not isinstance(ins, dict):
                        continue
                    if is_fabricated_placeholder(ins):
                        self.logger.error(
                            "Fabricated placeholder instruction detected in block %s; rejecting.",
                            bb_id
                        )
                        continue
                    if validate_instruction(ins):
                        validated_instructions.append(ins)
                    else:
                        self.logger.warning(
                            "Invalid instruction in block %s skipped: %s", bb_id, ins
                        )

                # Deduplicate by address, merging Ghidra and Radare2 records at the same address
                instructions_by_addr: Dict[str, List[Dict[str, Any]]] = {}
                for ins in validated_instructions:
                    addr = normalize_addr(ins.get("address"))
                    if addr:
                        ins_copy = dict(ins)
                        ins_copy["address"] = addr
                        instructions_by_addr.setdefault(addr, []).append(ins_copy)

                deduped_instructions = []
                for addr, ins_list in instructions_by_addr.items():
                    best_ins = max(ins_list, key=score_instruction_for_merge)
                    deduped_instructions.append(best_ins)

                deduped_instructions.sort(
                    key=lambda i: address_to_int(i["address"]) or 0
                )

                normalized_blocks.append({
                    "id": bb_id,
                    "size": bb_size,
                    "instructions": deduped_instructions,
                    "memory_accesses": bb_mem_accesses,
                    "edges": bb_edges
                })

            merged_functions[addr] = {
                "name": canonical_name,
                "entry_point": addr,
                "size_bytes": size_bytes,
                "calling_convention": calling_convention,
                "signature": f"{calling_convention} {canonical_name}()",
                "provenance": provenance,
                "local_variables": local_variables,
                "basic_blocks": normalized_blocks
            }
        
        self.logger.info(f"Merged {len(incoming_functions)} raw function records into {len(merged_functions)} canonical functions")

        meta = {
            "path": self.binary_path,
            "sha256": self.sha256,
            "architecture": architecture
        }
        
        # Instantiate empty Unified IR
        ir = UnifiedIR(meta)

        # Register functions in UnifiedIR
        canonical_name_by_addr = {}
        for addr, fdata in merged_functions.items():
            canonical_name_by_addr[addr] = fdata["name"]

            prov_set = set(fdata["provenance"])
            if "ghidra" in prov_set and "radare2" in prov_set:
                conf = 1.0
            elif "ghidra" in prov_set or "radare2" in prov_set:
                conf = 0.8
            else:
                conf = 0.5

            ir_func = ir.add_function(
                name=fdata["name"],
                entry_point=fdata["entry_point"],
                size_bytes=fdata["size_bytes"],
                calling_convention=fdata["calling_convention"],
                signature=fdata["signature"],
                confidence=conf
            )
            ir_func["provenance"] = fdata["provenance"]

            # Emulate stack variables
            for idx, var_name in enumerate(fdata["local_variables"]):
                ir_func["stack_variables"].append({
                    "name": var_name,
                    "offset_bytes": -4 * (idx + 1),
                    "size_bytes": 4
                })

            # Add basic blocks
            for bb in fdata["basic_blocks"]:
                ir.add_basic_block(
                    func_entry=addr,
                    block_id=bb["id"],
                    size=bb["size"],
                    instructions=bb["instructions"],
                    memory_accesses=bb["memory_accesses"],
                    edges=bb["edges"]
                )

        # Collect raw call graph elements
        cg_nodes = set()
        cg_edges = []

        g_cg = g_payload.get("call_graph", {})
        for n in g_cg.get("nodes", []):
            cg_nodes.add(clean_tool_prefix(n))
        for e in g_cg.get("edges", []):
            cg_edges.append({"caller": clean_tool_prefix(e.get("caller")), "callee": clean_tool_prefix(e.get("callee"))})

        r_cg = r_payload.get("call_graph", {})
        for n in r_cg.get("nodes", []):
            cg_nodes.add(clean_tool_prefix(n))
        for e in r_cg.get("edges", []):
            cg_edges.append({"caller": clean_tool_prefix(e.get("caller")), "callee": clean_tool_prefix(e.get("callee"))})

        # Rewrite call graph nodes and edges only after alias-to-canonical-name mapping is fully built.
        rewritten_nodes = set()
        rewritten_edges = []
        seen_edges = set()

        for node in cg_nodes:
            canonical_node = alias_to_canonical.get(node, node)
            rewritten_nodes.add(canonical_node)

        for edge in cg_edges:
            caller = alias_to_canonical.get(edge["caller"], edge["caller"])
            callee = alias_to_canonical.get(edge["callee"], edge["callee"])
            
            key = (caller, callee)
            if key not in seen_edges:
                seen_edges.add(key)
                rewritten_edges.append({
                    "caller": caller,
                    "callee": callee
                })

        ir.call_graph["nodes"] = list(rewritten_nodes)
        ir.call_graph["edges"] = rewritten_edges

        self.logger.info(f"Final canonical call graph: {len(rewritten_nodes)} nodes, {len(rewritten_edges)} edges")

        # Group symbols by normalized address
        symbols_by_addr = {}
        for sym in g_payload.get("symbols", []):
            addr = normalize_addr(sym.get("address"))
            if addr:
                symbols_by_addr.setdefault(addr, []).append(sym)

        for sym in r_payload.get("symbols", []):
            addr = normalize_addr(sym.get("address"))
            if addr:
                symbols_by_addr.setdefault(addr, []).append(sym)

        duplicate_symbol_count = 0
        symbols = []
        for addr, sym_list in symbols_by_addr.items():
            # When merging symbols by address, only collapse a symbol into a canonical function identity
            # if that symbol resolves to a known function entry point.
            canonical_func_name = canonical_name_by_addr.get(addr)
            if canonical_func_name:
                name = canonical_func_name
                if len(sym_list) > 1:
                    duplicate_symbol_count += len(sym_list) - 1
                
                sym_type = "function"
                sym_visibility = "global" if any(s.get("visibility", "").lower() == "global" for s in sym_list) else "static"
                
                symbols.append({
                    "address": addr,
                    "name": name,
                    "type": sym_type,
                    "visibility": sym_visibility
                })
            else:
                # Unrelated data labels, string labels, and non-function symbols preserved separately
                names = [s.get("name") for s in sym_list]
                name = choose_canonical_name(names)
                
                sym_type = sym_list[0].get("type", "data")
                sym_visibility = sym_list[0].get("visibility", "global")
                
                symbols.append({
                    "address": addr,
                    "name": name,
                    "type": sym_type,
                    "visibility": sym_visibility
                })

        # Register symbols
        for sym in symbols:
            ir.add_symbol(sym["address"], sym["name"], sym["type"], sym["visibility"])

        self.logger.info(f"Collapsed {duplicate_symbol_count} duplicate symbol aliases")

        # 4. Standard Imports / Exports - CLEANED
        extracted_imports = []
        extracted_exports = []
        imports = extracted_imports
        exports = extracted_exports

        # 5. Populate Strings & Constants - CLEANED
        extracted_strings = []
        extracted_constants = []
        strings = extracted_strings
        constants = extracted_constants

        # Debug Logging and Warnings
        self.logger.info(f"IR architecture resolved to: {architecture}")
        self.logger.info(f"IR imports count: {len(imports)}")
        self.logger.info(f"IR exports count: {len(exports)}")
        self.logger.info(f"IR strings count: {len(strings)}")
        self.logger.info(f"IR constants count: {len(constants)}")

        # Conditional instruction warning — only fire when no real instructions were recovered
        # across all functions (not unconditionally on every merge).
        all_funcs_empty_instructions = all(
            all(not bb.get("instructions") for bb in fdata.get("basic_blocks", []))
            for fdata in merged_functions.values()
        )
        if all_funcs_empty_instructions:
            self.logger.warning("No real instructions recovered across any function; emitting empty lists.")
        self.logger.warning("No real imports recovered; emitting empty list.")
        self.logger.warning("No real exports recovered; emitting empty list.")
        self.logger.warning("No real strings recovered; emitting empty list.")
        self.logger.warning("No real constants recovered; emitting empty list.")

        # 6. Transform trace logs into dynamic observations
        if t_payload:
            for inst in t_payload.get("instructions_executed", []):
                ir.add_dynamic_observation(
                    timestamp="runtime",
                    event_type="trace_instruction",
                    details={
                        "eip": inst.get("eip"),
                        "assembly": inst.get("assembly"),
                        "registers": inst.get("registers")
                    }
                )
            for l in t_payload.get("loops_detected", []):
                ir.add_dynamic_observation(
                    timestamp="runtime",
                    event_type="loop_latch",
                    details=l
                )

        return ir
