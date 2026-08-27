"""Operational proof for SAD's Docker-backed repair isolation boundary."""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from container_sandbox import DockerSandboxRunner, SandboxUnavailable


PROOF_TEST = r'''import os
import socket
import unittest
from pathlib import Path


class IsolationBoundaryProof(unittest.TestCase):
    def test_runs_non_root(self):
        if hasattr(os, "getuid"):
            self.assertNotEqual(os.getuid(), 0)

    def test_workspace_is_read_only(self):
        with self.assertRaises(OSError):
            Path("/workspace/should_not_write.txt").write_text("blocked", encoding="utf-8")

    def test_tmp_is_writable(self):
        path = Path("/tmp/sad-proof.txt")
        path.write_text("ok", encoding="utf-8")
        self.assertEqual(path.read_text(encoding="utf-8"), "ok")

    def test_no_git_credentials_are_in_environment(self):
        forbidden = [
            name for name in os.environ
            if name.startswith("GITHUB_")
            or name.startswith("GH_")
            or "TOKEN" in name
            or "SECRET" in name
        ]
        self.assertEqual(forbidden, [])

    def test_external_network_is_unavailable(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            code = sock.connect_ex(("1.1.1.1", 53))
        finally:
            sock.close()
        self.assertNotEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
'''


def run_proof() -> tuple[bool, str]:
    image = os.getenv("SAD_SANDBOX_IMAGE", "").strip()
    if not image:
        return False, "SAD_SANDBOX_IMAGE is not configured"

    with TemporaryDirectory(prefix="sad-docker-proof-") as directory:
        workspace = Path(directory)
        (workspace / "test_isolation_boundary.py").write_text(PROOF_TEST, encoding="utf-8")
        try:
            result = DockerSandboxRunner(image=image).run_tests(workspace, timeout=45)
        except SandboxUnavailable as error:
            return False, str(error)

    if result.returncode != 0:
        details = (result.stdout + "\n" + result.stderr).strip()
        return False, details[-8000:]
    return True, result.stdout.strip()


def main():
    passed, detail = run_proof()
    if not passed:
        print("DOCKER ISOLATION PROOF: BLOCKED")
        if detail:
            print(detail)
        raise SystemExit(1)
    print("DOCKER ISOLATION PROOF: PASS")
    if detail:
        print(detail)


if __name__ == "__main__":
    main()
