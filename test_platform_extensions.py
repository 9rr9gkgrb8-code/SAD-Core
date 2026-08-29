import tempfile
import unittest
from pathlib import Path

from platform_extensions import PlatformExtensionStore, normalize_extension_manifest
from platform_registry import PlatformRegistry


class PlatformExtensionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = PlatformExtensionStore(Path(self.temp.name) / "extensions.json")
        self.registry = PlatformRegistry()

    @staticmethod
    def manifest(**overrides):
        value = {
            "name": "SAD Example Extension",
            "publisher": "Local Developer",
            "version": "1.0.0",
            "description": "External client that consumes SAD discovery events.",
            "required_capabilities": [
                {"capability_id": "platform:discover", "min_version": "1.0.0"},
                {"capability_id": "platform:events", "min_version": "1.0.0"},
            ],
            "requested_event_types": ["failure.created"],
            "execution_model": "external_process",
            "transport": "sad_app_http",
            "network_scope": "loopback_only",
            "core_code_loading": False,
            "host_fallback": False,
            "git_authority": "none",
        }
        value.update(overrides)
        return value

    def test_registration_is_declarative_and_grants_no_authority(self):
        record = self.store.register(self.manifest(), self.registry, registered_by="owner-account")
        self.assertEqual(record["state"], "registered")
        self.assertTrue(record["compatibility"]["compatible"])
        self.assertFalse(record["authority_model"]["registration_grants_authority"])
        self.assertFalse(record["authority_model"]["credentials_created"])
        self.assertFalse(record["authority_model"]["dynamic_core_loading"])
        self.assertFalse(record["authority_model"]["host_fallback"])
        self.assertEqual(record["authority_model"]["git_authority"], "none")

    def test_manifest_rejects_execution_authority_escalation(self):
        with self.assertRaises(ValueError):
            normalize_extension_manifest(self.manifest(core_code_loading=True))
        with self.assertRaises(ValueError):
            normalize_extension_manifest(self.manifest(host_fallback=True))
        with self.assertRaises(ValueError):
            normalize_extension_manifest(self.manifest(git_authority="push"))
        with self.assertRaises(ValueError):
            normalize_extension_manifest(self.manifest(network_scope="internet"))

    def test_manifest_rejects_unreviewed_execution_fields(self):
        manifest = self.manifest()
        manifest["command"] = "python plugin.py"
        with self.assertRaises(ValueError):
            normalize_extension_manifest(manifest)

    def test_missing_platform_capability_is_recorded_not_granted(self):
        manifest = self.manifest(required_capabilities=[
            {"capability_id": "future:unknown", "min_version": "1.0.0"},
        ])
        record = self.store.register(manifest, self.registry, registered_by="owner-account")
        self.assertFalse(record["compatibility"]["compatible"])
        self.assertFalse(record["compatibility"]["requirements"][0]["available"])

    def test_duplicate_active_manifest_is_rejected_and_revocation_is_durable(self):
        record = self.store.register(self.manifest(), self.registry, registered_by="owner-account")
        with self.assertRaises(ValueError):
            self.store.register(self.manifest(), self.registry, registered_by="owner-account")
        revoked = self.store.revoke(
            record["extension_id"], revoked_by="owner-account", reason="Extension no longer needed."
        )
        self.assertEqual(revoked["state"], "revoked")
        self.assertEqual(self.store.get(record["extension_id"])["state"], "revoked")


if __name__ == "__main__":
    unittest.main()
