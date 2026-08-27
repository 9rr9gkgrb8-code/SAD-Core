"""Automated checks for the local-model adapter's safe defaults."""

import unittest
from unittest.mock import patch

import model_adapter
from model_adapter import build_system_prompt, local_model_is_configured, validated_local_model_url


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

    def test_local_model_url_rejects_remote_or_credentialed_endpoints(self):
        for url in ("https://example.com", "http://192.168.1.5:11434", "http://user:pass@localhost:11434", "http://localhost:11434/path"):
            with self.assertRaises(ValueError):
                validated_local_model_url(url)
        self.assertEqual(validated_local_model_url("http://127.0.0.1:11434"), "http://127.0.0.1:11434")


if __name__ == "__main__":
    unittest.main()
