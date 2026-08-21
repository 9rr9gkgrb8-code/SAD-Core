"""Tests for the visible dialogue-level settings."""

import json
import tempfile
import unittest
from pathlib import Path

import settings


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_settings_file = settings.SETTINGS_FILE
        settings.SETTINGS_FILE = str(Path(self.temp_directory.name) / "settings.json")

    def tearDown(self):
        settings.SETTINGS_FILE = self.original_settings_file
        self.temp_directory.cleanup()

    def test_invalid_level_is_reset_to_default(self):
        Path(settings.SETTINGS_FILE).write_text(
            json.dumps({"level": 3, "user_name": "Ken"}),
            encoding="utf-8",
        )

        loaded = settings.load_settings()

        self.assertNotIn(3, settings.LEVEL_NAMES)
        self.assertEqual(loaded["level"], 0)


if __name__ == "__main__":
    unittest.main()
