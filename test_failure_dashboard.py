import unittest
import tempfile
from pathlib import Path

from auth import AuthService
from failure_dashboard import FailureDashboard, FailureEvent


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
        self.assertEqual(len(second.evidence), 2)

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


if __name__ == "__main__":
    unittest.main()
