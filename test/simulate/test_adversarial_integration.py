# -*- coding: utf-8 -*-
"""
Optional Compiled C Integration Tests

Compiles three C programs (Arithmetic/printf, Recursion/Nested conditionals, Pointers)
and runs them through the extraction and semantic recovery pipeline, asserting invariants.
Skips cleanly if compilers or extraction tools are missing.
"""

import os
import sys
import shutil
import tempfile
import subprocess
import unittest
import pytest

from src.ir.types.refinement_engine import TypeRefinementEngine


# Check environment support
def _check_compiler():
    return shutil.which("clang") is not None or shutil.which("gcc") is not None


def _check_r2():
    return shutil.which("radare2") is not None or shutil.which("r2") is not None


# We skip integration tests if compile toolchain is missing
has_compiler = _check_compiler()
has_r2 = _check_r2()


@pytest.mark.integration
@pytest.mark.skipif(not (has_compiler and has_r2), reason="Requires compiler (clang/gcc) and radare2")
class TestAdversarialIntegration(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cc = "clang" if shutil.which("clang") is not None else "gcc"

    def tearDown(self):
        self.temp_dir.cleanup()

    def _compile(self, c_code: str, bin_name: str) -> str:
        c_path = os.path.join(self.temp_dir.name, f"{bin_name}.c")
        bin_path = os.path.join(self.temp_dir.name, bin_name)
        with open(c_path, "w", encoding="utf-8") as f:
            f.write(c_code)

        cmd = [self.cc, c_path, "-o", bin_path]
        # Add basic debugging symbols or optimization flags if preferred, keeping it simple
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Compilation failed: {res.stderr}")
        return bin_path

    # Program 1 — Local arithmetic + printf
    def test_program1_arithmetic_printf(self):
        c_code = """
#include <stdio.h>

int main(void) {
    int x = 1;
    x = x + 2;
    printf("%d\\n", x);
    return 0;
}
"""
        bin_path = self._compile(c_code, "prog1")

        # Run extraction & pipeline using python -m main or direct CLI integration
        out_dir = os.path.join(self.temp_dir.name, "out1")
        os.makedirs(out_dir, exist_ok=True)

        # Build and run pipeline
        cmd = [
            sys.executable,
            "main.py",
            bin_path,
            "--out-dir", out_dir,
            "--r2",
            "--export-ir"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"main.py failed: {res.stderr}")

        # Run recover-semantics
        cmd = [
            sys.executable,
            "main.py",
            "recover-semantics",
            "--out-dir", out_dir
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"recover-semantics failed: {res.stderr}")

        # Run refine-semantics
        cmd = [
            sys.executable,
            "main.py",
            "refine-semantics",
            "--out-dir", out_dir
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"refine-semantics failed: {res.stderr}")

        # Load semantic_recovery.json
        sem_path = os.path.join(out_dir, "semantic_recovery.json")
        self.assertTrue(os.path.exists(sem_path))
        with open(sem_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Assert no fabricated placeholders and no C source emitted
        serialized = json.dumps(data)
        self.assertNotIn("mov eax", serialized.lower())
        self.assertNotIn("c_source", serialized.lower())
        self.assertNotIn("source_code", serialized.lower())

    # Program 2 — Recursion + loop + break/continue + nested conditionals
    def test_program2_complex_flow(self):
        c_code = """
#include <stdio.h>

int helper(int x) {
    if (x <= 1) return 1;
    return x + helper(x - 2);
}

int main(void) {
    int i = 0;

    while (i < 6) {
        if (i == 1) {
            i++;
            continue;
        } else if (i == 4) {
            break;
        } else if (i % 2 == 0) {
            printf("even %d\\n", helper(i));
        } else {
            printf("odd %d\\n", helper(i));
        }
        i++;
    }

    if (i == 4) {
        printf("stopped\\n");
    } else {
        printf("done\\n");
    }

    return 0;
}
"""
        bin_path = self._compile(c_code, "prog2")

        out_dir = os.path.join(self.temp_dir.name, "out2")
        os.makedirs(out_dir, exist_ok=True)

        cmd = [sys.executable, "main.py", bin_path, "--out-dir", out_dir, "--r2", "--export-ir"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

        cmd = [sys.executable, "main.py", "recover-semantics", "--out-dir", out_dir]
        subprocess.run(cmd, capture_output=True)

        cmd = [sys.executable, "main.py", "refine-semantics", "--out-dir", out_dir]
        subprocess.run(cmd, capture_output=True)

        sem_path = os.path.join(out_dir, "semantic_recovery.json")
        self.assertTrue(os.path.exists(sem_path))

    # Program 3 — Pointer use without struct inference
    def test_program3_pointers_no_struct_inference(self):
        c_code = """
#include <stdio.h>

int sum_first_two(int *p) {
    return p[0] + p[1];
}

int main(void) {
    int arr[2] = {1, 2};
    printf("%d\\n", sum_first_two(arr));
    return 0;
}
"""
        bin_path = self._compile(c_code, "prog3")

        out_dir = os.path.join(self.temp_dir.name, "out3")
        os.makedirs(out_dir, exist_ok=True)

        cmd = [sys.executable, "main.py", bin_path, "--out-dir", out_dir, "--r2", "--export-ir"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

        cmd = [sys.executable, "main.py", "recover-semantics", "--out-dir", out_dir]
        subprocess.run(cmd, capture_output=True)

        cmd = [sys.executable, "main.py", "refine-semantics", "--out-dir", out_dir]
        subprocess.run(cmd, capture_output=True)

        sem_path = os.path.join(out_dir, "semantic_recovery.json")
        self.assertTrue(os.path.exists(sem_path))
        with open(sem_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        serialized = json.dumps(data)
        # Ensure no structs or fields keys indicating fabricated struct layouts
        self.assertNotIn('"structs"', serialized)
        self.assertNotIn('"fields"', serialized)


import json  # Import json inside module
