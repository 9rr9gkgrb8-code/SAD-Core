import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from api import SadApiService
from auth import AuthService
from conversation import ConversationStore
from failure_dashboard import FailureDashboard
from memory_store import MemoryStore
from mobile_access import MobileAccessStore
from platform_events import PlatformEventStore
from student_progress import ProgressStore
from tool_actions import ToolActionStore


class BetaEvaluatorJourneyTests(unittest.TestCase):
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
        self.events = PlatformEventStore(root / "events.json")
        self.dashboard = FailureDashboard(self.auth, root / "dashboard.json")
        self.service = SadApiService(
            auth=self.auth,
            dashboard=self.dashboard,
            progress=ProgressStore(root / "progress.json"),
            mobile_access=MobileAccessStore(root / "mobile.json"),
            conversations=ConversationStore(root / "chat.json"),
            platform_events=self.events,
            memory=self.memory,
            tool_actions=ToolActionStore(root / "tools.json", memory=self.memory),
        )

    @staticmethod
    def headers(token):
        return {"Authorization": f"Bearer {token}"}

    def call(self, method, path, token, body=None):
        return self.service.dispatch(method, path, self.headers(token), body or {})[1]

    def test_safe_cross_module_journey_is_observable_and_persistent(self):
        session = self.call("POST", "/v1/chat/sessions", self.student)
        with patch("conversation.generate_local_response", return_value="Use the saved goal as context."):
            self.call("POST", f"/v1/chat/sessions/{session['session_id']}/messages", self.student,
                      {"message": "Help me plan."})

        self.call("POST", "/v1/memory", self.student, {
            "category": "goal", "title": "Pilot", "content": "Finish the controlled beta journey",
        })
        action = self.call("POST", "/v1/tools/actions", self.student, {
            "tool_id": "memory.remember",
            "args": {"category": "note", "title": "Approved", "content": "Human approved action"},
        })
        with self.assertRaises(PermissionError):
            self.call("POST", f"/v1/tools/actions/{action['action_id']}/execute", self.student)
        self.call("POST", f"/v1/tools/actions/{action['action_id']}/decision", self.student,
                  {"decision": "approve"})
        self.call("POST", f"/v1/tools/actions/{action['action_id']}/execute", self.student)

        quest = self.call("POST", "/v1/forge/quests", self.student, {
            "subject": "math", "assignment": "Solve 2x + 4 = 10", "learning_objective": "isolate x",
        })
        self.call("POST", "/v1/forge/hint", self.student, {"quest_id": quest["quest_id"]})
        completed = self.call("POST", "/v1/forge/complete", self.student, {
            "quest": quest, "score": 1.0, "boss_passed": True,
        })
        self.assertTrue(completed["outcome"]["mastered"])

        self.call("POST", "/v1/failures", self.student, {
            "source": "test", "category": "evaluator_journey", "summary": "Safe synthetic failure",
            "evidence": [{"test": "synthetic"}], "suggested_correction": "Review only",
        })
        snapshot = self.call("GET", "/v1/observability/journey", self.owner)
        self.assertTrue(snapshot["complete"])
        self.assertEqual(snapshot["privacy"], "metadata_only")
        self.assertNotIn("Finish the controlled beta journey", str(snapshot))
        self.assertNotIn("Human approved action", str(snapshot))
        with self.assertRaises(PermissionError):
            self.call("GET", "/v1/observability/journey", self.student)

        restarted_events = PlatformEventStore(Path(self.temp.name) / "events.json")
        restarted_dashboard = FailureDashboard(self.auth, Path(self.temp.name) / "dashboard.json")
        from journey_observability import build_journey_snapshot
        restarted = build_journey_snapshot(restarted_events, restarted_dashboard)
        self.assertTrue(restarted["complete"])
        self.assertEqual(restarted["cursor"], snapshot["cursor"])


if __name__ == "__main__":
    unittest.main()
