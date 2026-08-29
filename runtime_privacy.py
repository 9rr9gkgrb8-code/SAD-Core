"""Shared private-runtime path policy for SAD.

Private state belongs below local_data/ whenever practical. This module also migrates
legacy root-level private stores before services become available so coding/release
surfaces cannot mistake private runtime data for source.
"""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parent
LOCAL_DATA_DIRECTORY = ROOT / "local_data"

PRIVATE_RUNTIME_FILES = frozenset({
    "accounts.json",
    "chat_history.json",
    "dashboard_state.json",
    "failures.json",
    "memory.json",
    "mobile_access.json",
    "platform_clients.json",
    "platform_events.json",
    "platform_extensions.json",
    "preferences.json",
    "sad_runtime.sqlite3",
    "settings.json",
    "skills.json",
    "student_progress.json",
    "tool_actions.json",
})

PRIVATE_RUNTIME_DIRECTORIES = frozenset({
    ".sad_sandbox",
    ".sad_dev",
    "local_data",
    "__pycache__",
})


def is_private_runtime_path(value):
    """Return True for repository-relative paths that must never be coding source."""
    path = PurePosixPath(str(value).replace("\\", "/"))
    if any(part in PRIVATE_RUNTIME_DIRECTORIES for part in path.parts):
        return True
    name = path.name
    if name in PRIVATE_RUNTIME_FILES:
        return True
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return True
    return False


def private_store_path(filename):
    if filename not in PRIVATE_RUNTIME_FILES:
        raise ValueError("Unknown private runtime filename.")
    return LOCAL_DATA_DIRECTORY / filename


def migrate_legacy_private_store(destination, legacy):
    """Move one legacy root private file below local_data, failing on ambiguity.

    If both paths exist we refuse to guess which copy is authoritative. That prevents a
    stale root copy from remaining available to a coding workspace while SAD silently
    uses another copy.
    """
    destination = Path(destination)
    legacy = Path(legacy)
    if destination == legacy:
        return destination
    if destination.exists() and legacy.exists():
        raise ValueError(
            f"Conflicting private runtime files exist at {destination.name} and legacy root path. "
            "Reconcile them before starting SAD."
        )
    if legacy.exists():
        if legacy.is_symlink() or not legacy.is_file():
            raise ValueError("Legacy private runtime path must be a regular file.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(legacy, destination)
        try:
            os.chmod(destination, 0o600)
        except OSError:
            pass
    return destination
