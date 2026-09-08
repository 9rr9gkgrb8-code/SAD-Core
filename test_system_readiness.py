import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from api import SadApiService
from auth import AuthService
from failure_dashboard import FailureDashboard
from student_progress import ProgressStore


class SystemReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.auth = AuthService(root / "accounts.json")
        self.auth.bootstrap_owner("owner", "StrongOwner123", True)
        self.owner = self.auth.login("owner", "StrongOwner123")
        self.service = SadApiService(self.auth, FailureDashboard(self.auth, root / "dashboard.json"), ProgressStore(root / "progress.json"))

    def test_owner_sees_actionable_optional_runtime_blockers(self):
        headers = {"Authorization": f"Bearer {self.owner}"}
        with patch.dict(os.environ, {}, clear=True):
            status, payload = self.service.dispatch("GET", "/v1/system/readiness", headers, {})
        self.assertEqual(status, 200)
        self.assertEqual(payload["items"]["core"]["status"], "ready")
        self.assertEqual(payload["items"]["local_ai"]["status"], "setup_needed")
        self.assertIn(payload["items"]["repair_isolation"]["status"], {"blocked", "ready"})

    def test_non_owner_cannot_read_host_readiness(self):
        self.auth.create_account("student", "StrongStudent123", "student", self.owner)
        student = self.auth.login("student", "StrongStudent123")
        with self.assertRaises(PermissionError):
            self.service.dispatch("GET", "/v1/system/readiness", {"Authorization": f"Bearer {student}"}, {})


if __name__ == "__main__":
    unittest.main()
