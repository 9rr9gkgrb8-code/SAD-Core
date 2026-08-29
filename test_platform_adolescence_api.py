import tempfile
import unittest
from pathlib import Path

from auth import AuthService
from failure_dashboard import FailureDashboard
from platform_events import PlatformEventStore
from platform_extensions import PlatformExtensionStore
from platform_v04_service import SadPlatform04Service
from skill_library import SkillLibrary
from student_progress import ProgressStore


class PlatformAdolescenceApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.auth = AuthService(root / "accounts.json")
        self.auth.bootstrap_owner("owner", "StrongOwner123", True)
        self.owner = self.auth.login("owner", "StrongOwner123")
        self.auth.create_account("developer", "StrongDeveloper123", "developer", self.owner)
        self.auth.create_account("reviewer", "StrongReviewer123", "reviewer", self.owner)
        self.auth.create_account("viewer", "StrongViewer123", "viewer", self.owner)
        self.auth.create_account("student", "StrongStudent123", "student", self.owner)
        self.developer = self.auth.login("developer", "StrongDeveloper123")
        self.reviewer = self.auth.login("reviewer", "StrongReviewer123")
        self.viewer = self.auth.login("viewer", "StrongViewer123")
        self.student = self.auth.login("student", "StrongStudent123")
        self.events = PlatformEventStore(root / "events.json")
        self.extensions = PlatformExtensionStore(root / "extensions.json")
        self.skills = SkillLibrary(root / "skills.json")
        self.service = SadPlatform04Service(
            self.auth,
            FailureDashboard(self.auth, root / "dashboard.json"),
            ProgressStore(root / "progress.json"),
            platform_events=self.events,
            platform_extensions=self.extensions,
            skills=self.skills,
        )

    @staticmethod
    def bearer(token):
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def extension_manifest():
        return {
            "name": "Failure Lens",
            "publisher": "Local Developer",
            "version": "1.0.0",
            "description": "Reads governed platform metadata through a separate SAD-App client.",
            "required_capabilities": [
                {"capability_id": "platform:discover", "min_version": "1.0.0"},
                {"capability_id": "platform:events", "min_version": "1.0.0"},
            ],
            "requested_event_types": ["failure.created"],
            "execution_model": "external_process",
            "transport": "sad_app_http",
            "network_scope": "loopback_only",
            "core_code_loading": False,
            "host_fallback": False,
            "git_authority": "none",
        }

    @staticmethod
    def skill_payload():
        return {
            "title": "Repair sandbox containment",
            "summary": "Reusable procedure for proving isolated repair boundaries.",
            "task_signature": "repair:sandbox-containment:v1",
            "configuration_fingerprint": "sandbox=docker;network=none;git=host-only",
            "producer_identity": "forge.worker",
            "source_failure_ids": ["failure-1"],
            "source_work_item_ids": ["work-1"],
            "repair_summary": "Validate canonical paths, execute in isolation, then compare integrity snapshots.",
            "execution_evidence_refs": ["receipt://work-1/execution"],
            "diff_hash": "a" * 64,
            "source_snapshot": "commit:abc123",
        }

    def test_owner_can_register_extension_but_registration_grants_no_authority(self):
        status, record = self.service.dispatch(
            "POST", "/v1/platform/extensions", self.bearer(self.owner), self.extension_manifest()
        )
        self.assertEqual(status, 201)
        self.assertFalse(record["authority_model"]["registration_grants_authority"])
        self.assertFalse(record["authority_model"]["credentials_created"])
        self.assertEqual(record["authority_model"]["git_authority"], "none")
        _, listed = self.service.dispatch(
            "GET", "/v1/platform/extensions", self.bearer(self.owner), {}
        )
        self.assertEqual(len(listed["extensions"]), 1)
        with self.assertRaises(PermissionError):
            self.service.dispatch(
                "POST", "/v1/platform/extensions", self.bearer(self.student), self.extension_manifest()
            )

    def test_skill_flows_developer_to_reviewer_to_owner_without_auto_promotion(self):
        status, candidate = self.service.dispatch(
            "POST", "/v1/skills", self.bearer(self.developer), self.skill_payload()
        )
        self.assertEqual(status, 201)
        self.assertEqual(candidate["state"], "candidate")

        with self.assertRaises(PermissionError):
            self.service.dispatch(
                "POST", f"/v1/skills/{candidate['skill_id']}/promote",
                self.bearer(self.developer), {"approved": True},
            )

        status, validated = self.service.dispatch(
            "POST", f"/v1/skills/{candidate['skill_id']}/validate",
            self.bearer(self.reviewer),
            {
                "verifier_identity": "sad.independent-verifier",
                "verification_evidence_refs": ["receipt://work-1/verification"],
                "verification_summary": "All deterministic checks passed.",
                "verification_passed": True,
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(validated["state"], "validated")

        with self.assertRaises(PermissionError):
            self.service.dispatch(
                "POST", f"/v1/skills/{candidate['skill_id']}/promote",
                self.bearer(self.owner), {"approved": False},
            )

        status, promoted = self.service.dispatch(
            "POST", f"/v1/skills/{candidate['skill_id']}/promote",
            self.bearer(self.owner), {"approved": True},
        )
        self.assertEqual(status, 200)
        self.assertEqual(promoted["state"], "promoted")
        self.assertEqual(promoted["approved_by"], self.auth.require(self.owner)["account_id"])

    def test_viewer_can_inspect_skills_but_cannot_propose(self):
        _, candidate = self.service.dispatch(
            "POST", "/v1/skills", self.bearer(self.developer), self.skill_payload()
        )
        status, payload = self.service.dispatch("GET", "/v1/skills", self.bearer(self.viewer), {})
        self.assertEqual(status, 200)
        self.assertEqual(payload["skills"][0]["skill_id"], candidate["skill_id"])
        with self.assertRaises(PermissionError):
            self.service.dispatch(
                "POST", "/v1/skills", self.bearer(self.viewer), self.skill_payload()
            )

    def test_skill_events_reveal_lifecycle_metadata_not_repair_content(self):
        _, candidate = self.service.dispatch(
            "POST", "/v1/skills", self.bearer(self.developer), self.skill_payload()
        )
        events = self.events.read(after_seq=0, limit=100)["events"]
        event = next(item for item in events if item["event_type"] == "skill.candidate.created")
        self.assertEqual(event["subject_id"], candidate["skill_id"])
        serialized = str(event)
        self.assertNotIn("Validate canonical paths", serialized)
        self.assertNotIn("repair:sandbox-containment", serialized)

    def test_platform_manifest_advertises_governed_04_boundaries(self):
        _, manifest = self.service.dispatch("GET", "/v1/platform", self.bearer(self.owner), {})
        self.assertEqual(manifest["platform_version"], "0.4-alpha")
        self.assertEqual(manifest["platform_schema_version"], 4)
        authority = manifest["authority_model"]
        self.assertFalse(authority["dynamic_extension_execution"])
        self.assertFalse(authority["extension_registration_grants_authority"])
        self.assertFalse(authority["host_fallback_on_extension_failure"])
        self.assertFalse(authority["repair_success_equals_skill_promotion"])


if __name__ == "__main__":
    unittest.main()
