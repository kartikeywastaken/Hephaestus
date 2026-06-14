# -*- coding: utf-8 -*-
"""
Phase 4C: Conservative Data Layout Recovery — Test Suite

Tests cover:
  1. MemoryAccessFact / LayoutCandidate model serialization
  2. collect_memory_access_facts — happy path, edge cases, adversarial inputs
  3. _classify_access_kind — all classification branches
  4. build_layout_candidates — grouping, unbound separation, determinism
  5. LayoutRecoveryEngine.recover — end-to-end
  6. layout_emitter — artifact schema validation
  7. Adversarial / regression invariants
"""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from typing import Any, Dict, List

import pytest

from src.ir.types.layouts import (
    ACCESS_LOAD,
    ACCESS_STORE,
    LAYOUT_ARRAY_LIKE,
    LAYOUT_POINTER_LIKE,
    LAYOUT_RECORD_LIKE,
    LAYOUT_SCALAR,
    LAYOUT_UNKNOWN,
    LayoutCandidate,
    MemoryAccessFact,
)
from src.ir.types.layout_recovery import (
    LayoutRecoveryEngine,
    _classify_access_kind,
    build_layout_candidates,
    collect_memory_access_facts,
)
from src.ir.types.layout_emitter import write_layout_recovery_artifact


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_func(
    name: str = "test_fn",
    entry: str = "0x1000",
    blocks: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "name": name,
        "entry_point": entry,
        "basic_blocks": blocks or [],
    }


def _make_block(
    block_id: str = "bb0",
    instructions: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "id": block_id,
        "instructions": instructions or [],
    }


def _make_instr(
    opcode: str,
    address: str,
    operands: List[Dict[str, Any]] = None,
    size_bytes: int = None,
) -> Dict[str, Any]:
    instr: Dict[str, Any] = {
        "opcode": opcode,
        "address": address,
        "operands": operands or [],
    }
    if size_bytes is not None:
        instr["size_bytes"] = size_bytes
    return instr


def _make_mem_op(base: str, offset: int = 0, size_bytes: int = None) -> Dict[str, Any]:
    op: Dict[str, Any] = {"kind": "memory", "base": base, "offset": offset}
    if size_bytes is not None:
        op["size_bytes"] = size_bytes
    return op


def _make_unified_ir(functions: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"data": {"functions": functions}}


# ---------------------------------------------------------------------------
# 1. Model serialization
# ---------------------------------------------------------------------------

class TestMemoryAccessFactSerialization:
    def test_to_dict_round_trip(self):
        fact = MemoryAccessFact(
            function_entry="0x1000",
            function_name="my_func",
            block_id="bb0",
            instr_address="0x1008",
            base_id="sp",
            offset=-16,
            size_bytes=8,
            access_kind=ACCESS_LOAD,
        )
        d = fact.to_dict()
        assert d["function_entry"] == "0x1000"
        assert d["function_name"] == "my_func"
        assert d["base_id"] == "sp"
        assert d["offset"] == -16
        assert d["size_bytes"] == 8
        assert d["access_kind"] == ACCESS_LOAD

    def test_none_fields_serialized(self):
        fact = MemoryAccessFact(
            function_entry="0x1000",
            function_name="fn",
            block_id="bb0",
            instr_address="0x1000",
            base_id="x9",
            offset=None,
            size_bytes=None,
            access_kind=ACCESS_STORE,
        )
        d = fact.to_dict()
        assert d["offset"] is None
        assert d["size_bytes"] is None


class TestLayoutCandidateSerialization:
    def test_to_dict_contains_required_keys(self):
        c = LayoutCandidate(
            function_entry="0x2000",
            function_name="foo",
            base_id="sp",
            layout_kind=LAYOUT_SCALAR,
            observed_offsets=[0],
            min_offset=0,
            max_offset=0,
            observed_sizes=[8],
            access_count=1,
            evidence_notes=["test"],
            source_instrs=["0x2004"],
        )
        d = c.to_dict()
        required = {
            "function_entry", "function_name", "base_id", "layout_kind",
            "observed_offsets", "min_offset", "max_offset", "observed_sizes",
            "access_count", "evidence_notes", "source_instrs",
        }
        assert required.issubset(d.keys())

    def test_no_forbidden_keys(self):
        c = LayoutCandidate(
            function_entry="0x2000",
            function_name="foo",
            base_id="sp",
            layout_kind=LAYOUT_SCALAR,
        )
        d = c.to_dict()
        forbidden = {"structs", "fields", "c_source", "expressions",
                     "statements", "confidence", "similarity"}
        assert not forbidden.intersection(d.keys())


# ---------------------------------------------------------------------------
# 2. collect_memory_access_facts
# ---------------------------------------------------------------------------

class TestCollectMemoryAccessFacts:
    def test_single_load(self):
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    _make_instr("ldr", "0x1000",
                                [{"kind": "register", "value": "x8"},
                                 _make_mem_op("sp", -16, 8)],
                                size_bytes=8),
                ])
            ])
        ])
        facts = collect_memory_access_facts(ir)
        assert len(facts) == 1
        f = facts[0]
        assert f.base_id == "sp"
        assert f.offset == -16
        assert f.size_bytes == 8
        assert f.access_kind == ACCESS_LOAD
        assert f.function_name == "fn"

    def test_single_store(self):
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    _make_instr("str", "0x1004",
                                [{"kind": "register", "value": "x8"},
                                 _make_mem_op("sp", 0, 4)],
                                size_bytes=4),
                ])
            ])
        ])
        facts = collect_memory_access_facts(ir)
        assert len(facts) == 1
        assert facts[0].access_kind == ACCESS_STORE
        assert facts[0].offset == 0

    def test_non_memory_instructions_ignored(self):
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    _make_instr("add", "0x1000",
                                [{"kind": "register", "value": "x0"},
                                 {"kind": "register", "value": "x1"}]),
                    _make_instr("mov", "0x1004",
                                [{"kind": "register", "value": "x0"},
                                 {"kind": "immediate", "value": 42}]),
                ])
            ])
        ])
        facts = collect_memory_access_facts(ir)
        assert facts == []

    def test_memory_operand_without_base_ignored(self):
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    _make_instr("ldr", "0x1000",
                                [{"kind": "register", "value": "x8"},
                                 {"kind": "memory", "offset": 0}],  # no base
                                8),
                ])
            ])
        ])
        facts = collect_memory_access_facts(ir)
        assert facts == []

    def test_empty_ir_returns_empty(self):
        assert collect_memory_access_facts({}) == []
        assert collect_memory_access_facts({"data": {}}) == []
        assert collect_memory_access_facts({"data": {"functions": []}}) == []

    def test_non_dict_ir_returns_empty(self):
        assert collect_memory_access_facts(None) == []
        assert collect_memory_access_facts([]) == []
        assert collect_memory_access_facts("bad") == []

    def test_multiple_functions_collected(self):
        ir = _make_unified_ir([
            _make_func("fn_a", "0x1000", [
                _make_block("bb0", [
                    _make_instr("ldr", "0x1000",
                                [{"kind": "register", "value": "x0"},
                                 _make_mem_op("sp", -8, 8)], 8),
                ])
            ]),
            _make_func("fn_b", "0x2000", [
                _make_block("bb0", [
                    _make_instr("str", "0x2000",
                                [{"kind": "register", "value": "x1"},
                                 _make_mem_op("sp", -4, 4)], 4),
                ])
            ]),
        ])
        facts = collect_memory_access_facts(ir)
        assert len(facts) == 2
        names = {f.function_name for f in facts}
        assert names == {"fn_a", "fn_b"}

    def test_facts_sorted_deterministically(self):
        """Same IR loaded twice must produce identical fact order."""
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    _make_instr("ldr", "0x100c",
                                [{"kind": "register", "value": "x8"},
                                 _make_mem_op("sp", -24, 8)], 8),
                    _make_instr("str", "0x1000",
                                [{"kind": "register", "value": "x9"},
                                 _make_mem_op("sp", -16, 4)], 4),
                    _make_instr("ldr", "0x1008",
                                [{"kind": "register", "value": "x10"},
                                 _make_mem_op("sp", -8, 8)], 8),
                ])
            ])
        ])
        f1 = collect_memory_access_facts(ir)
        f2 = collect_memory_access_facts(deepcopy(ir))
        assert [f.to_dict() for f in f1] == [f.to_dict() for f in f2]

    def test_register_normalization(self):
        """w8 base should be normalized to x8."""
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    _make_instr("ldr", "0x1000",
                                [{"kind": "register", "value": "x0"},
                                 {"kind": "memory", "base": "w8", "offset": 0}], 4),
                ])
            ])
        ])
        facts = collect_memory_access_facts(ir)
        assert len(facts) == 1
        assert facts[0].base_id == "x8"

    def test_fp_normalized_to_x29(self):
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    _make_instr("str", "0x1004",
                                [{"kind": "register", "value": "x1"},
                                 {"kind": "memory", "base": "fp", "offset": 8}], 8),
                ])
            ])
        ])
        facts = collect_memory_access_facts(ir)
        assert facts[0].base_id == "x29"

    def test_mnemonic_field_used_as_fallback(self):
        """Instruction using 'mnemonic' instead of 'opcode' should still work."""
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    {
                        "mnemonic": "ldr",
                        "address": "0x1000",
                        "size_bytes": 8,
                        "operands": [
                            {"kind": "register", "value": "x8"},
                            _make_mem_op("sp", -8, 8),
                        ],
                    }
                ])
            ])
        ])
        facts = collect_memory_access_facts(ir)
        assert len(facts) == 1

    def test_no_opcode_instruction_skipped(self):
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    {"address": "0x1000", "operands": [_make_mem_op("sp", 0, 8)]}
                ])
            ])
        ])
        facts = collect_memory_access_facts(ir)
        assert facts == []

    def test_malformed_operand_skipped(self):
        """Non-dict operands must not crash."""
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    _make_instr("ldr", "0x1000",
                                [None, "bad_operand", 42, _make_mem_op("sp", 0, 4)],
                                4),
                ])
            ])
        ])
        facts = collect_memory_access_facts(ir)
        assert len(facts) == 1

    def test_offset_none_when_missing(self):
        """Operands with no offset field produce offset=None."""
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    _make_instr("ldr", "0x1000",
                                [{"kind": "register", "value": "x0"},
                                 {"kind": "memory", "base": "sp"}],  # no offset key
                                8),
                ])
            ])
        ])
        facts = collect_memory_access_facts(ir)
        assert len(facts) == 1
        assert facts[0].offset is None

    def test_non_numeric_offset_becomes_none(self):
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    _make_instr("ldr", "0x1000",
                                [{"kind": "register", "value": "x0"},
                                 {"kind": "memory", "base": "sp", "offset": "bad"}],
                                8),
                ])
            ])
        ])
        facts = collect_memory_access_facts(ir)
        assert len(facts) == 1
        assert facts[0].offset is None


# ---------------------------------------------------------------------------
# 3. _classify_access_kind
# ---------------------------------------------------------------------------

class TestClassifyAccessKind:
    def test_empty_offsets_is_unknown(self):
        assert _classify_access_kind([], []) == LAYOUT_UNKNOWN

    def test_single_offset_single_size_scalar(self):
        assert _classify_access_kind([0], [4]) == LAYOUT_SCALAR

    def test_single_offset_pointer_width_8(self):
        assert _classify_access_kind([0], [8]) == LAYOUT_POINTER_LIKE

    def test_single_offset_pointer_width_4(self):
        assert _classify_access_kind([0], [4]) == LAYOUT_SCALAR  # 4 bytes is also scalar

    def test_pointer_like_requires_single_offset(self):
        # Two offsets with size=8 → array_like (regular stride)
        assert _classify_access_kind([0, 8], [8]) == LAYOUT_ARRAY_LIKE

    def test_single_offset_no_size_is_scalar(self):
        assert _classify_access_kind([0], []) == LAYOUT_SCALAR

    def test_single_offset_multiple_sizes_is_unknown(self):
        assert _classify_access_kind([0], [4, 8]) == LAYOUT_UNKNOWN

    def test_regular_stride_single_size_array_like(self):
        # stride = 4 consistently
        assert _classify_access_kind([0, 4, 8, 12], [4]) == LAYOUT_ARRAY_LIKE

    def test_irregular_stride_record_like(self):
        assert _classify_access_kind([0, 4, 12], [4]) == LAYOUT_RECORD_LIKE

    def test_multiple_sizes_record_like(self):
        assert _classify_access_kind([0, 8], [4, 8]) == LAYOUT_RECORD_LIKE

    def test_two_offsets_same_stride(self):
        assert _classify_access_kind([0, 8], [8]) == LAYOUT_ARRAY_LIKE

    def test_stride_zero_excluded(self):
        # duplicate offsets would be deduplicated before classification
        # but if stride == 0 somehow: record_like or unknown
        # sorted distinct: [0] → scalar (single offset case)
        assert _classify_access_kind([0], [8]) == LAYOUT_POINTER_LIKE


# ---------------------------------------------------------------------------
# 4. build_layout_candidates
# ---------------------------------------------------------------------------

class TestBuildLayoutCandidates:
    def _make_fact(self, fn_entry, base_id, offset, size=None, fn_name="fn",
                   access=ACCESS_LOAD):
        return MemoryAccessFact(
            function_entry=fn_entry,
            function_name=fn_name,
            block_id="bb0",
            instr_address=f"0x{abs(offset or 0):x}",
            base_id=base_id,
            offset=offset,
            size_bytes=size,
            access_kind=access,
        )

    def test_empty_facts(self):
        candidates, unbound = build_layout_candidates([])
        assert candidates == []
        assert unbound == []

    def test_single_fact_scalar(self):
        facts = [self._make_fact("0x1000", "sp", -16, 8)]
        candidates, unbound = build_layout_candidates(facts)
        assert len(candidates) == 1
        c = candidates[0]
        assert c.layout_kind == LAYOUT_POINTER_LIKE  # size=8 single offset
        assert c.base_id == "sp"
        assert unbound == []

    def test_unbound_fact_separated(self):
        facts = [
            self._make_fact("0x1000", "sp", -16, 8),
            self._make_fact("0x1000", "sp", None, 8),  # unbound
        ]
        candidates, unbound = build_layout_candidates(facts)
        assert len(candidates) == 1
        assert len(unbound) == 1
        assert unbound[0].offset is None

    def test_array_like_grouped_correctly(self):
        facts = [
            self._make_fact("0x1000", "x19", 0, 4),
            self._make_fact("0x1000", "x19", 4, 4),
            self._make_fact("0x1000", "x19", 8, 4),
        ]
        candidates, unbound = build_layout_candidates(facts)
        assert len(candidates) == 1
        c = candidates[0]
        assert c.layout_kind == LAYOUT_ARRAY_LIKE
        assert c.observed_offsets == [0, 4, 8]
        assert c.access_count == 3

    def test_record_like_irregular_offsets(self):
        facts = [
            self._make_fact("0x1000", "x19", 0, 4),
            self._make_fact("0x1000", "x19", 4, 4),
            self._make_fact("0x1000", "x19", 12, 8),
        ]
        candidates, _ = build_layout_candidates(facts)
        assert candidates[0].layout_kind == LAYOUT_RECORD_LIKE

    def test_different_functions_produce_separate_candidates(self):
        facts = [
            self._make_fact("0x1000", "sp", -8, 8, fn_name="fn_a"),
            self._make_fact("0x2000", "sp", -8, 8, fn_name="fn_b"),
        ]
        candidates, _ = build_layout_candidates(facts)
        assert len(candidates) == 2
        entries = {c.function_entry for c in candidates}
        assert entries == {"0x1000", "0x2000"}

    def test_min_max_offset(self):
        facts = [
            self._make_fact("0x1000", "sp", -32, 8),
            self._make_fact("0x1000", "sp", -16, 8),
            self._make_fact("0x1000", "sp", -8, 8),
        ]
        candidates, _ = build_layout_candidates(facts)
        c = candidates[0]
        assert c.min_offset == -32
        assert c.max_offset == -8

    def test_candidates_sorted_deterministically(self):
        facts = [
            self._make_fact("0x2000", "x1", 0, 4, fn_name="b"),
            self._make_fact("0x1000", "x0", 0, 4, fn_name="a"),
        ]
        c1, _ = build_layout_candidates(facts)
        c2, _ = build_layout_candidates(list(reversed(facts)))
        assert [c.to_dict() for c in c1] == [c.to_dict() for c in c2]

    def test_evidence_notes_non_empty(self):
        facts = [self._make_fact("0x1000", "sp", 0, 4)]
        candidates, _ = build_layout_candidates(facts)
        assert candidates[0].evidence_notes
        assert candidates[0].evidence_notes[0]  # non-empty string


# ---------------------------------------------------------------------------
# 5. LayoutRecoveryEngine end-to-end
# ---------------------------------------------------------------------------

class TestLayoutRecoveryEngine:
    def test_recover_empty_ir(self):
        engine = LayoutRecoveryEngine()
        candidates, unbound = engine.recover({})
        assert candidates == []
        assert unbound == []

    def test_recover_basic_scenario(self):
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    _make_instr("ldr", "0x1000",
                                [{"kind": "register", "value": "x8"},
                                 _make_mem_op("sp", -16, 8)], 8),
                    _make_instr("str", "0x1004",
                                [{"kind": "register", "value": "x9"},
                                 _make_mem_op("sp", -8, 4)], 4),
                ])
            ])
        ])
        engine = LayoutRecoveryEngine()
        candidates, unbound = engine.recover(ir)
        assert len(candidates) == 1
        assert candidates[0].base_id == "sp"
        assert len(candidates[0].observed_offsets) == 2
        assert unbound == []

    def test_recover_with_unbound(self):
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    _make_instr("ldr", "0x1000",
                                [{"kind": "register", "value": "x8"},
                                 {"kind": "memory", "base": "sp"}],  # no offset
                                8),
                ])
            ])
        ])
        engine = LayoutRecoveryEngine()
        candidates, unbound = engine.recover(ir)
        assert candidates == []
        assert len(unbound) == 1

    def test_recover_is_deterministic(self):
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    _make_instr("ldr", "0x1004",
                                [{"kind": "register", "value": "x8"},
                                 _make_mem_op("sp", -16, 8)], 8),
                    _make_instr("str", "0x1000",
                                [{"kind": "register", "value": "x9"},
                                 _make_mem_op("sp", -8, 4)], 4),
                ])
            ])
        ])
        engine = LayoutRecoveryEngine()
        c1, u1 = engine.recover(ir)
        c2, u2 = engine.recover(deepcopy(ir))
        assert [c.to_dict() for c in c1] == [c.to_dict() for c in c2]
        assert [f.to_dict() for f in u1] == [f.to_dict() for f in u2]

    def test_recover_non_load_store_opcodes_ignored(self):
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    _make_instr("add", "0x1000",
                                [{"kind": "memory", "base": "sp", "offset": 0}]),
                    _make_instr("cmp", "0x1004",
                                [{"kind": "memory", "base": "sp", "offset": 4}]),
                ])
            ])
        ])
        engine = LayoutRecoveryEngine()
        candidates, unbound = engine.recover(ir)
        assert candidates == []
        assert unbound == []


# ---------------------------------------------------------------------------
# 6. Emitter — schema validation
# ---------------------------------------------------------------------------

class TestLayoutEmitter:
    def _run_emitter(self, candidates, unbound):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "layout_recovery.json")
            write_layout_recovery_artifact(candidates, unbound, out_path)
            with open(out_path, "r", encoding="utf-8") as fh:
                return json.load(fh)

    def _make_candidate(self) -> LayoutCandidate:
        return LayoutCandidate(
            function_entry="0x1000",
            function_name="fn",
            base_id="sp",
            layout_kind=LAYOUT_SCALAR,
            observed_offsets=[-16],
            min_offset=-16,
            max_offset=-16,
            observed_sizes=[8],
            access_count=1,
            evidence_notes=["test note"],
            source_instrs=["0x1000"],
        )

    def test_schema_version(self):
        payload = self._run_emitter([self._make_candidate()], [])
        assert payload["schema_version"] == "4C.0.0"

    def test_provenance_phase(self):
        payload = self._run_emitter([], [])
        assert payload["provenance"]["phase"] == "4C"

    def test_data_keys_present(self):
        payload = self._run_emitter([self._make_candidate()], [])
        assert "layout_candidates" in payload["data"]
        assert "unbound_memory_accesses" in payload["data"]

    def test_candidate_serialized(self):
        c = self._make_candidate()
        payload = self._run_emitter([c], [])
        candidates = payload["data"]["layout_candidates"]
        assert len(candidates) == 1
        assert candidates[0]["layout_kind"] == LAYOUT_SCALAR

    def test_no_forbidden_keys_in_output(self):
        c = self._make_candidate()
        payload = self._run_emitter([c], [])
        forbidden = {"structs", "fields", "c_source", "expressions",
                     "statements", "confidence", "similarity", "source_code"}
        # Check top-level
        assert not forbidden.intersection(payload.keys())
        # Check data level
        assert not forbidden.intersection(payload["data"].keys())
        # Check individual candidate
        candidate_keys = set(payload["data"]["layout_candidates"][0].keys())
        assert not forbidden.intersection(candidate_keys)

    def test_empty_candidates_emitted(self):
        payload = self._run_emitter([], [])
        assert payload["data"]["layout_candidates"] == []
        assert payload["data"]["unbound_memory_accesses"] == []

    def test_unbound_facts_emitted(self):
        fact = MemoryAccessFact(
            function_entry="0x1000",
            function_name="fn",
            block_id="bb0",
            instr_address="0x1000",
            base_id="sp",
            offset=None,
            size_bytes=8,
            access_kind=ACCESS_LOAD,
        )
        payload = self._run_emitter([], [fact])
        unbound = payload["data"]["unbound_memory_accesses"]
        assert len(unbound) == 1
        assert unbound[0]["offset"] is None


# ---------------------------------------------------------------------------
# 7. Adversarial / regression invariants
# ---------------------------------------------------------------------------

class TestAdversarialLayoutRecovery:
    def test_malformed_function_skipped(self):
        """Non-dict function entry must not crash."""
        ir = {"data": {"functions": ["not_a_dict", None, 42]}}
        facts = collect_memory_access_facts(ir)
        assert facts == []

    def test_malformed_block_skipped(self):
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", ["not_a_dict", None])
        ])
        facts = collect_memory_access_facts(ir)
        assert facts == []

    def test_malformed_instruction_skipped(self):
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                {"id": "bb0", "instructions": [
                    "not_a_dict", None, 999,
                    _make_instr("ldr", "0x1000",
                                [{"kind": "register", "value": "x0"},
                                 _make_mem_op("sp", 0, 8)], 8),
                ]}
            ])
        ])
        facts = collect_memory_access_facts(ir)
        assert len(facts) == 1

    def test_all_same_offset_no_duplicates_in_offsets_list(self):
        """Multiple accesses to the same offset deduplicate offsets."""
        facts_raw = [
            MemoryAccessFact("0x1000", "fn", "bb0", f"0x{i:x}", "sp", 0, 8, ACCESS_LOAD)
            for i in range(10)
        ]
        candidates, _ = build_layout_candidates(facts_raw)
        assert len(candidates) == 1
        assert candidates[0].observed_offsets == [0]  # deduplicated
        assert candidates[0].access_count == 10  # but count preserved

    def test_large_stride_still_array_like(self):
        """Very large stride (e.g. 1024) with consistent pattern is still array_like."""
        facts = [
            MemoryAccessFact("0x1000", "fn", "bb0", f"0x{i:x}", "x19",
                             i * 1024, 8, ACCESS_LOAD)
            for i in range(4)
        ]
        candidates, _ = build_layout_candidates(facts)
        assert candidates[0].layout_kind == LAYOUT_ARRAY_LIKE

    def test_single_function_multiple_bases(self):
        """Two different base registers in the same function create two candidates."""
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    _make_instr("ldr", "0x1000",
                                [{"kind": "register", "value": "x8"},
                                 _make_mem_op("sp", -8, 8)], 8),
                    _make_instr("ldr", "0x1004",
                                [{"kind": "register", "value": "x9"},
                                 _make_mem_op("x19", 16, 8)], 8),
                ])
            ])
        ])
        engine = LayoutRecoveryEngine()
        candidates, _ = engine.recover(ir)
        assert len(candidates) == 2
        base_ids = {c.base_id for c in candidates}
        assert base_ids == {"sp", "x19"}

    def test_non_load_store_instruction_with_memory_operand_ignored(self):
        """A 'bl' with a memory operand (hypothetical) is ignored."""
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    _make_instr("bl", "0x1000",
                                [_make_mem_op("sp", 0, 8)]),
                ])
            ])
        ])
        facts = collect_memory_access_facts(ir)
        assert facts == []

    def test_output_never_contains_struct_key(self):
        """Full pipeline: output artifact must never have struct-related keys."""
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    _make_instr("ldr", "0x1000",
                                [{"kind": "register", "value": "x0"},
                                 _make_mem_op("sp", -16, 8)], 8),
                ])
            ])
        ])
        engine = LayoutRecoveryEngine()
        candidates, unbound = engine.recover(ir)
        output_str = json.dumps([c.to_dict() for c in candidates])
        for key in ("struct", "field", "c_source", "confidence", "similarity"):
            assert key not in output_str

    def test_empty_basic_block_no_crash(self):
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [])
            ])
        ])
        facts = collect_memory_access_facts(ir)
        assert facts == []

    def test_function_without_basic_blocks_no_crash(self):
        ir = _make_unified_ir([
            {"name": "fn", "entry_point": "0x1000"}  # no basic_blocks key
        ])
        facts = collect_memory_access_facts(ir)
        assert facts == []

    def test_string_offset_parsed_correctly(self):
        """String "16" in offset field should be converted to int 16."""
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    _make_instr("ldr", "0x1000",
                                [{"kind": "register", "value": "x0"},
                                 {"kind": "memory", "base": "sp", "offset": "16"}],
                                8),
                ])
            ])
        ])
        facts = collect_memory_access_facts(ir)
        assert len(facts) == 1
        assert facts[0].offset == 16

    def test_negative_offset_handled(self):
        ir = _make_unified_ir([
            _make_func("fn", "0x1000", [
                _make_block("bb0", [
                    _make_instr("ldr", "0x1000",
                                [{"kind": "register", "value": "x0"},
                                 {"kind": "memory", "base": "sp", "offset": -32}],
                                8),
                ])
            ])
        ])
        facts = collect_memory_access_facts(ir)
        assert facts[0].offset == -32

    def test_many_functions_many_blocks_no_crash(self):
        """Stress test: 50 functions × 10 blocks × 5 instructions each."""
        funcs = []
        for fi in range(50):
            blocks = []
            for bi in range(10):
                instrs = []
                for ii in range(5):
                    addr = f"0x{fi * 10000 + bi * 100 + ii * 4:x}"
                    instrs.append(_make_instr(
                        "ldr", addr,
                        [{"kind": "register", "value": "x0"},
                         _make_mem_op("sp", -(ii + 1) * 8, 8)],
                        8,
                    ))
                blocks.append(_make_block(f"bb{bi}", instrs))
            funcs.append(_make_func(f"fn_{fi}", f"0x{fi * 0x100:x}", blocks))

        ir = _make_unified_ir(funcs)
        engine = LayoutRecoveryEngine()
        candidates, unbound = engine.recover(ir)
        # Should not crash; all should be stack-sp-based
        assert len(candidates) == 50
        assert all(c.base_id == "sp" for c in candidates)
        assert unbound == []
