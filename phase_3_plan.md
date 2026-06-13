# Phase 3: Control Flow Graph (CFG) Structuring & Restructuring

This document outlines the technical design, algorithms, and references required to transition the reconstruction platform from raw basic block jumps (using labels/gotos) to high-level structured control flow constructs (`if-else` branches, loops, and sequences).

---

## 1. What We Have to Achieve

Our main goal is to convert the flat list of basic blocks and edges (jumps/branches) from the Unified IR into a structured Abstract Syntax Tree (AST) representation of the control flow. 

Specifically, we want to recover:
- **Sequences**: Linear sequences of instruction blocks executed consecutively.
- **Conditional Branches**: Binary splits (`if-else` blocks) that converge at a common merge node (post-dominator).
- **Loops**: Cycles (e.g., `while`, `for`, `do-while` loops) identified by back-edges where a block jumps back to a dominator block.
- **Switch Cases**: Multi-way branching tables.

### Current Representation (Flat basic blocks with gotos):
```c
block_entry:
    // instructions
    if (cond) goto block_then; else goto block_else;
block_then:
    // instructions
    goto block_merge;
block_else:
    // instructions
    goto block_merge;
block_merge:
    return;
```

### Structured AST Representation (Goal):
```c
if (cond) {
    // then block instructions
} else {
    // else block instructions
}
return;
```

---

## 2. References and Theoretical Foundations

We will base our structuring engine on established algorithms from decompiler theory and control-flow analysis:
1. **Iterative Dominator Framework (Cooper, Harvey, and Kennedy)**: A fast and simple algorithm to calculate dominator trees for the Control Flow Graph.
2. **Back-Edge and Loop Header Heuristics (Tarjan / Muchnick)**:
   - An edge `u -> v` is a **back-edge** if `v` dominates `u`.
   - `v` is designated as the **loop header** and `u` is the **loop latch**.
   - The loop body is recovered using a backward traversal from the latch to the header.
3. **Structured Control Flow Analysis (Phoenix / Dream Decompiler / Structural Analysis)**:
   - Identify hammocks and regions of code.
   - Match structured region patterns:
     - **Sequence**: `A -> B` where `A` has only one successor `B`, and `B` has only one predecessor `A`.
     - **If-Then**: `A` splits to `B` and `C`, `B` goes to `C` (where `C` is the merge node).
     - **If-Else**: `A` splits to `B` and `C`, and both `B` and `C` jump to `D` (where `D` is the merge node).
     - **Self-Loop**: `A -> A`.
     - **While-Loop**: Loop header `H` splits execution between loop body `B` and exit block `E`. `B` jumps back to `H`.

---

## 3. How We Will Achieve It (Proposed Implementation Steps)

We will implement a Python-based structuring module under `src/ir/structuring.py` and write unit tests in `test/simulate/test_structuring.py`.

### Step 1: Compute Dominators & Post-Dominators
Implement an iterative dominator tree solver:
- For each block, calculate the intersection of predecessors' dominators.
- Repeat until fixed point.
- Do the same on the reversed CFG to get **post-dominators** (essential for locating merge/join nodes).

### Step 2: Loop Recovery
Scan all CFG edges:
- Detect loop back-edges (`src -> dest` where `dest` dominates `src`).
- Recover the loop body by finding all blocks reachable backward from the latch `src` to the header `dest`.
- Mark these blocks as part of a `LoopNode`.

### Step 3: Conditional Branch Recovery
For each block with multiple outgoing edges (conditional split):
- Locate its immediate post-dominator `M` (the merge point).
- Group the blocks along the split paths (before they merge at `M`) into the `then_branch` and `else_branch` of an `IfElseNode`.

### Step 4: AST Node Representation
Define structural nodes in Python:
- `BlockNode(bb_id)`: Represents a raw basic block.
- `SequenceNode(nodes)`: A linear list of nodes.
- `IfElseNode(condition_id, then_node, else_node, merge_id)`: An if-else region.
- `LoopNode(header_id, body_node, exit_id)`: A loop region.

### Step 5: AST Emitter Integration (Phase 5)
Update the source generator (Phase 5) to traverse this structured AST tree recursively and emit clean, nested C code, completely replacing flat label gotos.
