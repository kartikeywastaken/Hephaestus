# -*- coding: utf-8 -*-
"""
Phase 11.8 — Test: Source assembler preserves file structure exactly.

Tests the FunctionSpan parser and replace_function_body_preserving_file.
"""

import unittest

from src.agent_source.source_assembler import (
    FunctionSpan,
    find_top_level_functions,
    replace_function_body_preserving_file,
)


SAMPLE_C = """\
/*
 * Hephaestus recovered_readable.c
 * No semantic equivalence is claimed.
 */

#include <stdio.h>
#include <stdlib.h>

#define HEPHAESTUS_UNKNOWN_COND(x) (1)

typedef struct {
    int x;
    int y;
} Point;

int _helper(int x) {
    return x + 1;
}

int _main(int argc, char **argv) {
    int result = _helper(argc);
    if (HEPHAESTUS_UNKNOWN_COND("cmp_site_0x1234")) {
        printf("hello\\n");
    }
    return result;
}

void _cleanup(void) {
    /* nothing to do */
}
"""


class TestFindTopLevelFunctions(unittest.TestCase):
    """Test the brace-tracking function parser."""

    def test_finds_all_functions(self):
        spans = find_top_level_functions(SAMPLE_C)
        names = [s.name for s in spans]
        self.assertIn("_helper", names)
        self.assertIn("_main", names)
        self.assertIn("_cleanup", names)
        self.assertEqual(len(spans), 3)

    def test_span_ordering(self):
        spans = find_top_level_functions(SAMPLE_C)
        self.assertEqual(spans[0].name, "_helper")
        self.assertEqual(spans[1].name, "_main")
        self.assertEqual(spans[2].name, "_cleanup")

    def test_spans_cover_full_function(self):
        spans = find_top_level_functions(SAMPLE_C)
        for span in spans:
            self.assertIn(span.name, span.body)
            self.assertTrue(span.body.rstrip().endswith("}"))

    def test_handles_comments_with_braces(self):
        source = """\
/* { not a function { } } */
int foo(void) {
    /* inner { brace } */
    return 0;
}
"""
        spans = find_top_level_functions(source)
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].name, "foo")

    def test_handles_strings_with_braces(self):
        source = """\
int bar(void) {
    printf("{ not a brace }");
    return 0;
}
"""
        spans = find_top_level_functions(source)
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].name, "bar")

    def test_handles_char_literals_with_braces(self):
        source = """\
int baz(void) {
    char c = '{';
    char d = '}';
    return 0;
}
"""
        spans = find_top_level_functions(source)
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].name, "baz")

    def test_unbalanced_braces_skipped(self):
        source = """\
int broken(void) {
    if (1) {
    /* missing closing brace */
"""
        spans = find_top_level_functions(source)
        # Should not include the broken function
        self.assertEqual(len(spans), 0)

    def test_empty_source(self):
        spans = find_top_level_functions("")
        self.assertEqual(len(spans), 0)


class TestReplaceFunctionBody(unittest.TestCase):
    """Test safe function replacement."""

    def test_replaces_target_preserves_others(self):
        replacement = """\
int _helper(int x) {
    /* improved by AI */
    return x + 42;
}"""
        new_text, replaced, diag = replace_function_body_preserving_file(
            SAMPLE_C, "_helper", replacement
        )
        self.assertTrue(replaced)
        # Target replaced
        self.assertIn("return x + 42", new_text)
        self.assertIn("improved by AI", new_text)
        # Others preserved exactly
        self.assertIn("_main", new_text)
        self.assertIn("_cleanup", new_text)
        self.assertIn("HEPHAESTUS_UNKNOWN_COND", new_text)

    def test_preserves_prelude_exactly(self):
        replacement = """\
int _helper(int x) {
    return x + 99;
}"""
        new_text, replaced, _ = replace_function_body_preserving_file(
            SAMPLE_C, "_helper", replacement
        )
        self.assertTrue(replaced)
        # Prelude should be preserved
        self.assertIn("#include <stdio.h>", new_text)
        self.assertIn("#include <stdlib.h>", new_text)
        self.assertIn("#define HEPHAESTUS_UNKNOWN_COND", new_text)
        self.assertIn("typedef struct", new_text)
        self.assertIn("No semantic equivalence is claimed.", new_text)

    def test_preserves_non_target_functions(self):
        replacement = """\
int _main(int argc, char **argv) {
    return 0;
}"""
        new_text, replaced, _ = replace_function_body_preserving_file(
            SAMPLE_C, "_main", replacement
        )
        self.assertTrue(replaced)
        # _helper and _cleanup must still be present
        self.assertIn("int _helper(int x)", new_text)
        self.assertIn("return x + 1", new_text)
        self.assertIn("void _cleanup(void)", new_text)

    def test_function_not_found_returns_original(self):
        new_text, replaced, diag = replace_function_body_preserving_file(
            SAMPLE_C, "nonexistent_function", "void nonexistent_function(void) {}"
        )
        self.assertFalse(replaced)
        self.assertEqual(new_text, SAMPLE_C)
        self.assertTrue(any("not found" in d for d in diag))

    def test_rejects_unbalanced_replacement(self):
        replacement = """\
int _helper(int x) {
    if (x) {
    /* missing closing brace */
"""
        new_text, replaced, diag = replace_function_body_preserving_file(
            SAMPLE_C, "_helper", replacement
        )
        self.assertFalse(replaced)
        self.assertEqual(new_text, SAMPLE_C)
        self.assertTrue(any("unbalanced" in d for d in diag))

    def test_multiple_replacements_sequential(self):
        """Multiple sequential replacements should work."""
        r1 = "int _helper(int x) {\n    return x + 10;\n}"
        text1, ok1, _ = replace_function_body_preserving_file(SAMPLE_C, "_helper", r1)
        self.assertTrue(ok1)

        r2 = "void _cleanup(void) {\n    /* cleaned */\n}"
        text2, ok2, _ = replace_function_body_preserving_file(text1, "_cleanup", r2)
        self.assertTrue(ok2)

        self.assertIn("return x + 10", text2)
        self.assertIn("/* cleaned */", text2)
        self.assertIn("_main", text2)


if __name__ == "__main__":
    unittest.main()
