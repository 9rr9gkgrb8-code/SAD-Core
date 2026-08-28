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


class FakeWorkspaceStore:
    def __init__(self):
        self.created_by = None

    def list(self):
        return [{"workspace_id": "11111111-1111-1111-1111-111111111111", "state": "tests_passed", "created_by": self.created_by}]

    def get(self, workspace_id):
        return {"workspace_id": workspace_id, "state": "tests_passed", "diff": "diff", "created_by": self.created_by}

    def create(self, task, allowed_paths, actor_account_id):
        self.created_by = actor_account_id
        return {"workspace_id": "11111111-1111-1111-1111-111111111111", "state": "scope_approved", "task": task, "allowed_paths": allowed_paths, "created_by": actor_account_id}

    def execute(self, workspace_id):
        return {"workspace_id": workspace_id, "state": "tests_passed", "tests": {"passed": True}, "created_by": self.created_by}

    def apply(self, workspace_id):
        return {"workspace_id": workspace_id, "state": "applied"}

    def rollback(self, workspace_id):
        return {"workspace_id": workspace_id, "state": "rolled_back"}


class DeveloperWorkspaceApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.auth = AuthService(root / "accounts.json")
        self.auth.bootstrap_owner("owner", "StrongOwner123", True)
        self.owner = self.auth.login("owner", "StrongOwner123")
        for username, role in (("developer", "developer"), ("developer2", "developer"), ("reviewer", "reviewer"), ("viewer", "viewer"), ("student", "student")):
            self.auth.create_account(username, f"Strong{username.title()}123", role, self.owner)
        self.tokens = {name: self.auth.login(name, f"Strong{name.title()}123") for name in ("developer", "developer2", "reviewer", "viewer", "student")}
        self.workspaces = FakeWorkspaceStore()
        self.service = SadApiService(
            self.auth,
            FailureDashboard(self.auth, root / "dashboard.json"),
            ProgressStore(root / "progress.json"),
            MobileAccessStore(root / "mobile.json"),
            ConversationStore(root / "chat.json"),
            self.workspaces,
        )
        self.workspace_id = "11111111-1111-1111-1111-111111111111"

    def headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_developer_can_plan_create_and_execute_own_workspace_but_cannot_apply(self):
        token = self.tokens["developer"]
        with patch("api.suggest_scope", return_value={"summary": "scope", "paths": ["api.py"]}):
            status, plan = self.service.dispatch("POST", "/v1/dev/workspaces/scope", self.headers(token), {"task": "change API"})
        self.assertEqual(status, 200)
        self.assertEqual(plan["paths"], ["api.py"])
        status, created = self.service.dispatch("POST", "/v1/dev/workspaces", self.headers(token), {"task": "change API", "allowed_paths": ["api.py"]})
        self.assertEqual(status, 201)
        self.assertEqual(created["state"], "scope_approved")
        _, tested = self.service.dispatch("POST", f"/v1/dev/workspaces/{self.workspace_id}/execute", self.headers(token), {})
        self.assertEqual(tested["state"], "tests_passed")
        for action in ("apply", "rollback"):
            with self.assertRaises(PermissionError):
                self.service.dispatch("POST", f"/v1/dev/workspaces/{self.workspace_id}/{action}", self.headers(token), {})

    def test_developer_cannot_execute_another_developers_workspace(self):
        owner = self.tokens["developer"]
        other = self.tokens["developer2"]
        self.service.dispatch("POST", "/v1/dev/workspaces", self.headers(owner), {"task": "change API", "allowed_paths": ["api.py"]})
        with self.assertRaises(PermissionError):
            self.service.dispatch("POST", f"/v1/dev/workspaces/{self.workspace_id}/execute", self.headers(other), {})

    def test_owner_alone_crosses_live_application_boundary(self):
        _, applied = self.service.dispatch("POST", f"/v1/dev/workspaces/{self.workspace_id}/apply", self.headers(self.owner), {})
        self.assertEqual(applied["state"], "applied")
        _, rolled = self.service.dispatch("POST", f"/v1/dev/workspaces/{self.workspace_id}/rollback", self.headers(self.owner), {})
        self.assertEqual(rolled["state"], "rolled_back")

    def test_owner_may_execute_any_scoped_workspace(self):
        self.workspaces.created_by = "someone-else"
        _, tested = self.service.dispatch("POST", f"/v1/dev/workspaces/{self.workspace_id}/execute", self.headers(self.owner), {})
        self.assertEqual(tested["state"], "tests_passed")

    def test_reviewer_and_viewer_are_inspection_only(self):
        for role in ("reviewer", "viewer"):
            token = self.tokens[role]
            status, listing = self.service.dispatch("GET", "/v1/dev/workspaces", self.headers(token), {})
            self.assertEqual(status, 200)
            self.assertEqual(len(listing["workspaces"]), 1)
            status, detail = self.service.dispatch("GET", f"/v1/dev/workspaces/{self.workspace_id}", self.headers(token), {})
            self.assertEqual(status, 200)
            self.assertEqual(detail["diff"], "diff")
            with self.assertRaises(PermissionError):
                self.service.dispatch("POST", "/v1/dev/workspaces", self.headers(token), {"task": "x", "allowed_paths": ["api.py"]})
            with self.assertRaises(PermissionError):
                self.service.dispatch("POST", f"/v1/dev/workspaces/{self.workspace_id}/execute", self.headers(token), {})

    def test_student_cannot_reach_developer_workspace(self):
        with self.assertRaises(PermissionError):
            self.service.dispatch("GET", "/v1/dev/workspaces", self.headers(self.tokens["student"]), {})


if __name__ == "__main__":
    unittest.main()
