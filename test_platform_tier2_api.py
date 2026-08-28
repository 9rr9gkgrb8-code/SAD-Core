import tempfile
import unittest
from pathlib import Path

from api import SadApiService
from auth import AuthService
from conversation import ConversationStore
from failure_dashboard import FailureDashboard
from mobile_gateway import mobile_route_allowed
from platform_clients import PlatformClientStore
from platform_events import PlatformEventStore
from student_progress import ProgressStore


class PlatformTierTwoApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.auth = AuthService(root / "accounts.json")
        self.auth.bootstrap_owner("owner", "StrongOwner123", True)
        self.owner = self.auth.login("owner", "StrongOwner123")
        self.auth.create_account("student", "StrongStudent123", "student", self.owner)
        self.student = self.auth.login("student", "StrongStudent123")
        self.clients = PlatformClientStore(root / "clients.json")
        self.events = PlatformEventStore(root / "events.json")
        self.service = SadApiService(
            self.auth,
            FailureDashboard(self.auth, root / "dashboard.json"),
            ProgressStore(root / "progress.json"),
            conversations=ConversationStore(root / "chat.json"),
            platform_clients=self.clients,
            platform_events=self.events,
        )

    @staticmethod
    def bearer(token):
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def app_header(client):
        return {"Authorization": f"SAD-App {client['client_id']}.{client['client_secret']}"}

    def test_owner_can_create_scoped_client_but_student_cannot(self):
        status, client = self.service.dispatch(
            "POST", "/v1/platform/clients", self.bearer(self.owner),
            {"name": "Status panel", "capability_ids": ["platform:discover", "platform:events"], "event_types": ["failure.created"]},
        )
        self.assertEqual(status, 201)
        self.assertIn("client_secret", client)
        with self.assertRaises(PermissionError):
            self.service.dispatch(
                "POST", "/v1/platform/clients", self.bearer(self.student),
                {"name": "Nope", "capability_ids": ["platform:discover"]},
            )

    def test_machine_client_cannot_be_used_as_user_bearer(self):
        client = self.clients.create("Discovery", ["platform:discover"], [])
        headers = self.app_header(client)
        status, manifest = self.service.dispatch("POST", "/v1/platform/client/manifest", headers, {})
        self.assertEqual(status, 200)
        self.assertEqual(manifest["principal"]["kind"], "local_app")
        self.assertFalse(manifest["authority_model"]["user_impersonation"])
        with self.assertRaises(PermissionError):
            self.service.dispatch("GET", "/v1/chat/sessions", headers, {})

    def test_app_reads_only_subscribed_event_types(self):
        client = self.clients.create("Failure watcher", ["platform:events"], ["failure.created"])
        self.events.publish("chat.session.created", subject_id="chat-1")
        self.events.publish("failure.created", subject_id="fail-1", details={"category": "logic"})
        _, result = self.service.dispatch("POST", "/v1/platform/client/events", self.app_header(client), {"after_seq": 0})
        self.assertEqual([item["event_type"] for item in result["events"]], ["failure.created"])

    def test_empty_app_event_subscription_reads_nothing(self):
        client = self.clients.create("Quiet watcher", ["platform:events"], [])
        self.events.publish("failure.created", subject_id="fail-1")
        _, result = self.service.dispatch("POST", "/v1/platform/client/events", self.app_header(client), {})
        self.assertEqual(result["events"], [])

    def test_capability_compatibility_is_role_and_scope_filtered(self):
        _, human = self.service.dispatch(
            "POST", "/v1/platform/compatibility", self.bearer(self.student),
            {"requirements": [{"capability_id": "voice:conversation", "min_version": "1.0.0"}, {"capability_id": "development:govern", "min_version": "1.0.0"}]},
        )
        self.assertFalse(human["compatible"])
        self.assertTrue(human["requirements"][0]["compatible"])
        self.assertFalse(human["requirements"][1]["available"])

        client = self.clients.create("Compat", ["platform:compatibility"], [])
        _, machine = self.service.dispatch(
            "POST", "/v1/platform/client/compatibility", self.app_header(client),
            {"requirements": [{"capability_id": "platform:compatibility", "min_version": "1.0.0"}, {"capability_id": "platform:events", "min_version": "1.0.0"}]},
        )
        self.assertTrue(machine["requirements"][0]["compatible"])
        self.assertFalse(machine["requirements"][1]["available"])

    def test_voice_turn_uses_normal_conversation_identity(self):
        status, result = self.service.dispatch(
            "POST", "/v1/voice/turn", self.bearer(self.student), {"transcript": "Tell me hello."},
        )
        self.assertEqual(status, 200)
        self.assertTrue(result["session_id"])
        self.assertEqual(result["speech_text"], result["reply"])
        self.assertEqual(result["input_mode"], "transcript")
        _, session = self.service.dispatch(
            "GET", f"/v1/chat/sessions/{result['session_id']}", self.bearer(self.student), {},
        )
        self.assertEqual(session["message_count"], 2)

    def test_mobile_allows_user_voice_but_never_machine_client_routes(self):
        self.assertTrue(mobile_route_allowed("learning", "POST", "/v1/voice/turn"))
        self.assertFalse(mobile_route_allowed("learning", "POST", "/v1/platform/client/events"))
        self.assertFalse(mobile_route_allowed("full_role", "POST", "/v1/platform/client/events"))


if __name__ == "__main__":
    unittest.main()
