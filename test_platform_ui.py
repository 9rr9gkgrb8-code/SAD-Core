import unittest
from pathlib import Path


ROOT = Path(__file__).parent
WEB = ROOT / "web"


class PlatformUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.platform_js = (WEB / "platform.js").read_text(encoding="utf-8")
        cls.platform_css = (WEB / "platform.css").read_text(encoding="utf-8")
        cls.mobile_js = (WEB / "mobile.js").read_text(encoding="utf-8")
        cls.sw = (WEB / "sw.js").read_text(encoding="utf-8")

    def test_platform_surface_is_loaded_and_read_only(self):
        self.assertIn('/ui/platform.js', self.mobile_js)
        self.assertIn('/ui/platform.css', self.mobile_js)
        self.assertIn('button.textContent="SAD Platform"', self.platform_js)
        self.assertIn('apiCall("/v1/platform")', self.platform_js)
        self.assertNotIn('method:"POST"', self.platform_js)

    def test_platform_ui_describes_authority_boundary(self):
        self.assertIn('Platform discovery is descriptive only', self.platform_js)
        self.assertIn('never grants permissions', self.platform_js)
        self.assertIn('human approval', self.platform_js)

    def test_platform_nav_is_limited_to_development_roles(self):
        self.assertIn('["owner","developer","reviewer","viewer"]', self.platform_js)
        self.assertNotIn('["student"', self.platform_js)

    def test_platform_ui_is_responsive_and_accessible(self):
        self.assertIn('tabindex="-1"', self.platform_js)
        self.assertIn('role="status"', self.platform_js)
        self.assertIn('aria-live="polite"', self.platform_js)
        self.assertIn('@media(max-width:850px)', self.platform_css)
        self.assertIn('min-height:44px', self.platform_css)

    def test_pwa_caches_platform_shell_but_not_platform_api(self):
        self.assertIn('/ui/platform.js', self.sw)
        self.assertIn('/ui/platform.css', self.sw)
        self.assertIn('url.pathname.startsWith("/v1/")', self.sw)
        self.assertNotIn('/v1/platform', self.sw)


if __name__ == "__main__":
    unittest.main()
