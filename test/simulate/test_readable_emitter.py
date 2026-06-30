# -*- coding: utf-8 -*-
"""
Tests for Readable C Emitter
"""

from src.readability.readable_emitter import emit_readable_c, extract_candidate_sites, DISCLAIMER_HEADER

def test_extract_candidate_sites():
    code = """
void test_fn() {
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: cbz w8")) {
        while (HEPHAESTUS_UNKNOWN_COND("condition unknown: block 0x1000")) {
            // some logic
        }
    }
}
"""
    candidates = extract_candidate_sites(code)
    assert len(candidates) == 2
    
    assert candidates[0]["line_number"] == 3
    assert candidates[0]["kind"] == "if"
    assert candidates[0]["function"] == "test_fn"
    assert "cbz w8" in candidates[0]["adapter_raw"]
    
    assert candidates[1]["line_number"] == 4
    assert candidates[1]["kind"] == "while"
    assert "condition unknown" in candidates[1]["adapter_raw"]

def test_emit_readable_c_replaces_correct_sites():
    code = """static int HEPHAESTUS_UNKNOWN_COND(const char *e) { return 0; }

void test_fn() {
    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: cbz w8")) {
        while (HEPHAESTUS_UNKNOWN_COND("condition unknown: block 0x1000")) {
            // inside loop
        }
    }
}
"""
    # map line 4 (if) to replacement, leave line 5 (while) unchanged
    recovered_sites = {
        4: ("tmp_w8 == 0", "cbz")
    }
    
    readable_c = emit_readable_c(code, recovered_sites)
    
    # Verify header prepended
    assert readable_c.startswith(DISCLAIMER_HEADER)
    
    # Verify helper preserved
    assert "static int HEPHAESTUS_UNKNOWN_COND(const char *e)" in readable_c
    
    # Verify replaced line
    # Should preserve indentation and add inline comment after the brace {
    assert "    if (tmp_w8 == 0) { /* inferred from cbz; uncertain */" in readable_c
    
    # Verify unchanged line is unchanged
    assert '        while (HEPHAESTUS_UNKNOWN_COND("condition unknown: block 0x1000")) {' in readable_c
    
    # Verify line endings/formatting is preserved
    assert "// inside loop" in readable_c
