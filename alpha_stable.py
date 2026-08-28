"""Fail-closed completion gate for the frozen SAD + Forge Alpha scope."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from platform_registry import PlatformRegistry
from release_gate import ROOT, run_release_gate


@dataclass(frozen=True)
class StabilitySurface:
    name: str
    module_ids: frozenset[str]
    capability_ids: frozenset[str]
    required_paths: tuple[str, ...]


SAD = StabilitySurface(
    "SAD",
    frozenset({
        "sad.platform", "sad.chat", "sad.voice", "sad.memory", "sad.tools",
        "sad.study", "sad.developer", "sad.accounts", "sad.mobile",
    }),
    frozenset({
        "platform:discover", "platform:compatibility", "chat:conversation",
        "voice:conversation", "memory:own", "tools:catalog", "tools:actions",
        "study:personal", "development:view", "development:work",
        "development:review", "development:decide", "development:govern",
        "account:list", "account:manage", "mobile:paired_client",
    }),
    (
        "ALPHA_STABLE.md", "API.md", "BACKUP.md", "DEVELOPER_WORKSPACE.md",
        "ENCRYPTION_TIER2_UAT.md", "MOBILE.md", "PLATFORM.md", "PLATFORM_SDK.md",
        "PROTOCOL_BLACK.md", "SECURITY.md", "VOICE.md", "WINDOWS.md",
        "test_alpha_product.py", "test_api.py", "test_developer_workspace.py",
        "test_encryption_tier2.py", "test_memory_store.py", "test_mobile_gateway.py",
        "test_platform_api.py", "test_tool_actions.py", "test_voice_runtime.py",
    ),
)

FORGE = StabilitySurface(
    "Forge",
    frozenset({"sad.forge"}),
    frozenset({"forge:play", "progress:own", "progress:students"}),
    (
        "ALPHA_STABLE.md", "ALPHA_UAT.md", "forge_student.py", "forge_worker.py",
        "personal_study.py", "sad_forge_contract.py", "student_progress.py",
        "study_generator.py", "test_forge_game_ui.py", "test_forge_student.py",
        "test_personal_study.py", "test_sad_forge_contract.py",
        "web/app.js", "web/index.html", "web/styles.css",
    ),
)

SURFACES = (SAD, FORGE)


def evaluate_surface(surface: StabilitySurface, *, root: Path = ROOT, registry=None):
    registry = registry or PlatformRegistry()
    module_ids = {module.module_id for module in registry.modules}
    capability_ids = set(registry.capabilities)
    checks = []
    for module_id in sorted(surface.module_ids):
        checks.append((f"module:{module_id}", module_id in module_ids))
    for capability_id in sorted(surface.capability_ids):
        checks.append((f"capability:{capability_id}", capability_id in capability_ids))
    for relative in surface.required_paths:
        checks.append((f"path:{relative}", (root / relative).is_file()))
    return checks


def completion(checks):
    total = len(checks)
    passed = sum(1 for _, ready in checks if ready)
    return passed, total, int((passed / total) * 100) if total else 0


def run_stability_gate(*, root: Path = ROOT, registry=None):
    problems = list(run_release_gate(root))
    results = {}
    for surface in SURFACES:
        checks = evaluate_surface(surface, root=root, registry=registry)
        results[surface.name] = checks
        missing = [name for name, ready in checks if not ready]
        if missing:
            problems.append(f"{surface.name} stability requirements missing: {', '.join(missing)}")
    return problems, results


def main():
    problems, results = run_stability_gate()
    for name, checks in results.items():
        passed, total, percent = completion(checks)
        print(f"{name.upper()} ALPHA STABLE: {percent}% ({passed}/{total})")
    if problems:
        print("ALPHA STABLE GATE: BLOCKED")
        for problem in problems:
            print(f"- {problem}")
        raise SystemExit(1)
    print("ALPHA STABLE GATE: PASS")


if __name__ == "__main__":
    main()
