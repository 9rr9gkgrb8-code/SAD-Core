import unittest

from forge_high_school import (
    HINT_POLICY,
    build_high_school_plan,
    high_school_homework_to_quest,
    verify_high_school_completion,
)


class ForgeHighSchoolTests(unittest.TestCase):
    def test_each_supported_grade_has_grade_specific_rigor(self):
        expected = {
            9: "guided high-school foundation",
            10: "intermediate high-school application",
            11: "upper high-school analysis",
            12: "college-readiness synthesis",
        }
        for grade, rigor in expected.items():
            with self.subTest(grade=grade):
                self.assertEqual(build_high_school_plan(grade, "math").rigor, rigor)

    def test_core_subject_tracks_are_available_for_all_high_school_grades(self):
        for grade in (9, 10, 11, 12):
            for subject in ("math", "science", "english", "history"):
                with self.subTest(grade=grade, subject=subject):
                    plan = build_high_school_plan(grade, subject)
                    self.assertEqual(plan.grade, grade)
                    self.assertTrue(plan.tracks)
                    self.assertEqual(plan.tutoring_mode, "method_first_then_mastery")

    def test_aliases_are_normalized(self):
        self.assertEqual(build_high_school_plan(10, "ELA").subject, "english")
        self.assertEqual(build_high_school_plan(11, "social studies").subject, "history")

    def test_method_first_hint_policy_delays_full_explanation(self):
        self.assertEqual(HINT_POLICY[0], "diagnostic_question")
        self.assertIn("worked_example", HINT_POLICY)
        self.assertEqual(HINT_POLICY[-1], "full_explanation")

    def test_math_science_history_require_verification(self):
        for subject in ("math", "science", "history"):
            self.assertTrue(build_high_school_plan(12, subject).verification_required)
        self.assertFalse(build_high_school_plan(12, "english").verification_required)

    def test_homework_conversion_preserves_original_assignment_without_solving(self):
        payload = high_school_homework_to_quest(
            9,
            "math",
            "Solve 3x - 7 = 11 and explain each step.",
        )
        self.assertEqual(
            payload["quest"]["challenges"],
            ["Solve 3x - 7 = 11 and explain each step."],
        )
        self.assertEqual(payload["curriculum"]["grade"], 9)
        self.assertTrue(payload["teaching_contract"]["teach_method_before_final_answer"])
        self.assertTrue(payload["teaching_contract"]["require_transfer_mastery_check"])

    def test_out_of_range_grades_fail_closed(self):
        for grade in (8, 13, True, "9"):
            with self.subTest(grade=grade):
                with self.assertRaises(ValueError):
                    build_high_school_plan(grade, "math")

    def test_unknown_subject_fails_closed(self):
        with self.assertRaises(ValueError):
            build_high_school_plan(10, "astrology")

    def test_completion_enforces_teaching_and_verification_evidence(self):
        bundle = high_school_homework_to_quest(10, "math", "Solve x")
        with self.assertRaises(PermissionError):
            verify_high_school_completion(bundle, {"student_attempt": True})
        evidence = {
            "student_attempt": True,
            "method_explanation": True,
            "transfer_mastery_passed": True,
            "source_or_work_verified": True,
        }
        self.assertTrue(verify_high_school_completion(bundle, evidence))


if __name__ == "__main__":
    unittest.main()
