import unittest

from failure_dashboard import FailureDashboard, FailureEvent


def event(source="sad"):
    return FailureEvent(source, "conversation_quality", "Wrong response", [{"message": "expected X"}], "Review context")


class FailureDashboardTests(unittest.TestCase):
    def test_detection_never_starts_development(self):
        dashboard = FailureDashboard()
        saved = dashboard.ingest(event())
        self.assertEqual(saved.state, "new")
        self.assertEqual(dashboard.dev_items, {})

    def test_owner_push_creates_exactly_one_work_item(self):
        dashboard = FailureDashboard()
        saved = dashboard.ingest(event())
        first = dashboard.push_to_development(saved.failure_id, "owner", True)
        second = dashboard.push_to_development(saved.failure_id, "owner", True)
        self.assertEqual(first.work_item_id, second.work_item_id)
        self.assertEqual(len(dashboard.dev_items), 1)

    def test_push_requires_explicit_owner_approval(self):
        dashboard = FailureDashboard()
        saved = dashboard.ingest(event())
        for role, approved in (("developer", True), ("owner", False)):
            with self.assertRaises(PermissionError):
                dashboard.push_to_development(saved.failure_id, role, approved)

    def test_duplicate_sources_merge_evidence(self):
        dashboard = FailureDashboard()
        first = dashboard.ingest(event("sad"))
        second = dashboard.ingest(event("forge"))
        self.assertEqual(first.failure_id, second.failure_id)
        self.assertEqual(len(second.evidence), 2)

    def test_future_developer_uses_same_dashboard_without_owner_governance(self):
        dashboard = FailureDashboard()
        saved = dashboard.ingest(event())
        item = dashboard.push_to_development(saved.failure_id, "owner", True)
        with self.assertRaises(PermissionError):
            dashboard.approve_isolated_work(item.work_item_id, "developer")


if __name__ == "__main__":
    unittest.main()
