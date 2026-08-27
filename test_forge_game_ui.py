import unittest
from pathlib import Path

from forge_student import RANK_THRESHOLDS


ROOT = Path(__file__).parent
WEB = ROOT / "web"


class ForgeGameUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (WEB / "index.html").read_text(encoding="utf-8")
        cls.css = (WEB / "styles.css").read_text(encoding="utf-8")
        cls.js = (WEB / "app.js").read_text(encoding="utf-8")

    def test_game_surface_keeps_real_quest_workflow_controls(self):
        for element_id in (
            "progress",
            "quest-form",
            "active-quest",
            "quest-output",
            "hint",
            "hint-ladder",
            "quest-actions",
            "complete-form",
            "boss-prompt",
            "companion-orb",
        ):
            self.assertIn(f'id="{element_id}"', self.html)

    def test_frontend_rank_thresholds_match_backend_contract(self):
        for threshold, rank in RANK_THRESHOLDS:
            self.assertIn(f'["{rank.value}",{threshold}]', self.js)

    def test_game_ui_uses_persisted_progress_fields(self):
        for field in ("xp", "rank", "completed_quests", "companion_stage"):
            self.assertIn(field, self.js)
        self.assertIn('/v1/forge/progress', self.js)
        self.assertIn('/v1/forge/quests', self.js)
        self.assertIn('/v1/forge/hint', self.js)
        self.assertIn('/v1/forge/complete', self.js)

    def test_hint_ladder_matches_backend_levels(self):
        for level in ("nudge", "stronger_hint", "worked_example", "explanation"):
            self.assertIn(level, self.js)
            self.assertIn(f'data-level="{level}"', self.html)

    def test_game_surface_remains_responsive_and_focus_visible(self):
        self.assertIn(".forge-layout", self.css)
        self.assertIn("@media(max-width:800px)", self.css)
        self.assertIn(":focus-visible", self.css)


if __name__ == "__main__":
    unittest.main()
