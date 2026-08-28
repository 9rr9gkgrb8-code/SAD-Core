"""Load optional preferences stored with one local SAD installation."""

import json
from pathlib import Path

from runtime_database import RuntimeDatabase
from runtime_document import RuntimeJSONDocument


ROOT = Path(__file__).resolve().parent
LOCAL_DATA_DIRECTORY = ROOT / "local_data"
LOCAL_PREFERENCES_FILE = LOCAL_DATA_DIRECTORY / "preferences.json"
DEFAULT_PREFERENCES_FILE = LOCAL_PREFERENCES_FILE
PREFERENCES_NAMESPACE = "local_preferences"
MAX_PREFERENCES_BYTES = 512_000


def _validate_preferences(value):
    if not isinstance(value, dict):
        raise ValueError("Local preferences must be a JSON object.")
    return value


def _using_live_preferences():
    try:
        return Path(LOCAL_PREFERENCES_FILE).resolve() == Path(DEFAULT_PREFERENCES_FILE).resolve()
    except OSError:
        return Path(LOCAL_PREFERENCES_FILE) == Path(DEFAULT_PREFERENCES_FILE)


def _persistence():
    return RuntimeJSONDocument(
        "preferences.json",
        PREFERENCES_NAMESPACE,
        {},
        _validate_preferences,
        MAX_PREFERENCES_BYTES,
        path=None if _using_live_preferences() else LOCAL_PREFERENCES_FILE,
    )


def local_preferences_are_configured():
    """Return whether optional local preferences exist in the selected persistence mode."""
    if not _using_live_preferences():
        return Path(LOCAL_PREFERENCES_FILE).exists()
    if Path(LOCAL_PREFERENCES_FILE).exists():
        return True
    try:
        return RuntimeDatabase().has_document(PREFERENCES_NAMESPACE)
    except (OSError, ValueError):
        return False


def load_local_preferences():
    """Load optional local preferences safely.

    Custom file-path mode keeps the historic tolerant behavior for isolated local tooling.
    The live encrypted runtime fails closed on malformed/migration-conflicting state.
    """
    if not local_preferences_are_configured():
        return {}
    if not _using_live_preferences():
        try:
            preferences = json.loads(Path(LOCAL_PREFERENCES_FILE).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return preferences if isinstance(preferences, dict) else {}
    return _persistence().load()
