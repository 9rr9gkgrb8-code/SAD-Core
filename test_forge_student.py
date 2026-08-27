import unittest

from forge_student import StudentProgress, complete_quest, homework_to_quest, next_hint


class ForgeStudentTests(unittest.TestCase):
    def test_homework_becomes_a_quest_without_an_answer(self):
        quest = homework_to_quest("math", "Solve 2x + 4 = 10")
        self.assertEqual(quest.source_type, "homework")
        self.assertEqual(quest.challenges, ["Solve 2x + 4 = 10"])
        self.assertTrue(quest.boss_check)

    def test_hint_ladder_escalates_and_caps(self):
        progress = StudentProgress("student")
        hints = [next_hint(progress, "q") for _ in range(6)]
        self.assertEqual(hints[:4], ["nudge", "stronger_hint", "worked_example", "explanation"])
        self.assertEqual(hints[-1], "explanation")

    def test_xp_requires_mastery_and_boss_check(self):
        quest = homework_to_quest("science", "Explain photosynthesis")
        progress = StudentProgress("student")
        self.assertFalse(complete_quest(progress, quest, .95, False)["mastered"])
        self.assertEqual(progress.xp, 0)
        self.assertTrue(complete_quest(progress, quest, .95, True)["mastered"])
        self.assertEqual(progress.xp, 100)
        self.assertEqual(progress.rank.value, "Apprentice")

    def test_replaying_a_quest_does_not_farm_xp(self):
        quest = homework_to_quest("reading", "Find the theme")
        progress = StudentProgress("student")
        complete_quest(progress, quest, 1, True)
        complete_quest(progress, quest, 1, True)
        self.assertEqual(progress.xp, 100)

    def test_oversized_homework_is_rejected(self):
        with self.assertRaises(ValueError):
            homework_to_quest("math", "x" * 1_000_001)


if __name__ == "__main__":
    unittest.main()
