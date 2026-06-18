# -*- coding: utf-8 -*-
"""
Phase 7.2 Static Readable Symbol and Local Promotion Engine
"""

import re
import logging
from typing import Dict, Any, List, Set, Tuple, Optional

logger = logging.getLogger("readability.symbol_promotion")

IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
STACK_VAR_RE = re.compile(r"^stack_(m)?([0-9]+)$")

# C keywords to avoid collisions
C_KEYWORDS = {
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if", "int",
    "long", "register", "return", "short", "signed", "sizeof", "static",
    "struct", "switch", "typedef", "union", "unsigned", "void", "volatile",
    "while", "u8", "u16", "u32", "u64", "i8", "i16", "i32", "i64", "uint8_t",
    "uint16_t", "uint32_t", "uint64_t", "int8_t", "int16_t", "int32_t", "int64_t",
    "HEPHAESTUS_UNKNOWN_COND", "HEPHAESTUS_CSET"
}

def split_c_line(line: str, inside_block_comment: bool) -> Tuple[List[Tuple[str, str]], bool]:
    """
    Statefully splits a C line into chunks of code, string literals, and comments.
    Preserves exact formatting and line endings.
    """
    chunks = []
    n = len(line)
    i = 0
    current_chunk = []
    
    def flush_code():
        if current_chunk:
            chunks.append(("code", "".join(current_chunk)))
            current_chunk.clear()
            
    while i < n:
        if inside_block_comment:
            # Looking for end of block comment '*/'
            if i + 1 < n and line[i:i+2] == "*/":
                chunks.append(("comment", "*/"))
                inside_block_comment = False
                i += 2
            else:
                end_idx = line.find("*/", i)
                if end_idx != -1:
                    chunks.append(("comment", line[i:end_idx]))
                    i = end_idx
                else:
                    chunks.append(("comment", line[i:]))
                    i = n
        else:
            if i + 1 < n and line[i:i+2] == "/*":
                flush_code()
                chunks.append(("comment", "/*"))
                inside_block_comment = True
                i += 2
            elif i + 1 < n and line[i:i+2] == "//":
                flush_code()
                chunks.append(("comment", line[i:]))
                i = n
            elif line[i] == '"':
                flush_code()
                str_chars = ['"']
                i += 1
                escaped = False
                while i < n:
                    c = line[i]
                    str_chars.append(c)
                    if escaped:
                        escaped = False
                    elif c == '\\':
                        escaped = True
                    elif c == '"':
                        i += 1
                        break
                    i += 1
                chunks.append(("string", "".join(str_chars)))
            elif line[i] == "'":
                flush_code()
                char_chars = ["'"]
                i += 1
                escaped = False
                while i < n:
                    c = line[i]
                    char_chars.append(c)
                    if escaped:
                        escaped = False
                    elif c == '\\':
                        escaped = True
                    elif c == "'":
                        i += 1
                        break
                    i += 1
                chunks.append(("string", "".join(char_chars)))
            else:
                current_chunk.append(line[i])
                i += 1
    flush_code()
    return chunks, inside_block_comment

def rewrite_code_chunk(code_text: str, rename_map: Dict[str, str]) -> str:
    """
    Safely replaces identifiers inside a code chunk using word boundaries.
    """
    if not rename_map:
        return code_text
        
    pattern = r"\b(" + "|".join(re.escape(k) for k in rename_map.keys()) + r")\b"
    
    def repl(match):
        old_name = match.group(1)
        return rename_map.get(old_name, old_name)
        
    return re.sub(pattern, repl, code_text)

def parse_c_into_functions(c_content: str) -> List[Dict[str, Any]]:
    """
    Parses C code into function blocks and global blocks.
    Uses brace-depth parsing to determine function boundaries.
    """
    lines = c_content.splitlines(keepends=True)
    blocks = []
    
    current_block_lines = []
    current_block_type = "global"
    current_block_name = "global"
    current_block_start = 0
    
    brace_depth = 0
    inside_function = False
    inside_block_comment = False
    
    # Matches function definition headers and excludes keywords (allowing optional trailing brace)
    func_header_regex = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_* ]+\s+([a-zA-Z0-9_]+)\s*\([^;]*\)\s*(\{)?\s*$')
    
    for idx, line in enumerate(lines):
        line_stripped = line.rstrip("\r\n")
        
        if not inside_function:
            m = func_header_regex.match(line_stripped)
            if m and m.group(1) not in {"if", "while", "for", "switch", "return"}:
                # Flush the current global block
                if current_block_lines:
                    blocks.append({
                        "type": current_block_type,
                        "name": current_block_name,
                        "lines": list(current_block_lines),
                        "start_line_idx": current_block_start
                    })
                    current_block_lines.clear()
                
                current_block_type = "function"
                current_block_name = m.group(1)
                current_block_start = idx
                inside_function = True
                brace_depth = 0
                
        current_block_lines.append(line)
        
        if inside_function:
            # We must split the line to check braces strictly in code chunks
            chunks, inside_block_comment = split_c_line(line, inside_block_comment)
            for c_type, c_text in chunks:
                if c_type == "code":
                    for char in c_text:
                        if char == "{":
                            brace_depth += 1
                        elif char == "}":
                            brace_depth -= 1
                            if brace_depth == 0:
                                blocks.append({
                                    "type": "function",
                                    "name": current_block_name,
                                    "lines": list(current_block_lines),
                                    "start_line_idx": current_block_start
                                })
                                current_block_lines.clear()
                                current_block_type = "global"
                                current_block_name = "global"
                                current_block_start = idx + 1
                                inside_function = False
                                break
                    if not inside_function:
                        break
                        
    if current_block_lines:
        blocks.append({
            "type": current_block_type,
            "name": current_block_name,
            "lines": list(current_block_lines),
            "start_line_idx": current_block_start
        })
        
    return blocks

def extract_identifiers_from_block(lines: List[str]) -> Set[str]:
    """
    Extracts all C identifiers present in code chunks of the block.
    """
    identifiers = set()
    inside_block_comment = False
    for line in lines:
        chunks, inside_block_comment = split_c_line(line, inside_block_comment)
        for c_type, c_text in chunks:
            if c_type == "code":
                words = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b", c_text)
                identifiers.update(words)
    return identifiers

def map_parameter_name(old_name: str) -> Optional[str]:
    """
    Converts parameter names argN and arg_N to param_N.
    """
    if old_name.startswith("arg"):
        suffix = old_name[3:]
        if suffix.startswith("_"):
            suffix = suffix[1:]
        if suffix:
            return f"param_{suffix}"
    return None

def map_stack_slot_name(old_name: str) -> Optional[str]:
    """
    Converts stack slot names to local_N or local_mN.
    """
    m = STACK_VAR_RE.match(old_name)
    if m:
        is_neg = m.group(1) is not None
        digits = m.group(2)
        if is_neg:
            return f"local_m{digits}"
        else:
            return f"local_{digits}"
    return None

def build_entry_point_map(source_recon: dict, type_recovery: dict) -> Dict[str, str]:
    """
    Maps function entry point addresses to canonical clean names.
    """
    ep_map = {}
    
    def process_function(f):
        ep = f.get("entry_point")
        if ep:
            ep_normalized = ep.strip().lower()
            if not ep_normalized.startswith("0x"):
                ep_normalized = "0x" + ep_normalized
                
            name = f.get("c_name") or f.get("canonical_name") or f.get("name")
            if name and IDENTIFIER_RE.match(name) and name not in C_KEYWORDS:
                if not (name.startswith("func_") or name.startswith("call_")):
                    ep_map[ep_normalized] = name
                    
    if source_recon:
        funcs = source_recon.get("data", {}).get("functions", []) or source_recon.get("functions", [])
        for f in funcs:
            process_function(f)
            
    if type_recovery:
        funcs = type_recovery.get("data", {}).get("functions", []) or type_recovery.get("functions", [])
        for f in funcs:
            process_function(f)
            
    return ep_map

def extract_metadata_parameters(fn_name: str, source_recon: dict, type_recovery: dict) -> List[Dict[str, Any]]:
    """
    Helper to extract parameter structures from reconstruction metadata.
    """
    # 1. Search in source_recon
    if source_recon:
        funcs = source_recon.get("data", {}).get("functions", []) or source_recon.get("functions", [])
        for f in funcs:
            if f.get("c_name") == fn_name or f.get("name") == fn_name or f.get("canonical_name") == fn_name:
                p = f.get("parameters", [])
                if p:
                    return p
                    
    # 2. Search in type_recovery
    if type_recovery:
        funcs = type_recovery.get("data", {}).get("functions", []) or type_recovery.get("functions", [])
        for f in funcs:
            if f.get("c_name") == fn_name or f.get("name") == fn_name or f.get("canonical_name") == fn_name:
                sig = f.get("signature") or f.get("recovered_signature") or f.get("refined_signature")
                if sig and isinstance(sig, dict):
                    p = sig.get("parameters", [])
                    if p:
                        return p
                        
    return []

def extract_metadata_layouts(fn_name: str, source_recon: dict, phase4_semantics: dict, layout_recovery: dict) -> List[Dict[str, Any]]:
    """
    Collects stack layout candidate structures from all present phase data.
    """
    candidates = []
    
    def matches(name):
        if not name:
            return False
        return name == fn_name or name == f"_{fn_name}" or f"_{name}" == fn_name
        
    if source_recon:
        funcs = source_recon.get("data", {}).get("functions", []) or source_recon.get("functions", [])
        for f in funcs:
            if matches(f.get("c_name")) or matches(f.get("name")) or matches(f.get("canonical_name")):
                lc = f.get("layout_candidates", [])
                if lc:
                    candidates.extend(lc)
                    
    if phase4_semantics:
        funcs = phase4_semantics.get("data", {}).get("functions", []) or phase4_semantics.get("functions", [])
        for f in funcs:
            if matches(f.get("c_name")) or matches(f.get("name")) or matches(f.get("canonical_name")):
                lc = f.get("layout_candidates", [])
                if lc:
                    candidates.extend(lc)
                    
    if layout_recovery:
        lc = layout_recovery.get("layout_candidates", []) or layout_recovery.get("data", {}).get("layout_candidates", [])
        if lc:
            for c in lc:
                if matches(c.get("function_name")):
                    candidates.append(c)
                    
    return candidates

def is_layout_artifact_backed(fn_name: str, offset: int, candidates: List[Dict[str, Any]]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Checks if a stack slot offset matches layout candidates observed offsets.
    """
    for c in candidates:
        observed = c.get("observed_offsets", [])
        if offset in observed:
            return True, "phase4_layout_stack_slot", c
    return False, None, None

class SymbolPromotionEngine:
    def __init__(
        self,
        source_recon: dict,
        type_recovery: dict,
        phase4_semantics: dict,
        layout_recovery: dict,
        promote_temps: bool = False
    ):
        self.source_recon = source_recon
        self.type_recovery = type_recovery
        self.phase4_semantics = phase4_semantics
        self.layout_recovery = layout_recovery
        self.promote_temps = promote_temps
        
        # Build global entry point address mapping
        self.ep_map = build_entry_point_map(source_recon, type_recovery)
        
        self.promotions_list = []
        self.skipped_list = []
        self.promotion_counter = 0
        
        # Diagnostics
        self.pseudo_registers_seen = 0
        self.pseudo_stack_slots_seen = 0
        self.register_aliases_created = 0
        self.stack_slots_promoted = 0
        self.parameters_promoted = 0
        self.temps_promoted = 0
        self.function_symbols_promoted = 0

    def get_next_promo_id(self) -> str:
        self.promotion_counter += 1
        return f"sym_{self.promotion_counter:06d}"

    def run_symbol_promotion(self, c_content: str) -> Tuple[str, dict]:
        """
        Executes token-safe symbol promotion on the C source content.
        Returns (rewritten_c, report_dict).
        """
        blocks = parse_c_into_functions(c_content)
        
        # Collect original declaration types before renaming
        self.original_types_by_func = {}
        for b in blocks:
            if b["type"] == "function":
                from src.readability.compile_shape import collect_original_declaration_types
                self.original_types_by_func[b["name"]] = collect_original_declaration_types(b)
        
        # 1. Step: Build global function renaming map
        global_fn_rename = {}
        all_identifiers = extract_identifiers_from_block(c_content.splitlines(keepends=True))
        
        from src.readability.compile_shape import collect_all_function_declarations, is_global_function_collision
        all_decls = collect_all_function_declarations(c_content)
        
        for name in all_identifiers:
            hex_part = None
            if name.startswith("call_0x"):
                hex_part = name[len("call_"):]
            elif name.startswith("func_0x"):
                hex_part = name[len("func_"):]
            elif name.startswith("func_") and name[5:].isalnum():
                hex_part = "0x" + name[len("func_"):]
                
            if hex_part:
                hex_norm = hex_part.lower()
                if hex_norm in self.ep_map:
                    proposed = self.ep_map[hex_norm]
                    # Verify no collision with helpers, keywords, or existing identifiers
                    if proposed in C_KEYWORDS:
                        continue
                        
                    old_decl = all_decls.get(name, ["u64 " + name + "();"])[0]
                    if is_global_function_collision(proposed, old_decl, all_decls):
                        self.skipped_list.append({
                            "promotion_id": self.get_next_promo_id(),
                            "function": "global",
                            "old_name": name,
                            "proposed_new_name": proposed,
                            "kind": "function",
                            "reason": "global function collision",
                            "confidence": "artifact_backed",
                            "evidence": {
                                "entry_point": hex_norm
                            }
                        })
                    elif proposed in all_identifiers:
                        self.skipped_list.append({
                            "promotion_id": self.get_next_promo_id(),
                            "function": "global",
                            "old_name": name,
                            "proposed_new_name": proposed,
                            "kind": "function",
                            "reason": "name collision",
                            "confidence": "artifact_backed",
                            "evidence": {
                                "entry_point": hex_norm
                            }
                        })
                    else:
                        global_fn_rename[name] = proposed
                        
        # 2. Step: Rewrite each block
        rewritten_blocks = []
        forward_decl_regex = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_* ]+\s+([a-zA-Z0-9_]+)\s*\([^;]*\)\s*;\s*$')
        
        func_param_renames = {}
        
        for b in blocks:
            if b["type"] == "function":
                fn_name = b["name"]
                existing_ids = extract_identifiers_from_block(b["lines"])
                
                # Identify variables and counts
                for name in existing_ids:
                    if name.startswith("tmp_"):
                        self.pseudo_registers_seen += 1
                    elif name.startswith("stack_"):
                        self.pseudo_stack_slots_seen += 1
                        
                # Resolve mapping for this function
                rename_map = self._resolve_function_promotions(fn_name, existing_ids)
                func_param_renames[fn_name] = {k: v for k, v in rename_map.items() if k.startswith("arg")}
                b["rename_map"] = rename_map
                
        self.function_promotions = {}
        for b in blocks:
            if b["type"] == "function":
                self.function_promotions[b["name"]] = b.get("rename_map", {})
                
        for b in blocks:
            if b["type"] == "global":
                rewritten_lines = []
                inside_block_comment = False
                for line in b["lines"]:
                    line_stripped = line.rstrip("\r\n")
                    line_ending = line[len(line_stripped):]
                    
                    m = forward_decl_regex.match(line_stripped)
                    local_rename = dict(global_fn_rename)
                    if m:
                        target_fn = m.group(1)
                        if target_fn in func_param_renames:
                            local_rename.update(func_param_renames[target_fn])
                        elif target_fn in global_fn_rename:
                            mapped_fn = global_fn_rename[target_fn]
                            if mapped_fn in func_param_renames:
                                local_rename.update(func_param_renames[mapped_fn])
                                
                    chunks, inside_block_comment = split_c_line(line_stripped, inside_block_comment)
                    rewritten_chunks = []
                    for c_type, c_text in chunks:
                        if c_type == "code":
                            rewritten_chunks.append(rewrite_code_chunk(c_text, local_rename))
                        else:
                            rewritten_chunks.append(c_text)
                    rewritten_lines.append("".join(rewritten_chunks) + line_ending)
                rewritten_blocks.append("".join(rewritten_lines))
                
            elif b["type"] == "function":
                fn_name = b["name"]
                local_rename = dict(global_fn_rename)
                local_rename.update(b.get("rename_map", {}))
                
                rewritten_lines = []
                inside_block_comment = False
                for line in b["lines"]:
                    line_stripped = line.rstrip("\r\n")
                    line_ending = line[len(line_stripped):]
                    
                    chunks, inside_block_comment = split_c_line(line_stripped, inside_block_comment)
                    rewritten_chunks = []
                    for c_type, c_text in chunks:
                        if c_type == "code":
                            rewritten_chunks.append(rewrite_code_chunk(c_text, local_rename))
                        else:
                            rewritten_chunks.append(c_text)
                    rewritten_lines.append("".join(rewritten_chunks) + line_ending)
                rewritten_blocks.append("".join(rewritten_lines))
                
        # Record function symbol promotions
        for old_fn, new_fn in global_fn_rename.items():
            self.function_symbols_promoted += 1
            self.promotions_list.append({
                "promotion_id": self.get_next_promo_id(),
                "function": "global",
                "old_name": old_fn,
                "new_name": new_fn,
                "kind": "function",
                "type": "u64",
                "source": "disassembly_symbols",
                "status": "promoted",
                "confidence": "artifact_backed",
                "evidence": {
                    "entry_point": old_fn[len("call_"):] if old_fn.startswith("call_") else old_fn[5:]
                },
                "notes": [
                    "Deterministic function alias resolution to artifact clean name."
                ]
            })
            
        report_data = {
            "pseudo_registers_seen": self.pseudo_registers_seen,
            "pseudo_stack_slots_seen": self.pseudo_stack_slots_seen,
            "symbols_promoted": len(self.promotions_list),
            "register_aliases_created": self.register_aliases_created,
            "stack_slots_promoted": self.stack_slots_promoted,
            "parameters_promoted": self.parameters_promoted,
            "temps_promoted": self.temps_promoted,
            "function_symbols_promoted": self.function_symbols_promoted,
            "promotion_skipped": len(self.skipped_list),
            "promotions": self.promotions_list,
            "skipped_promotions": self.skipped_list
        }
        
        return "".join(rewritten_blocks), report_data

    def _resolve_function_promotions(self, fn_name: str, existing_ids: Set[str]) -> Dict[str, str]:
        """
        Builds the symbol promotion mapping for a single function scope, resolving collisions.
        """
        rename_map = {}
        
        meta_params = extract_metadata_parameters(fn_name, self.source_recon, self.type_recovery)
        layout_candidates = extract_metadata_layouts(fn_name, self.source_recon, self.phase4_semantics, self.layout_recovery)
        
        proposed = {}
        
        # 1a. Propose Parameter promotions
        for param in meta_params:
            p_name = param.get("name")
            if p_name and p_name in existing_ids:
                mapped = map_parameter_name(p_name)
                if mapped:
                    p_type = param.get("type", "u64")
                    if isinstance(p_type, dict):
                        p_type_str = p_type.get("type", "u64")
                    else:
                        p_type_str = str(p_type)
                    proposed[p_name] = (
                        mapped,
                        "parameter",
                        "artifact_backed",
                        "source_reconstruction_parameter" if self.source_recon else "type_recovery_parameter",
                        {"index": param.get("index", 0), "type": p_type_str}
                    )
                    
        # 1b. Propose Stack slot promotions
        for name in existing_ids:
            mapped = map_stack_slot_name(name)
            if mapped:
                m = STACK_VAR_RE.match(name)
                is_neg = m.group(1) is not None
                offset = -int(m.group(2)) if is_neg else int(m.group(2))
                
                is_backed, source_name, cand = is_layout_artifact_backed(fn_name, offset, layout_candidates)
                confidence = "artifact_backed" if is_backed else "syntax_backed"
                source = source_name or "declaration_syntax"
                
                evidence = {
                    "offset": offset,
                    "base": "fp" if is_neg else "sp",
                    "layout_candidate": str(cand) if cand else None
                }
                
                proposed[name] = (mapped, "stack_slot", confidence, source, evidence)
                
        # 1c. Propose Temporary promotions if requested
        if self.promote_temps:
            for name in existing_ids:
                if name.startswith("tmp_"):
                    suffix = name[4:]
                    if suffix:
                        mapped = f"temp_{suffix}"
                        proposed[name] = (
                            mapped,
                            "temporary",
                            "syntax_backed",
                            "temporary_style",
                            {"register": suffix}
                        )
                        
        # 2. Check Name Collisions and Conflicts
        target_counts = {}
        for old, (new, *_) in proposed.items():
            target_counts[new] = target_counts.get(new, 0) + 1
            
        for old_name, (new_name, kind, confidence, source, evidence) in proposed.items():
            promo_id = self.get_next_promo_id()
            
            if old_name == new_name:
                continue
                
            if new_name in C_KEYWORDS or new_name in existing_ids:
                self.skipped_list.append({
                    "promotion_id": promo_id,
                    "function": fn_name,
                    "old_name": old_name,
                    "proposed_new_name": new_name,
                    "kind": kind,
                    "reason": "name collision",
                    "confidence": confidence,
                    "evidence": evidence
                })
                continue
                
            if target_counts[new_name] > 1:
                self.skipped_list.append({
                    "promotion_id": promo_id,
                    "function": fn_name,
                    "old_name": old_name,
                    "proposed_new_name": new_name,
                    "kind": kind,
                    "reason": "name collision",
                    "confidence": confidence,
                    "evidence": evidence
                })
                continue
                
            rename_map[old_name] = new_name
            
            if kind == "stack_slot":
                self.stack_slots_promoted += 1
            elif kind == "parameter":
                self.parameters_promoted += 1
            elif kind == "temporary":
                self.temps_promoted += 1
                self.register_aliases_created += 1
                
            self.promotions_list.append({
                "promotion_id": promo_id,
                "function": fn_name,
                "old_name": old_name,
                "new_name": new_name,
                "kind": kind,
                "type": "u64",
                "source": source,
                "status": "promoted",
                "confidence": confidence,
                "evidence": evidence,
                "notes": [
                    "Deterministic synthetic name promotion. Not recovered source name."
                ]
            })
            
        return rename_map
