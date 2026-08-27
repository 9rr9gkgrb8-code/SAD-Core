import unittest
from pathlib import Path

from mobile_gateway import mobile_route_allowed


ROOT = Path(__file__).parent
WEB = ROOT / "web"


class DeveloperWorkspaceUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = (WEB / "developer_workspace.js").read_text(encoding="utf-8")
        cls.css = (WEB / "developer_workspace.css").read_text(encoding="utf-8")
        cls.mobile = (WEB / "mobile.js").read_text(encoding="utf-8")
        cls.sw = (WEB / "sw.js").read_text(encoding="utf-8")

    def test_code_workspace_is_loaded_as_a_separate_surface(self):
        self.assertIn('loadSurface("developer_workspace")', self.mobile)
        self.assertIn('button.textContent="Code Workspace"', self.js)
        self.assertIn('Build in isolation', self.js)
        self.assertIn('Plan file scope', self.js)

    def test_human_scope_then_tested_diff_then_owner_apply_is_visible(self):
        self.assertIn('/v1/dev/workspaces/scope', self.js)
        self.assertIn('Create isolated workspace', self.js)
        self.assertIn('Generate code + run Docker tests', self.js)
        self.assertIn('Exact tested diff', self.js)
        self.assertIn('YES: Apply tested workspace', self.js)
        self.assertIn('Rollback applied workspace', self.js)
        self.assertIn('Git was not changed', self.js)

    def test_learning_phone_cannot_reach_code_workspace_routes(self):
        self.assertFalse(mobile_route_allowed("learning", "GET", "/v1/dev/workspaces"))
        self.assertFalse(mobile_route_allowed("learning", "POST", "/v1/dev/workspaces"))
        self.assertFalse(mobile_route_allowed("learning", "POST", "/v1/dev/workspaces/scope"))
        self.assertTrue(mobile_route_allowed("full_role", "GET", "/v1/dev/workspaces"))

    def test_service_worker_caches_only_workspace_shell_not_api_data(self):
        self.assertIn('/ui/developer_workspace.js', self.sw)
        self.assertIn('/ui/developer_workspace.css', self.sw)
        self.assertIn('url.pathname.startsWith("/v1/")', self.sw)
        self.assertNotIn('.sad_dev', self.sw)

    def test_code_workspace_has_phone_layout_and_accessible_status(self):
        self.assertIn('@media(max-width:600px)', self.css)
        self.assertIn('role="status"', self.js)
        self.assertIn('aria-live="polite"', self.js)
        self.assertIn('aria-label="Developer workspaces"', self.js)


if __name__ == "__main__":
    unittest.main()
