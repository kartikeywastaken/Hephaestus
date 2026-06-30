# -*- coding: utf-8 -*-
"""
Phase 11.8 — Test: Source generation target selection.

Verifies that:
  - Functions with debate suggestions are generated first
  - Metadata-only suggestions do not trigger LLM calls
  - --max-functions 1 picks the debate-suggested function, not file order
"""

import unittest
from unittest.mock import MagicMock
from types import SimpleNamespace


SAMPLE_READABLE_C = """\
#include <stdio.h>

int _main(int argc, char **argv) {
    return _checksum(argc);
}

int _checksum(int val) {
    return val ^ 0xFF;
}
"""


def _make_arts(readable_c=SAMPLE_READABLE_C):
    arts = SimpleNamespace()
    arts.recovered_readable_c = readable_c
    arts.recovered_c = readable_c
    arts.source_reconstruction = None
    arts.behavior_model = None
    arts.agent_suggestions = None
    return arts


class TestTargetSelection(unittest.TestCase):
    """Verify source generation target ordering."""

    def test_debate_suggested_function_generated_first(self):
        """With --max-functions 1 and debate suggesting _checksum,
        _checksum should be generated, not _main."""
        from src.agent_source.generator import generate_source

        arts = _make_arts()
        plan = [
            {
                "kind": "rename_variable", "function": "_checksum", "enabled": True,
                "target": "val", "replacement": "input_val", "basis": ["debate"],
                "confidence": "medium", "evidence_level": "static_evidence",
            },
        ]

        mock_provider = MagicMock()
        mock_provider.complete_json.return_value = {
            "generated_c": "int _checksum(int input_val) {\n    return input_val ^ 0xFF;\n}",
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

        # _checksum should be the one generated
        checksum_rec = [r for r in records if r["c_name"] == "_checksum"]
        self.assertEqual(len(checksum_rec), 1)
        self.assertTrue(checksum_rec[0]["generated"])

        # _main should NOT be generated (copied unchanged)
        main_rec = [r for r in records if r["c_name"] == "_main"]
        self.assertEqual(len(main_rec), 1)
        self.assertFalse(main_rec[0]["generated"])
        self.assertIn(main_rec[0]["status"], ("copied_unchanged",))

    def test_metadata_only_suggestion_does_not_trigger_generation(self):
        """A 'name' suggestion should not trigger LLM call."""
        from src.agent_source.generator import generate_source

        arts = _make_arts()
        # The 'name' kind maps to metadata-only
        plan = [
            {
                "kind": "name", "function": "_checksum", "enabled": True,
                "target": "_checksum", "replacement": "checksum",
                "basis": ["debate"], "confidence": "medium",
                "evidence_level": "static_evidence",
            },
        ]

        mock_provider = MagicMock()

        text, records, diag = generate_source(
            arts, plan, mock_provider,
            mode="function_by_function",
            max_functions=1,
        )

        # Provider should NOT have been called
        mock_provider.complete_json.assert_not_called()

        # Record for _checksum should show metadata_only_skipped
        checksum_rec = [r for r in records if r["c_name"] == "_checksum"]
        self.assertEqual(len(checksum_rec), 1)
        self.assertEqual(checksum_rec[0]["status"], "metadata_only_skipped")
        self.assertFalse(checksum_rec[0]["generated"])

    def test_no_unrelated_function_generated(self):
        """If only _checksum has suggestions (all disabled), no function should
        be generated."""
        from src.agent_source.generator import generate_source

        arts = _make_arts()
        plan = [
            {
                "kind": "rename_variable", "function": "_checksum", "enabled": False,
                "target": "val", "replacement": "v",
                "basis": ["test"], "confidence": "low",
                "evidence_level": "static_evidence",
                "reason_disabled": "disabled for test",
            },
        ]

        mock_provider = MagicMock()

        text, records, diag = generate_source(
            arts, plan, mock_provider,
            mode="function_by_function",
            max_functions=1,
        )

        # Neither function should have been generated via LLM
        # (no enabled source-transform suggestions exist, so all stay as copied_unchanged)
        for r in records:
            self.assertFalse(r.get("generated", False))
        mock_provider.complete_json.assert_not_called()


class TestMetadataOnlyClassification(unittest.TestCase):
    """Verify kind classification in plan_builder."""

    def test_source_transform_kinds(self):
        from src.agent_source.plan_builder import SOURCE_TRANSFORM_KINDS
        self.assertIn("rename_variable", SOURCE_TRANSFORM_KINDS)
        self.assertIn("rename_function", SOURCE_TRANSFORM_KINDS)
        self.assertIn("add_function_comment", SOURCE_TRANSFORM_KINDS)

    def test_metadata_only_kinds(self):
        from src.agent_source.plan_builder import METADATA_ONLY_KINDS
        self.assertIn("name", METADATA_ONLY_KINDS)
        self.assertIn("comment", METADATA_ONLY_KINDS)
        self.assertIn("role", METADATA_ONLY_KINDS)
        self.assertIn("hypothesis", METADATA_ONLY_KINDS)

    def test_has_source_transforms_true(self):
        from src.agent_source.plan_builder import has_source_transforms
        plan = [{"kind": "rename_variable", "function": "foo", "enabled": True}]
        self.assertTrue(has_source_transforms(plan, "foo"))

    def test_has_source_transforms_false_for_metadata_only(self):
        from src.agent_source.plan_builder import has_source_transforms
        plan = [{"kind": "name", "function": "foo", "enabled": True}]
        self.assertFalse(has_source_transforms(plan, "foo"))

    def test_has_source_transforms_false_when_disabled(self):
        from src.agent_source.plan_builder import has_source_transforms
        plan = [{"kind": "rename_variable", "function": "foo", "enabled": False}]
        self.assertFalse(has_source_transforms(plan, "foo"))


if __name__ == "__main__":
    unittest.main()
