"""Automated checks for isolated sandbox creation."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import json
import sandbox


class SandboxTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_sandbox_directory = sandbox.SANDBOX_DIRECTORY
        sandbox.SANDBOX_DIRECTORY = Path(self.temp_directory.name) / "sandboxes"

    def tearDown(self):
        sandbox.SANDBOX_DIRECTORY = self.original_sandbox_directory
        self.temp_directory.cleanup()

    def test_proposal_uses_a_separate_copy_of_the_project(self):
        proposal, sandbox_path = sandbox.create_sandbox_proposal(
            "failure-123", "personality.py", "Use a warmer follow-up response."
        )

        self.assertEqual(proposal["status"], "sandbox_created")
        self.assertTrue((sandbox_path / "personality.py").exists())
        self.assertTrue((sandbox_path / "proposal.json").exists())


    def test_draft_patch_changes_only_the_sandbox_copy(self):
        proposal, sandbox_path = sandbox.create_sandbox_proposal(
            "failure-456", "personality.py", "Improve a response."
        )
        live_source = (sandbox.PROJECT_DIRECTORY / "personality.py").read_text(
            encoding="utf-8"
        )
        original_marker = live_source.splitlines()[0]
        draft, diff = sandbox.create_draft_patch(
            sandbox_path,
            "personality.py",
            original_marker,
            '"""Sasha\'s sandbox draft response layer."""',
        )
        self.assertEqual(proposal["status"], "sandbox_created")
        self.assertEqual(draft["status"], "draft_created")
        saved_proposal, saved_diff = sandbox.get_sandbox_proposal(
            proposal["proposal_id"]
        )
        self.assertEqual(saved_proposal["proposal_id"], proposal["proposal_id"])
        self.assertEqual(saved_diff, diff)
        self.assertIn("sandbox draft response", diff)
        self.assertEqual(live_source, (sandbox.PROJECT_DIRECTORY / "personality.py").read_text(encoding="utf-8"))
        self.assertTrue((sandbox_path / "draft.patch").exists())

    def test_only_passing_drafts_can_be_approved(self):
        proposal, sandbox_path = sandbox.create_sandbox_proposal(
            "failure-789", "personality.py", "Review a draft."
        )
        self.assertIsNone(sandbox.approve_sandbox_proposal(proposal["proposal_id"]))

        original_marker = (sandbox_path / "personality.py").read_text(
            encoding="utf-8"
        ).splitlines()[0]
        proposal, _ = sandbox.create_draft_patch(
            sandbox_path,
            "personality.py",
            original_marker,
            '"""Sasha\'s exported draft response layer."""',
        )
        proposal_path = sandbox_path / "proposal.json"
        proposal["status"] = "sandbox_tests_passed"
        proposal["tested_target_sha256"] = sandbox._hash_file(sandbox_path / "personality.py")
        proposal_path.write_text(json.dumps(proposal), encoding="utf-8")
        approved = sandbox.approve_sandbox_proposal(proposal["proposal_id"])
        exported_path = sandbox.export_approved_patch(proposal["proposal_id"])

        self.assertEqual(approved["status"], "draft_approved_by_human")
        self.assertIn("approved_at", approved)
        self.assertTrue(exported_path.exists())
        exported_patch = exported_path.read_text(encoding="utf-8")
        self.assertIn("--- a/personality.py", exported_patch)
        self.assertIn("+++ b/personality.py", exported_patch)

    def test_approved_patch_can_be_checked_without_applying(self):
        proposal, sandbox_path = sandbox.create_sandbox_proposal(
            "failure-987", "personality.py", "Validate a draft."
        )
        original_marker = (sandbox_path / "personality.py").read_text(
            encoding="utf-8"
        ).splitlines()[0]
        proposal, _ = sandbox.create_draft_patch(
            sandbox_path,
            "personality.py",
            original_marker,
            '"""Sasha\'s validated draft response layer."""',
        )
        proposal["status"] = "sandbox_tests_passed"
        proposal["tested_target_sha256"] = sandbox._hash_file(sandbox_path / "personality.py")
        (sandbox_path / "proposal.json").write_text(
            json.dumps(proposal), encoding="utf-8"
        )
        sandbox.approve_sandbox_proposal(proposal["proposal_id"])
        validation = sandbox.validate_approved_patch(proposal["proposal_id"])

        self.assertTrue(validation["is_valid"])
        self.assertTrue(validation["patch_path"].exists())
        self.assertEqual(validation["details"], "")

if __name__ == "__main__":
    unittest.main()
