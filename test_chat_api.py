import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from api import SadApiService
from auth import AuthService
from conversation import ConversationStore
from failure_dashboard import FailureDashboard
from mobile_access import MobileAccessStore
from student_progress import ProgressStore


class ChatApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.auth = AuthService(root / "accounts.json")
        self.auth.bootstrap_owner("owner", "OwnerPassword123", explicitly_approved=True)
        self.owner_token = self.auth.login("owner", "OwnerPassword123")
        self.auth.create_account("student", "StudentPassword123", "student", self.owner_token)
        self.student_token = self.auth.login("student", "StudentPassword123")
        self.service = SadApiService(
            auth=self.auth,
            dashboard=FailureDashboard(self.auth, root / "dashboard.json"),
            progress=ProgressStore(root / "progress.json"),
            mobile_access=MobileAccessStore(root / "mobile.json"),
            conversations=ConversationStore(root / "chat.json"),
        )

    @staticmethod
    def headers(token):
        return {"Authorization": f"Bearer {token}"}

    def test_authenticated_account_can_create_talk_and_reload_conversation(self):
        status, session = self.service.dispatch("POST", "/v1/chat/sessions", self.headers(self.student_token), {})
        self.assertEqual(status, 201)
        session_id = session["session_id"]

        with patch("conversation.generate_local_response", return_value="That sounds worth checking."):
            status, result = self.service.dispatch(
                "POST",
                f"/v1/chat/sessions/{session_id}/messages",
                self.headers(self.student_token),
                {"message": "Could a loose belt cause that?"},
            )
        self.assertEqual(status, 200)
        self.assertEqual(result["engine"], "local_model")
        self.assertEqual(result["reply"], "That sounds worth checking.")
        self.assertEqual(len(result["session"]["messages"]), 2)

        status, loaded = self.service.dispatch(
            "GET", f"/v1/chat/sessions/{session_id}", self.headers(self.student_token), {}
        )
        self.assertEqual(status, 200)
        self.assertEqual(loaded["messages"][0]["text"], "Could a loose belt cause that?")

    def test_one_account_cannot_read_another_accounts_chat(self):
        _, session = self.service.dispatch("POST", "/v1/chat/sessions", self.headers(self.student_token), {})
        with self.assertRaises(KeyError):
            self.service.dispatch(
                "GET", f"/v1/chat/sessions/{session['session_id']}", self.headers(self.owner_token), {}
            )

    def test_archive_removes_session_from_active_list_without_deleting_file(self):
        _, session = self.service.dispatch("POST", "/v1/chat/sessions", self.headers(self.student_token), {})
        session_id = session["session_id"]
        status, archived = self.service.dispatch(
            "POST", f"/v1/chat/sessions/{session_id}/archive", self.headers(self.student_token), {}
        )
        self.assertEqual(status, 200)
        self.assertIsNotNone(archived["archived_at"])
        _, listing = self.service.dispatch("GET", "/v1/chat/sessions", self.headers(self.student_token), {})
        self.assertEqual(listing["sessions"], [])

    def test_chat_requires_login(self):
        with self.assertRaises(PermissionError):
            self.service.dispatch("GET", "/v1/chat/sessions", {}, {})


if __name__ == "__main__":
    unittest.main()
