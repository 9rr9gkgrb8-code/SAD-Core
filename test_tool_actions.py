import tempfile
import unittest
from pathlib import Path

from memory_store import MemoryStore
from platform_registry import PlatformRegistry
from tool_actions import ToolActionStore


class ToolActionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.memory = MemoryStore(Path(self.temp.name) / "memory.json")
        self.store = ToolActionStore(
            Path(self.temp.name) / "tool_actions.json",
            memory=self.memory,
            platform=PlatformRegistry(),
        )
        self.account = {"account_id": "a", "role": "student"}
        self.permissions = {"study:personal", "forge:play", "progress:own"}

    def test_read_only_tool_is_ready_and_executes(self):
        action = self.store.create("a", self.permissions, "platform.status", {})
        self.assertEqual(action["state"], "ready")
        result = self.store.execute(self.account, self.permissions, action["action_id"])
        self.assertEqual(result["state"], "completed")
        self.assertEqual(result["output"]["product"], "SAD")

    def test_mutating_memory_tool_requires_explicit_approval(self):
        action = self.store.create("a", self.permissions, "memory.remember", {
            "category": "goal", "title": "Goal", "content": "Ship Tier 3"
        })
        self.assertEqual(action["state"], "awaiting_approval")
        with self.assertRaises(PermissionError):
            self.store.execute(self.account, self.permissions, action["action_id"])
        approved = self.store.decide("a", action["action_id"], "approve")
        self.assertEqual(approved["state"], "ready")
        completed = self.store.execute(self.account, self.permissions, action["action_id"])
        self.assertEqual(completed["state"], "completed")
        self.assertEqual(self.memory.list("a")[0]["content"], "Ship Tier 3")

    def test_rejection_and_cross_account_access_fail_closed(self):
        action = self.store.create("a", self.permissions, "memory.remember", {
            "category": "note", "title": "No", "content": "Reject this"
        })
        rejected = self.store.decide("a", action["action_id"], "reject")
        self.assertEqual(rejected["state"], "rejected")
        with self.assertRaises(PermissionError):
            self.store.execute(self.account, self.permissions, action["action_id"])
        with self.assertRaises(KeyError):
            self.store.get("b", action["action_id"])
        with self.assertRaises(KeyError):
            self.store.decide("b", action["action_id"], "approve")

    def test_unknown_tool_and_bad_arguments_are_rejected(self):
        with self.assertRaises(ValueError):
            self.store.create("a", self.permissions, "shell.run", {})
        with self.assertRaises(ValueError):
            self.store.create("a", self.permissions, "memory.search", "not-an-object")


if __name__ == "__main__":
    unittest.main()
