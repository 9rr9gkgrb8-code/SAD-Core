"""Automated checks for the local-model adapter's safe defaults."""

import unittest
from unittest.mock import patch

import model_adapter
from model_adapter import build_system_prompt, local_model_is_configured


class ModelAdapterTests(unittest.TestCase):
    def test_system_prompt_includes_the_users_name(self):
        prompt = build_system_prompt("Kenneth")
        self.assertIn("Kenneth", prompt)
        self.assertIn("Do not claim", prompt)
        self.assertIn("thoughtful collaborator", prompt)
        self.assertIn("light, friendly humor", prompt)

    def test_local_model_is_disabled_without_a_model_name(self):
        with patch.object(model_adapter, "LOCAL_MODEL_NAME", ""):
            self.assertFalse(local_model_is_configured())


if __name__ == "__main__":
    unittest.main()
