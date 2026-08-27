import unittest
from pathlib import Path


ROOT = Path(__file__).parent
WEB = ROOT / "web"


class OwnerRepairUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (WEB / "index.html").read_text(encoding="utf-8")
        cls.js = (WEB / "owner_dashboard.js").read_text(encoding="utf-8")
        cls.css = (WEB / "owner_dashboard.css").read_text(encoding="utf-8")

    def test_owner_dashboard_assets_are_loaded(self):
        self.assertIn('/ui/owner_dashboard.css', self.html)
        self.assertIn('/ui/owner_dashboard.js', self.html)

    def test_one_click_prepare_uses_existing_governed_pipeline(self):
        for fragment in (
            '/review',
            '/push',
            '/approve-isolated',
            '/execute',
        ):
            self.assertIn(fragment, self.js)
        self.assertIn('approved: true', self.js)
        self.assertIn('source_snapshot: "owner-ui"', self.js)

    def test_final_owner_choice_is_yes_or_no_and_closes(self):
        self.assertIn('YES: Approve repair', self.js)
        self.assertIn('NO: Reject repair', self.js)
        self.assertIn('/decision', self.js)
        self.assertIn('/close', self.js)

    def test_failed_verification_cannot_be_approved_from_simple_owner_flow(self):
        self.assertIn('job.result?.state === "succeeded"', self.js)
        self.assertIn('disabled title=', self.js)

    def test_owner_surface_does_not_claim_live_merge(self):
        self.assertIn('does not auto-merge', self.js)
        self.assertIn('No live-code merge was performed.', self.js)

    def test_non_owner_dashboard_keeps_existing_loader(self):
        self.assertIn('const legacyLoadDashboard = loadDashboard', self.js)
        self.assertIn('return legacyLoadDashboard()', self.js)

    def test_mobile_decision_controls_reflow(self):
        self.assertIn('.owner-decision', self.css)
        self.assertIn('@media(max-width:600px)', self.css)


if __name__ == "__main__":
    unittest.main()
