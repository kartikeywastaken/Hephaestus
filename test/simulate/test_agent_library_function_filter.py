# -*- coding: utf-8 -*-
"""
Tests for src/agent/library_filter.py
"""
import pytest

from src.agent.library_filter import (
    classify_function_role,
    is_skippable_for_debate,
    is_skippable_for_source,
    filter_debatable_packets,
    KNOWN_LIBRARY_FUNCTIONS,
)


def _pkt(name: str, **extra) -> dict:
    """Build a minimal packet dict."""
    return {"function": name, **extra}


class TestClassifyFunctionRole:
    def test_printf_is_external(self):
        assert classify_function_role(_pkt("printf")) == "external_library_function"

    def test_strlen_is_external(self):
        assert classify_function_role(_pkt("strlen")) == "external_library_function"

    def test_malloc_is_external(self):
        assert classify_function_role(_pkt("malloc")) == "external_library_function"

    def test_free_is_external(self):
        assert classify_function_role(_pkt("free")) == "external_library_function"

    def test_underscore_printf_is_external(self):
        """macOS symbols have a leading underscore."""
        assert classify_function_role(_pkt("_printf")) == "external_library_function"

    def test_underscore_strlen_is_external(self):
        assert classify_function_role(_pkt("_strlen")) == "external_library_function"

    def test_user_main_is_user_defined(self):
        assert classify_function_role(_pkt("_main")) == "user_defined_function"

    def test_user_score_packet_is_user_defined(self):
        assert classify_function_role(_pkt("_score_packet")) == "user_defined_function"

    def test_user_mix32_is_user_defined(self):
        assert classify_function_role(_pkt("_mix32")) == "user_defined_function"

    def test_plt_metadata_marks_external(self):
        pkt = _pkt("custom_name", metadata={"is_plt": True})
        assert classify_function_role(pkt) == "external_library_function"

    def test_import_metadata_marks_external(self):
        pkt = _pkt("custom_name", metadata={"is_import": True})
        assert classify_function_role(pkt) == "external_library_function"

    def test_plt_section_marks_external(self):
        pkt = _pkt("unknown_fn", metadata={"section": ".plt"})
        assert classify_function_role(pkt) == "external_library_function"

    def test_role_external_marks_external(self):
        pkt = _pkt("my_fn", role="external")
        assert classify_function_role(pkt) == "external_library_function"

    def test_unknown_function_is_user_defined(self):
        assert classify_function_role(_pkt("my_custom_function")) == "user_defined_function"

    def test_double_underscore_preserved(self):
        """__stack_chk_fail should be external; double underscore not stripped."""
        assert classify_function_role(_pkt("__stack_chk_fail")) == "external_library_function"


class TestIsSkippable:
    def test_printf_skippable_for_debate(self):
        assert is_skippable_for_debate(_pkt("printf")) is True

    def test_strlen_skippable_for_source(self):
        assert is_skippable_for_source(_pkt("strlen")) is True

    def test_user_function_not_skippable(self):
        assert is_skippable_for_debate(_pkt("_score_packet")) is False
        assert is_skippable_for_source(_pkt("_score_packet")) is False


class TestFilterDebatablePackets:
    def test_separates_library_from_user(self):
        packets = [_pkt("printf"), _pkt("_main"), _pkt("strlen"), _pkt("_score_packet")]
        debatable, skipped = filter_debatable_packets(packets)
        assert [p["function"] for p in debatable] == ["_main", "_score_packet"]
        assert [p["function"] for p in skipped] == ["printf", "strlen"]

    def test_max_functions_limits_debatable(self):
        packets = [_pkt("_main"), _pkt("_score_packet"), _pkt("_mix32")]
        debatable, skipped = filter_debatable_packets(packets, max_functions=1)
        assert len(debatable) == 1
        assert debatable[0]["function"] == "_main"
        assert len(skipped) == 0

    def test_skipped_do_not_count_toward_max(self):
        """Library functions do not consume max_functions slots."""
        packets = [
            _pkt("printf"),
            _pkt("strlen"),
            _pkt("_main"),
            _pkt("_score_packet"),
            _pkt("_mix32"),
        ]
        debatable, skipped = filter_debatable_packets(packets, max_functions=2)
        assert len(debatable) == 2
        assert [p["function"] for p in debatable] == ["_main", "_score_packet"]
        assert len(skipped) == 2  # printf, strlen

    def test_all_library_returns_empty_debatable(self):
        packets = [_pkt("printf"), _pkt("malloc"), _pkt("free")]
        debatable, skipped = filter_debatable_packets(packets)
        assert len(debatable) == 0
        assert len(skipped) == 3

    def test_skipped_functions_reported_in_optimization_report(self):
        """Skipped list should contain enough info for reporting."""
        packets = [_pkt("printf"), _pkt("_main")]
        _, skipped = filter_debatable_packets(packets)
        assert len(skipped) == 1
        assert skipped[0]["function"] == "printf"
