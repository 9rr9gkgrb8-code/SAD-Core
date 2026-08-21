"""Tests for SAD's optional local preferences."""

import json
import tempfile
import unittest
from pathlib import Path

import local_preferences


class LocalPreferencesTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_directory = local_preferences.LOCAL_DATA_DIRECTORY
        self.original_preferences_file = local_preferences.LOCAL_PREFERENCES_FILE
        local_preferences.LOCAL_DATA_DIRECTORY = Path(self.temp_directory.name) / "local_data"
        local_preferences.LOCAL_PREFERENCES_FILE = (
            local_preferences.LOCAL_DATA_DIRECTORY / "preferences.json"
        )

    def tearDown(self):
        local_preferences.LOCAL_DATA_DIRECTORY = self.original_directory
        local_preferences.LOCAL_PREFERENCES_FILE = self.original_preferences_file
        self.temp_directory.cleanup()

    def test_missing_local_preferences_are_optional(self):
        self.assertFalse(local_preferences.local_preferences_are_configured())
        self.assertEqual(local_preferences.load_local_preferences(), {})

    def test_local_preferences_load(self):
        local_preferences.LOCAL_DATA_DIRECTORY.mkdir()
        local_preferences.LOCAL_PREFERENCES_FILE.write_text(
            json.dumps({"memory_notes": ["Local note"]}), encoding="utf-8"
        )

        self.assertTrue(local_preferences.local_preferences_are_configured())
        self.assertEqual(
            local_preferences.load_local_preferences()["memory_notes"],
            ["Local note"],
        )


if __name__ == "__main__":
    unittest.main()
