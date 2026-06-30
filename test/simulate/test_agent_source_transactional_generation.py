# -*- coding: utf-8 -*-
"""
Phase 11.8 — Test: Transactional validation-gated source generation.

Verifies that invalid AI output is rejected and falls back to
the original recovered_readable.c function.
"""

import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace


SAMPLE_READABLE_C = """\
#include <stdio.h>

int _helper(int x) {
    return x + 1;
}

int _main(int argc, char **argv) {
    return _helper(argc);
}
"""


def _make_arts(readable_c=SAMPLE_READABLE_C, conservative_c=None):
    """Create a mock Phase11Artifacts."""
    arts = SimpleNamespace()
    arts.recovered_readable_c = readable_c
    arts.recovered_c = conservative_c or readable_c
    arts.source_reconstruction = None
    arts.behavior_model = None
    arts.agent_suggestions = None
    return arts


class TestTransactionalGeneration(unittest.TestCase):
    """Verify transactional validation gate behavior."""

    def test_invalid_ai_function_falls_back(self):
        """If AI returns unbalanced braces, function should fall back."""
        from src.agent_source.generator import generate_source

        arts = _make_arts()
        plan = [{"kind": "rename_variable", "function": "_helper", "enabled": True,
                 "target": "x", "replacement": "val", "basis": ["test"],
                 "confidence": "medium", "evidence_level": "static_evidence"}]

        mock_provider = MagicMock()
        # Return invalid C with unbalanced braces
        mock_provider.complete_json.return_value = {
            "generated_c": "int _helper(int val) {\n    return val + 1;\n/* missing closing brace */",
            "applied_transformations": ["rename_variable"],
            "skipped_transformations": [],
            "uncertainties": [],
            "notes": [],
        }

        text, records, diag = generate_source(
            arts, plan, mock_provider,
            mode="function_by_function",
            max_functions=1,
        )

        # Should have fallen back — original function preserved
        self.assertIn("return x + 1", text)
        # Check the record
        helper_rec = [r for r in records if r["c_name"] == "_helper"]
        self.assertEqual(len(helper_rec), 1)
        self.assertEqual(helper_rec[0]["status"], "fallback")
        self.assertFalse(helper_rec[0]["generated"])

    def test_valid_ai_function_is_accepted(self):
        """If AI returns valid C, function should be accepted."""
        from src.agent_source.generator import generate_source

        arts = _make_arts()
        plan = [{"kind": "rename_variable", "function": "_helper", "enabled": True,
                 "target": "x", "replacement": "val", "basis": ["test"],
                 "confidence": "medium", "evidence_level": "static_evidence"}]

        mock_provider = MagicMock()
        mock_provider.complete_json.return_value = {
            "generated_c": "int _helper(int val) {\n    return val + 1;\n}",
            "applied_transformations": ["rename_variable"],
            "skipped_transformations": [],
            "uncertainties": ["AI-assisted approximation only"],
            "notes": [],
        }

        text, records, diag = generate_source(
            arts, plan, mock_provider,
            mode="function_by_function",
            max_functions=1,
        )

        # Should be accepted
        self.assertIn("return val + 1", text)
        helper_rec = [r for r in records if r["c_name"] == "_helper"]
        self.assertEqual(len(helper_rec), 1)
        self.assertEqual(helper_rec[0]["status"], "ok")
        self.assertTrue(helper_rec[0]["generated"])

    def test_forbidden_phrase_in_generated_rejects(self):
        """Generated function containing forbidden phrases should be rejected."""
        from src.agent_source.generator import generate_source

        arts = _make_arts()
        plan = [{"kind": "rename_variable", "function": "_helper", "enabled": True,
                 "target": "x", "replacement": "val", "basis": ["test"],
                 "confidence": "medium", "evidence_level": "static_evidence"}]

        mock_provider = MagicMock()
        mock_provider.complete_json.return_value = {
            "generated_c": (
                'int _helper(int val) {\n'
                '    /* This is semantically equivalent to the original */\n'
                '    return val + 1;\n'
                '}'
            ),
            "applied_transformations": [],
            "skipped_transformations": [],
            "uncertainties": [],
            "notes": [],
        }

        text, records, diag = generate_source(
            arts, plan, mock_provider,
            mode="function_by_function",
            max_functions=1,
        )

        # Should have fallen back
        helper_rec = [r for r in records if r["c_name"] == "_helper"]
        self.assertEqual(len(helper_rec), 1)
        self.assertIn(helper_rec[0]["status"], ("fallback", "failed"))
        self.assertFalse(helper_rec[0]["generated"])

    def test_fallback_produces_valid_file(self):
        """Even if all AI replacements fail, the result should be valid."""
        from src.agent_source.generator import generate_source

        arts = _make_arts()
        plan = [{"kind": "rename_variable", "function": "_helper", "enabled": True,
                 "target": "x", "replacement": "val", "basis": ["test"],
                 "confidence": "medium", "evidence_level": "static_evidence"}]

        mock_provider = MagicMock()
        mock_provider.complete_json.side_effect = RuntimeError("Provider unavailable")

        text, records, diag = generate_source(
            arts, plan, mock_provider,
            mode="function_by_function",
            max_functions=1,
        )

        # Should return a valid file (the original readable_c)
        self.assertIn("_helper", text)
        self.assertIn("_main", text)
        # File should have balanced braces
        from src.agent_source.generator import _validate_balanced_braces
        self.assertTrue(_validate_balanced_braces(text))

    def test_generated_count_reflects_only_accepted(self):
        """functions_generated should count only accepted AI replacements."""
        from src.agent_source.generator import generate_source

        arts = _make_arts()
        plan = [{"kind": "rename_variable", "function": "_helper", "enabled": True,
                 "target": "x", "replacement": "val", "basis": ["test"],
                 "confidence": "medium", "evidence_level": "static_evidence"}]

        mock_provider = MagicMock()
        mock_provider.complete_json.side_effect = RuntimeError("fail")

        text, records, diag = generate_source(
            arts, plan, mock_provider,
            mode="function_by_function",
            max_functions=1,
        )

        generated = sum(1 for r in records if r.get("generated"))
        fallback = sum(1 for r in records if r.get("status") == "fallback")
        self.assertEqual(generated, 0)
        self.assertGreaterEqual(fallback, 1)


if __name__ == "__main__":
    unittest.main()
