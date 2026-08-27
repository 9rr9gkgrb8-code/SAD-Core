import json
import tempfile
import threading
import unittest
import urllib.request
import uuid
from pathlib import Path

from api import SadApiService, create_server
from auth import AuthService
from failure_dashboard import FailureDashboard
from student_progress import ProgressStore
from sad_clients import PersonalStudyClient, ForgeStudentClient, SadClient


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.auth = AuthService(root / "accounts.json")
        self.auth.bootstrap_owner("owner", "StrongOwner123", True)
        self.owner = self.auth.login("owner", "StrongOwner123")
        self.dashboard = FailureDashboard(self.auth, root / "dashboard.json")
        self.service = SadApiService(self.auth, self.dashboard, ProgressStore(root / "progress.json"))

    def headers(self, token=None):
        return {"Authorization": f"Bearer {token or self.owner}"}

    def test_health_http_endpoint_and_loopback_binding(self):
        with self.assertRaises(ValueError):
            create_server("0.0.0.0", 0, self.service)
        server = create_server("127.0.0.1", 0, self.service)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/health", timeout=3) as response:
                body = json.loads(response.read())
            self.assertEqual(body, {"status": "ok", "api_version": "v1"})
        finally:
            server.shutdown()
            server.server_close()

    def test_failure_job_dashboard_contract_smoke_flow(self):
        status, failure = self.service.dispatch("POST", "/v1/failures", self.headers(), {
            "category": "general", "summary": "API failure", "evidence": [{"test": "failed"}],
            "suggested_correction": "repair", "affected_files": ["app.py"],
        })
        self.assertEqual(status, 201)
        _, work = self.service.dispatch("POST", "/v1/jobs", self.headers(), {"failure_id": failure["failure_id"], "approved": True})
        _, work = self.service.dispatch("POST", f"/v1/jobs/{work['work_item_id']}/approve-isolated", self.headers(), {"source_snapshot": "abc123"})
        self.auth.create_account("developer", "StrongDeveloper123", "developer", self.owner)
        developer = self.auth.login("developer", "StrongDeveloper123")
        self.service.dispatch("POST", f"/v1/jobs/{work['work_item_id']}/start", self.headers(developer), {})
        request = work["request"]
        result_payload = {
            "job_id": str(uuid.uuid4()), "request_id": request["request_id"],
            "correlation_id": request["correlation_id"], "state": "succeeded",
            "artifacts": [{"kind": "tests", "content": {"passed": True}}],
            "tests": [{"name": "suite", "passed": True}],
        }
        _, result = self.service.dispatch("POST", f"/v1/jobs/{work['work_item_id']}/result", self.headers(developer), result_payload)
        self.assertEqual(result["state"], "awaiting_human_decision")
        self.service.dispatch("POST", f"/v1/jobs/{work['work_item_id']}/decision", self.headers(), {"decision": "approve"})
        self.service.dispatch("POST", f"/v1/jobs/{work['work_item_id']}/close", self.headers(), {})
        _, dashboard = self.service.dispatch("GET", "/v1/dashboard", self.headers(), {})
        self.assertEqual(dashboard["development"][0]["state"], "closed")

    def test_same_dashboard_different_role_permissions(self):
        for name, role in (("developer", "developer"), ("reviewer", "reviewer"), ("viewer", "viewer")):
            self.auth.create_account(name, f"Strong{role}123", role, self.owner)
            token = self.auth.login(name, f"Strong{role}123")
            self.service.dispatch("GET", "/v1/dashboard", self.headers(token), {})
        viewer = self.auth.login("viewer", "Strongviewer123")
        with self.assertRaises(PermissionError):
            self.service.dispatch("POST", "/v1/jobs", self.headers(viewer), {"failure_id": "missing", "approved": True})

    def test_personal_study_and_forge_student_are_real_clients_of_api(self):
        self.auth.create_account("student", "StrongStudent123", "student", self.owner)
        student = self.auth.login("student", "StrongStudent123")
        _, plan = self.service.dispatch("POST", "/v1/study/plan", self.headers(student), {"action": "teach_method", "material": "fractions"})
        self.assertEqual(plan["action"], "teach_method")
        _, quest = self.service.dispatch("POST", "/v1/forge/quests", self.headers(student), {"subject": "math", "assignment": "Solve 2x=8"})
        self.service.dispatch("POST", "/v1/forge/hint", self.headers(student), {"quest_id": quest["quest_id"]})
        _, completed = self.service.dispatch("POST", "/v1/forge/complete", self.headers(student), {"quest": quest, "score": .9, "boss_passed": True})
        self.assertEqual(completed["progress"]["xp"], 100)
        restarted = SadApiService(self.auth, self.dashboard, ProgressStore(Path(self.temp.name) / "progress.json"))
        _, progress = restarted.dispatch("GET", "/v1/forge/progress", self.headers(student), {})
        self.assertEqual(progress["xp"], 100)

    def test_http_clients_login_study_and_forge_smoke(self):
        self.auth.create_account("student", "StrongStudent123", "student", self.owner)
        server = create_server("127.0.0.1", 0, self.service)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            login = SadClient.login("student", "StrongStudent123", base)
            study = PersonalStudyClient(login["token"], base)
            forge = ForgeStudentClient(login["token"], base)
            self.assertEqual(study.plan("break_down", "2x=8")["action"], "break_down")
            quest = forge.homework_quest("math", "2x=8")
            self.assertEqual(forge.hint(quest["quest_id"])["hint_level"], "nudge")
            self.assertEqual(forge.complete(quest, .9, True)["progress"]["xp"], 100)
        finally:
            server.shutdown()
            server.server_close()

    def test_clients_refuse_remote_token_exposure(self):
        with self.assertRaises(ValueError):
            PersonalStudyClient("token", "https://example.com")

    def test_teacher_can_read_student_progress_but_viewer_cannot(self):
        self.auth.create_account("student", "StrongStudent123", "student", self.owner)
        self.auth.create_account("teacher", "StrongTeacher123", "teacher", self.owner)
        self.auth.create_account("viewer", "StrongViewer123", "viewer", self.owner)
        student = self.auth.login("student", "StrongStudent123")
        teacher = self.auth.login("teacher", "StrongTeacher123")
        viewer = self.auth.login("viewer", "StrongViewer123")
        account = self.auth.require(student)
        _, progress = self.service.dispatch("GET", f"/v1/forge/progress/{account['account_id']}", self.headers(teacher), {})
        self.assertEqual(progress["student_id"], account["account_id"])
        with self.assertRaises(PermissionError):
            self.service.dispatch("GET", f"/v1/forge/progress/{account['account_id']}", self.headers(viewer), {})


if __name__ == "__main__":
    unittest.main()
