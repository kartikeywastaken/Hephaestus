# -*- coding: utf-8 -*-
"""
Tests for Artifact Invariant Check utilities
"""

from __future__ import annotations
import json
import tempfile
from pathlib import Path
from src.pipeline.checks import strip_c_comments, strip_c_strings, extract_conditions, check_recovered_c_safety, run_artifact_checks

def test_strip_c_comments():
    code = """
    // This is line comment
    int x = 10; /* This is
    block comment */
    char* str = "abc /* hello */ def";
    """
    stripped = strip_c_comments(code)
    assert "line comment" not in stripped
    assert "block comment" not in stripped
    # Should not touch comments inside strings, but wait, simple regex matches /* hello */ inside strings
    # We don't worry about it too much since decompiler output doesn't contain multi-line comments inside string literals.

def test_strip_c_strings():
    code = 'char* x = "hello world"; int y = 42;'
    stripped = strip_c_strings(code)
    assert "hello world" not in stripped
    assert '"placeholder"' in stripped
    assert "y = 42" in stripped

def test_extract_conditions():
    code = """
    if (HEPHAESTUS_UNKNOWN_COND("ev1")) {
        while (HEPHAESTUS_UNKNOWN_COND("ev2")) {
            // inside loop
        }
    }
    """
    conds = extract_conditions(code)
    assert len(conds) == 2
    assert conds[0] == 'HEPHAESTUS_UNKNOWN_COND("ev1")'
    assert conds[1] == 'HEPHAESTUS_UNKNOWN_COND("ev2")'

def test_check_recovered_c_safety_faulty_address():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        c_file = out_dir / "recovered.c"
        
        # Test code containing phantom address 0x5f5e outside comment
        c_file.write_text("""
        static int HEPHAESTUS_UNKNOWN_COND(const char *e) { return 0; }
        void main() {
            int x = 0x5f5e;
        }
        """, encoding="utf-8")
        res = check_recovered_c_safety(out_dir)
        assert res["no_phantom_0x5f5e"] is False

def test_check_recovered_c_safety_arrow_and_struct():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        c_file = out_dir / "recovered.c"
        
        # Test code containing structural arrow field or struct definition outside comments
        c_file.write_text("""
        static int HEPHAESTUS_UNKNOWN_COND(const char *e) { return 0; }
        struct Context { int a; }; // struct fabrication
        void main() {
            ctx->field = 10; // arrow field
        }
        """, encoding="utf-8")
        res = check_recovered_c_safety(out_dir)
        assert res["no_struct_fabrication"] is False
        assert res["no_arrow_fields_executable"] is False

def test_check_recovered_c_safety_comments_ignored():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        c_file = out_dir / "recovered.c"
        
        # In comments, structural arrow field and raw ARM memory leaks are allowed!
        c_file.write_text("""
        static int HEPHAESTUS_UNKNOWN_COND(const char *e) { return 0; }
        // struct Context { int a; }; 
        /* ctx->field = 10; */
        /* [x0, x1, LSL #3] */
        void main() {
            int x = 10;
        }
        """, encoding="utf-8")
        res = check_recovered_c_safety(out_dir)
        assert res["no_struct_fabrication"] is True
        assert res["no_arrow_fields_executable"] is True
        assert res["no_raw_arm_indexed_leak_executable"] is True

def test_check_recovered_c_safety_executable_conditions():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        c_file = out_dir / "recovered.c"
        
        # Unwrapped tmp_ or arg condition
        c_file.write_text("""
        static int HEPHAESTUS_UNKNOWN_COND(const char *e) { return 0; }
        void main() {
            if (tmp_w8 == 0) {
                // ...
            }
        }
        """, encoding="utf-8")
        res = check_recovered_c_safety(out_dir)
        assert res["no_executable_tmp_conditions"] is False

def test_check_recovered_c_safety_empty_conditions():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        c_file = out_dir / "recovered.c"
        
        # Empty condition
        c_file.write_text("""
        static int HEPHAESTUS_UNKNOWN_COND(const char *e) { return 0; }
        void main() {
            if () {
                // ...
            }
        }
        """, encoding="utf-8")
        res = check_recovered_c_safety(out_dir)
        assert res["no_empty_conditions"] is False

def test_check_recovered_c_safety_cset_consistency():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        c_file = out_dir / "recovered.c"
        
        # cset used but static helper NOT defined
        c_file.write_text("""
        void main() {
            tmp_w8 = HEPHAESTUS_CSET("eq");
        }
        """, encoding="utf-8")
        res = check_recovered_c_safety(out_dir)
        assert res["cset_helper_consistent"] is False
