import unittest

from forge_skill_tree import available_branches, boss_test, branch_nodes, get_skill_tree, require_prerequisites, unlocked_nodes


class ForgeSkillTreeTests(unittest.TestCase):
    def test_three_root_skill_trees_exist(self):
        for root in ("artificial_intelligence", "cybersecurity", "technology"):
            tree = get_skill_tree(root)
            self.assertTrue(tree["trunk"])
            self.assertTrue(tree["branches"])

    def test_ai_root_branches_into_specialties(self):
        branches = available_branches("artificial_intelligence")
        self.assertIn("ml_engineering", branches)
        self.assertIn("ai_application_engineering", branches)
        self.assertIn("ai_safety_security", branches)

    def test_cyber_root_branches_into_specialties(self):
        branches = available_branches("cybersecurity")
        self.assertIn("soc_blue_team", branches)
        self.assertIn("dfir", branches)
        self.assertIn("appsec", branches)
        self.assertIn("cloud_security", branches)

    def test_each_branch_builds_toward_one_interview_boss(self):
        for root in ("artificial_intelligence", "cybersecurity", "technology"):
            for branch in available_branches(root):
                with self.subTest(root=root, branch=branch):
                    nodes = branch_nodes(root, branch)
                    self.assertGreaterEqual(len(nodes), 2)
                    boss = boss_test(root, branch)
                    self.assertEqual(boss.level, 5)
                    self.assertTrue(boss.boss_test)
                    self.assertTrue(boss.prerequisites)

    def test_software_boss_contains_realistic_hiring_categories(self):
        boss = boss_test("technology", "software_engineering")
        self.assertIn("leetcode_style", boss.challenge_types)
        self.assertIn("debugging", boss.challenge_types)
        self.assertIn("code_review", boss.challenge_types)
        self.assertIn("system_design", boss.challenge_types)

    def test_cyber_boss_remains_defensive(self):
        boss = boss_test("cybersecurity", "soc_blue_team")
        self.assertIn("security_scenario", boss.challenge_types)
        self.assertIn("synthetic", boss.boss_test.lower())

    def test_unknown_paths_fail_closed(self):
        with self.assertRaises(ValueError):
            get_skill_tree("magic")
        with self.assertRaises(ValueError):
            branch_nodes("cybersecurity", "attack_everything")

    def test_declared_prerequisites_are_enforced(self):
        boss = boss_test("technology", "software_engineering")
        with self.assertRaises(PermissionError):
            require_prerequisites(boss, ())
        self.assertIs(require_prerequisites(boss, ("swe_design",)), boss)
        unlocked = unlocked_nodes("technology", "software_engineering", ("tech_computing",))
        self.assertIn("tech_code", {node.node_id for node in unlocked})
        self.assertNotIn("swe_boss", {node.node_id for node in unlocked})


if __name__ == "__main__":
    unittest.main()
