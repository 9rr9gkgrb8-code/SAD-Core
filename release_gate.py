"""Fail-closed release checks for the SAD + Forge Alpha surface."""

from __future__ import annotations

from pathlib import Path

from runtime_privacy import PRIVATE_RUNTIME_DIRECTORIES, PRIVATE_RUNTIME_FILES

ROOT = Path(__file__).resolve().parent

REQUIRED_PATHS = (
    ".github/workflows/ci.yml",
    "ALPHA1.md",
    "ALPHA_STABLE.md",
    "ALPHA_UAT.md",
    "API.md",
    "BACKUP.md",
    "DEVELOPER_WORKSPACE.md",
    "ENCRYPTION.md",
    "ENCRYPTION_TIER2_UAT.md",
    "MOBILE.md",
    "PLATFORM.md",
    "PLATFORM_0_4.md",
    "PLATFORM_SDK.md",
    "PLATFORM_TIER2_UAT.md",
    "PLATFORM_TIER3_UAT.md",
    "PROTOCOL_WHITE.md",
    "PROTOCOL_BLACK.md",
    "PROTOCOL_BLACK_REPORT.md",
    "SECURITY.md",
    "VOICE.md",
    "WINDOWS.md",
    "requirements.txt",
    "alpha.py",
    "alpha_doctor.py",
    "alpha_stable.py",
    "api.py",
    "auth.py",
    "backup.py",
    "backup_manager.py",
    "bounded_http.py",
    "container_sandbox.py",
    "conversation.py",
    "developer_workspace.py",
    "docker_proof.py",
    "failure_dashboard.py",
    "forge_worker.py",
    "live_apply.py",
    "memory_store.py",
    "mobile.py",
    "mobile_access.py",
    "mobile_doctor.py",
    "mobile_gateway.py",
    "platform_clients.py",
    "platform_events.py",
    "platform_extensions.py",
    "platform_registry.py",
    "platform_v04_service.py",
    "portable_crypto.py",
    "portable_runtime.py",
    "protocol_white.py",
    "protocol_black.py",
    "repair_planner.py",
    "request_security.py",
    "runtime_database.py",
    "runtime_document.py",
    "runtime_privacy.py",
    "sad_sdk.py",
    "sandbox.py",
    "skill_library.py",
    "sqlite_bytes.py",
    "start_mobile.ps1",
    "start_sad_windows.ps1",
    "tool_actions.py",
    "voice_client.py",
    "voice_runtime.py",
    "windows_crypto.py",
    "windows_doctor.py",
    "test_alpha_doctor.py",
    "test_alpha_stable.py",
    "test_alpha_product.py",
    "test_backup_recovery.py",
    "test_bounded_http.py",
    "test_chat_api.py",
    "test_chat_ui.py",
    "test_conversation.py",
    "test_developer_workspace.py",
    "test_developer_workspace_api.py",
    "test_developer_workspace_ui.py",
    "test_encryption_tier2.py",
    "test_forge_game_ui.py",
    "test_live_repair.py",
    "test_memory_store.py",
    "test_memory_tools_ui.py",
    "test_mobile_access.py",
    "test_mobile_gateway.py",
    "test_mobile_pwa.py",
    "test_owner_repair_ui.py",
    "test_platform_04_privacy.py",
    "test_platform_adolescence_api.py",
    "test_platform_api.py",
    "test_platform_clients.py",
    "test_platform_events.py",
    "test_platform_extensions.py",
    "test_platform_registry.py",
    "test_platform_tier2_api.py",
    "test_platform_tier3_api.py",
    "test_platform_ui.py",
    "test_protocol_black.py",
    "test_protocol_black_supply_chain.py",
    "test_runtime_database.py",
    "test_runtime_persistence.py",
    "test_sad_sdk.py",
    "test_skill_library.py",
    "test_tool_actions.py",
    "test_voice_runtime.py",
    "test_web_accessibility.py",
    "test_windows_crypto.py",
    "test_windows_doctor.py",
    "web/app.js",
    "web/chat.css",
    "web/chat.js",
    "web/developer_workspace.css",
    "web/developer_workspace.js",
    "web/icon.svg",
    "web/index.html",
    "web/manifest.webmanifest",
    "web/memory_tools.css",
    "web/memory_tools.js",
    "web/mobile.js",
    "web/owner_dashboard.css",
    "web/owner_dashboard.js",
    "web/platform.css",
    "web/platform.js",
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
EXCLUDED_PARTS = {".git", *PRIVATE_RUNTIME_DIRECTORIES}
EXCLUDED_NAMES = set(PRIVATE_RUNTIME_FILES)


def iter_release_text_files(root: Path = ROOT):
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path.name in EXCLUDED_NAMES or any(part in EXCLUDED_PARTS for part in path.parts):
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
