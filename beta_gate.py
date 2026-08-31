"""Fail-closed repository gate for SAD + Forge Beta candidates.

This gate proves repository evidence only. It intentionally does not claim that physical
Windows, phone, microphone/speaker, network, accessibility, or recovery UAT has passed.
"""

from __future__ import annotations

from pathlib import Path
import os
import re

from alpha_stable import run_stability_gate

ROOT = Path(__file__).resolve().parent

REQUIRED_FILES = (
    "README.md",
    "ALPHA_STABLE.md",
    "BETA.md",
    "requirements.txt",
    "protocol_black.py",
    "release_gate.py",
    "alpha_stable.py",
    "alpha_doctor.py",
    "windows_doctor.py",
    "docker_proof.py",
    "BETA_ACCEPTANCE.md",
)

BETA_CONTRACT_MARKERS = (
    "SAD Beta contract",
    "Forge Beta contract",
    "Beta evaluator journey",
    "Human acceptance required before public Beta",
    "v0.5.0-beta.1",
)
ACCEPTANCE_SECTIONS = ("Host and security", "SAD", "Voice and Mobile", "Forge", "Recovery", "Accessibility and evaluator experience", "Release decision")


def parse_acceptance_record(text):
    """Parse explicit checklist evidence; prose or copied marker strings cannot count."""
    sections = {name: [] for name in ACCEPTANCE_SECTIONS}
    current = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip() if line[3:].strip() in sections else None
        elif current and re.fullmatch(r"- \[[ xX]\] .+", line):
            sections[current].append(line[3].lower() == "x")
    if any(not values for values in sections.values()):
        raise ValueError("Acceptance evidence must contain checklist items in every required section.")
    decision = re.search(r"^Final Owner decision:\s*\*\*(HOLD|APPROVE)\*\*", text, re.MULTILINE)
    if not decision:
        raise ValueError("Acceptance evidence requires an explicit Owner HOLD or APPROVE decision.")
    return {"sections": sections, "decision": decision.group(1), "complete": all(all(values) for values in sections.values())}


def fail(message: str) -> int:
    print(f"BETA GATE: FAIL - {message}")
    return 1


def main() -> int:
    missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    if missing:
        return fail("missing required repository evidence: " + ", ".join(missing))

    contract = (ROOT / "BETA.md").read_text(encoding="utf-8")
    missing_markers = [marker for marker in BETA_CONTRACT_MARKERS if marker not in contract]
    if missing_markers:
        return fail("BETA.md is incomplete: " + ", ".join(missing_markers))
    try:
        acceptance = parse_acceptance_record((ROOT / "BETA_ACCEPTANCE.md").read_text(encoding="utf-8"))
    except ValueError as error:
        return fail(str(error))
    if os.getenv("SAD_BETA_RELEASE") == "1" and (not acceptance["complete"] or acceptance["decision"] != "APPROVE"):
        return fail("release mode requires every structured acceptance item and an Owner APPROVE decision")

    # Alpha Stable remains a hard dependency for Beta. Call the existing in-process
    # fail-closed gate rather than introducing a new subprocess-capable module.
    problems, _ = run_stability_gate(root=ROOT)
    if problems:
        return fail("Alpha Stable prerequisite failed")

    print("BETA GATE: REPOSITORY CONTRACT READY")
    print("BETA GATE: HUMAN ACCEPTANCE STILL REQUIRED - see BETA.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
