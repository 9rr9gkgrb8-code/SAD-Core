import unittest
import tempfile
import uuid
import threading
from pathlib import Path

from auth import AuthService
from failure_dashboard import FailureDashboard, FailureEvent
from sad_forge_contract import Artifact, ForgeResult


def event(source="sad"):
    return FailureEvent(source, "conversation_quality", "Wrong response", [{"message": "expected X"}], "Review context")


class FailureDashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.auth = AuthService(Path(self.temp.name) / "accounts.json")
        self.auth.bootstrap_owner("owner", "StrongOwner123", True)
        self.owner = self.auth.login("owner", "StrongOwner123")

    def test_detection_never_starts_development(self):
        dashboard = FailureDashboard(self.auth)
        saved = dashboard.ingest(event())
        self.assertEqual(saved.state, "new")
        self.assertEqual(dashboard.dev_items, {})

    def test_owner_push_creates_exactly_one_work_item(self):
        dashboard = FailureDashboard(self.auth)
        saved = dashboard.ingest(event())
        first = dashboard.push_to_development(saved.failure_id, self.owner, True)
        second = dashboard.push_to_development(saved.failure_id, self.owner, True)
        self.assertEqual(first.work_item_id, second.work_item_id)
        self.assertEqual(len(dashboard.dev_items), 1)

    def test_push_requires_explicit_owner_approval(self):
        dashboard = FailureDashboard(self.auth)
        saved = dashboard.ingest(event())
        self.auth.create_account("developer", "StrongDeveloper123", "developer", self.owner)
        developer = self.auth.login("developer", "StrongDeveloper123")
        with self.assertRaises(PermissionError):
            dashboard.push_to_development(saved.failure_id, developer, True)
        with self.assertRaises(PermissionError):
            dashboard.push_to_development(saved.failure_id, self.owner, False)

    def test_duplicate_sources_merge_evidence(self):
        dashboard = FailureDashboard(self.auth)
        first = dashboard.ingest(event("sad"))
        second = dashboard.ingest(event("forge"))
        self.assertEqual(first.failure_id, second.failure_id)
        self.assertEqual(len([item for item in second.evidence if "message" in item]), 2)
        self.assertTrue(any(item.get("event") == "failure_deduplicated" for item in second.evidence))

    def test_future_developer_uses_same_dashboard_without_owner_governance(self):
        dashboard = FailureDashboard(self.auth)
        saved = dashboard.ingest(event())
        item = dashboard.push_to_development(saved.failure_id, self.owner, True)
        self.auth.create_account("developer", "StrongDeveloper123", "developer", self.owner)
        developer = self.auth.login("developer", "StrongDeveloper123")
        with self.assertRaises(PermissionError):
            dashboard.approve_isolated_work(item.work_item_id, developer)

    def test_forged_role_string_is_not_authorization(self):
        dashboard = FailureDashboard(self.auth)
        saved = dashboard.ingest(event())
        with self.assertRaises(PermissionError):
            dashboard.push_to_development(saved.failure_id, "owner", True)

    def test_dashboard_snapshot_requires_development_view(self):
        dashboard = FailureDashboard(self.auth)
        dashboard.ingest(event())
        self.auth.create_account("student", "StrongStudent123", "student", self.owner)
        student = self.auth.login("student", "StrongStudent123")
        with self.assertRaises(PermissionError):
            dashboard.snapshot(student)
        self.assertEqual(len(dashboard.snapshot(self.owner)["failures"]), 1)

    def test_oversized_failure_is_rejected(self):
        with self.assertRaises(ValueError):
            FailureEvent("sad", "general", "x" * 10_001, [{"message": "evidence"}], "review")

    def test_failure_and_workflow_survive_restart_without_duplicate_work(self):
        state = Path(self.temp.name) / "dashboard.json"
        dashboard = FailureDashboard(self.auth, state)
        saved = dashboard.ingest(event())
        item = dashboard.push_to_development(saved.failure_id, self.owner, True)
        restarted = FailureDashboard(self.auth, state)
        duplicate = restarted.push_to_development(saved.failure_id, self.owner, True)
        self.assertEqual(item.work_item_id, duplicate.work_item_id)
        self.assertEqual(len(restarted.dev_items), 1)

    def test_complete_forge_flow_preserves_ordered_evidence_and_human_authority(self):
        state = Path(self.temp.name) / "dashboard.json"
        dashboard = FailureDashboard(self.auth, state)
        saved = dashboard.ingest(FailureEvent("sad", "general", "broken", [{"test": "failed"}], "fix", ["app.py"]))
        item = dashboard.push_to_development(saved.failure_id, self.owner, True)
        item = dashboard.approve_isolated_work(item.work_item_id, self.owner, "source-sha")
        self.auth.create_account("developer", "StrongDeveloper123", "developer", self.owner)
        self.auth.create_account("reviewer", "StrongReviewer123", "reviewer", self.owner)
        developer = self.auth.login("developer", "StrongDeveloper123")
        reviewer = self.auth.login("reviewer", "StrongReviewer123")
        dashboard.start_forge(item.work_item_id, developer)
        request = item.request
        from forge_worker import _attestation
        proposal_id = str(uuid.uuid4())
        receipt = Artifact("execution_receipt", {"proposal_id": proposal_id, "tested_target_sha256": "a" * 64, "worker_attestation": _attestation(request["forge_job_id"], request["request_id"], request["correlation_id"], proposal_id, "a" * 64, "failed")})
        result = ForgeResult(request["forge_job_id"], request["request_id"], request["correlation_id"], "failed", (Artifact("tests", {"passed": 0}), receipt), error="failed")
        dashboard.record_forge_result(item.work_item_id, result, developer)
        with self.assertRaises(PermissionError):
            dashboard.decide(item.work_item_id, "approve", developer)
        with self.assertRaises(PermissionError):
            dashboard.decide(item.work_item_id, "approve", reviewer)
        dashboard.decide(item.work_item_id, "reject", reviewer)
        dashboard.close(item.work_item_id, self.owner)
        sequences = [entry["sequence"] for entry in dashboard.dev_items[item.work_item_id].evidence]
        self.assertEqual(sequences, sorted(sequences))
        self.assertEqual(dashboard.dev_items[item.work_item_id].state, "closed")

    def test_concurrent_pushes_still_create_one_work_item(self):
        dashboard = FailureDashboard(self.auth, Path(self.temp.name) / "dashboard.json")
        saved = dashboard.ingest(event())
        results = []
        threads = [threading.Thread(target=lambda: results.append(dashboard.push_to_development(saved.failure_id, self.owner, True))) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len({item.work_item_id for item in results}), 1)
        self.assertEqual(len(dashboard.dev_items), 1)


if __name__ == "__main__":
    unittest.main()
