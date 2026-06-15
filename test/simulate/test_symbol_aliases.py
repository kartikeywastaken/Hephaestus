# -*- coding: utf-8 -*-
"""
Tests for symbol alias canonicalization (src/ir/symbols/aliases.py).
"""

import pytest

from src.ir.symbols.aliases import (
    FunctionAliasGroup,
    build_function_alias_groups,
    choose_canonical_function_name,
    apply_function_aliases_to_ir,
)


# ---------------------------------------------------------------------------
# choose_canonical_function_name
# ---------------------------------------------------------------------------

class TestChooseCanonicalFunctionName:
    """Tests for the canonical name selection logic."""

    def test_real_name_over_synthetic(self):
        """Non-synthetic names should beat FUN_/sub_ names."""
        names = ["FUN_100000460", "_main", "sub_100000460"]
        result = choose_canonical_function_name(names, "0x100000460")
        assert result == "_main"

    def test_library_known_name_preferred(self):
        """Known library names like printf should be preferred."""
        names = ["sym.imp.printf", "printf", "FUN_deadbeef"]
        result = choose_canonical_function_name(names, "0xdeadbeef")
        assert result == "printf"

    def test_empty_names_returns_unknown(self):
        """Empty name list should return 'unknown'."""
        assert choose_canonical_function_name([], "0x0") == "unknown"

    def test_all_empty_strings_returns_unknown(self):
        """All-empty strings should return 'unknown'."""
        assert choose_canonical_function_name(["", "  ", ""], "0x0") == "unknown"

    def test_single_name(self):
        """Single name should be returned as-is."""
        result = choose_canonical_function_name(["_start"], "0x1000")
        assert result == "_start"

    def test_stable_deterministic_ordering(self):
        """Given same-quality names, ordering should be deterministic."""
        names_a = ["foo", "bar", "baz"]
        names_b = ["baz", "bar", "foo"]
        assert (
            choose_canonical_function_name(names_a, "0x1")
            == choose_canonical_function_name(names_b, "0x1")
        )

    def test_sym_prefix_stripped(self):
        """sym.imp. prefix should be stripped, exposing the real name."""
        names = ["sym.imp.malloc", "FUN_2000"]
        result = choose_canonical_function_name(names, "0x2000")
        assert result in ("malloc", "sym.imp.malloc")

    def test_main_and_underscore_main(self):
        """_main and main should both be valid choices."""
        names = ["_main", "main"]
        result = choose_canonical_function_name(names, "0x1000")
        assert result in ("_main", "main")


# ---------------------------------------------------------------------------
# build_function_alias_groups
# ---------------------------------------------------------------------------

class TestBuildFunctionAliasGroups:
    """Tests for grouping functions by entry point."""

    def test_same_entry_grouped(self):
        """Two functions with the same entry point should be grouped."""
        functions = [
            {"name": "_main", "entry_point": "0x100000460", "source_tool": "ghidra"},
            {"name": "sym._main", "entry_point": "0x100000460", "source_tool": "radare2"},
        ]
        groups = build_function_alias_groups(functions)
        assert "0x100000460" in groups
        group = groups["0x100000460"]
        assert "_main" in group.aliases

    def test_different_entries_not_grouped(self):
        """Functions with different entry points should NOT be grouped."""
        functions = [
            {"name": "foo", "entry_point": "0x1000"},
            {"name": "foo", "entry_point": "0x2000"},
        ]
        groups = build_function_alias_groups(functions)
        assert "0x1000" in groups
        assert "0x2000" in groups
        assert groups["0x1000"].entry_point != groups["0x2000"].entry_point

    def test_canonical_name_is_real_symbol(self):
        """Canonical name should prefer real symbol over FUN_ synthetic."""
        functions = [
            {"name": "FUN_100000460", "entry_point": "0x100000460"},
            {"name": "_main", "entry_point": "0x100000460"},
        ]
        groups = build_function_alias_groups(functions)
        assert groups["0x100000460"].canonical_name == "_main"

    def test_no_functions_no_groups(self):
        """Empty function list should produce empty groups."""
        assert build_function_alias_groups([]) == {}

    def test_unknown_entry_skipped(self):
        """Functions with entry_point='unknown' should be skipped."""
        functions = [{"name": "foo", "entry_point": "unknown"}]
        assert build_function_alias_groups(functions) == {}

    def test_aliases_sorted_deterministically(self):
        """Aliases should be sorted for deterministic output."""
        functions = [
            {"name": "z_func", "entry_point": "0x1000"},
            {"name": "a_func", "entry_point": "0x1000"},
        ]
        groups = build_function_alias_groups(functions)
        aliases = list(groups["0x1000"].aliases)
        assert aliases == sorted(aliases)

    def test_to_dict_serialization(self):
        """FunctionAliasGroup should serialize cleanly to dict."""
        functions = [
            {"name": "_main", "entry_point": "0x100000460", "source_tool": "ghidra"},
        ]
        groups = build_function_alias_groups(functions)
        d = groups["0x100000460"].to_dict()
        assert d["entry_point"] == "0x100000460"
        assert isinstance(d["aliases"], list)
        assert isinstance(d["evidence_notes"], list)


# ---------------------------------------------------------------------------
# apply_function_aliases_to_ir
# ---------------------------------------------------------------------------

class TestApplyFunctionAliasesToIR:
    """Tests for injecting symbol_aliases into the Unified IR."""

    def test_applies_to_data_section(self):
        """Aliases should be placed under data.symbol_aliases."""
        ir = {
            "schema_version": "2.0.0",
            "data": {
                "functions": [
                    {"name": "_main", "entry_point": "0x100000460"},
                    {"name": "sym._main", "entry_point": "0x100000460"},
                ],
            },
        }
        result = apply_function_aliases_to_ir(ir)
        assert "symbol_aliases" in result["data"]
        assert isinstance(result["data"]["symbol_aliases"], list)
        assert len(result["data"]["symbol_aliases"]) > 0

    def test_does_not_remove_functions(self):
        """Existing function records should not be removed."""
        ir = {
            "data": {
                "functions": [
                    {"name": "foo", "entry_point": "0x1000"},
                ],
            },
        }
        result = apply_function_aliases_to_ir(ir)
        assert len(result["data"]["functions"]) == 1

    def test_empty_ir_safe(self):
        """Should not crash on empty or malformed IR."""
        result = apply_function_aliases_to_ir({})
        assert isinstance(result, dict)
        assert apply_function_aliases_to_ir(None) is None

    def test_no_data_section(self):
        """Should handle IR without a data section."""
        ir = {"functions": [{"name": "foo", "entry_point": "0x1000"}]}
        result = apply_function_aliases_to_ir(ir)
        assert "symbol_aliases" in result
