import tempfile
import unittest
from pathlib import Path

from api import SadApiService
from auth import AuthService
from failure_dashboard import FailureDashboard
from student_progress import ProgressStore


class PlatformApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.auth = AuthService(root / "accounts.json")
        self.auth.bootstrap_owner("owner", "StrongOwner123", True)
        self.owner = self.auth.login("owner", "StrongOwner123")
        self.auth.create_account("student", "StrongStudent123", "student", self.owner)
        self.auth.create_account("viewer", "StrongViewer123", "viewer", self.owner)
        self.student = self.auth.login("student", "StrongStudent123")
        self.viewer = self.auth.login("viewer", "StrongViewer123")
        dashboard = FailureDashboard(self.auth, root / "dashboard.json")
        self.service = SadApiService(self.auth, dashboard, ProgressStore(root / "progress.json"))

    @staticmethod
    def headers(token):
        return {"Authorization": f"Bearer {token}"}

    def test_health_advertises_platform_version_without_private_catalog(self):
        status, payload = self.service.dispatch("GET", "/health", {}, {})
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertIn("platform_version", payload)
        self.assertNotIn("modules", payload)
        self.assertNotIn("capabilities", payload)

    def test_platform_discovery_requires_login(self):
        with self.assertRaises(PermissionError):
            self.service.dispatch("GET", "/v1/platform", {}, {})

    def test_owner_manifest_discovers_full_governed_surface(self):
        _, manifest = self.service.dispatch("GET", "/v1/platform", self.headers(self.owner), {})
        module_ids = {module["module_id"] for module in manifest["modules"]}
        self.assertEqual(manifest["role"], "owner")
        self.assertIn("sad.developer", module_ids)
        self.assertIn("sad.accounts", module_ids)
        self.assertFalse(manifest["authority_model"]["platform_metadata_grants_authority"])

    def test_student_manifest_does_not_leak_privileged_capabilities(self):
        _, manifest = self.service.dispatch("GET", "/v1/platform", self.headers(self.student), {})
        rendered = str(manifest)
        self.assertIn("sad.chat", rendered)
        self.assertIn("sad.forge", rendered)
        self.assertNotIn("development:govern", rendered)
        self.assertNotIn("account:manage", rendered)

    def test_viewer_gets_development_view_but_not_work_or_govern(self):
        _, data = self.service.dispatch("GET", "/v1/platform/capabilities", self.headers(self.viewer), {})
        ids = {cap["capability_id"] for cap in data["capabilities"]}
        self.assertIn("development:view", ids)
        self.assertNotIn("development:work", ids)
        self.assertNotIn("development:govern", ids)

    def test_modules_and_capabilities_are_consistent(self):
        _, modules = self.service.dispatch("GET", "/v1/platform/modules", self.headers(self.owner), {})
        _, capabilities = self.service.dispatch("GET", "/v1/platform/capabilities", self.headers(self.owner), {})
        module_caps = {
            cap["capability_id"] for module in modules["modules"] for cap in module["capabilities"]
        }
        catalog_caps = {cap["capability_id"] for cap in capabilities["capabilities"]}
        self.assertEqual(module_caps, catalog_caps)


if __name__ == "__main__":
    unittest.main()
