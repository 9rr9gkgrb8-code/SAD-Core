import unittest

from forge_career_paths import CAREER_TRACKS, challenge_rules, get_career_track, interview_mix


class ForgeCareerPathTests(unittest.TestCase):
    def test_distinct_cyber_labels_exist(self):
        expected = {"security_foundations", "soc_blue_team", "dfir", "cloud_security", "appsec", "network_security", "governance_risk", "security_engineering"}
        self.assertTrue(expected.issubset(CAREER_TRACKS))
        self.assertEqual(len({CAREER_TRACKS[key].label for key in expected}), len(expected))

    def test_ai_paths_are_distinct(self):
        self.assertEqual(get_career_track("ai_foundations").family, "artificial_intelligence")
        self.assertEqual(get_career_track("ml_engineering").label, "Machine Learning Engineering")
        self.assertEqual(get_career_track("ai_safety_security").label, "AI Safety & Security")

    def test_grade_9_gets_foundational_interview_mix(self):
        mix = interview_mix("software_engineering", 9)
        self.assertIn("leetcode_style", mix)
        self.assertIn("debugging", mix)
        self.assertNotIn("system_design", mix)
        self.assertNotIn("behavioral_star", mix)

    def test_grade_11_adds_system_design(self):
        self.assertIn("system_design", interview_mix("ml_engineering", 11))

    def test_grade_12_adds_behavioral_interview(self):
        self.assertIn("behavioral_star", interview_mix("soc_blue_team", 12))

    def test_cyber_path_gets_defensive_security_scenario(self):
        mix = interview_mix("appsec", 10)
        self.assertIn("security_scenario", mix)
        self.assertIn("code_review", mix)

    def test_invalid_grade_and_track_fail_closed(self):
        with self.assertRaises(ValueError):
            interview_mix("software_engineering", 8)
        with self.assertRaises(ValueError):
            get_career_track("red_team_everything")

    def test_challenge_rules_preserve_safe_and_original_content(self):
        rules = challenge_rules()
        self.assertIn("original", rules["leetcode_style"].lower())
        self.assertIn("authorized", rules["cyber"].lower())
        self.assertIn("not confidential", rules["company_style"].lower())


if __name__ == "__main__":
    unittest.main()
