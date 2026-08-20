"""Automated checks for Sasha's conversational response layer."""

import unittest

from personality import (
    detect_conversation_topic,
    detect_topic_detail,
    get_contextual_follow_up,
    get_response,
)


class PersonalityTests(unittest.TestCase):
    def test_warm_greeting_uses_the_saved_name(self):
        response = get_response("hello", 1, "Kenneth")
        self.assertIn("Kenneth", response)
        self.assertTrue("How are you" in response or "How has your day" in response)

    def test_stressed_message_gets_a_supportive_follow_up(self):
        response = get_response("I feel stressed", 1, "Kenneth")
        self.assertTrue(
            any(
                phrase in response.lower()
                for phrase in [
                    "one piece at a time",
                    "most urgent",
                    "untangle first",
                ]
            )
        )

    def test_capability_question_has_a_clear_answer(self):
        response = get_response("What can you do?", 1, "Kenneth")
        self.assertTrue(
            "talk things through" in response or "keep you company" in response
        )

    def test_work_follow_up_remembers_a_stress_topic(self):
        topic = detect_conversation_topic("I feel stressed")
        response = get_contextual_follow_up("My job", 1, "Kenneth", topic)
        self.assertIn("work", response.lower())

    def test_work_detail_stays_in_session_context(self):
        topic = detect_conversation_topic("I feel stressed")
        detail = detect_topic_detail("My job", topic)
        response = get_contextual_follow_up(
            "The deadlines keep changing.", 1, "Kenneth", topic, detail
        )
        self.assertIn("deadline", response.lower())


if __name__ == "__main__":
    unittest.main()
