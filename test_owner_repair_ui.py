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

    def test_owner_must_see_exact_tested_change_before_final_choice(self):
        self.assertIn('Review exact tested code change', self.js)
        self.assertIn('artifact.kind === "diff"', self.js)
        self.assertIn('diffArtifact?.content?.patch', self.js)

    def test_final_owner_choice_is_apply_or_reject_and_closes(self):
        self.assertIn('YES: Apply tested repair', self.js)
        self.assertIn('NO: Reject repair', self.js)
        self.assertIn('/decision', self.js)
        self.assertIn('/close', self.js)
        self.assertIn('exact tested patch', self.js)

    def test_failed_verification_cannot_be_approved_from_simple_owner_flow(self):
        self.assertIn('job.result?.state === "succeeded"', self.js)
        self.assertIn('disabled title=', self.js)

    def test_owner_surface_preserves_git_boundary(self):
        self.assertIn('no Git commit, push, or merge authority', self.js)
        self.assertIn('Git was not committed, pushed, or merged.', self.js)

    def test_non_owner_dashboard_keeps_existing_loader(self):
        self.assertIn('const legacyLoadDashboard = loadDashboard', self.js)
        self.assertIn('return legacyLoadDashboard()', self.js)

    def test_mobile_decision_controls_reflow(self):
        self.assertIn('.owner-decision', self.css)
        self.assertIn('@media(max-width:600px)', self.css)


if __name__ == "__main__":
    unittest.main()
