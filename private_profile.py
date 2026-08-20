"""Keep optional personal profile data local to one SAD installation."""

import json
from pathlib import Path


PRIVATE_DIRECTORY = Path(__file__).with_name("private")
PRIVATE_PROFILE_FILE = PRIVATE_DIRECTORY / "profile.json"


def private_profile_is_configured():
    """Return whether a local-only profile file is available."""
    return PRIVATE_PROFILE_FILE.exists()


def load_private_profile():
    """Load local-only data safely; never require it for SAD to run."""
    if not private_profile_is_configured():
        return {}

    try:
        profile = json.loads(PRIVATE_PROFILE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    return profile if isinstance(profile, dict) else {}
