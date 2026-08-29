import tempfile
import unittest
from pathlib import Path

from auth import AuthService
from failure_dashboard import FailureDashboard
from platform_events import PlatformEventStore
from platform_v04_service import SadPlatform04Service
from skill_library import SkillLibrary
from student_progress import ProgressStore


class RedTeamProvenanceLaunderingTests(unittest.TestCase):
    """Adversarial proof that metadata-only evidence references can be laundered."""

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
        self.service = SadPlatform04Service(
            self.auth,
            FailureDashboard(self.auth, root / "dashboard.json"),
            ProgressStore(root / "progress.json"),
            platform_events=PlatformEventStore(root / "events.json"),
            skills=SkillLibrary(root / "skills.json"),
        )

    @staticmethod
    def bearer(token):
        return {"Authorization": f"Bearer {token}"}

    def test_attacker_can_launder_nonexistent_evidence_into_promoted_skill(self):
        # Attacker controls a developer credential and supplies fabricated provenance.
        status, candidate = self.service.dispatch(
            "POST",
            "/v1/skills",
            self.bearer(self.developer),
            {
                "title": "Trusted repair procedure",
                "summary": "Looks legitimate but is backed only by attacker-chosen strings.",
                "task_signature": "repair:forged:v1",
                "configuration_fingerprint": "forged-config",
                "producer_identity": "forge.worker.trusted",
                "source_failure_ids": ["failure-does-not-exist"],
                "source_work_item_ids": ["work-does-not-exist"],
                "repair_summary": "Fabricated repair narrative.",
                "execution_evidence_refs": ["receipt://does-not-exist/execution"],
                "diff_hash": "a" * 64,
                "source_snapshot": "commit:does-not-exist",
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(candidate["state"], "candidate")

        # A compromised/colluding reviewer can also self-assert an arbitrary verifier identity
        # and arbitrary verification receipt. No evidence registry lookup is performed.
        status, validated = self.service.dispatch(
            "POST",
            f"/v1/skills/{candidate['skill_id']}/validate",
            self.bearer(self.reviewer),
            {
                "verifier_identity": "sad.independent-verifier.trusted",
                "verification_evidence_refs": ["receipt://does-not-exist/verification"],
                "verification_summary": "All checks passed (fabricated).",
                "verification_passed": True,
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(validated["state"], "validated")

        # Owner approval remains a real human gate, but the record presented to that gate has
        # no cryptographic/existence binding to the claimed evidence. The forged provenance is
        # therefore promotable if the human trusts the record at face value.
        status, promoted = self.service.dispatch(
            "POST",
            f"/v1/skills/{candidate['skill_id']}/promote",
            self.bearer(self.owner),
            {"approved": True},
        )
        self.assertEqual(status, 200)
        self.assertEqual(promoted["state"], "promoted")
        self.assertEqual(promoted["source_failure_ids"], ["failure-does-not-exist"])
        self.assertEqual(promoted["execution_evidence_refs"], ["receipt://does-not-exist/execution"])
        self.assertEqual(promoted["verification_evidence_refs"], ["receipt://does-not-exist/verification"])


if __name__ == "__main__":
    unittest.main()
