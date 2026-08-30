import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from memory_store import MemoryStore


# Regression coverage for bounded, observable memory retrieval.
class MemoryContextPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = MemoryStore(
            Path(self.temp.name) / "memory.json",
            now=lambda: datetime(2026, 8, 30, 16, 0, tzinfo=timezone.utc),
        )

    def test_context_plan_promotes_strong_matches_and_exposes_trace(self):
        project = self.store.create(
            "a",
            "project",
            "SAD memory architecture",
            "Build local first memory retrieval with observable context selection and validation.",
        )
        self.store.create("a", "preference", "Writing style", "Keep answers concise and direct.")

        plan = self.store.context_plan("a", "SAD memory retrieval validation", budget_chars=2000)

        self.assertEqual(plan["trace"][0]["memory_id"], project["memory_id"])
        self.assertEqual(plan["trace"][0]["level"], "full")
        self.assertTrue(plan["trace"][0]["selected"])
        self.assertIn("strong relevance", plan["trace"][0]["reason"])
        self.assertTrue(any("observable context selection" in item for item in plan["context"]))

    def test_context_plan_respects_account_enabled_state_and_expiry(self):
        self.store.create("a", "goal", "Visible", "Ship SAD alpha", enabled=True)
        self.store.create("a", "note", "Disabled", "Never inject me", enabled=False)
        self.store.create("b", "project", "Other account", "Private to another account")

        plan = self.store.context_plan("a", "ship alpha", budget_chars=1000)
        rendered = "\n".join(plan["context"])

        self.assertIn("Visible", rendered)
        self.assertNotIn("Disabled", rendered)
        self.assertNotIn("Other account", rendered)

    def test_budget_downgrades_detail_instead_of_overflowing(self):
        self.store.create(
            "a",
            "project",
            "SAD validation",
            "validation " + ("detail " * 200),
        )

        plan = self.store.context_plan("a", "SAD validation", budget_chars=300)

        self.assertLessEqual(plan["used_chars"], 300)
        self.assertEqual(plan["trace"][0]["level"], "overview")
        self.assertIn("downgraded", plan["trace"][0]["reason"])

    def test_invalid_context_budget_fails_closed(self):
        with self.assertRaises(ValueError):
            self.store.context_plan("a", "query", budget_chars=199)
        with self.assertRaises(ValueError):
            self.store.context_plan("a", "query", budget_chars=50001)


if __name__ == "__main__":
    unittest.main()
