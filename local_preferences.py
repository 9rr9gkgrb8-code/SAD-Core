"""Load optional preferences stored with one local SAD installation."""

import json
from pathlib import Path


LOCAL_DATA_DIRECTORY = Path(__file__).with_name("local_data")
LOCAL_PREFERENCES_FILE = LOCAL_DATA_DIRECTORY / "preferences.json"


def local_preferences_are_configured():
    """Return whether a local preferences file is available."""
    return LOCAL_PREFERENCES_FILE.exists()


def load_local_preferences():
    """Load optional local preferences safely."""
    if not local_preferences_are_configured():
        return {}

    try:
        preferences = json.loads(LOCAL_PREFERENCES_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    return preferences if isinstance(preferences, dict) else {}
