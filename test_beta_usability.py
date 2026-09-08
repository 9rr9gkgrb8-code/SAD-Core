import unittest
from pathlib import Path


ROOT = Path(__file__).parent


class BetaUsabilityTests(unittest.TestCase):
    def test_owner_has_plain_language_system_status(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="system"', html)
        self.assertIn('System Status', script)
        self.assertIn('/v1/system/readiness', script)

    def test_reviewer_is_not_offered_owner_decision_buttons(self):
        script = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn('account.role==="owner"', script)
        self.assertIn('Review evidence; Owner decision required', script)


if __name__ == "__main__":
    unittest.main()
