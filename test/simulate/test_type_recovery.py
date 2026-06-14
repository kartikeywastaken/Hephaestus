# -*- coding: utf-8 -*-
"""
Phase 4A: Type Recovery Unit Tests

Validates the signature recovery backbone, variable classification,
known library signature database, and artifact emission.
"""

import json
import os
import tempfile
import unittest

from src.ir.types.models import (
    RecoveredFunctionSemantics,
    RecoveredSignature,
    RecoveredType,
    RecoveredVariable,
    RecoveredParameter,
    TYPE_INT32,
    TYPE_POINTER,
    TYPE_UNKNOWN,
    CATEGORY_PARAMETER,
    CATEGORY_LOCAL,
    CATEGORY_UNKNOWN_STACK_SLOT,
    FUNCTION_KIND_LIBRARY,
    FUNCTION_KIND_ENTRYPOINT,
    FUNCTION_KIND_USER,
)
from src.ir.types.signatures import (
    normalize_symbol_name,
    get_known_signature,
    is_known_library_function,
)
from src.ir.types.variable_classifier import classify_variable
from src.ir.types.inference import TypeRecoveryEngine, recover_types
from src.ir.types.emitter import write_type_recovery_artifact, SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Helper: build a minimal unified IR around a list of raw function dicts
# ---------------------------------------------------------------------------

def _make_unified_ir(*functions) -> dict:
    """Wrap raw function dicts in the canonical Unified IR shape."""
    return {
        "schema_version": "2.0.0",
        "provenance": {"binary_path": "test.bin"},
        "data": {
            "functions": list(functions),
            "call_graph": {"nodes": [], "edges": []},
            "symbols": [],
            "imports": [],
            "exports": [],
            "strings": [],
            "constants": [],
            "dynamic_observations": [],
        },
    }


def _make_func(name: str, entry: str = "0x1000", **kwargs) -> dict:
    """Build a minimal raw function dict."""
    func = {
        "name": name,
        "entry_point": entry,
        "size_bytes": 64,
        "calling_convention": "unknown",
        "provenance": ["radare2"],
        "local_variables": [],
        "stack_variables": [],
        "basic_blocks": [],
    }
    func.update(kwargs)
    return func


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestPhase4ATypeRecovery(unittest.TestCase):

    # -----------------------------------------------------------------------
    # Test 1: known printf signature
    # -----------------------------------------------------------------------

    def test_known_printf_signature(self):
        """printf must be recovered as library with exact known signature."""
        ir = _make_unified_ir(_make_func("printf", entry="0x0"))
        results = recover_types(ir)

        self.assertEqual(len(results), 1)
        fn = results[0]

        self.assertEqual(fn.function_kind, FUNCTION_KIND_LIBRARY,
                         "printf must be classified as library")
        self.assertEqual(fn.signature.return_type.type_name, TYPE_INT32,
                         "printf return type must be int32")
        self.assertTrue(fn.signature.variadic,
                        "printf must be variadic")
        self.assertAlmostEqual(fn.signature.confidence, 1.0, places=4,
                               msg="library signature confidence must be 1.0")
        self.assertGreaterEqual(len(fn.signature.parameters), 1,
                                "printf must have at least one parameter")
        self.assertEqual(fn.signature.parameters[0].recovered_type.type_name, TYPE_POINTER,
                         "printf first parameter type must be pointer")

    # -----------------------------------------------------------------------
    # Test 2: known signature name normalization
    # -----------------------------------------------------------------------

    def test_known_signature_name_normalization(self):
        """Both printf and _printf must resolve to the same known signature."""
        sig_plain = get_known_signature("printf")
        sig_underscore = get_known_signature("_printf")

        self.assertIsNotNone(sig_plain, "printf must be in the known signature DB")
        self.assertIsNotNone(sig_underscore, "_printf must be in the known signature DB")
        self.assertEqual(sig_plain.canonical_name, sig_underscore.canonical_name,
                         "printf and _printf must map to the same canonical entry")
        self.assertEqual(sig_plain.return_type, sig_underscore.return_type)
        self.assertEqual(sig_plain.variadic, sig_underscore.variadic)

        # Also verify the normalization function itself
        self.assertEqual(normalize_symbol_name("_printf"), "printf")
        self.assertEqual(normalize_symbol_name("printf"), "printf")
        self.assertEqual(normalize_symbol_name("__malloc"), "malloc")

    # -----------------------------------------------------------------------
    # Test 3: main with no argc/argv → int main(void)
    # -----------------------------------------------------------------------

    def test_main_void_signature(self):
        """_main with no argc/argv variables must produce int main(void) at confidence 0.8."""
        ir = _make_unified_ir(_make_func("_main", entry="0x1000"))
        results = recover_types(ir)

        self.assertEqual(len(results), 1)
        fn = results[0]

        self.assertEqual(fn.function_kind, FUNCTION_KIND_ENTRYPOINT,
                         "_main must be classified as entrypoint")
        self.assertEqual(fn.signature.return_type.type_name, TYPE_INT32,
                         "_main return type must be int32")
        self.assertEqual(fn.signature.parameters, [],
                         "_main with no variables must have empty parameter list")
        self.assertFalse(fn.signature.variadic,
                         "_main must not be variadic")
        self.assertGreaterEqual(fn.confidence, 0.8,
                                "_main confidence must be >= 0.8")

    # -----------------------------------------------------------------------
    # Test 4: main with argc + argv → int main(int argc, char **argv)
    # -----------------------------------------------------------------------

    def test_main_argc_argv_signature(self):
        """_main with argc+argv variables must infer the full main signature at confidence >= 0.9."""
        func = _make_func("_main", entry="0x1000", stack_variables=[
            {"name": "argc", "offset_bytes": -4, "size_bytes": 4},
            {"name": "argv", "offset_bytes": -8, "size_bytes": 8},
        ])
        ir = _make_unified_ir(func)
        results = recover_types(ir)

        self.assertEqual(len(results), 1)
        fn = results[0]

        self.assertEqual(fn.function_kind, FUNCTION_KIND_ENTRYPOINT)
        self.assertEqual(fn.signature.return_type.type_name, TYPE_INT32)
        self.assertGreaterEqual(fn.confidence, 0.9)

        params = fn.signature.parameters
        self.assertEqual(len(params), 2,
                         "must have exactly 2 parameters when argc + argv are present")

        param_names = [p.name for p in params]
        self.assertIn("argc", param_names)
        self.assertIn("argv", param_names)

        argc_param = next(p for p in params if p.name == "argc")
        argv_param = next(p for p in params if p.name == "argv")

        self.assertEqual(argc_param.recovered_type.type_name, TYPE_INT32,
                         "argc type must be int32")
        self.assertEqual(argv_param.recovered_type.type_name, TYPE_POINTER,
                         "argv type must be pointer")

    # -----------------------------------------------------------------------
    # Test 5: arg* variables become parameters with deterministic ordering
    # -----------------------------------------------------------------------

    def test_arg_variables_become_parameters(self):
        """arg1 and arg2 must both be recovered as parameters with unknown type."""
        func = _make_func("user_func", stack_variables=[
            {"name": "arg1", "offset_bytes": -4, "size_bytes": 4},
            {"name": "arg2", "offset_bytes": -8, "size_bytes": 4},
        ])
        ir = _make_unified_ir(func)
        results = recover_types(ir)

        self.assertEqual(len(results), 1)
        fn = results[0]

        param_vars = [v for v in fn.variables if v.category == CATEGORY_PARAMETER]
        self.assertEqual(len(param_vars), 2,
                         "arg1 and arg2 must both be classified as parameters")

        # Check the recovered parameters in the signature
        sig_params = fn.signature.parameters
        self.assertEqual(len(sig_params), 2)

        param_names = [p.name for p in sig_params]
        self.assertIn("arg1", param_names)
        self.assertIn("arg2", param_names)

        # Types remain unknown
        for p in sig_params:
            self.assertEqual(p.recovered_type.type_name, TYPE_UNKNOWN,
                             f"param {p.name} must remain type unknown")

        # Ordering must be deterministic (by offset ascending: -8 before -4)
        self.assertEqual(sig_params[0].name, "arg2",
                         "arg2 has lower offset (-8) so it should come first")
        self.assertEqual(sig_params[1].name, "arg1")

    # -----------------------------------------------------------------------
    # Test 6: local variables are preserved in variables list
    # -----------------------------------------------------------------------

    def test_locals_preserved(self):
        """local_ and var_ variables must appear in the variables list with correct categories."""
        func = _make_func("user_func", stack_variables=[
            {"name": "local_10", "offset_bytes": -16, "size_bytes": 4},
            {"name": "var_8h", "offset_bytes": -8, "size_bytes": 4},
        ])
        ir = _make_unified_ir(func)
        results = recover_types(ir)

        self.assertEqual(len(results), 1)
        fn = results[0]

        var_names = {v.name for v in fn.variables}
        self.assertIn("local_10", var_names)
        self.assertIn("var_8h", var_names)

        local_10 = next(v for v in fn.variables if v.name == "local_10")
        var_8h = next(v for v in fn.variables if v.name == "var_8h")

        self.assertEqual(local_10.category, CATEGORY_LOCAL)
        self.assertEqual(var_8h.category, CATEGORY_LOCAL)
        self.assertEqual(local_10.recovered_type.type_name, TYPE_UNKNOWN)
        self.assertEqual(var_8h.recovered_type.type_name, TYPE_UNKNOWN)

        # Offsets must be preserved
        self.assertEqual(local_10.offset_bytes, -16)
        self.assertEqual(var_8h.offset_bytes, -8)
        self.assertEqual(local_10.size_bytes, 4)

    # -----------------------------------------------------------------------
    # Test 7: unknowns are not over-inferred
    # -----------------------------------------------------------------------

    def test_unknowns_are_not_over_inferred(self):
        """An ambiguous user function with no arg/param vars must stay unknown."""
        func = _make_func("some_internal_fn")
        ir = _make_unified_ir(func)
        results = recover_types(ir)

        self.assertEqual(len(results), 1)
        fn = results[0]

        # Return type must be unknown
        self.assertEqual(fn.signature.return_type.type_name, TYPE_UNKNOWN,
                         "unknown function return type must remain unknown")

        # No fake parameters
        self.assertEqual(len(fn.signature.parameters), 0,
                         "no parameters must be invented when no variable evidence exists")

        # Confidence must be low
        self.assertLessEqual(fn.confidence, 0.4,
                             "confidence must be low for unevidenced function")

    # -----------------------------------------------------------------------
    # Test 8: emitted artifact has correct schema
    # -----------------------------------------------------------------------

    def test_type_recovery_artifact_schema(self):
        """The emitter must produce a valid type_recovery.json with the correct schema."""
        func = _make_func("_main")
        ir = _make_unified_ir(func)
        functions = recover_types(ir)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "type_recovery.json")
            write_type_recovery_artifact(
                functions,
                output_path,
                source_ir="artifacts/unified_ir.json",
                source_structuring="artifacts/structuring_regions.json",
            )

            with open(output_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)

        # Top-level keys
        self.assertIn("schema_version", payload)
        self.assertIn("provenance", payload)
        self.assertIn("data", payload)
        self.assertIn("functions", payload["data"])

        # Schema version
        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertEqual(payload["schema_version"], "4A.0.0")

        # Provenance block
        prov = payload["provenance"]
        self.assertEqual(prov["phase"], "4A")
        self.assertIn("source_ir", prov)
        self.assertIn("source_structuring", prov)

        # Functions list non-empty
        self.assertGreaterEqual(len(payload["data"]["functions"]), 1)

    # -----------------------------------------------------------------------
    # Test 9: no duplicate parameters
    # -----------------------------------------------------------------------

    def test_no_duplicate_parameters(self):
        """Repeated raw variables with the same name must produce only one parameter."""
        func = _make_func("user_fn", stack_variables=[
            {"name": "arg1", "offset_bytes": -4, "size_bytes": 4},
            {"name": "arg1", "offset_bytes": -4, "size_bytes": 4},  # duplicate
        ])
        ir = _make_unified_ir(func)
        results = recover_types(ir)

        self.assertEqual(len(results), 1)
        fn = results[0]

        # Only one parameter named arg1
        params_named_arg1 = [p for p in fn.signature.parameters if p.name == "arg1"]
        self.assertEqual(len(params_named_arg1), 1,
                         "duplicate arg1 entries must deduplicate to a single parameter")

    # -----------------------------------------------------------------------
    # Test 10: empty unified IR does not crash
    # -----------------------------------------------------------------------

    def test_empty_unified_ir_does_not_crash(self):
        """An empty Unified IR must return an empty list without crashing."""
        empty_ir = {"data": {"functions": []}}
        results = recover_types(empty_ir)
        self.assertEqual(results, [],
                         "empty IR must produce empty results list")

        # Emitter must still write a valid artifact
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "type_recovery.json")
            write_type_recovery_artifact(results, output_path)
            with open(output_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            self.assertEqual(payload["data"]["functions"], [])

    # -----------------------------------------------------------------------
    # Additional: variable classifier unit tests
    # -----------------------------------------------------------------------

    def test_classifier_argc(self):
        rv = classify_variable({"name": "argc", "offset_bytes": -4, "size_bytes": 4})
        self.assertEqual(rv.category, CATEGORY_PARAMETER)
        self.assertEqual(rv.recovered_type.type_name, TYPE_INT32)
        self.assertAlmostEqual(rv.confidence, 0.9, places=4)

    def test_classifier_argv(self):
        rv = classify_variable({"name": "argv", "offset_bytes": -8, "size_bytes": 8})
        self.assertEqual(rv.category, CATEGORY_PARAMETER)
        self.assertEqual(rv.recovered_type.type_name, TYPE_POINTER)
        self.assertAlmostEqual(rv.confidence, 0.85, places=4)

    def test_classifier_arg_prefix(self):
        rv = classify_variable({"name": "arg1"})
        self.assertEqual(rv.category, CATEGORY_PARAMETER)
        self.assertEqual(rv.recovered_type.type_name, TYPE_UNKNOWN)
        self.assertAlmostEqual(rv.confidence, 0.45, places=4)

    def test_classifier_param_prefix(self):
        rv = classify_variable({"name": "param_0"})
        self.assertEqual(rv.category, CATEGORY_PARAMETER)
        self.assertEqual(rv.recovered_type.type_name, TYPE_UNKNOWN)
        self.assertAlmostEqual(rv.confidence, 0.45, places=4)

    def test_classifier_local_prefix(self):
        rv = classify_variable({"name": "local_10", "offset_bytes": -16})
        self.assertEqual(rv.category, CATEGORY_LOCAL)
        self.assertEqual(rv.recovered_type.type_name, TYPE_UNKNOWN)
        self.assertAlmostEqual(rv.confidence, 0.4, places=4)

    def test_classifier_var_prefix(self):
        rv = classify_variable({"name": "var_8h", "offset_bytes": -8})
        self.assertEqual(rv.category, CATEGORY_LOCAL)
        self.assertEqual(rv.recovered_type.type_name, TYPE_UNKNOWN)
        self.assertAlmostEqual(rv.confidence, 0.35, places=4)

    def test_classifier_unknown_fallback(self):
        rv = classify_variable({"name": "xyzzy123"})
        self.assertEqual(rv.category, CATEGORY_UNKNOWN_STACK_SLOT)
        self.assertEqual(rv.recovered_type.type_name, TYPE_UNKNOWN)
        self.assertAlmostEqual(rv.confidence, 0.2, places=4)

    def test_classifier_empty_name_fallback(self):
        rv = classify_variable({})
        self.assertEqual(rv.category, CATEGORY_UNKNOWN_STACK_SLOT)
        self.assertEqual(rv.recovered_type.type_name, TYPE_UNKNOWN)

    # -----------------------------------------------------------------------
    # Additional: known signatures completeness
    # -----------------------------------------------------------------------

    def test_all_known_signatures_present(self):
        """All six required library signatures must be in the DB."""
        required = ["printf", "_printf", "puts", "_puts", "atoi", "_atoi",
                    "strlen", "_strlen", "malloc", "_malloc", "free", "_free"]
        for name in required:
            self.assertIsNotNone(
                get_known_signature(name),
                f"Known signature for {name!r} must be present"
            )

    def test_strlen_returns_uint64(self):
        sig = get_known_signature("strlen")
        self.assertIsNotNone(sig)
        self.assertEqual(sig.return_type, "uint64")
        self.assertFalse(sig.variadic)

    def test_malloc_returns_pointer(self):
        sig = get_known_signature("malloc")
        self.assertIsNotNone(sig)
        self.assertEqual(sig.return_type, "pointer")
        self.assertFalse(sig.variadic)

    def test_free_returns_void(self):
        sig = get_known_signature("free")
        self.assertIsNotNone(sig)
        self.assertEqual(sig.return_type, "void")

    # -----------------------------------------------------------------------
    # Additional: to_dict() serialization correctness
    # -----------------------------------------------------------------------

    def test_recovered_type_to_dict(self):
        rt = RecoveredType(type_name=TYPE_INT32, confidence=0.9, source="test", notes=["a"])
        d = rt.to_dict()
        self.assertEqual(d["type"], "int32")
        self.assertEqual(d["confidence"], 0.9)
        self.assertEqual(d["source"], "test")
        self.assertEqual(d["notes"], ["a"])

    def test_recovered_variable_to_dict(self):
        rv = RecoveredVariable(
            name="local_10",
            storage="stack",
            category="local",
            recovered_type=RecoveredType(type_name=TYPE_UNKNOWN, confidence=0.4,
                                          source="local_name_heuristic", notes=[]),
            offset_bytes=-16,
            size_bytes=4,
            source="unified_ir",
            confidence=0.4,
            notes=[],
        )
        d = rv.to_dict()
        self.assertEqual(d["name"], "local_10")
        self.assertEqual(d["storage"], "stack")
        self.assertEqual(d["category"], "local")
        self.assertEqual(d["offset_bytes"], -16)
        self.assertEqual(d["size_bytes"], 4)
        self.assertEqual(d["type"]["type"], "unknown")

    def test_recovered_function_semantics_to_dict(self):
        fn = RecoveredFunctionSemantics(
            name="test_fn",
            entry_point="0x1000",
            function_kind=FUNCTION_KIND_USER,
            signature=RecoveredSignature(),
            variables=[],
            evidence=["test"],
            confidence=0.3,
        )
        d = fn.to_dict()
        self.assertEqual(d["name"], "test_fn")
        self.assertEqual(d["entry_point"], "0x1000")
        self.assertEqual(d["function_kind"], FUNCTION_KIND_USER)
        self.assertIn("signature", d)
        self.assertIn("variables", d)
        self.assertIn("evidence", d)
        self.assertIn("confidence", d)

    # -----------------------------------------------------------------------
    # New Hardening Tests
    # -----------------------------------------------------------------------

    def test_missing_unified_ir_fails_clearly(self):
        """CLI must fail clearly with SystemExit(1) if unified_ir.json is missing."""
        import tempfile
        from main import handle_recover_semantics
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # unified_ir.json is missing in tmpdir
            with self.assertRaises(SystemExit) as cm:
                handle_recover_semantics(tmpdir)
            self.assertEqual(cm.exception.code, 1)

    def test_missing_structuring_regions_continues(self):
        """CLI must continue normally even if structuring_regions.json is missing, unreadable, or malformed."""
        import tempfile
        from main import handle_recover_semantics
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Create a valid unified_ir.json
            ir = _make_unified_ir(_make_func("some_fn"))
            with open(os.path.join(tmpdir, "unified_ir.json"), "w") as f:
                json.dump(ir, f)
            
            # Case A: structuring_regions.json is missing
            with self.assertRaises(SystemExit) as cm:
                handle_recover_semantics(tmpdir)
            self.assertEqual(cm.exception.code, 0)
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "type_recovery.json")))

            # Case B: structuring_regions.json exists but is malformed JSON
            with open(os.path.join(tmpdir, "structuring_regions.json"), "w") as f:
                f.write("invalid json {")
            with self.assertRaises(SystemExit) as cm:
                handle_recover_semantics(tmpdir)
            self.assertEqual(cm.exception.code, 0)

            # Case C: structuring_regions.json exists but is not a dictionary (e.g. list)
            with open(os.path.join(tmpdir, "structuring_regions.json"), "w") as f:
                f.write("[1, 2, 3]")
            with self.assertRaises(SystemExit) as cm:
                handle_recover_semantics(tmpdir)
            self.assertEqual(cm.exception.code, 0)

    def test_deterministic_output_ordering(self):
        """Scrambling functions, variables, and parameters in input must produce stable sorted output order."""
        # Create user functions with variables in different input orders
        func_b = _make_func("func_b", entry="0x2000", stack_variables=[
            {"name": "local_b", "offset_bytes": -8, "size_bytes": 4},
            {"name": "arg_b1", "offset_bytes": -4, "size_bytes": 4},
        ])
        func_a = _make_func("func_a", entry="0x1000", stack_variables=[
            {"name": "arg_a2", "offset_bytes": -8, "size_bytes": 4},
            {"name": "arg_a1", "offset_bytes": -4, "size_bytes": 4},
            {"name": "local_a", "offset_bytes": -12, "size_bytes": 4},
        ])

        # Scramble order 1: func_b first, then func_a
        ir1 = _make_unified_ir(func_b, func_a)
        res1 = recover_types(ir1)

        # Scramble order 2: func_a first, then func_b
        ir2 = _make_unified_ir(func_a, func_b)
        res2 = recover_types(ir2)

        # The function list output must be sorted by entry point address (func_a first, then func_b)
        self.assertEqual(len(res1), 2)
        self.assertEqual(len(res2), 2)

        self.assertEqual(res1[0].name, "func_a")
        self.assertEqual(res1[1].name, "func_b")
        self.assertEqual(res2[0].name, "func_a")
        self.assertEqual(res2[1].name, "func_b")

        # The variables list must be sorted by category (parameter < local), storage, offset, size, name
        # Category order: parameters first, then locals
        # Parameters sorted by offset: arg_a2 (-8) < arg_a1 (-4)
        # So variables list should be: [arg_a2, arg_a1, local_a]
        func_a_vars = res1[0].variables
        self.assertEqual(len(func_a_vars), 3)
        self.assertEqual(func_a_vars[0].name, "arg_a2")
        self.assertEqual(func_a_vars[1].name, "arg_a1")
        self.assertEqual(func_a_vars[2].name, "local_a")

        # Similarly, the signature parameters list must be sorted by offset: [arg_a2, arg_a1]
        func_a_params = res1[0].signature.parameters
        self.assertEqual(len(func_a_params), 2)
        self.assertEqual(func_a_params[0].name, "arg_a2")
        self.assertEqual(func_a_params[1].name, "arg_a1")

    def test_partial_unified_ir_does_not_crash(self):
        """Malformed or missing keys in the Unified IR payload must not crash type recovery."""
        # 1. Non-dict input
        res = recover_types(None)
        self.assertEqual(res, [])

        # 2. Dict input with malformed functions field
        res = recover_types({"data": {"functions": "not a list"}})
        self.assertEqual(res, [])

        # 3. List of functions containing non-dict or malformed elements
        ir = {
            "data": {
                "functions": [
                    None,
                    "not a dict",
                    {"name": "good_func", "entry_point": "0x1000", "stack_variables": None},
                    {"name": 123, "entry_point": None, "stack_variables": ["malformed_var", None, {"name": None}]}
                ]
            }
        }
        res = recover_types(ir)
        good_func_res = next((r for r in res if r.name == "good_func"), None)
        self.assertIsNotNone(good_func_res)

    def test_provenance_paths_are_consistent(self):
        """If both files are inside custom output directory, they are relative to it."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "type_recovery.json")
            
            # Create files on disk so possible_structuring detection finds it
            with open(os.path.join(tmpdir, "unified_ir.json"), "w") as f:
                f.write("{}")
            with open(os.path.join(tmpdir, "structuring_regions.json"), "w") as f:
                f.write("{}")
                
            write_type_recovery_artifact(
                [],
                output_path,
                source_ir=os.path.join(tmpdir, "unified_ir.json"),
                source_structuring=os.path.join(tmpdir, "structuring_regions.json"),
            )
            with open(output_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            
            prov = payload["provenance"]
            self.assertEqual(prov["source_ir"], "unified_ir.json")
            self.assertEqual(prov["source_structuring"], "structuring_regions.json")

    def test_missing_structuring_provenance_is_clean(self):
        """If structuring regions file is absent, source_ir is relative and source_structuring is null."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "type_recovery.json")
            
            # unified_ir.json is created on disk
            with open(os.path.join(tmpdir, "unified_ir.json"), "w") as f:
                f.write("{}")
                
            write_type_recovery_artifact(
                [],
                output_path,
                source_ir=os.path.join(tmpdir, "unified_ir.json"),
                source_structuring=None, # structuring regions file is absent
            )
            with open(output_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            
            prov = payload["provenance"]
            self.assertEqual(prov["source_ir"], "unified_ir.json")
            self.assertIsNone(prov["source_structuring"])

    def test_no_absolute_host_paths_in_phase4a_provenance(self):
        """Ensure provenance doesn't contain mixed absolute local-machine paths when files are inside output dir."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "type_recovery.json")
            
            # Create files on disk so possible_structuring detection finds it
            with open(os.path.join(tmpdir, "unified_ir.json"), "w") as f:
                f.write("{}")
            with open(os.path.join(tmpdir, "structuring_regions.json"), "w") as f:
                f.write("{}")
                
            write_type_recovery_artifact(
                [],
                output_path,
                source_ir=os.path.abspath(os.path.join(tmpdir, "unified_ir.json")),
                source_structuring=os.path.abspath(os.path.join(tmpdir, "structuring_regions.json")),
            )
            with open(output_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            
            prov = payload["provenance"]
            # Both should be simple relative POSIX basenames, no absolute paths (which start with '/' on POSIX)
            self.assertFalse(prov["source_ir"].startswith("/"))
            self.assertFalse(prov["source_structuring"].startswith("/"))
            self.assertEqual(prov["source_ir"], "unified_ir.json")
            self.assertEqual(prov["source_structuring"], "structuring_regions.json")


if __name__ == "__main__":
    unittest.main()
