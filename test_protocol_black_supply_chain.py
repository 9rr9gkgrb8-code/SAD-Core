import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CHECKOUT_SHA = "11d5960a326750d5838078e36cf38b85af677262"
SETUP_PYTHON_SHA = "a26af69be951a213d495a4c3e4e4022e16d87065"
SANDBOX_DIGEST = "1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6"


class ProtocolBlackSupplyChainTests(unittest.TestCase):
    def test_ci_actions_are_commit_pinned(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn(f"actions/checkout@{CHECKOUT_SHA}", workflow)
        self.assertIn(f"actions/setup-python@{SETUP_PYTHON_SHA}", workflow)
        self.assertNotRegex(workflow, r"actions/(?:checkout|setup-python)@v\d")

    def test_ci_sandbox_image_is_digest_pinned_without_mutable_tag_pull(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn(f"python@sha256:{SANDBOX_DIGEST}", workflow)
        self.assertNotIn("docker pull python:3.11-slim", workflow)
        self.assertRegex(workflow, r"docker pull \"\$SAD_CI_SANDBOX_IMAGE\"")

    def test_ci_permissions_remain_read_only(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertRegex(workflow, r"permissions:\s*\n\s*contents: read")
        self.assertNotRegex(workflow, r"contents:\s*write")


if __name__ == "__main__":
    unittest.main()
