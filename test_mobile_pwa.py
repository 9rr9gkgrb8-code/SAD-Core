import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parent
WEB = ROOT / "web"


class MobilePwaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (WEB / "index.html").read_text(encoding="utf-8")
        cls.js = (WEB / "mobile.js").read_text(encoding="utf-8")
        cls.app = (WEB / "app.js").read_text(encoding="utf-8")
        cls.css = (WEB / "styles.css").read_text(encoding="utf-8")
        cls.sw = (WEB / "sw.js").read_text(encoding="utf-8")
        cls.manifest = json.loads((WEB / "manifest.webmanifest").read_text(encoding="utf-8"))

    def test_manifest_is_installable_standalone_shell(self):
        self.assertEqual(self.manifest["display"], "standalone")
        self.assertEqual(self.manifest["start_url"], "/")
        self.assertEqual(self.manifest["scope"], "/")
        self.assertTrue(self.manifest["icons"])
        self.assertIn('rel="manifest" href="/manifest.webmanifest"', self.html)
        self.assertIn("apple-mobile-web-app-capable", self.html)

    def test_service_worker_never_caches_api_or_pairing_traffic(self):
        self.assertIn('url.pathname.startsWith("/v1/")', self.sw)
        self.assertIn('url.pathname.startsWith("/mobile/")', self.sw)
        self.assertNotIn("sad_token", self.sw)
        self.assertNotIn("sad_device_token", self.sw)

    def test_phone_requires_pairing_before_login_on_remote_origin(self):
        self.assertIn('id="pairing"', self.html)
        self.assertIn('pattern="[0-9]{8}"', self.html)
        self.assertIn('fetch("/mobile/pair"', self.js)
        self.assertIn('localStorage.setItem("sad_device_token"', self.js)
        self.assertIn('"X-SAD-Device":deviceToken', self.js)
        self.assertIn("ensurePaired", self.app)

    def test_owner_can_manage_pairing_and_revocation(self):
        self.assertIn('id="mobile-pairing-form"', self.html)
        self.assertIn('id="mobile-devices-output"', self.html)
        self.assertIn('/v1/mobile/pairings', self.app)
        self.assertIn('/v1/mobile/devices/', self.app)
        self.assertIn('items.push(["mobile","Mobile Access"])', self.app)

    def test_touch_and_safe_area_rules_exist(self):
        self.assertIn("min-height:44px", self.css)
        self.assertIn("env(safe-area-inset-bottom)", self.css)
        self.assertIn("font-size:16px", self.css)
        self.assertIn("position:sticky", self.css)


if __name__ == "__main__":
    unittest.main()
