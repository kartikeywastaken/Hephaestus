# -*- coding: utf-8 -*-
"""
Phase 7.2.1 Compile-Shape Hardening Patch
Ensures recovered_readable.c compiles cleanly with no syntax errors.
"""

import re
import logging
from typing import Dict, Any, List, Set, Tuple, Optional
from src.readability.symbol_promotion import split_c_line, parse_c_into_functions, extract_identifiers_from_block, C_KEYWORDS

logger = logging.getLogger("readability.compile_shape")

DECL_TYPES = {
    "u8", "u16", "u32", "u64", "i8", "i16", "i32", "i64",
    "uint8_t", "uint16_t", "uint32_t", "uint64_t",
    "int8_t", "int16_t", "int32_t", "int64_t",
    "char", "int", "float", "double", "long", "short", "void", "size_t",
    "Item"
}

def collect_declared_identifiers(func_block: Dict[str, Any]) -> Set[str]:
    """
    Collects all declared identifiers (parameters and local variables) in a function block.
    """
    declared = set()
    
    # 1. Parse function parameters from header
    header_text = ""
    for line in func_block["lines"]:
        header_text += line
        if ")" in line:
            break
            
    m = re.search(r'\(([^)]*)\)', header_text)
    if m:
        params_str = m.group(1).strip()
        if params_str and params_str != "void":
            for param_decl in params_str.split(","):
                param_decl = param_decl.strip()
                words = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', param_decl)
                if words:
                    param_name = words[-1]
                    if param_name not in C_KEYWORDS:
                        declared.add(param_name)
                        
    # 2. Parse local declarations in function body
    decl_regex = re.compile(
        r'^\s*(?:const\s+|volatile\s+|static\s+)*([a-zA-Z_][a-zA-Z0-9_]*)\s*\*?\s*\*?\s*([a-zA-Z_][a-zA-Z0-9_]*)\b'
    )
    for line in func_block["lines"]:
        m = decl_regex.match(line.strip())
        if m:
            type_name = m.group(1)
            var_name = m.group(2)
            if (type_name in DECL_TYPES or type_name.endswith('_t') or type_name == "Item") and var_name not in C_KEYWORDS:
                declared.add(var_name)
                
    return declared

def collect_original_declaration_types(func_block: Dict[str, Any]) -> Dict[str, str]:
    """
    Collects original type names of variables declared inside the function.
    """
    types = {}
    decl_regex = re.compile(
        r'^\s*(?:const\s+|volatile\s+|static\s+)*([a-zA-Z_][a-zA-Z0-9_]*)\s*\*?\s*\*?\s*([a-zA-Z_][a-zA-Z0-9_]*)\b'
    )
    for line in func_block["lines"]:
        m = decl_regex.match(line.strip())
        if m:
            type_name = m.group(1)
            var_name = m.group(2)
            if type_name in DECL_TYPES or type_name.endswith('_t') or type_name == "Item":
                types[var_name] = type_name
    return types

def is_safe_pseudo_register(name: str, promote_temps_active: bool = False) -> bool:
    """
    Checks if an identifier is a safe pseudo-register form.
    """
    if name in {"tmp_sp", "tmp_fp", "tmp_lr"}:
        return True
    m_tmp = re.match(r'^tmp_([wx])([0-9]+)$', name)
    if m_tmp:
        reg_num = int(m_tmp.group(2))
        if 0 <= reg_num <= 30:
            return True
    if promote_temps_active:
        m_temp = re.match(r'^temp_([wx])([0-9]+)$', name)
        if m_temp:
            reg_num = int(m_temp.group(2))
            if 0 <= reg_num <= 30:
                return True
    return False

def validate_predicate_condition(
    replacement_cond: str,
    declared_ids: Set[str],
    promote_temps_active: bool = False
) -> Tuple[bool, List[str]]:
    """
    Validates replacement predicate. Checks if all identifiers are declared or are safe pseudo-registers.
    """
    words = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', replacement_cond)
    missing = []
    is_safe = True
    
    for w in words:
        if w in C_KEYWORDS:
            continue
        if w not in declared_ids:
            missing.append(w)
            if not is_safe_pseudo_register(w, promote_temps_active):
                is_safe = False
                
    return is_safe, missing

def get_completion_declaration(
    name: str,
    promote_map: Dict[str, str],
    original_types: Dict[str, str]
) -> Optional[Tuple[str, str]]:
    """
    Checks if name matches allowed scratch/promoted forms and returns (type, reason).
    """
    # 1. tmp_wN / temp_wN -> u32
    if re.match(r'^(tmp|temp)_w[0-9]+$', name):
        return "u32", "scratch pseudo-register"
        
    # 2. tmp_xN / temp_xN / tmp_sp / tmp_fp / tmp_lr -> u64
    if re.match(r'^(tmp|temp)_x[0-9]+$', name) or name in {"tmp_sp", "tmp_fp", "tmp_lr"}:
        return "u64", "scratch pseudo-register"
        
    # 3. argN / arg_N / param_N -> u64
    if re.match(r'^arg_?[0-9]+$', name) or re.match(r'^param_[0-9]+$', name):
        return "u64", "scratch identifier"
        
    # 4. local_mN / local_N -> type from stack_slot or u64
    if re.match(r'^local_m?[0-9]+$', name):
        # Find if it was promoted
        old_stack_name = None
        for k, v in promote_map.items():
            if v == name:
                old_stack_name = k
                break
        if old_stack_name:
            t = original_types.get(old_stack_name, "u64")
            return t, "promoted stack slot"
            
    return None

def insert_declarations_into_function(
    func_lines: List[str],
    decls: List[Tuple[str, str, str]]
) -> List[str]:
    """
    Inserts readability compile-shape declarations cleanly into function block lines.
    """
    if not decls:
        return func_lines
        
    # Find insertion index
    comment_idx = -1
    for idx, line in enumerate(func_lines):
        if "Conservative pseudo declarations:" in line:
            comment_idx = idx
            break
            
    insert_idx = -1
    if comment_idx != -1:
        # Find the last declaration line in the pseudo declaration block
        for idx in range(comment_idx + 1, len(func_lines)):
            line = func_lines[idx].strip()
            if line.startswith("/*") and not line.endswith("*/"):
                insert_idx = idx
                break
            elif line.startswith("/*") and "declarations" not in line.lower() and "layout" not in line.lower():
                insert_idx = idx
                break
            elif line and not line.endswith(";") and not line.startswith("//") and not line.startswith("/*"):
                insert_idx = idx
                break
    else:
        # No comment section, insert after opening brace { and metadata comments
        brace_idx = -1
        for idx, line in enumerate(func_lines):
            if "{" in line:
                brace_idx = idx
                break
        if brace_idx != -1:
            insert_idx = brace_idx + 1
            for idx in range(brace_idx + 1, len(func_lines)):
                line = func_lines[idx].strip()
                if line.startswith("/*") and "declarations" not in line.lower():
                    continue
                elif not line:
                    continue
                else:
                    insert_idx = idx
                    break
                    
    if insert_idx == -1:
        insert_idx = len(func_lines) - 1
        
    new_lines = []
    new_lines.append("\n")
    new_lines.append("    /* Readability compile-shape declarations: */\n")
    for type_name, var_name, comment in decls:
        new_lines.append(f"    {type_name} {var_name} = 0; /* {comment} */\n")
        
    result = list(func_lines)
    result[insert_idx:insert_idx] = new_lines
    return result

def normalize_sig(sig: str) -> str:
    """Normalize signature to a single space-separated string without semicolon."""
    sig = sig.strip().rstrip(";").strip()
    sig = re.sub(r'\s+', ' ', sig)
    return sig

def get_param_types(proto: str) -> List[str]:
    """Extract list of parameter types from a prototype signature."""
    m = re.search(r'\(([^)]*)\)', proto)
    if not m:
        return []
    params_str = m.group(1).strip()
    if not params_str or params_str == "void":
        return []
    types = []
    for p in params_str.split(","):
        p = p.strip()
        words = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', p)
        if len(words) > 1:
            type_part = re.sub(r'\b' + re.escape(words[-1]) + r'\s*$', '', p).strip()
            types.append(type_part)
        else:
            types.append(p)
    return types

def get_return_type(sig: str) -> str:
    """Extract return type of signature."""
    sig = sig.strip()
    m = re.match(r'^([a-zA-Z0-9_* ]+)\s+[a-zA-Z0-9_]+\s*\(', sig)
    if m:
        return m.group(1).strip()
    return "u64"

def collect_all_function_declarations(c_content: str) -> Dict[str, List[str]]:
    """
    Collects all declarations of functions (forward declarations or definitions) present in the C content.
    """
    decls = {}
    blocks = parse_c_into_functions(c_content)
    forward_decl_regex = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_* ]+\s+([a-zA-Z0-9_]+)\s*\([^;]*\)\s*;\s*$')
    
    for b in blocks:
        if b["type"] == "global":
            for line in b["lines"]:
                m = forward_decl_regex.match(line.strip())
                if m:
                    name = m.group(1)
                    decls.setdefault(name, []).append(line.strip())
        elif b["type"] == "function":
            name = b["name"]
            header_text = ""
            for line in b["lines"]:
                header_text += line
                if ")" in line:
                    break
            decls.setdefault(name, []).append(header_text.strip())
            
    return decls

def is_global_function_collision(
    proposed: str,
    old_decl_signature: str,
    all_declarations: Dict[str, List[str]]
) -> bool:
    """
    Checks if renaming a helper to 'proposed' causes a collision with existing declarations of a different signature.
    """
    if proposed not in all_declarations:
        return False
        
    old_ret = get_return_type(old_decl_signature)
    old_params = get_param_types(old_decl_signature)
    
    for p_decl in all_declarations[proposed]:
        p_ret = get_return_type(p_decl)
        p_params = get_param_types(p_decl)
        if p_ret != old_ret or len(p_params) != len(old_params):
            return True
            
    return False

def harden_compile_shape_functions(
    c_content: str,
    promote_temps_active: bool,
    function_promotions: Dict[str, Dict[str, str]],
    original_types_by_func: Dict[str, Dict[str, str]],
    added_decls_from_predicates: Dict[str, List[str]]
) -> Tuple[str, List[Dict[str, Any]], Dict[str, int]]:
    """
    Applies Fix 1 and Fix 2 to the function blocks of the C content.
    Returns (hardened_c, report_items, stats).
    """
    blocks = parse_c_into_functions(c_content)
    report_items = []
    stats = {
        "missing_predicate_declarations_added": 0,
        "scratch_declarations_added": 0
    }
    
    for b in blocks:
        if b["type"] != "function":
            continue
            
        fn_name = b["name"]
        promote_map = function_promotions.get(fn_name, {})
        orig_types = original_types_by_func.get(fn_name, {})
        
        # 1. Collect currently declared ids
        declared_ids = collect_declared_identifiers(b)
        
        # 2. Add missing predicate register declarations
        pred_decls_to_add = []
        pred_missing = added_decls_from_predicates.get(fn_name, [])
        for pm in pred_missing:
            if pm not in declared_ids:
                type_name = "u32" if "w" in pm else "u64"
                pred_decls_to_add.append((type_name, pm, "added for readable predicate compile-shape"))
                declared_ids.add(pm)
                stats["missing_predicate_declarations_added"] += 1
                report_items.append({
                    "kind": "declaration_added",
                    "function": fn_name,
                    "name": pm,
                    "type": type_name,
                    "reason": "predicate compile-shape",
                    "confidence": "syntax_backed"
                })
                
        # Insert them first so body check sees them
        b["lines"] = insert_declarations_into_function(b["lines"], pred_decls_to_add)
        
        # Re-collect declared ids after predicate insertions
        declared_ids = collect_declared_identifiers(b)
        
        # 3. Collect used ids in body
        used_ids = extract_identifiers_from_block(b["lines"])
        
        # 4. Check for undeclared scratch/promoted identifiers (Fix 2)
        scratch_decls_to_add = []
        for name in sorted(list(used_ids)):
            if name in C_KEYWORDS or name in declared_ids:
                continue
            res = get_completion_declaration(name, promote_map, orig_types)
            if res:
                type_name, reason = res
                scratch_decls_to_add.append((type_name, name, "added for readable compile-shape"))
                declared_ids.add(name)
                stats["scratch_declarations_added"] += 1
                report_items.append({
                    "kind": "declaration_added",
                    "function": fn_name,
                    "name": name,
                    "type": type_name,
                    "reason": "body scratch compile-shape",
                    "confidence": "syntax_backed"
                })
                
        # Insert scratch declarations
        b["lines"] = insert_declarations_into_function(b["lines"], scratch_decls_to_add)
        
    # Re-emit C content
    rewritten_blocks = []
    for b in blocks:
        rewritten_blocks.append("".join(b["lines"]))
        
    return "".join(rewritten_blocks), report_items, stats

def dedupe_and_resolve_forward_declarations(
    c_content: str
) -> Tuple[str, List[Dict[str, Any]], Dict[str, int]]:
    """
    Finds and resolves duplicate or conflicting forward declarations in the C content.
    Returns (normalized_c, report_items, stats).
    """
    blocks = parse_c_into_functions(c_content)
    forward_decl_regex = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_* ]+\s+([a-zA-Z0-9_]+)\s*\([^;]*\)\s*;\s*$')
    
    report_items = []
    stats = {
        "forward_declarations_removed": 0,
        "forward_declaration_conflicts_resolved": 0
    }
    
    # 1. Rename duplicate function definitions to avoid compile conflicts (Fix 3 Special Case & Definition safety)
    func_definitions_by_name = {}
    for b in blocks:
        if b["type"] == "function":
            func_definitions_by_name.setdefault(b["name"], []).append(b)
            
    for fn_name, def_blocks in func_definitions_by_name.items():
        if len(def_blocks) > 1:
            for idx, b in enumerate(def_blocks[1:], start=1):
                ep = None
                for line in b["lines"]:
                    m = re.search(r'/\*\s*Entry:\s*(0x[0-9a-fA-F]+)\s*\*/', line)
                    if m:
                        ep = m.group(1)
                        break
                if ep:
                    new_name = f"{fn_name}_{ep}"
                else:
                    new_name = f"{fn_name}_dup{idx}"
                
                # Update function definition header line
                for i in range(len(b["lines"])):
                    line = b["lines"][i]
                    if re.search(r'\b' + re.escape(fn_name) + r'\b', line) and "(" in line:
                        b["lines"][i] = re.sub(r'\b' + re.escape(fn_name) + r'\b', new_name, line)
                        break
                
                # Extract parameter signature of this definition
                header_text = ""
                for line in b["lines"]:
                    header_text += line
                    if ")" in line:
                        break
                def_params = get_param_types(header_text)
                
                b["name"] = new_name
                
                # Rename the matching forward declaration in global blocks
                for gb in blocks:
                    if gb["type"] == "global":
                        for i in range(len(gb["lines"])):
                            line = gb["lines"][i]
                            m = forward_decl_regex.match(line.strip())
                            if m and m.group(1) == fn_name:
                                p_types = get_param_types(line)
                                if len(p_types) == len(def_params):
                                    gb["lines"][i] = re.sub(r'\b' + re.escape(fn_name) + r'\b', new_name, line)
                                    break
                
                report_items.append({
                    "kind": "forward_declaration_conflict_resolved",
                    "function": fn_name,
                    "kept": f"int32_t {new_name}(...);",
                    "removed": f"int32_t {fn_name}(...);",
                    "reason": f"renamed duplicate definition to avoid global collision"
                })
                stats["forward_declaration_conflicts_resolved"] += 1
                
    # 2. Find actual function definitions
    definitions = {}
    for b in blocks:
        if b["type"] == "function":
            fn_name = b["name"]
            header_text = ""
            for line in b["lines"]:
                header_text += line
                if ")" in line:
                    break
            definitions[fn_name] = normalize_sig(header_text)
    
    # 2. Iterate through each block to rewrite forward declarations
    for b in blocks:
        if b["type"] != "global":
            continue
            
        new_lines = []
        fd_lines = []
        for line in b["lines"]:
            m = forward_decl_regex.match(line.strip())
            if m:
                fd_lines.append((m.group(1), line))
                
        by_func = {}
        for fn_name, line in fd_lines:
            by_func.setdefault(fn_name, []).append(line)
            
        resolved_fds = {}
        for fn_name, lines_list in by_func.items():
            if len(lines_list) == 1:
                resolved_fds[fn_name] = lines_list[0]
                continue
                
            unique_normalized = {}
            for line in lines_list:
                norm = normalize_sig(line)
                unique_normalized.setdefault(norm, []).append(line)
                
            if len(unique_normalized) == 1:
                kept = lines_list[0]
                resolved_fds[fn_name] = kept
                stats["forward_declarations_removed"] += len(lines_list) - 1
                continue
                
            # Conflicting prototypes exist!
            def_sig = definitions.get(fn_name)
            kept_line = None
            
            if def_sig:
                def_params = get_param_types(def_sig)
                def_ret = get_return_type(def_sig)
                
                for norm, instances in unique_normalized.items():
                    p_types = get_param_types(norm)
                    ret_type = get_return_type(norm)
                    if ret_type == def_ret and len(p_types) == len(def_params):
                        kept_line = instances[0]
                        break
                        
            if not kept_line:
                best_len = -1
                best_line = None
                for norm, instances in unique_normalized.items():
                    params = get_param_types(norm)
                    if len(params) > best_len:
                        best_len = len(params)
                        best_line = instances[0]
                kept_line = best_line
                
            resolved_fds[fn_name] = kept_line
            
            # Record resolved conflicts
            for line in lines_list:
                if line != kept_line:
                    stats["forward_declarations_removed"] += 1
                    stats["forward_declaration_conflicts_resolved"] += 1
                    report_items.append({
                        "kind": "forward_declaration_conflict_resolved",
                        "function": fn_name,
                        "kept": kept_line.strip(),
                        "removed": line.strip(),
                        "reason": "matched emitted function definition" if def_sig else "preferred signature with parameters"
                    })
                    
        seen_emitted = set()
        for line in b["lines"]:
            m = forward_decl_regex.match(line.strip())
            if m:
                fn_name = m.group(1)
                kept = resolved_fds[fn_name]
                if line == kept and fn_name not in seen_emitted:
                    new_lines.append(line)
                    seen_emitted.add(fn_name)
                else:
                    pass
            else:
                new_lines.append(line)
                
        b["lines"] = new_lines
        
    rewritten_blocks = []
    for b in blocks:
        rewritten_blocks.append("".join(b["lines"]))
        
    return "".join(rewritten_blocks), report_items, stats
