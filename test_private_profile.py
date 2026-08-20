"""Tests for SAD's local-only private profile boundary."""

import json
import tempfile
import unittest
from pathlib import Path

import private_profile


class PrivateProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_directory = private_profile.PRIVATE_DIRECTORY
        self.original_profile_file = private_profile.PRIVATE_PROFILE_FILE
        private_profile.PRIVATE_DIRECTORY = Path(self.temp_directory.name) / "private"
        private_profile.PRIVATE_PROFILE_FILE = (
            private_profile.PRIVATE_DIRECTORY / "profile.json"
        )

    def tearDown(self):
        private_profile.PRIVATE_DIRECTORY = self.original_directory
        private_profile.PRIVATE_PROFILE_FILE = self.original_profile_file
        self.temp_directory.cleanup()

    def test_missing_private_profile_is_optional(self):
        self.assertFalse(private_profile.private_profile_is_configured())
        self.assertEqual(private_profile.load_private_profile(), {})

    def test_private_profile_loads_only_local_data(self):
        private_profile.PRIVATE_DIRECTORY.mkdir()
        private_profile.PRIVATE_PROFILE_FILE.write_text(
            json.dumps({"memory_notes": ["Private note"]}), encoding="utf-8"
        )

        self.assertTrue(private_profile.private_profile_is_configured())
        self.assertEqual(
            private_profile.load_private_profile()["memory_notes"],
            ["Private note"],
        )


if __name__ == "__main__":
    unittest.main()
