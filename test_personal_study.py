import unittest

from personal_study import StudyAction, StudyRequest, build_study_plan


class PersonalStudyTests(unittest.TestCase):
    def test_each_requested_study_action_is_supported(self):
        for action in StudyAction:
            kwargs = {"target_word_count": 900} if action == StudyAction.EXPAND_WORD_COUNT else {}
            plan = build_study_plan(StudyRequest(action, "material", **kwargs))
            self.assertEqual(plan.action, action.value)
            self.assertNotIn("three-question", plan.instruction)

    def test_expansion_requires_a_target_and_preserves_voice(self):
        with self.assertRaises(ValueError):
            build_study_plan(StudyRequest(StudyAction.EXPAND_WORD_COUNT, "draft"))
        plan = build_study_plan(StudyRequest(StudyAction.EXPAND_WORD_COUNT, "draft", target_word_count=900, graded=True))
        self.assertIn("Preserve", " ".join(plan.boundaries))
        self.assertIn("submitted work", " ".join(plan.boundaries))

    def test_direct_answer_is_not_replaced_by_a_forced_tutor_loop(self):
        plan = build_study_plan(StudyRequest(StudyAction.DIRECT_ANSWER, "question"))
        self.assertTrue(plan.instruction.startswith("Answer directly"))


if __name__ == "__main__":
    unittest.main()
