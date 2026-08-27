import json
import tempfile
import threading
import unittest
import urllib.request
import uuid
from pathlib import Path
from unittest.mock import patch

from api import SadApiService, create_server
from auth import AuthService
from failure_dashboard import FailureDashboard
from forge_worker import verify_approved_job
from sad_forge_contract import ForgeResult
from student_progress import ProgressStore
from alpha import ensure_owner


class AlphaProductTests(unittest.TestCase):
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

    def test_browser_ui_is_served_with_security_headers(self):
        server = create_server("127.0.0.1", 0, self.service)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/", timeout=3) as response:
                content = response.read().decode()
                self.assertIn("SAD + Forge Alpha", content)
                self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
                self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        finally:
            server.shutdown()
            server.server_close()

    def test_alpha_launcher_preserves_existing_owner(self):
        with patch("builtins.input", side_effect=AssertionError("setup should not prompt")):
            ensure_owner(self.auth)

    def test_account_lifecycle_and_teacher_student_roster(self):
        _, student = self.service.dispatch("POST", "/v1/accounts", self.headers(), {
            "username": "student", "password": "StrongStudent123", "role": "student",
        })
        self.service.dispatch("POST", "/v1/accounts", self.headers(), {
            "username": "teacher", "password": "StrongTeacher123", "role": "teacher",
        })
        teacher = self.auth.login("teacher", "StrongTeacher123")
        _, roster = self.service.dispatch("GET", "/v1/students", self.headers(teacher), {})
        self.assertEqual(roster["students"][0]["username"], "student")
        self.service.dispatch("POST", f"/v1/accounts/{student['account_id']}/active", self.headers(), {"active": False})
        self.assertIsNone(self.auth.login("student", "StrongStudent123"))

    def test_password_change_revokes_old_password(self):
        self.service.dispatch("POST", "/v1/auth/password", self.headers(), {
            "current_password": "StrongOwner123", "new_password": "EvenStrongerOwner456",
        })
        self.assertIsNone(self.auth.login("owner", "StrongOwner123"))
        self.assertTrue(self.auth.login("owner", "EvenStrongerOwner456"))

    def test_study_generate_fails_honestly_without_local_model(self):
        with patch("study_generator.generate_local_response", return_value=None):
            _, result = self.service.dispatch("POST", "/v1/study/plan", self.headers(), {
                "action": "break_down", "material": "2x=8", "generate": True,
            })
        self.assertEqual(result["result"]["status"], "model_unavailable")
        self.assertIsNone(result["result"]["provider"])

    def test_worker_returns_evidence_without_approval_authority(self):
        request = {
            "request_id": str(uuid.uuid4()), "correlation_id": str(uuid.uuid4()),
            "allowed_targets": ["app.py"], "objective": "verify",
        }
        item = type("Item", (), {"request": request, "failure_id": str(uuid.uuid4())})()
        proposal = {"proposal_id": str(uuid.uuid4())}
        evidence = {
            "status": "sandbox_tests_passed", "test_output": "OK", "ordered_evidence": [],
            "live_project_integrity": True, "git_topology_integrity": True,
            "host_only_git_authority": True, "context_execution_root_match": True,
        }
        with patch("forge_worker.create_sandbox_proposal", return_value=(proposal, Path(self.temp.name))), patch("forge_worker.run_sandbox_tests", return_value=evidence):
            result = verify_approved_job(item)
        self.assertIsInstance(result, ForgeResult)
        self.assertEqual(result.state, "succeeded")
        self.assertFalse(hasattr(result, "approval"))
        self.assertFalse(hasattr(result, "merge"))

    def test_execute_endpoint_runs_only_after_owner_isolation_approval(self):
        _, failure = self.service.dispatch("POST", "/v1/failures", self.headers(), {
            "category": "alpha", "summary": "Worker route", "evidence": [{"passed": False}],
            "suggested_correction": "Verify app", "affected_files": ["app.py"],
        })
        _, work = self.service.dispatch("POST", "/v1/jobs", self.headers(), {
            "failure_id": failure["failure_id"], "approved": True,
        })
        _, work = self.service.dispatch("POST", f"/v1/jobs/{work['work_item_id']}/approve-isolated", self.headers(), {
            "source_snapshot": "alpha-test",
        })
        result = ForgeResult(
            str(uuid.uuid4()), work["request"]["request_id"], work["request"]["correlation_id"],
            "succeeded", tests=({"name": "suite", "passed": True},),
        )
        with patch("api.verify_approved_job", return_value=result):
            _, completed = self.service.dispatch(
                "POST", f"/v1/jobs/{work['work_item_id']}/execute", self.headers(), {},
            )
        self.assertEqual(completed["state"], "awaiting_human_decision")
        self.assertIsNone(completed["human_decision"])


if __name__ == "__main__":
    unittest.main()
