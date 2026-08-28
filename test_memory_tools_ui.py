import unittest
from pathlib import Path


ROOT = Path(__file__).parent
WEB = ROOT / "web"


class MemoryToolsUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = (WEB / "memory_tools.js").read_text(encoding="utf-8")
        cls.css = (WEB / "memory_tools.css").read_text(encoding="utf-8")
        cls.mobile = (WEB / "mobile.js").read_text(encoding="utf-8")
        cls.sw = (WEB / "sw.js").read_text(encoding="utf-8")

    def test_memory_tools_surface_is_loaded(self):
        self.assertIn('/ui/memory_tools.js', self.mobile)
        self.assertIn('/ui/memory_tools.css', self.mobile)
        self.assertIn('button.textContent="Memory & Tools"', self.js)
        self.assertIn('/v1/memory', self.js)
        self.assertIn('/v1/tools/actions', self.js)

    def test_memory_ui_is_explicit_and_user_controlled(self):
        self.assertIn('Use in Local AI context', self.js)
        self.assertIn('Memory saved explicitly.', self.js)
        self.assertIn('memory-delete', self.js)
        self.assertIn('memory-toggle', self.js)
        self.assertNotIn('autoSave', self.js)

    def test_tool_ui_preserves_approval_before_mutation(self):
        self.assertIn('awaiting_approval', self.js)
        self.assertIn('data-decision="approve"', self.js)
        self.assertIn('/decision', self.js)
        self.assertIn('/execute', self.js)
        self.assertIn('No shell, dynamic plugin, arbitrary network, or Git execution.', self.js)

    def test_pwa_caches_shell_but_not_memory_or_tool_api(self):
        self.assertIn('/ui/memory_tools.js', self.sw)
        self.assertIn('/ui/memory_tools.css', self.sw)
        self.assertIn('url.pathname.startsWith("/v1/")', self.sw)
        self.assertNotIn('/v1/memory', self.sw)
        self.assertNotIn('/v1/tools', self.sw)

    def test_phone_layout_and_touch_targets_exist(self):
        self.assertIn('@media(max-width:600px)', self.css)
        self.assertIn('min-height:44px', self.css)
        self.assertIn('font-size:1rem', self.css)


if __name__ == "__main__":
    unittest.main()
