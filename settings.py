from pathlib import Path

from runtime_document import RuntimeJSONDocument


DEFAULT_SETTINGS_FILE = str(Path(__file__).with_name("settings.json"))
SETTINGS_FILE = DEFAULT_SETTINGS_FILE
SETTINGS_NAMESPACE = "settings"
MAX_SETTINGS_BYTES = 128_000

LEVEL_NAMES = {
    0: "Business",
    1: "Warm",
    2: "Playful"
}

DEFAULT_SETTINGS = {
    "level": 0,
    "user_name": ""
}


def _validate_settings_document(value):
    if not isinstance(value, dict):
        raise ValueError("Settings must be an object.")
    return value


def _persistence():
    try:
        is_live_default = Path(SETTINGS_FILE).resolve() == Path(DEFAULT_SETTINGS_FILE).resolve()
    except OSError:
        is_live_default = SETTINGS_FILE == DEFAULT_SETTINGS_FILE
    return RuntimeJSONDocument(
        "settings.json",
        SETTINGS_NAMESPACE,
        DEFAULT_SETTINGS,
        _validate_settings_document,
        MAX_SETTINGS_BYTES,
        path=None if is_live_default else SETTINGS_FILE,
    )


def _normalized(settings):
    if not isinstance(settings, dict):
        return DEFAULT_SETTINGS.copy(), True
    value = dict(settings)
    changed = False
    if value.get("level") not in LEVEL_NAMES:
        value["level"] = 0
        changed = True
    if not isinstance(value.get("user_name"), str):
        value["user_name"] = ""
        changed = True
    if "user_name" not in value:
        value["user_name"] = ""
        changed = True
    return value, changed


def save_settings(settings):
    value, _changed = _normalized(settings)
    _persistence().save(value)


def load_settings():
    persistence = _persistence()
    try:
        settings = persistence.load()
    except (ValueError, OSError):
        # Explicit compatibility/test files retain the legacy self-healing behavior.
        if Path(SETTINGS_FILE).resolve() != Path(DEFAULT_SETTINGS_FILE).resolve():
            settings = DEFAULT_SETTINGS.copy()
            persistence.save(settings)
            return settings
        raise
    settings, changed = _normalized(settings)
    if changed:
        persistence.save(settings)
    return settings
