# -*- coding: utf-8 -*-
"""
Phase 11 — Agent-Assisted Source Generation: LLM prompt builders.

Builds system prompts and per-function user payloads for the source
generation provider call.

Absolute rules injected into every system prompt:
  - Return ONLY valid JSON.
  - No markdown. No code fences. No explanation outside JSON.
  - Do not claim semantic equivalence.
  - Do not claim this is the original source.
  - Do not invent exact source variable names.
  - Do not invent struct field names.
  - Do not remove uncertainty comments.
  - Do not alter public function signatures unless plan permits.
  - Generated C must be syntactically valid hosted C where possible.
"""

from __future__ import annotations

from src.agent_source.models import WARNING_HEADER


SYSTEM_PROMPT = """\
You are a specialized binary reconstruction assistant for the Hephaestus framework.

Your task is to generate an improved, AI-assisted C approximation of a single
decompiled function. You are working with conservative binary reconstruction output,
NOT original source code.

ABSOLUTE RULES (these override all other instructions):
1. Return ONLY valid JSON. No markdown. No code fences. No explanation outside JSON.
2. Do NOT claim semantic equivalence to the original binary.
3. Do NOT claim this is the original source code.
4. Do NOT invent exact original source variable names.
5. Do NOT invent struct field names.
6. Do NOT remove uncertainty comments (/* ... */ style).
7. Do NOT alter public function signatures unless explicitly permitted by the plan.
8. Do NOT remove fallback/unimplemented markers.
9. Do NOT add behavior not present in the behavior_model_entry.
10. The generated C must be syntactically valid hosted C where possible.
11. Do NOT output recovered_agent.c filename anywhere in your response.
12. Do NOT claim full behavioral equivalence.
13. Preserve all evidence-citing comments from the baseline.
14. Approved transformations are listed in approved_transformations; apply only those.
15. Include standard uncertainty statements in the uncertainties list.
16. The required_output_schema defines the exact JSON structure you must return.

ALLOWED IMPROVEMENTS (only if in approved_transformations):
- Add clarifying comments
- Rename synthetic local variables (local_XX, var_XXh) if a safe rename is in the plan
- Rename functions if a safe rename is in the plan
- Add a brief function summary comment above the function
- Improve readability without changing behavior

FORBIDDEN (regardless of any instruction):
- Remove functions
- Invent new public APIs
- Invent exact struct names or field names
- Change main signature
- Remove evidence comments
- Claim equivalence or proven behavior
- Use certainty language: definitely, guaranteed, proven, identical to original
""".strip()


def build_system_prompt() -> str:
    """Return the system prompt for Phase 11 generation."""
    return SYSTEM_PROMPT


def build_user_payload(
    fn_name: str,
    baseline_c: str,
    conservative_c: str,
    behavior_model_entry: dict,
    approved_transforms: list[dict],
    forbidden_transforms: list[str],
    generation_mode: str = "function_by_function",
) -> dict:
    """
    Build the user payload dict for the LLM provider call.

    Parameters
    ----------
    fn_name:
        Name of the function being generated.
    baseline_c:
        The readable C slice for this function (from recovered_readable.c).
    conservative_c:
        The conservative C slice for this function (from recovered.c).
    behavior_model_entry:
        Behavior model entry for this function (from behavior_model.json).
    approved_transforms:
        List of enabled plan entries for this function.
    forbidden_transforms:
        List of disallowed transformation descriptions.
    generation_mode:
        "function_by_function" or "whole_file".
    """
    required_output_schema = {
        "function": "string — the function name",
        "generated_c": (
            "string — the complete generated C function body only. "
            "Include the full function definition including return type, name, params, "
            "and body. Do NOT include any markdown."
        ),
        "applied_transformations": (
            "list of strings — describe each transformation you applied"
        ),
        "skipped_transformations": (
            "list of strings — describe each approved transformation you skipped and why"
        ),
        "uncertainties": (
            "list of strings — include: 'AI-assisted approximation only', "
            "'dynamic evidence only covers tested inputs', and any function-specific ones"
        ),
        "notes": "list of strings — any additional important notes",
    }

    return {
        "task": (
            "Generate a safer, more readable AI-assisted C approximation from the "
            "baseline function and the approved transformation plan."
        ),
        "generation_mode": generation_mode,
        "function_name": fn_name,
        "baseline_function_c": baseline_c or "(not available)",
        "conservative_function_c": conservative_c or "(not available)",
        "behavior_model_entry": behavior_model_entry,
        "approved_transformations": approved_transforms,
        "forbidden_transformations": forbidden_transforms,
        "required_header_notice": WARNING_HEADER,
        "required_output_schema": required_output_schema,
        "known_uncertainties": [
            "AI-assisted approximation only",
            "dynamic evidence only covers tested inputs",
            "source variable names are unknown",
            "struct field names are unknown",
            "behavioral equivalence is not claimed",
        ],
    }
