import tempfile
import unittest
from pathlib import Path

from skill_library import SkillLibrary


class SkillLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "skills.json"
        self.skills = SkillLibrary(self.path)

    def propose(self, **overrides):
        payload = {
            "title": "Repair sandbox containment",
            "summary": "Reusable procedure for proving repair isolation.",
            "task_signature": "repair:sandbox-containment:v1",
            "configuration_fingerprint": "sandbox=docker;network=none;git=host-only",
            "producer_identity": "forge.worker",
            "source_failure_ids": ["failure-1"],
            "source_work_item_ids": ["work-1"],
            "repair_summary": "Validate canonical paths, execute in isolation, compare integrity snapshots.",
            "execution_evidence_refs": ["receipt://work-1/execution"],
            "proposed_by": "developer-account",
            "diff_hash": "a" * 64,
            "source_snapshot": "commit:abc123",
        }
        payload.update(overrides)
        return self.skills.propose(**payload)

    def validate(self, skill_id, **overrides):
        payload = {
            "reviewed_by": "reviewer-account",
            "verifier_identity": "sad.independent-verifier",
            "verification_evidence_refs": ["receipt://work-1/verification"],
            "verification_summary": "All deterministic checks passed.",
            "verification_passed": True,
        }
        payload.update(overrides)
        return self.skills.validate(skill_id, **payload)

    def test_candidate_never_auto_promotes(self):
        candidate = self.propose()
        self.assertEqual(candidate["state"], "candidate")
        self.assertIsNone(candidate["approved_by"])
        reloaded = SkillLibrary(self.path).get(candidate["skill_id"])
        self.assertEqual(reloaded["state"], "candidate")

    def test_validation_requires_independent_evidence_and_identity(self):
        candidate = self.propose()
        with self.assertRaises(ValueError):
            self.validate(candidate["skill_id"], verification_evidence_refs=[])
        with self.assertRaises(ValueError):
            self.validate(candidate["skill_id"], verifier_identity="forge.worker")
        validated = self.validate(candidate["skill_id"])
        self.assertEqual(validated["state"], "validated")
        self.assertEqual(validated["verifier_identity"], "sad.independent-verifier")

    def test_promotion_requires_explicit_human_approval(self):
        candidate = self.propose()
        self.validate(candidate["skill_id"])
        with self.assertRaises(PermissionError):
            self.skills.promote(candidate["skill_id"], approved_by="owner-account", approved=False)
        promoted = self.skills.promote(candidate["skill_id"], approved_by="owner-account", approved=True)
        self.assertEqual(promoted["state"], "promoted")
        self.assertEqual(promoted["approved_by"], "owner-account")

    def test_superseding_skill_increments_version_and_preserves_lineage(self):
        first = self.propose()
        self.validate(first["skill_id"])
        self.skills.promote(first["skill_id"], approved_by="owner-account", approved=True)

        second = self.propose(
            title="Repair sandbox containment v2",
            source_failure_ids=["failure-2"],
            source_work_item_ids=["work-2"],
            execution_evidence_refs=["receipt://work-2/execution"],
            supersedes=first["skill_id"],
        )
        self.assertEqual(second["version"], 2)
        self.validate(
            second["skill_id"],
            verification_evidence_refs=["receipt://work-2/verification"],
        )
        promoted = self.skills.promote(second["skill_id"], approved_by="owner-account", approved=True)
        old = self.skills.get(first["skill_id"])
        self.assertEqual(promoted["state"], "promoted")
        self.assertEqual(old["state"], "superseded")
        self.assertEqual(old["superseded_by"], promoted["skill_id"])

    def test_promoted_skill_can_be_revoked_with_reason(self):
        candidate = self.propose()
        self.validate(candidate["skill_id"])
        self.skills.promote(candidate["skill_id"], approved_by="owner-account", approved=True)
        revoked = self.skills.revoke(
            candidate["skill_id"], revoked_by="owner-account", reason="New evidence invalidated the procedure."
        )
        self.assertEqual(revoked["state"], "revoked")
        self.assertIn("invalidated", revoked["revocation_reason"])

    def test_candidate_requires_source_and_execution_provenance(self):
        with self.assertRaises(ValueError):
            self.propose(source_failure_ids=[], source_work_item_ids=[])
        with self.assertRaises(ValueError):
            self.propose(execution_evidence_refs=[])


if __name__ == "__main__":
    unittest.main()
