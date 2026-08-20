"""Checks for Sasha's consistent conversational voice guidance."""

import unittest

from sasha_voice import build_sasha_voice


class SashaVoiceTests(unittest.TestCase):
    def test_voice_guidance_is_personal_but_honest(self):
        voice = build_sasha_voice("Kenneth")
        self.assertIn("Kenneth", voice)
        self.assertIn("thoughtful collaborator", voice)
        self.assertIn("do not pretend to remember", voice)


if __name__ == "__main__":
    unittest.main()
