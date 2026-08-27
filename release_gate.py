"""Fail-closed release checks for the SAD + Forge Alpha surface."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent

REQUIRED_PATHS = (
    ".github/workflows/ci.yml",
    "ALPHA1.md",
    "ALPHA_UAT.md",
    "MOBILE.md",
    "SECURITY.md",
    "alpha.py",
    "alpha_doctor.py",
    "api.py",
    "auth.py",
    "container_sandbox.py",
    "docker_proof.py",
    "failure_dashboard.py",
    "forge_worker.py",
    "live_apply.py",
    "mobile.py",
    "mobile_access.py",
    "mobile_doctor.py",
    "mobile_gateway.py",
    "repair_planner.py",
    "sandbox.py",
    "start_mobile.ps1",
    "test_alpha_doctor.py",
    "test_alpha_product.py",
    "test_forge_game_ui.py",
    "test_live_repair.py",
    "test_mobile_access.py",
    "test_mobile_gateway.py",
    "test_mobile_pwa.py",
    "test_owner_repair_ui.py",
    "test_web_accessibility.py",
    "web/app.js",
    "web/icon.svg",
    "web/index.html",
    "web/manifest.webmanifest",
    "web/mobile.js",
    "web/owner_dashboard.css",
    "web/owner_dashboard.js",
    "web/styles.css",
    "web/sw.js",
)

# Construct retired markers from fragments so the gate does not match itself.
RETIRED_MARKERS = (
    "adult" + "_mode",
    "adult mode " + "on",
    "adult mode " + "off",
    "private." + "adult" + "_mode",
    "private." + "adult" + "_guardrails",
    "18" + "+ add-on",
)

TEXT_SUFFIXES = {
    ".py", ".md", ".json", ".yml", ".yaml", ".txt", ".ps1",
    ".js", ".html", ".css", ".svg", ".webmanifest",
}
EXCLUDED_PARTS = {".git", ".sad_sandbox", "local_data", "__pycache__"}


def iter_release_text_files(root: Path = ROOT):
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        yield path


def find_retired_markers(root: Path = ROOT):
    findings = []
    for path in iter_release_text_files(root):
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for marker in RETIRED_MARKERS:
            if marker.lower() in text:
                findings.append((path.relative_to(root).as_posix(), marker))
    return findings


def find_missing_required_paths(root: Path = ROOT):
    return [path for path in REQUIRED_PATHS if not (root / path).is_file()]


def run_release_gate(root: Path = ROOT):
    problems = []
    missing = find_missing_required_paths(root)
    if missing:
        problems.append("missing required Alpha paths: " + ", ".join(missing))

    retired = find_retired_markers(root)
    if retired:
        rendered = ", ".join(f"{path} [{marker}]" for path, marker in retired)
        problems.append("retired private-mode markers found: " + rendered)

    return problems


def main():
    problems = run_release_gate()
    if problems:
        print("ALPHA RELEASE GATE: BLOCKED")
        for problem in problems:
            print(f"- {problem}")
        raise SystemExit(1)
    print("ALPHA RELEASE GATE: PASS")


if __name__ == "__main__":
    main()
