# -*- coding: utf-8 -*-
"""
Unit Tests for Phase 7.2.1 Compile-Shape Hardening Patch
"""

import pytest
from src.readability.compile_shape import (
    validate_predicate_condition,
    harden_compile_shape_functions,
    dedupe_and_resolve_forward_declarations,
    is_global_function_collision,
    collect_declared_identifiers
)

def test_validate_predicate_condition():
    # Declared set
    declared = {"param_0", "local_m16"}
    
    # Case 1: All identifiers declared
    is_safe, missing = validate_predicate_condition("param_0 < local_m16", declared)
    assert is_safe
    assert not missing
    
    # Case 2: Undeclared but safe pseudo-registers (tmp_w8)
    is_safe, missing = validate_predicate_condition("tmp_w8 < local_m16", declared)
    assert is_safe
    assert missing == ["tmp_w8"]
    
    # Case 3: Undeclared and unsafe (custom name like 'some_var')
    is_safe, missing = validate_predicate_condition("some_var < local_m16", declared)
    assert not is_safe
    assert "some_var" in missing

    # Case 4: temp_w8 is safe under promote_temps
    is_safe, missing = validate_predicate_condition("temp_w8 < local_m16", declared, promote_temps_active=True)
    assert is_safe
    assert missing == ["temp_w8"]
    
    # temp_w8 not safe without promote_temps
    is_safe, missing = validate_predicate_condition("temp_w8 < local_m16", declared, promote_temps_active=False)
    assert not is_safe
    assert "temp_w8" in missing

def test_harden_compile_shape_functions_predicate_inserts():
    # C content with a predicate that uses tmp_w8 (which is missing)
    c_input = """
int32_t main(int32_t param_0)
{
    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    
    if (tmp_w8 < 5) {
        return 0;
    }
}
"""
    # Simulate predicate recovery adding tmp_w8 to missing lists
    added_decls = {
        "main": ["tmp_w8"]
    }
    
    hardened, items, stats = harden_compile_shape_functions(
        c_content=c_input,
        promote_temps_active=False,
        function_promotions={},
        original_types_by_func={},
        added_decls_from_predicates=added_decls
    )
    
    assert "u32 tmp_w8 = 0;" in hardened
    assert "Readability compile-shape declarations" in hardened
    assert stats["missing_predicate_declarations_added"] == 1
    assert any(x["name"] == "tmp_w8" and x["type"] == "u32" for x in items)

def test_harden_compile_shape_functions_body_scratch_inserts():
    # C content where body uses arg1 and temp_x9, but they are not declared.
    c_input = """
int32_t test_func()
{
    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    
    arg1 = 5;
    temp_x9 = 10;
    return 0;
}
"""
    
    hardened, items, stats = harden_compile_shape_functions(
        c_content=c_input,
        promote_temps_active=True,
        function_promotions={},
        original_types_by_func={},
        added_decls_from_predicates={}
    )
    
    assert "u64 arg1 = 0;" in hardened
    assert "u64 temp_x9 = 0;" in hardened
    assert stats["scratch_declarations_added"] == 2
    assert any(x["name"] == "arg1" and x["type"] == "u64" for x in items)
    assert any(x["name"] == "temp_x9" and x["type"] == "u64" for x in items)

def test_harden_compile_shape_functions_promoted_inserts():
    # C content where stack slot was promoted to local_m16, which is used in body but not declared.
    c_input = """
int32_t test_func()
{
    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    
    local_m16 = 5;
    return 0;
}
"""
    # original type was u32
    original_types = {
        "test_func": {
            "stack_m16": "u32"
        }
    }
    promotions = {
        "test_func": {
            "stack_m16": "local_m16"
        }
    }
    
    hardened, items, stats = harden_compile_shape_functions(
        c_content=c_input,
        promote_temps_active=False,
        function_promotions=promotions,
        original_types_by_func=original_types,
        added_decls_from_predicates={}
    )
    
    assert "u32 local_m16 = 0;" in hardened
    assert stats["scratch_declarations_added"] == 1
    assert any(x["name"] == "local_m16" and x["type"] == "u32" for x in items)

def test_harden_compile_shape_functions_scope_isolation():
    c_input = """
int32_t test_func1()
{
    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    
    arg1 = 5;
    return 0;
}

int32_t test_func2()
{
    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    
    return 0;
}
"""
    # arg1 used in test_func1 should not be declared in test_func2.
    hardened, items, stats = harden_compile_shape_functions(
        c_content=c_input,
        promote_temps_active=False,
        function_promotions={},
        original_types_by_func={},
        added_decls_from_predicates={}
    )
    
    # Split by function definition to verify
    funcs = hardened.split("int32_t")
    func1_body = funcs[1]
    func2_body = funcs[2]
    
    assert "arg1" in func1_body
    assert "arg1" not in func2_body

def test_comments_and_strings_ignored():
    # scratch variables inside comments or strings should NOT be auto-declared.
    c_input = """
int32_t test_func()
{
    /* Conservative pseudo declarations: */
    u64 tmp_sp = 0;
    
    /* This comment mentions arg1 and temp_w8 */
    char * str = "arg2 and temp_x0 inside string";
    return 0;
}
"""
    hardened, items, stats = harden_compile_shape_functions(
        c_content=c_input,
        promote_temps_active=True,
        function_promotions={},
        original_types_by_func={},
        added_decls_from_predicates={}
    )
    
    assert "u64 arg1" not in hardened
    assert "u32 temp_w8" not in hardened
    assert "u64 arg2" not in hardened
    assert "u64 temp_x0" not in hardened
    assert stats["scratch_declarations_added"] == 0

def test_forward_declaration_deduping():
    c_input = """
int32_t func_a(int32_t x);
int32_t func_a(int32_t x);

int32_t main()
{
    return 0;
}
"""
    normalized, items, stats = dedupe_and_resolve_forward_declarations(c_input)
    assert normalized.count("int32_t func_a(int32_t x);") == 1
    assert stats["forward_declarations_removed"] == 1

def test_forward_declaration_conflicts_resolved():
    # main(argc, argv) conflict with main(void)
    c_input = """
int32_t main(int32_t argc, char ** argv);
int32_t main(void);

int32_t main(int32_t argc, char ** argv)
{
    return 0;
}
"""
    normalized, items, stats = dedupe_and_resolve_forward_declarations(c_input)
    assert "int32_t main(int32_t argc, char **argv);" in normalized
    assert "int32_t main(void);" not in normalized
    assert stats["forward_declarations_removed"] == 1
    assert stats["forward_declaration_conflicts_resolved"] == 1

def test_forward_declaration_unresolved_conflict():
    # multiple prototypes, but no actual definition exists.
    # Prefer the one with more parameter details.
    c_input = """
int32_t mystery_func(int32_t x, int32_t y);
int32_t mystery_func(void);
"""
    normalized, items, stats = dedupe_and_resolve_forward_declarations(c_input)
    assert "int32_t mystery_func(int32_t x, int32_t y);" in normalized
    assert "int32_t mystery_func(void);" not in normalized
    assert stats["forward_declarations_removed"] == 1
    assert stats["forward_declaration_conflicts_resolved"] == 1

def test_global_function_collision():
    # Helper rename collision verification
    all_decls = {
        "printf": ["int32_t printf(const char * format, ...);"],
        "call_0x100001ab8": ["u64 call_0x100001ab8(void * a1);"]
    }
    
    # Collision target printf has signature with different params count/types
    has_collision = is_global_function_collision(
        proposed="printf",
        old_decl_signature="u64 call_0x100001ab8(void * a1);",
        all_declarations=all_decls
    )
    assert has_collision
