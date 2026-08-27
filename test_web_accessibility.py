import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).parent
WEB = ROOT / "web"


class AccessibilityParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.label_depth = 0
        self.html_lang = None
        self.has_viewport = False
        self.unlabeled_controls = []
        self.positive_tabindex = []
        self.roles = {}
        self.live_regions = {}
        self.programmatic_headings = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.html_lang = attrs.get("lang")
        if tag == "meta" and attrs.get("name") == "viewport":
            self.has_viewport = True
        if tag == "label":
            self.label_depth += 1
        if tag in {"input", "select", "textarea"} and attrs.get("type") != "hidden":
            if self.label_depth == 0 and not attrs.get("aria-label") and not attrs.get("aria-labelledby"):
                self.unlabeled_controls.append((tag, attrs.get("name")))
        tabindex = attrs.get("tabindex")
        if tabindex is not None:
            try:
                if int(tabindex) > 0:
                    self.positive_tabindex.append((tag, attrs.get("id"), tabindex))
            except ValueError:
                self.positive_tabindex.append((tag, attrs.get("id"), tabindex))
        element_id = attrs.get("id")
        if element_id and attrs.get("role"):
            self.roles[element_id] = attrs["role"]
        if element_id and attrs.get("aria-live"):
            self.live_regions[element_id] = attrs["aria-live"]
        if tag == "h2" and attrs.get("tabindex") == "-1":
            self.programmatic_headings += 1

    def handle_endtag(self, tag):
        if tag == "label":
            self.label_depth -= 1


class WebAccessibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (WEB / "index.html").read_text(encoding="utf-8")
        cls.css = (WEB / "styles.css").read_text(encoding="utf-8")
        cls.js = (WEB / "app.js").read_text(encoding="utf-8")
        cls.parser = AccessibilityParser()
        cls.parser.feed(cls.html)

    def test_document_language_viewport_and_title_exist(self):
        self.assertEqual(self.parser.html_lang, "en")
        self.assertTrue(self.parser.has_viewport)
        self.assertIn("<title>SAD + Forge Alpha</title>", self.html)

    def test_form_controls_have_accessible_labels(self):
        self.assertEqual(self.parser.unlabeled_controls, [])

    def test_keyboard_order_does_not_use_positive_tabindex(self):
        self.assertEqual(self.parser.positive_tabindex, [])
        self.assertGreaterEqual(self.parser.programmatic_headings, 6)

    def test_errors_status_and_generated_outputs_are_announced(self):
        self.assertEqual(self.parser.roles.get("login-error"), "alert")
        self.assertEqual(self.parser.roles.get("notice"), "status")
        self.assertEqual(self.parser.live_regions.get("study-output"), "polite")
        self.assertEqual(self.parser.live_regions.get("quest-output"), "polite")

    def test_keyboard_focus_is_visibly_preserved(self):
        self.assertIn(":focus-visible", self.css)
        self.assertNotIn("outline:none", self.css.replace(" ", ""))

    def test_dynamic_navigation_exposes_current_view(self):
        self.assertIn('setAttribute("aria-current","page")', self.js)
        self.assertIn('setAttribute("aria-controls",id)', self.js)
        self.assertIn('querySelector("h2")', self.js)

    def test_dynamic_tables_have_captions_and_column_scopes(self):
        self.assertGreaterEqual(self.js.count("<caption>"), 4)
        self.assertGreaterEqual(self.js.count('scope="col"'), 4)


if __name__ == "__main__":
    unittest.main()
