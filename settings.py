import json
import os


SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "settings.json"
)

LEVEL_NAMES = {
    0: "Business",
    1: "Warm",
    2: "Playful"
}

DEFAULT_SETTINGS = {
    "level": 0,
    "user_name": ""
}


def save_settings(settings):
    with open(SETTINGS_FILE, "w") as file:
        json.dump(settings, file, indent=4)


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        settings = DEFAULT_SETTINGS.copy()
        save_settings(settings)
        return settings

    try:
        with open(SETTINGS_FILE, "r") as file:
            settings = json.load(file)

        if not isinstance(settings, dict):
            settings = DEFAULT_SETTINGS.copy()
            save_settings(settings)
            return settings

        changed = False

        if settings.get("level") not in LEVEL_NAMES:
            settings["level"] = 0
            changed = True

        if not isinstance(settings.get("user_name"), str):
            settings["user_name"] = ""
            changed = True

        if "user_name" not in settings:
            settings["user_name"] = ""
            changed = True

        if changed:
            save_settings(settings)

        return settings

    except (json.JSONDecodeError, OSError):
        settings = DEFAULT_SETTINGS.copy()
        save_settings(settings)
        return settings
    