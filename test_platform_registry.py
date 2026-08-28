import unittest

from auth import ROLE_PERMISSIONS
from platform_registry import BUILTIN_MODULES, PLATFORM_SCHEMA_VERSION, PLATFORM_VERSION, PlatformRegistry


class PlatformRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = PlatformRegistry()

    def test_builtin_registry_is_versioned_and_unique(self):
        self.assertEqual(PLATFORM_SCHEMA_VERSION, 3)
        self.assertEqual(PLATFORM_VERSION, "0.3-alpha")
        module_ids = [module.module_id for module in BUILTIN_MODULES]
        capability_ids = [cap.capability_id for module in BUILTIN_MODULES for cap in module.capabilities]
        self.assertEqual(len(module_ids), len(set(module_ids)))
        self.assertEqual(len(capability_ids), len(set(capability_ids)))
        self.assertIn("sad.platform", module_ids)
        self.assertIn("sad.chat", module_ids)
        self.assertIn("sad.voice", module_ids)
        self.assertIn("sad.memory", module_ids)
        self.assertIn("sad.tools", module_ids)
        self.assertIn("sad.developer", module_ids)

    def test_student_catalog_exposes_personal_platform_not_development(self):
        manifest = self.registry.manifest("student", ROLE_PERMISSIONS["student"])
        module_ids = {module["module_id"] for module in manifest["modules"]}
        capability_ids = {
            cap["capability_id"] for module in manifest["modules"] for cap in module["capabilities"]
        }
        for module in ("sad.platform", "sad.chat", "sad.voice", "sad.memory", "sad.tools", "sad.study", "sad.forge"):
            self.assertIn(module, module_ids)
        self.assertNotIn("sad.developer", module_ids)
        self.assertNotIn("sad.accounts", module_ids)
        self.assertIn("voice:conversation", capability_ids)
        self.assertIn("memory:own", capability_ids)
        self.assertIn("tools:catalog", capability_ids)
        self.assertIn("tools:actions", capability_ids)
        self.assertNotIn("development:govern", capability_ids)
        self.assertNotIn("platform:clients", capability_ids)

    def test_owner_catalog_includes_platform_management_and_governance(self):
        manifest = self.registry.manifest("owner", ROLE_PERMISSIONS["owner"])
        capability_ids = {
            cap["capability_id"] for module in manifest["modules"] for cap in module["capabilities"]
        }
        self.assertIn("platform:clients", capability_ids)
        self.assertIn("platform:events", capability_ids)
        self.assertIn("development:govern", capability_ids)
        govern = next(cap for cap in self.registry.catalog(ROLE_PERMISSIONS["owner"]) if cap["capability_id"] == "development:govern")
        self.assertTrue(govern["human_approval_boundary"])
        self.assertTrue(govern["mutates_state"])
        self.assertEqual(govern["capability_version"], "1.0.0")
        self.assertEqual(govern["lifecycle"], "alpha")

    def test_compatibility_reports_missing_and_versions(self):
        student_allowed = self.registry.allowed_capability_ids(ROLE_PERMISSIONS["student"])
        result = self.registry.compatibility([
            {"capability_id": "voice:conversation", "min_version": "1.0.0"},
            {"capability_id": "memory:own", "min_version": "1.0.0"},
            {"capability_id": "development:govern", "min_version": "1.0.0"},
        ], student_allowed)
        self.assertFalse(result["compatible"])
        self.assertTrue(result["requirements"][0]["compatible"])
        self.assertTrue(result["requirements"][1]["compatible"])
        self.assertFalse(result["requirements"][2]["available"])
        with self.assertRaises(ValueError):
            self.registry.compatibility([{"capability_id": "voice:conversation", "min_version": "banana"}], student_allowed)

    def test_platform_metadata_explicitly_grants_no_authority(self):
        manifest = self.registry.manifest("owner", ROLE_PERMISSIONS["owner"])
        self.assertFalse(manifest["authority_model"]["platform_metadata_grants_authority"])
        self.assertFalse(manifest["authority_model"]["dynamic_extension_execution"])
        self.assertEqual(manifest["authority_model"]["tool_execution"], "registered_internal_tools_only")
        self.assertEqual(manifest["authority_model"]["memory_model"], "explicit_user_controlled")
        self.assertEqual(manifest["authority_model"]["git_authority"], "human_host_only")

    def test_invalid_duplicate_capability_fails_closed(self):
        with self.assertRaises(ValueError):
            PlatformRegistry((BUILTIN_MODULES[0], BUILTIN_MODULES[0]))


if __name__ == "__main__":
    unittest.main()
