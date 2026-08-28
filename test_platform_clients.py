import json
import tempfile
import unittest
from pathlib import Path

from platform_clients import PlatformClientStore


class PlatformClientStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "clients.json"
        self.store = PlatformClientStore(self.path)

    def test_secret_is_returned_once_and_hashed_at_rest(self):
        created = self.store.create("Voice shell", ["platform:discover"], [])
        self.assertIn("client_secret", created)
        raw = self.path.read_text(encoding="utf-8")
        self.assertNotIn(created["client_secret"], raw)
        listed = self.store.list()[0]
        self.assertNotIn("client_secret", listed)
        self.assertNotIn("secret_hash", listed)
        self.assertNotIn("secret_salt", listed)

    def test_authentication_scope_rotation_and_revoke(self):
        created = self.store.create("Status app", ["platform:discover", "platform:events"], ["failure.created"])
        header = f"SAD-App {created['client_id']}.{created['client_secret']}"
        client = self.store.require(header, "platform:discover")
        self.assertEqual(client["event_types"], ["failure.created"])
        with self.assertRaises(PermissionError):
            self.store.require(header, "platform:catalog")

        rotated = self.store.rotate(created["client_id"])
        with self.assertRaises(PermissionError):
            self.store.require(header, "platform:discover")
        new_header = f"SAD-App {created['client_id']}.{rotated['client_secret']}"
        self.store.require(new_header, "platform:discover")
        self.store.revoke(created["client_id"])
        with self.assertRaises(PermissionError):
            self.store.require(new_header, "platform:discover")

    def test_invalid_or_duplicate_scopes_fail_closed(self):
        with self.assertRaises(ValueError):
            self.store.create("Bad", ["development:govern"], [])
        with self.assertRaises(ValueError):
            self.store.create("Bad", ["platform:discover", "platform:discover"], [])
        with self.assertRaises(ValueError):
            self.store.create("Bad", ["platform:discover"], ["failure.created"])

    def test_event_subscription_must_be_known(self):
        with self.assertRaises(ValueError):
            self.store.create("Bad", ["platform:events"], ["secret.dumped"])


if __name__ == "__main__":
    unittest.main()
