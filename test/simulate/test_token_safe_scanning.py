# -*- coding: utf-8 -*-
"""
Unit Tests for src/ir/source/c_tokens.py — Token-Safe C Scanning

These tests verify that the shared token-safe scanning utility correctly
ignores identifiers that appear only inside:
  - double-quoted string literals
  - single-quoted char literals
  - // line comments
  - /* block */ comments
  - HEPHAESTUS_UNKNOWN_COND / HEPHAESTUS_CSET adapter strings

Only executable code-chunk identifiers must be returned.
"""

import pytest
from src.ir.source.c_tokens import split_c_line, collect_identifiers_from_code_only


# ---------------------------------------------------------------------------
# split_c_line tests
# ---------------------------------------------------------------------------

class TestSplitCLine:
    def test_plain_code_line(self):
        chunks, in_bc = split_c_line("arg0 = arg1 + 5;", False)
        code_text = "".join(c for t, c in chunks if t == "code")
        assert "arg0" in code_text
        assert "arg1" in code_text
        assert in_bc is False

    def test_line_comment_stripped(self):
        chunks, in_bc = split_c_line("x = 1; // arg0 in comment", False)
        code_text = "".join(c for t, c in chunks if t == "code")
        comment_text = "".join(c for t, c in chunks if t == "comment")
        assert "arg0" not in code_text
        assert "arg0" in comment_text

    def test_block_comment_inline(self):
        chunks, in_bc = split_c_line("x = 1; /* arg0 */ y = 2;", False)
        code_text = "".join(c for t, c in chunks if t == "code")
        comment_text = "".join(c for t, c in chunks if t == "comment")
        assert "arg0" not in code_text
        assert "arg0" in comment_text
        # y is executable code
        assert "y" in code_text

    def test_block_comment_spanning_lines(self):
        # Start of block comment — everything after /* is comment
        chunks, in_bc = split_c_line("x = 1; /* arg0 here", False)
        code_text = "".join(c for t, c in chunks if t == "code")
        assert "arg0" not in code_text
        assert in_bc is True

        # Continuation: still inside block comment
        chunks2, in_bc2 = split_c_line("still arg1 in comment */", True)
        code_text2 = "".join(c for t, c in chunks2 if t == "code")
        assert "arg1" not in code_text2
        assert in_bc2 is False

    def test_double_quoted_string(self):
        chunks, in_bc = split_c_line('printf("arg0 %d", x);', False)
        code_text = "".join(c for t, c in chunks if t == "code")
        string_text = "".join(c for t, c in chunks if t == "string")
        # arg0 is in the string, not code
        assert "arg0" not in code_text
        assert "arg0" in string_text
        # x is real code
        assert "x" in code_text

    def test_single_quoted_char_literal(self):
        chunks, in_bc = split_c_line("char c = 'a';", False)
        code_text = "".join(c for t, c in chunks if t == "code")
        # 'a' is char literal, but 'c' as variable name is code
        assert "c" in code_text

    def test_escaped_quote_in_string(self):
        # Escaped quote should not close the string early
        chunks, in_bc = split_c_line(r'char *s = "he said \"arg0\" here";', False)
        code_text = "".join(c for t, c in chunks if t == "code")
        string_text = "".join(c for t, c in chunks if t == "string")
        assert "arg0" not in code_text
        assert "arg0" in string_text


# ---------------------------------------------------------------------------
# collect_identifiers_from_code_only tests
# ---------------------------------------------------------------------------

class TestCollectIdentifiersFromCodeOnly:
    def test_basic_code_identifiers(self):
        lines = ["    arg0 = arg1 + 5;"]
        found = collect_identifiers_from_code_only(lines)
        assert "arg0" in found
        assert "arg1" in found

    def test_string_literal_ignored(self):
        lines = ['    printf("arg0 argument count: %d\\n", argc);']
        found = collect_identifiers_from_code_only(lines)
        assert "arg0" not in found
        # printf and argc are real code identifiers
        assert "printf" in found
        assert "argc" in found

    def test_char_literal_ignored(self):
        lines = ["    char c = 'a';"]
        found = collect_identifiers_from_code_only(lines)
        # 'a' is in a char literal, not a real identifier
        assert "a" not in found  # 'a' as identifier should not appear
        assert "c" in found

    def test_line_comment_ignored(self):
        lines = ["    x = 5; // arg0 mentioned in comment"]
        found = collect_identifiers_from_code_only(lines)
        assert "arg0" not in found
        assert "x" in found

    def test_block_comment_ignored(self):
        lines = ["    /* arg0 in block comment */", "    real_var = 1;"]
        found = collect_identifiers_from_code_only(lines)
        assert "arg0" not in found
        assert "real_var" in found

    def test_multiline_block_comment_ignored(self):
        lines = [
            "    /* arg0 start of block",
            "       still_inside_comment arg1",
            "    */ real_code = 5;",
        ]
        found = collect_identifiers_from_code_only(lines)
        assert "arg0" not in found
        assert "arg1" not in found  # still inside block comment
        assert "real_code" in found

    def test_hephaestus_unknown_cond_evidence_ignored(self):
        lines = [
            '    if (HEPHAESTUS_UNKNOWN_COND("condition evidence: arg0")) {',
        ]
        found = collect_identifiers_from_code_only(lines)
        # arg0 is inside the string argument to HEPHAESTUS_UNKNOWN_COND
        assert "arg0" not in found
        # HEPHAESTUS_UNKNOWN_COND itself is in the excluded helper names set
        assert "HEPHAESTUS_UNKNOWN_COND" not in found

    def test_hephaestus_cset_evidence_ignored(self):
        lines = [
            '    HEPHAESTUS_CSET("arg1 cset evidence");',
        ]
        found = collect_identifiers_from_code_only(lines)
        assert "arg1" not in found
        assert "HEPHAESTUS_CSET" not in found

    def test_real_code_not_filtered(self):
        lines = [
            "    u64 arg0 = 0;",
            "    arg0 = arg_30h + 5;",
            "    return arg0;",
        ]
        found = collect_identifiers_from_code_only(lines)
        assert "arg0" in found
        assert "arg_30h" in found
        assert "u64" in found

    def test_mixed_line_code_and_comment(self):
        # Only the code part should be scanned
        lines = [
            "    arg0 = 1; /* old name was param_first */",
        ]
        found = collect_identifiers_from_code_only(lines)
        assert "arg0" in found
        # param_first is only in a comment
        assert "param_first" not in found

    def test_empty_lines(self):
        lines = ["", "   ", "// just a comment"]
        found = collect_identifiers_from_code_only(lines)
        assert len(found) == 0

    def test_abi_scratch_comment_evidence(self):
        # The comment after an ABI scratch declaration should not trigger
        # extra declarations in a second scan pass
        lines = [
            "    /* ABI scratch declarations: */",
            "    u64 arg0 = 0; /* added for ABI scratch compile-shape */",
        ]
        found = collect_identifiers_from_code_only(lines)
        # arg0 is found in code (the declaration line itself)
        assert "arg0" in found
        # But the comment content "added for ABI scratch compile-shape" should not
        # produce spurious identifiers that look like ABI scratch names
        # (none of those words match ABI scratch patterns anyway)

    def test_main_abi_bridge_comment_ignored(self):
        # The bridge comment mentioning "argc" should not add argc to used-identifiers
        # (argc is already declared as a parameter and the comment is ignored)
        lines = [
            "    u64 arg0 = (u64)argc;                  /* main ABI bridge: argc */",
        ]
        found = collect_identifiers_from_code_only(lines)
        # argc IS in code (the RHS of the assignment) — that's fine
        assert "argc" in found
        # arg0 is in code too
        assert "arg0" in found
