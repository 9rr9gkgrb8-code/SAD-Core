import tempfile
import unittest
from pathlib import Path

from auth import AuthService
from failure_dashboard import FailureDashboard
from platform_v04_service import SadPlatform04Service
from student_progress import ProgressStore


class RedTeamForgeStudentIntegrityTests(unittest.TestCase):
    """Prove a student can self-assert mastery and manufacture progression."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.auth = AuthService(root / "accounts.json")
        self.auth.bootstrap_owner("owner", "StrongOwner123", True)
        self.owner = self.auth.login("owner", "StrongOwner123")
        self.auth.create_account("student", "StrongStudent123", "student", self.owner)
        self.student = self.auth.login("student", "StrongStudent123")
        self.progress = ProgressStore(root / "progress.json")
        self.service = SadPlatform04Service(
            self.auth,
            FailureDashboard(self.auth, root / "dashboard.json"),
            self.progress,
        )

    @staticmethod
    def bearer(token):
        return {"Authorization": f"Bearer {token}"}

    def test_student_can_forge_master_rank_without_server_issued_quests(self):
        final = None
        for index in range(15):
            # The client invents the quest, its unique ID, a negative mastery threshold,
            # and directly claims the boss check passed. No server-issued quest registry
            # or trusted assessment receipt is consulted.
            quest = {
                "quest_id": f"attacker-forged-{index}",
                "title": "Forged Quest",
                "subject": "math",
                "objective": "gain XP without demonstrating learning",
                "challenges": ["not actually completed"],
                "source_type": "homework",
                "mastery_threshold": -1.0,
                "boss_check": "not actually answered",
            }
            status, payload = self.service.dispatch(
                "POST",
                "/v1/forge/complete",
                self.bearer(self.student),
                {"quest": quest, "score": 0.0, "boss_passed": True},
            )
            self.assertEqual(status, 200)
            final = payload["progress"]

        self.assertEqual(final["xp"], 1500)
        self.assertEqual(final["rank"], "Master")
        self.assertEqual(len(final["completed_quests"]), 15)


if __name__ == "__main__":
    unittest.main()
