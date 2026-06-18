# Conservative Binary Reconstruction Policy

## Core Principle

> [!IMPORTANT]
> **Missing evidence is acceptable. Fabricated evidence is not.**

The primary goal of Hephaestus is syntax-safe binary reconstruction, NOT semantic equivalence or high-level program representation mapping. It does not attempt to guess or invent program logic where direct compiler evidence is missing.

---

## Allowed Output Structures

Hephaestus is allowed to generate the following structures when backed by direct or indirect analysis evidence:

1. **Pseudo Registers**: Representation of register values using prefix assignments (e.g. `tmp_x0`, `tmp_w0`).
2. **Pseudo Stack Slots**: Inferred local stack variables (e.g. `stack_0`, `stack_m20`).
3. **Call Helpers**: Forward declarations of unrecovered functions (e.g. `call_0x100000abc()`).
4. **Syntax Adapters**: Emitted markers for unrecovered conditions and operands:
   - `HEPHAESTUS_UNKNOWN_COND("evidence")` for conditional branches where flags/predicates cannot be accurately mapped.
   - `HEPHAESTUS_CSET("condition")` for ARM64 conditional set instructions.
5. **Unsupported Instructions Comments**: Preserved comments representing unlowered instructions to maintain analysis transparency.
6. **Branch Evidence Comments**: Comments indicating branch flow targets.
7. **Layout Candidates**: Struct and data layout candidates without actual fabricated struct types in code.

---

## Forbidden Output Structures

To guarantee that no program semantics or variables are invented, Hephaestus is strictly prohibited from generating:

1. **Fake Source Variables**: No guessing of loop counters, parameter names, or variable types without evidence.
2. **Fake Structs**: Creating structure definitions (`struct foo { ... }`) that do not exist or cannot be fully verified.
3. **Fake Fields**: Guessing member names (`->field_name`) or structure hierarchy.
4. **Fake Arrays**: Guessing array indices or size bounds.
5. **Fake Executable Conditions**: Building executable conditional expressions (e.g. `if (tmp_w0 == 0)`) without complete control-flow validation.
6. **Fake Flag Variables**: Fabricating custom CPU flag representations in code.
7. **Fake Semantic Equivalence Claims**: Claiming reconstructed source functions behave exactly as the input binary.
