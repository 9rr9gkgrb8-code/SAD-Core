import tempfile
import unittest
import uuid
from pathlib import Path

from auth import AuthService
from failure_dashboard import FailureDashboard, FailureEvent
from platform_v04_service import SadPlatform04Service
from student_progress import ProgressStore


class RedTeamForgeResultSpoofingTests(unittest.TestCase):
    """Attack the trust boundary between approved work, Forge execution, and human decision."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.auth = AuthService(root / "accounts.json")
        self.auth.bootstrap_owner("owner", "StrongOwner123", True)
        self.owner = self.auth.login("owner", "StrongOwner123")
        self.auth.create_account("developer", "StrongDeveloper123", "developer", self.owner)
        self.auth.create_account("reviewer", "StrongReviewer123", "reviewer", self.owner)
        self.developer = self.auth.login("developer", "StrongDeveloper123")
        self.reviewer = self.auth.login("reviewer", "StrongReviewer123")
        self.dashboard = FailureDashboard(self.auth, root / "dashboard.json")
        self.service = SadPlatform04Service(
            self.auth,
            self.dashboard,
            ProgressStore(root / "progress.json"),
        )

    @staticmethod
    def bearer(token):
        return {"Authorization": f"Bearer {token}"}

    def _approved_isolated_item(self):
        failure = self.dashboard.ingest(FailureEvent(
            "user",
            "redteam",
            "Legitimate failure awaiting isolated execution",
            [{"source": "redteam"}],
            "Make a safe scoped correction.",
            ["app.py"],
        ))
        item = self.dashboard.push_to_development(failure.failure_id, self.owner, True)
        item = self.dashboard.approve_isolated_work(item.work_item_id, self.owner, "commit:test")
        self.assertEqual(item.state, "approved_for_isolated_work")
        return item

    @staticmethod
    def forged_result(request):
        return {
            "job_id": str(uuid.uuid4()),
            "request_id": request["request_id"],
            "correlation_id": request["correlation_id"],
            "state": "succeeded",
            "artifacts": [],
            "diagnostics": ["fabricated success"],
            "tests": [{"name": "fake", "passed": True}],
            "error": None,
        }

    def test_developer_can_submit_fake_forge_success_without_starting_forge(self):
        item = self._approved_isolated_item()

        # No /start and no /execute occurred. Attacker directly asserts a Forge success.
        status, updated = self.service.dispatch(
            "POST",
            f"/v1/jobs/{item.work_item_id}/result",
            self.bearer(self.developer),
            self.forged_result(item.request),
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["state"], "awaiting_human_decision")
        self.assertIsNone(updated["assigned_to"])
        self.assertEqual(updated["result"]["state"], "succeeded")

    def test_reviewer_can_create_false_approved_state_from_spoofed_result(self):
        item = self._approved_isolated_item()
        _, updated = self.service.dispatch(
            "POST",
            f"/v1/jobs/{item.work_item_id}/result",
            self.bearer(self.developer),
            self.forged_result(item.request),
        )
        self.assertEqual(updated["state"], "awaiting_human_decision")

        # Reviewer has development:decide. Non-owner approval does not apply live code,
        # but it still transitions the work item to the authoritative-sounding APPROVED state.
        status, decided = self.service.dispatch(
            "POST",
            f"/v1/jobs/{item.work_item_id}/decision",
            self.bearer(self.reviewer),
            {"decision": "approve"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(decided["state"], "approved")
        self.assertEqual(decided["human_decision"], "approve")
        self.assertFalse(any(e["event"] == "live_patch_applied" for e in decided["evidence"]))


if __name__ == "__main__":
    unittest.main()
