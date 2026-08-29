import tempfile
import unittest
from pathlib import Path

from memory_store import MemoryStore
from platform_clients import PlatformClientStore
from platform_events import PlatformEventStore
from platform_extensions import PlatformExtensionStore
from platform_registry import PlatformRegistry
from runtime_database import RuntimeDatabase
from skill_library import SkillLibrary
from tool_actions import ToolActionStore


class RuntimePersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = Path(self.temp.name) / "sad_runtime.sqlite3"
        self.db = RuntimeDatabase(self.db_path)

    def test_tier2_tier3_and_platform04_state_share_versioned_sqlite_database(self):
        memory = MemoryStore(database=self.db)
        events = PlatformEventStore(database=self.db)
        clients = PlatformClientStore(database=self.db)
        extensions = PlatformExtensionStore(database=self.db)
        skills = SkillLibrary(database=self.db)
        tools = ToolActionStore(memory=memory, platform=PlatformRegistry(), database=self.db)

        saved = memory.create("account-a", "goal", "Ship", "Finish stabilization")
        event = events.publish("memory.created", subject_id=saved["memory_id"], details={"category": "goal"})
        client = clients.create("observer", ["platform:events"], ["memory.created"])
        extension = extensions.register(
            {
                "name": "Observer Extension",
                "publisher": "Local Developer",
                "version": "1.0.0",
                "description": "Read-only local observer contract.",
                "required_capabilities": [
                    {"capability_id": "platform:discover", "min_version": "1.0.0"},
                ],
                "requested_event_types": ["memory.created"],
                "execution_model": "external_process",
                "transport": "sad_app_http",
                "network_scope": "loopback_only",
                "core_code_loading": False,
                "host_fallback": False,
                "git_authority": "none",
            },
            PlatformRegistry(),
            registered_by="owner-a",
        )
        skill = skills.propose(
            title="Validated repair pattern",
            summary="Reusable repair candidate with retained provenance.",
            task_signature="repair:test:v1",
            configuration_fingerprint="sandbox=docker;git=host-only",
            producer_identity="forge.worker",
            source_failure_ids=["failure-a"],
            source_work_item_ids=["work-a"],
            repair_summary="Apply the tested isolated correction.",
            execution_evidence_refs=["receipt://work-a/execution"],
            proposed_by="developer-a",
        )
        action = tools.create("account-a", set(), "memory.search", {"query": "Ship"})
        completed = tools.execute({"account_id": "account-a", "role": "student"}, set(), action["action_id"])

        self.assertEqual(event["seq"], 1)
        self.assertIn("client_secret", client)
        self.assertEqual(extension["state"], "registered")
        self.assertEqual(skill["state"], "candidate")
        self.assertEqual(completed["state"], "completed")
        self.assertEqual(
            set(self.db.document_names()),
            {
                "memory",
                "platform_clients",
                "platform_events",
                "platform_extensions",
                "skills",
                "tool_actions",
            },
        )
        self.assertTrue(self.db.quick_check())

        reopened = RuntimeDatabase(self.db_path)
        self.assertEqual(MemoryStore(database=reopened).list("account-a")[0]["content"], "Finish stabilization")
        self.assertEqual(PlatformEventStore(database=reopened).read()["events"][0]["event_type"], "memory.created")
        self.assertEqual(PlatformClientStore(database=reopened).list()[0]["name"], "observer")
        self.assertEqual(PlatformExtensionStore(database=reopened).list()[0]["extension_id"], extension["extension_id"])
        self.assertEqual(SkillLibrary(database=reopened).get(skill["skill_id"])["state"], "candidate")
        self.assertEqual(ToolActionStore(memory=MemoryStore(database=reopened), database=reopened).list("account-a")[0]["state"], "completed")


if __name__ == "__main__":
    unittest.main()
