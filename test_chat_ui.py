import unittest
from pathlib import Path

from mobile_gateway import mobile_route_allowed


ROOT = Path(__file__).parent
WEB = ROOT / "web"


class ChatUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chat_js = (WEB / "chat.js").read_text(encoding="utf-8")
        cls.chat_css = (WEB / "chat.css").read_text(encoding="utf-8")
        cls.mobile_js = (WEB / "mobile.js").read_text(encoding="utf-8")
        cls.sw = (WEB / "sw.js").read_text(encoding="utf-8")

    def test_chat_is_loaded_as_separate_surface_and_becomes_primary_view(self):
        self.assertIn('/ui/chat.js', self.mobile_js)
        self.assertIn('/ui/chat.css', self.mobile_js)
        self.assertIn('button.textContent="Chat"', self.chat_js)
        self.assertIn('window.showView("chat")', self.chat_js)
        self.assertIn('Forge and repair tools stay behind the scenes until the task needs them.', self.chat_js)

    def test_chat_has_accessible_log_composer_and_history_controls(self):
        self.assertIn('role="log"', self.chat_js)
        self.assertIn('aria-live="polite"', self.chat_js)
        self.assertIn('label for="chat-input"', self.chat_js)
        self.assertIn('New chat', self.chat_js)
        self.assertIn('Archive', self.chat_js)
        self.assertIn('event.key==="Enter"&&!event.shiftKey', self.chat_js)

    def test_chat_displays_local_model_vs_builtin_engine(self):
        self.assertIn('"Local AI"', self.chat_js)
        self.assertIn('"Built-in dialogue"', self.chat_js)
        self.assertIn('Local AI unavailable', self.chat_js)

    def test_chat_is_a_bounded_frame_with_internal_scrolling(self):
        self.assertIn('height:clamp(560px,72dvh,780px)', self.chat_css)
        self.assertIn('grid-template-rows:auto minmax(0,1fr) auto auto', self.chat_css)
        self.assertIn('overscroll-behavior:contain', self.chat_css)
        self.assertIn('overflow-y:auto', self.chat_css)
        self.assertIn('max-height:none', self.chat_css)

    def test_learning_phone_allows_only_exact_personal_chat_routes(self):
        session = "12345678-1234-1234-1234-123456789abc"
        self.assertTrue(mobile_route_allowed("learning", "GET", "/v1/chat/sessions"))
        self.assertTrue(mobile_route_allowed("learning", "POST", "/v1/chat/sessions"))
        self.assertTrue(mobile_route_allowed("learning", "GET", f"/v1/chat/sessions/{session}"))
        self.assertTrue(mobile_route_allowed("learning", "POST", f"/v1/chat/sessions/{session}/messages"))
        self.assertTrue(mobile_route_allowed("learning", "POST", f"/v1/chat/sessions/{session}/archive"))
        self.assertFalse(mobile_route_allowed("learning", "GET", "/v1/chat/sessions/admin"))
        self.assertFalse(mobile_route_allowed("learning", "POST", f"/v1/chat/sessions/{session}/repair"))
        self.assertFalse(mobile_route_allowed("learning", "GET", "/v1/dashboard"))

    def test_pwa_caches_chat_shell_but_never_api_conversation_data(self):
        self.assertIn('/ui/chat.js', self.sw)
        self.assertIn('/ui/chat.css', self.sw)
        self.assertIn('url.pathname.startsWith("/v1/")', self.sw)
        self.assertNotIn('chat_history.json', self.sw)

    def test_mobile_chat_is_phone_first_and_stays_framed(self):
        self.assertIn('@media(max-width:760px)', self.chat_css)
        self.assertIn('env(safe-area-inset-bottom)', self.chat_css)
        self.assertIn('font-size:16px', self.chat_css)
        self.assertIn('position:sticky', self.chat_css)
        self.assertIn('height:calc(100dvh - 126px)', self.chat_css)
        self.assertIn('overflow:hidden', self.chat_css)
        self.assertIn('min-height:0', self.chat_css)


if __name__ == "__main__":
    unittest.main()
