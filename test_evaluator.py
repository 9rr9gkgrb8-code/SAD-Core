"""Automated checks for SAD's controlled self-correction records."""

import tempfile
import unittest
from pathlib import Path

import evaluator


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_failures_file = evaluator.FAILURES_FILE
        evaluator.FAILURES_FILE = Path(self.temp_directory.name) / "failures.json"

    def tearDown(self):
        evaluator.FAILURES_FILE = self.original_failures_file
        self.temp_directory.cleanup()

    def test_report_can_be_approved_by_a_human(self):
        record = evaluator.report_failure(
            "SAD gave an incorrect answer.",
            "The answer should be checked before responding.",
        )

        self.assertEqual(record["fix_status"], "pending_human_approval")
        self.assertEqual(len(evaluator.load_failure_records()), 1)

        approved_record = evaluator.approve_failure(record["failure_id"])

        self.assertEqual(approved_record["fix_status"], "approved_by_human")
        self.assertIn("approved_at", approved_record)
        self.assertEqual(
            evaluator.get_approved_failure(record["failure_id"]), approved_record
        )

    def test_repair_summary_groups_failure_evidence(self):
        first = evaluator.report_failure(
            "The local model is not turning on.",
            "Check the local model connection.",
        )
        second = evaluator.report_failure(
            "The local model response repeats itself.",
            "Review the response behavior.",
        )
        evaluator.approve_failure(first["failure_id"])

        summary = evaluator.build_repair_summary()

        self.assertEqual(summary[0]["category"], "local_model")
        self.assertEqual(summary[0]["count"], 2)
        self.assertEqual(summary[0]["approved_count"], 1)
        self.assertIn("connection", summary[0]["recommended_next_step"])

    def test_repair_candidates_require_two_human_approvals(self):
        first = evaluator.report_failure(
            "The local model is not turning on.",
            "Check the local model connection.",
        )
        second = evaluator.report_failure(
            "Ollama local model is not responding.",
            "Check the local model connection.",
        )
        evaluator.approve_failure(first["failure_id"])

        self.assertEqual(evaluator.find_repair_candidates(), [])

        evaluator.approve_failure(second["failure_id"])
        candidates = evaluator.find_repair_candidates()

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["category"], "local_model")
        self.assertEqual(candidates[0]["approved_count"], 2)

    def test_repair_plan_is_sandbox_only_and_evidence_based(self):
        first = evaluator.report_failure(
            "The local model is not turning on.",
            "Check the local model connection.",
        )
        second = evaluator.report_failure(
            "Ollama local model is not responding.",
            "Check the local model connection.",
        )
        evaluator.approve_failure(first["failure_id"])
        evaluator.approve_failure(second["failure_id"])

        plans = evaluator.build_repair_plans()

        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]["category"], "local_model")
        self.assertIn("model_adapter.py", plans[0]["target_areas"])
        self.assertIn("sandbox", plans[0]["plan"].lower())
        self.assertIn("human", plans[0]["safeguard"].lower())


if __name__ == "__main__":
    unittest.main()
