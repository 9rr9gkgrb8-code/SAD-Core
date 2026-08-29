import unittest

from runtime_privacy import LOCAL_DATA_DIRECTORY, PRIVATE_RUNTIME_FILES, is_private_runtime_path, private_store_path


class Platform04PrivacyTests(unittest.TestCase):
    def test_new_governance_stores_are_private_runtime_state(self):
        for name in ("platform_extensions.json", "skills.json"):
            with self.subTest(name=name):
                self.assertIn(name, PRIVATE_RUNTIME_FILES)
                self.assertEqual(private_store_path(name).parent, LOCAL_DATA_DIRECTORY)
                self.assertTrue(is_private_runtime_path(name))
                self.assertTrue(is_private_runtime_path(f"local_data/{name}"))


if __name__ == "__main__":
    unittest.main()
