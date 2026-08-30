"""Fail-closed repository gate for SAD + Forge Beta candidates.

This gate proves repository evidence only. It intentionally does not claim that physical
Windows, phone, microphone/speaker, network, accessibility, or recovery UAT has passed.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

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
)

BETA_CONTRACT_MARKERS = (
    "SAD Beta contract",
    "Forge Beta contract",
    "Beta evaluator journey",
    "Human acceptance required before public Beta",
    "v0.5.0-beta.1",
)


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

    # Alpha Stable remains a hard dependency for Beta. Run its fail-closed gate rather
    # than duplicating the frozen Alpha contract here.
    result = subprocess.run(
        [sys.executable, str(ROOT / "alpha_stable.py")],
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        return fail("Alpha Stable prerequisite failed")

    print("BETA GATE: REPOSITORY CONTRACT READY")
    print("BETA GATE: HUMAN ACCEPTANCE STILL REQUIRED - see BETA.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
