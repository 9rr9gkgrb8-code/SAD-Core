import unittest

from developer_workspace import DeveloperWorkspaceError, normalize_scope_path


class RedTeamGovernanceSelfEditTests(unittest.TestCase):
    """Show which security/governance files remain eligible for automatic coding scope."""

    def test_automatic_workspace_can_target_security_gate_python_files(self):
        # The GitHub workflow directory itself is protected, which is good.
        with self.assertRaises(DeveloperWorkspaceError):
            normalize_scope_path(".github/workflows/ci.yml")

        # But the runtime coding workspace still accepts the Python programs that define
        # security/release decisions. An automated coding task can therefore propose edits
        # to its own verifier/governance layer and rely on the Owner to notice the conflict.
        accepted = {
            normalize_scope_path("protocol_black.py"),
            normalize_scope_path("protocol_white.py"),
            normalize_scope_path("release_gate.py"),
            normalize_scope_path("alpha_stable.py"),
            normalize_scope_path("sandbox.py"),
            normalize_scope_path("auth.py"),
        }
        self.assertEqual(
            accepted,
            {
                "protocol_black.py",
                "protocol_white.py",
                "release_gate.py",
                "alpha_stable.py",
                "sandbox.py",
                "auth.py",
            },
        )


if __name__ == "__main__":
    unittest.main()
