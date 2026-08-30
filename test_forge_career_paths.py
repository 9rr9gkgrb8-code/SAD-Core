import unittest

from forge_career_paths import (
    CAREER_TRACKS,
    backtrack_path,
    challenge_rules,
    get_career_track,
    interview_mix,
    level_label,
    specialties,
    switch_path,
)


class ForgeCareerPathTests(unittest.TestCase):
    def test_distinct_cyber_labels_exist(self):
        expected = {"security_foundations", "soc_blue_team", "dfir", "cloud_security", "appsec", "network_security", "governance_risk", "security_engineering"}
        self.assertTrue(expected.issubset(CAREER_TRACKS))
        self.assertEqual(len({CAREER_TRACKS[key].label for key in expected}), len(expected))

    def test_ai_paths_are_distinct(self):
        self.assertEqual(get_career_track("ai_foundations").family, "artificial_intelligence")
        self.assertEqual(get_career_track("ml_engineering").label, "Machine Learning Engineering")
        self.assertEqual(get_career_track("ai_safety_security").label, "AI Safety & Security")

    def test_levels_replace_school_grade_gates(self):
        self.assertEqual(level_label(1), "Explorer")
        self.assertEqual(level_label(5), "Career Ready")
        with self.assertRaises(ValueError):
            level_label(6)

    def test_cyber_root_diverges_into_specialties(self):
        labels = {track.label for track in specialties("cybersecurity")}
        self.assertIn("SOC / Blue Team", labels)
        self.assertIn("Application Security", labels)
        self.assertIn("DFIR / Incident Response", labels)

    def test_level_progression_adds_interview_complexity(self):
        level_one = interview_mix("software_engineering", 1)
        level_three = interview_mix("software_engineering", 3)
        level_five = interview_mix("software_engineering", 5)
        self.assertNotIn("leetcode_style", level_one)
        self.assertIn("leetcode_style", level_three)
        self.assertIn("code_review", level_three)
        self.assertIn("system_design", level_five)
        self.assertIn("behavioral_star", level_five)

    def test_cyber_path_gets_defensive_security_scenario(self):
        self.assertIn("security_scenario", interview_mix("appsec", 2))

    def test_switching_paths_preserves_mastery(self):
        progress = {"active_track": "soc_blue_team", "track_mastery": {"soc_blue_team": 0.8}}
        switch_path(progress, "appsec")
        self.assertEqual(progress["active_track"], "appsec")
        self.assertEqual(progress["track_mastery"]["soc_blue_team"], 0.8)
        self.assertEqual(progress["path_history"], ["soc_blue_team"])

    def test_backtrack_returns_to_previous_specialty_without_loss(self):
        progress = {"active_track": "soc_blue_team", "track_mastery": {"soc_blue_team": 0.8}}
        switch_path(progress, "appsec")
        progress["track_mastery"]["appsec"] = 0.5
        backtrack_path(progress)
        self.assertEqual(progress["active_track"], "soc_blue_team")
        self.assertEqual(progress["track_mastery"]["appsec"], 0.5)
        self.assertEqual(progress["track_mastery"]["soc_blue_team"], 0.8)

    def test_invalid_track_and_family_fail_closed(self):
        with self.assertRaises(ValueError):
            get_career_track("red_team_everything")
        with self.assertRaises(ValueError):
            specialties("unknown")

    def test_challenge_rules_preserve_safe_original_and_free_paths(self):
        rules = challenge_rules()
        self.assertIn("original", rules["leetcode_style"].lower())
        self.assertIn("authorized", rules["cyber"].lower())
        self.assertIn("not confidential", rules["company_style"].lower())
        self.assertIn("backtrack", rules["path_freedom"].lower())


if __name__ == "__main__":
    unittest.main()
