"""Generate one tightly-scoped repair edit through the configured local model."""

from __future__ import annotations

import json

from model_adapter import generate_local_response


MAX_SOURCE_CHARACTERS = 200_000
MAX_REPLACEMENT_CHARACTERS = 200_000


class RepairPlanningError(ValueError):
    """Raised when a repair plan cannot be generated or safely validated."""


def _parse_plan(raw, source_text):
    if not isinstance(raw, str) or not raw.strip():
        raise RepairPlanningError("The local repair model did not return a plan.")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RepairPlanningError("The local repair model must return JSON only.") from error
    if not isinstance(data, dict):
        raise RepairPlanningError("The local repair model returned an invalid plan shape.")

    find_text = data.get("find_text")
    replacement_text = data.get("replacement_text")
    rationale = data.get("rationale", "")
    if not isinstance(find_text, str) or not find_text:
        raise RepairPlanningError("The repair plan requires non-empty find_text.")
    if not isinstance(replacement_text, str):
        raise RepairPlanningError("The repair plan requires replacement_text.")
    if len(replacement_text) > MAX_REPLACEMENT_CHARACTERS:
        raise RepairPlanningError("The proposed replacement is too large.")
    if source_text.count(find_text) != 1:
        raise RepairPlanningError("The proposed edit must match exactly one source location.")
    if replacement_text == find_text:
        raise RepairPlanningError("The proposed edit does not change the target file.")
    if not isinstance(rationale, str) or len(rationale) > 10_000:
        raise RepairPlanningError("The repair rationale is invalid.")
    return {
        "find_text": find_text,
        "replacement_text": replacement_text,
        "rationale": rationale,
    }


def plan_repair(target_file, objective, source_text, generator=None):
    """Ask the local model for one exact replacement and validate it fail-closed."""
    if not isinstance(source_text, str) or not source_text:
        raise RepairPlanningError("The repair target source is empty.")
    if len(source_text) > MAX_SOURCE_CHARACTERS:
        raise RepairPlanningError("The repair target is too large for automatic planning.")
    if not isinstance(objective, str) or not objective.strip():
        raise RepairPlanningError("The repair objective is required.")

    prompt = (
        "You are the repair planner for SAD. Produce exactly one minimal text edit for the "
        "single target file below. Return ONLY a JSON object with string fields find_text, "
        "replacement_text, and rationale. find_text must be copied exactly from the source, "
        "must occur exactly once, and replacement_text must contain the complete replacement. "
        "Do not use markdown fences. Do not propose edits to any other file. Preserve unrelated "
        "behavior and security controls.\n\n"
        f"TARGET FILE: {target_file}\n"
        f"REPAIR OBJECTIVE: {objective.strip()}\n\n"
        "SOURCE:\n"
        f"{source_text}"
    )
    generate = generator or (lambda text: generate_local_response(text, "SAD repair planner", []))
    return _parse_plan(generate(prompt), source_text)
