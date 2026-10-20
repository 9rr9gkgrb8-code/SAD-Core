import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory_store import MemoryStore
from platform_registry import PlatformRegistry
from tool_actions import ToolActionStore
from runtime_database import RuntimeDatabase


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

    def test_interrupted_effect_cannot_be_replayed_after_restart(self):
        action = self.store.create("a", self.permissions, "memory.remember", {
            "title": "Once", "content": "Survives interruption"
        })
        action_id = action["action_id"]
        self.store.decide("a", action_id, "approve")
        original_run = self.store._run

        def interrupted_run(*args):
            self.assertEqual(self.store.get("a", action_id)["state"], "executing")
            original_run(*args)
            raise SystemExit("simulated interruption after effect")

        with patch.object(self.store, "_run", side_effect=interrupted_run):
            with self.assertRaises(SystemExit):
                self.store.execute(self.account, self.permissions, action_id)
        restarted = ToolActionStore(self.store.path, memory=self.memory)
        with self.assertRaises(PermissionError):
            restarted.execute(self.account, self.permissions, action_id)
        self.assertEqual(len(self.memory.list("a")), 1)

    def test_failed_reservation_never_dispatches(self):
        action = self.store.create("a", self.permissions, "platform.status", {})
        with patch.object(self.store, "_save", side_effect=OSError("disk unavailable")):
            with patch.object(self.store, "_run") as run:
                with self.assertRaises(OSError):
                    self.store.execute(self.account, self.permissions, action["action_id"])
                run.assert_not_called()

    def test_sqlite_reservation_survives_new_store_instance(self):
        root = Path(self.temp.name)
        database = RuntimeDatabase(root / "runtime.sqlite3", protect_at_rest=False)
        with patch("tool_actions.TOOL_ACTION_FILE", root / "unused.json"), patch(
            "tool_actions.LEGACY_TOOL_ACTION_FILE", root / "legacy.json"
        ):
            store = ToolActionStore(database=database, memory=self.memory)
            action = store.create("a", self.permissions, "platform.status", {})
            with patch.object(store, "_run", side_effect=SystemExit("interrupted")):
                with self.assertRaises(SystemExit):
                    store.execute(self.account, self.permissions, action["action_id"])
            restarted = ToolActionStore(
                database=RuntimeDatabase(database.path, protect_at_rest=False), memory=self.memory
            )
            self.assertEqual(restarted.get("a", action["action_id"])["state"], "executing")
            with patch.object(restarted, "_run") as run:
                with self.assertRaises(PermissionError):
                    restarted.execute(self.account, self.permissions, action["action_id"])
                run.assert_not_called()

    def test_nonfinite_arguments_are_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.store.create("a", self.permissions, "memory.search", {"limit": value})

    def test_public_action_does_not_share_nested_arguments(self):
        args = {"categories": ["note"]}
        action = self.store.create("a", self.permissions, "memory.search", args)
        action["args"]["categories"].append("goal")
        args["categories"].append("preference")
        self.assertEqual(self.store.get("a", action["action_id"])["args"], {"categories": ["note"]})


if __name__ == "__main__":
    unittest.main()
