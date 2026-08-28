import tempfile
import unittest
from pathlib import Path

from memory_store import MemoryStore
from platform_clients import PlatformClientStore
from platform_events import PlatformEventStore
from platform_registry import PlatformRegistry
from runtime_database import RuntimeDatabase
from tool_actions import ToolActionStore


class RuntimePersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = Path(self.temp.name) / "sad_runtime.sqlite3"
        self.db = RuntimeDatabase(self.db_path)

    def test_tier2_and_tier3_state_share_versioned_sqlite_database(self):
        memory = MemoryStore(database=self.db)
        events = PlatformEventStore(database=self.db)
        clients = PlatformClientStore(database=self.db)
        tools = ToolActionStore(memory=memory, platform=PlatformRegistry(), database=self.db)

        saved = memory.create("account-a", "goal", "Ship", "Finish stabilization")
        event = events.publish("memory.created", subject_id=saved["memory_id"], details={"category": "goal"})
        client = clients.create("observer", ["platform:events"], ["memory.created"])
        action = tools.create("account-a", set(), "memory.search", {"query": "Ship"})
        completed = tools.execute({"account_id": "account-a", "role": "student"}, set(), action["action_id"])

        self.assertEqual(event["seq"], 1)
        self.assertIn("client_secret", client)
        self.assertEqual(completed["state"], "completed")
        self.assertEqual(
            set(self.db.document_names()),
            {"memory", "platform_clients", "platform_events", "tool_actions"},
        )
        self.assertTrue(self.db.quick_check())

        reopened = RuntimeDatabase(self.db_path)
        self.assertEqual(MemoryStore(database=reopened).list("account-a")[0]["content"], "Finish stabilization")
        self.assertEqual(PlatformEventStore(database=reopened).read()["events"][0]["event_type"], "memory.created")
        self.assertEqual(PlatformClientStore(database=reopened).list()[0]["name"], "observer")
        self.assertEqual(ToolActionStore(memory=MemoryStore(database=reopened), database=reopened).list("account-a")[0]["state"], "completed")


if __name__ == "__main__":
    unittest.main()
