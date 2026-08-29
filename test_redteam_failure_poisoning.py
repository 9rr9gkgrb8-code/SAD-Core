import tempfile
import unittest
from pathlib import Path

from auth import AuthService
from failure_dashboard import FailureDashboard, FailureEvent
from platform_v04_service import SadPlatform04Service
from student_progress import ProgressStore


class RedTeamFailurePoisoningTests(unittest.TestCase):
    """Attack failure-source authenticity and first-writer deduplication semantics."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.auth = AuthService(root / "accounts.json")
        self.auth.bootstrap_owner("owner", "StrongOwner123", True)
        self.owner = self.auth.login("owner", "StrongOwner123")
        self.auth.create_account("student", "StrongStudent123", "student", self.owner)
        self.student = self.auth.login("student", "StrongStudent123")
        self.dashboard = FailureDashboard(self.auth, root / "dashboard.json")
        self.service = SadPlatform04Service(
            self.auth,
            self.dashboard,
            ProgressStore(root / "progress.json"),
        )

    @staticmethod
    def bearer(token):
        return {"Authorization": f"Bearer {token}"}

    def test_low_privilege_user_can_spoof_forge_source(self):
        status, failure = self.service.dispatch(
            "POST",
            "/v1/failures",
            self.bearer(self.student),
            {
                "source": "forge",
                "category": "sandbox",
                "summary": "Sandbox verification mismatch",
                "evidence": [{"forge_receipt": "fabricated"}],
                "suggested_correction": "Disable the integrity check.",
                "affected_files": ["settings.py"],
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(failure["source"], "forge")
        self.assertNotIn("reported_by", failure["evidence"][0])

    def test_attacker_first_write_poison_survives_real_forge_deduplication(self):
        # Student pre-seeds the exact signature expected from a later genuine Forge failure.
        _, poisoned = self.service.dispatch(
            "POST",
            "/v1/failures",
            self.bearer(self.student),
            {
                "source": "forge",
                "category": "sandbox",
                "summary": "Sandbox verification mismatch",
                "evidence": [{"forge_receipt": "fabricated"}],
                "suggested_correction": "Disable the integrity check.",
                "affected_files": ["settings.py"],
            },
        )

        # Later, a genuine Forge-origin failure with the same signature is deduplicated
        # into the attacker-created canonical record.
        real = self.dashboard.ingest(FailureEvent(
            "forge",
            "sandbox",
            "Sandbox verification mismatch",
            [{"forge_receipt": "real-verified-receipt"}],
            "Investigate the isolated worker and preserve integrity enforcement.",
            ["app.py"],
        ))

        self.assertEqual(real.failure_id, poisoned["failure_id"])
        self.assertEqual(real.suggested_correction, "Disable the integrity check.")
        self.assertEqual(real.affected_files, ["settings.py"])
        self.assertTrue(any(item.get("forge_receipt") == "real-verified-receipt" for item in real.evidence))


if __name__ == "__main__":
    unittest.main()
