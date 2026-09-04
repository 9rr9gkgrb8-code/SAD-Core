"""Static release checks for the Forge private-alpha cloud/mobile surface."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class CloudMobileReadyTests(unittest.TestCase):
    def test_cloud_proxy_keeps_core_loopback_only(self):
        caddy = (ROOT / "deploy" / "Caddyfile.example").read_text(encoding="utf-8")
        self.assertIn("reverse_proxy 127.0.0.1:8765", caddy)
        self.assertIn("header_up Host 127.0.0.1:8765", caddy)
        self.assertIn("header_up Origin http://127.0.0.1:8765", caddy)
        self.assertNotIn("reverse_proxy 0.0.0.0", caddy)

    def test_mobile_styles_are_loaded_after_shared_styles(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        shared = html.index('/ui/styles.css')
        mobile = html.index('/ui/mobile-cloud.css')
        self.assertLess(shared, mobile)

    def test_mobile_shell_has_safe_area_and_thumb_navigation(self):
        css = (ROOT / "web" / "mobile-cloud.css").read_text(encoding="utf-8")
        self.assertIn("env(safe-area-inset-bottom)", css)
        self.assertIn("position: fixed", css)
        self.assertIn("bottom: 0", css)
        self.assertIn("min-height: 48px", css)


if __name__ == "__main__":
    unittest.main()
