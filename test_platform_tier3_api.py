import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from api import SadApiService
from auth import AuthService
from conversation import ConversationStore
from failure_dashboard import FailureDashboard
from memory_store import MemoryStore
from mobile_gateway import mobile_route_allowed
from platform_events import PlatformEventStore
from student_progress import ProgressStore
from tool_actions import ToolActionStore


class PlatformTierThreeApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.auth = AuthService(root / "accounts.json")
        self.auth.bootstrap_owner("owner", "StrongOwner123", True)
        self.owner = self.auth.login("owner", "StrongOwner123")
        self.auth.create_account("student", "StrongStudent123", "student", self.owner)
        self.student = self.auth.login("student", "StrongStudent123")
        self.memory = MemoryStore(root / "memory.json")
        self.tools = ToolActionStore(root / "tools.json", memory=self.memory)
        self.events = PlatformEventStore(root / "events.json")
        self.service = SadApiService(
            self.auth,
            FailureDashboard(self.auth, root / "dashboard.json"),
            ProgressStore(root / "progress.json"),
            conversations=ConversationStore(root / "chat.json"),
            platform_events=self.events,
            memory=self.memory,
            tool_actions=self.tools,
        )

    @staticmethod
    def bearer(token):
        return {"Authorization": f"Bearer {token}"}

    def test_memory_crud_is_account_owned(self):
        status, memory = self.service.dispatch(
            "POST", "/v1/memory", self.bearer(self.student),
            {"category": "preference", "title": "Style", "content": "Prefer concise answers", "enabled": True},
        )
        self.assertEqual(status, 201)
        _, listed = self.service.dispatch("GET", "/v1/memory", self.bearer(self.student), {})
        self.assertEqual(len(listed["memories"]), 1)
        _, owner_list = self.service.dispatch("GET", "/v1/memory", self.bearer(self.owner), {})
        self.assertEqual(owner_list["memories"], [])
        with self.assertRaises(KeyError):
            self.service.dispatch("POST", f"/v1/memory/{memory['memory_id']}", self.bearer(self.owner), {"enabled": False})
        _, updated = self.service.dispatch(
            "POST", f"/v1/memory/{memory['memory_id']}", self.bearer(self.student), {"enabled": False},
        )
        self.assertFalse(updated["enabled"])
        _, deleted = self.service.dispatch(
            "POST", f"/v1/memory/{memory['memory_id']}/delete", self.bearer(self.student), {},
        )
        self.assertTrue(deleted["deleted"])

    def test_enabled_memory_reaches_local_model_context_and_can_be_disabled_per_turn(self):
        self.service.dispatch(
            "POST", "/v1/memory", self.bearer(self.student),
            {"category": "project", "title": "Project", "content": "Forge is the game learning module"},
        )
        _, session = self.service.dispatch("POST", "/v1/chat/sessions", self.bearer(self.student), {})
        captured = []

        def fake_generate(message, name, history):
            captured.append(history)
            return "I used local context."

        with patch("conversation.generate_local_response", side_effect=fake_generate):
            _, reply = self.service.dispatch(
                "POST", f"/v1/chat/sessions/{session['session_id']}/messages", self.bearer(self.student),
                {"message": "What is Forge?"},
            )
            self.assertTrue(reply["memory_used"])
            self.assertTrue(any("Forge is the game learning module" in text for _speaker, text in captured[-1]))
            _, reply2 = self.service.dispatch(
                "POST", f"/v1/chat/sessions/{session['session_id']}/messages", self.bearer(self.student),
                {"message": "Again", "use_memory": False},
            )
            self.assertFalse(reply2["memory_used"])
            self.assertFalse(any("Forge is the game learning module" in text for _speaker, text in captured[-1]))

    def test_mutating_tool_action_requires_human_decision(self):
        status, action = self.service.dispatch(
            "POST", "/v1/tools/actions", self.bearer(self.student),
            {"tool_id": "memory.remember", "args": {"category": "goal", "title": "Goal", "content": "Finish the pilot"}},
        )
        self.assertEqual(status, 201)
        self.assertEqual(action["state"], "awaiting_approval")
        with self.assertRaises(PermissionError):
            self.service.dispatch(
                "POST", f"/v1/tools/actions/{action['action_id']}/execute", self.bearer(self.student), {},
            )
        _, approved = self.service.dispatch(
            "POST", f"/v1/tools/actions/{action['action_id']}/decision", self.bearer(self.student), {"decision": "approve"},
        )
        self.assertEqual(approved["state"], "ready")
        _, completed = self.service.dispatch(
            "POST", f"/v1/tools/actions/{action['action_id']}/execute", self.bearer(self.student), {},
        )
        self.assertEqual(completed["state"], "completed")
        self.assertEqual(self.memory.list(self.auth.require(self.student)["account_id"])[0]["content"], "Finish the pilot")

    def test_platform_and_mobile_expose_personal_tier3_without_privileged_machine_routes(self):
        _, manifest = self.service.dispatch("GET", "/v1/platform", self.bearer(self.student), {})
        modules = {item["module_id"] for item in manifest["modules"]}
        self.assertIn("sad.memory", modules)
        self.assertIn("sad.tools", modules)
        self.assertTrue(mobile_route_allowed("learning", "GET", "/v1/memory"))
        self.assertTrue(mobile_route_allowed("learning", "POST", "/v1/tools/actions"))
        self.assertTrue(mobile_route_allowed("learning", "POST", "/v1/tools/actions/123e4567-e89b-12d3-a456-426614174000/decision"))
        self.assertFalse(mobile_route_allowed("learning", "GET", "/v1/dashboard"))
        self.assertFalse(mobile_route_allowed("full_role", "POST", "/v1/platform/client/events"))

    def test_events_are_metadata_only(self):
        _, memory = self.service.dispatch(
            "POST", "/v1/memory", self.bearer(self.student),
            {"category": "note", "title": "Private title", "content": "Very private memory text"},
        )
        result = self.events.read(after_seq=0, limit=100)
        event = next(item for item in result["events"] if item["event_type"] == "memory.created")
        self.assertEqual(event["subject_id"], memory["memory_id"])
        serialized = str(event)
        self.assertNotIn("Very private memory text", serialized)
        self.assertNotIn("Private title", serialized)


if __name__ == "__main__":
    unittest.main()
