import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sandbox


class SandboxHardeningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sandbox_root = self.root / ".sad_sandbox"
        self.proposal = self.sandbox_root / "proposal"
        self.proposal.mkdir(parents=True)
        (self.proposal / "proposal.json").write_text(json.dumps({"status": "sandbox_created"}), encoding="utf-8")

    def test_path_validation_rejects_escape_and_root(self):
        with patch.object(sandbox, "SANDBOX_DIRECTORY", self.sandbox_root):
            with self.assertRaises(ValueError):
                sandbox.validate_sandbox_path(self.root)
            with self.assertRaises(ValueError):
                sandbox.validate_sandbox_path(self.sandbox_root)

    def test_context_root_must_equal_execution_root(self):
        self.assertTrue(sandbox.verify_context_execution_root(self.proposal, self.proposal))
        self.assertFalse(sandbox.verify_context_execution_root(self.root, self.proposal))

    def test_worker_has_no_git_or_credentials(self):
        with patch.object(sandbox, "SANDBOX_DIRECTORY", self.sandbox_root):
            self.assertTrue(sandbox.sandbox_has_host_only_git_authority(self.proposal, {}))
            self.assertFalse(sandbox.sandbox_has_host_only_git_authority(self.proposal, {"GH_TOKEN": "secret"}))

    def test_git_metadata_change_causes_isolation_failure(self):
        completed = type("Result", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()
        with patch.object(sandbox, "SANDBOX_DIRECTORY", self.sandbox_root), \
             patch.object(sandbox, "snapshot_live_project", side_effect=[{"a": "1"}, {"a": "1"}]), \
             patch.object(sandbox, "snapshot_git_topology", side_effect=[{"config.worktree": "missing"}, {"config.worktree": "created"}]):
            runner = type("Runner", (), {"run_tests": lambda self, path: completed})()
            result = sandbox.run_sandbox_tests(self.proposal, runner=runner)
        self.assertEqual(result["status"], "isolation_failed")
        self.assertFalse(result["git_topology_integrity"])
        self.assertEqual([e["sequence"] for e in result["ordered_evidence"]], list(range(1, 8)))

    def test_worker_environment_strips_git_credentials(self):
        clean = sandbox.build_worker_environment({"GH_TOKEN": "secret", "AWS_SECRET_ACCESS_KEY": "secret", "PATH": "safe"})
        self.assertNotIn("GH_TOKEN", clean)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", clean)
        self.assertEqual(clean["PATH"], "safe")
        self.assertEqual(clean["GIT_TERMINAL_PROMPT"], "0")

    def test_proposal_id_and_patch_scope_reject_traversal_or_extra_files(self):
        with self.assertRaises(ValueError):
            sandbox._validated_proposal_id("../outside")
        with self.assertRaises(ValueError):
            sandbox._validate_patch_scope("--- original/app.py\n+++ proposed/settings.py\n", "app.py")
        with self.assertRaises(ValueError):
            sandbox._validate_patch_scope("GIT binary patch", "app.py")

    def test_isolation_failure_blocks_approval_and_export(self):
        with patch.object(sandbox, "SANDBOX_DIRECTORY", self.sandbox_root):
            proposal = {
                "proposal_id": "00000000-0000-0000-0000-000000000001",
                "failure_id": "failure", "target_file": "app.py",
                "status": "isolation_failed", "draft_diff": "--- original/app.py\n+++ proposed/app.py\n",
            }
            path = self.sandbox_root / proposal["proposal_id"]
            path.mkdir()
            (path / "app.py").write_text("pass\n", encoding="utf-8")
            (path / "proposal.json").write_text(json.dumps(proposal), encoding="utf-8")
            self.assertIsNone(sandbox.approve_sandbox_proposal(proposal["proposal_id"]))
            with self.assertRaises(ValueError):
                sandbox.export_approved_patch(proposal["proposal_id"])


if __name__ == "__main__":
    unittest.main()
