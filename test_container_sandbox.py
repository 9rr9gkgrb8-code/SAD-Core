import subprocess
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from container_sandbox import DockerSandboxRunner, SandboxUnavailable
import sandbox


IMAGE = "sad-python@sha256:" + "a" * 64


class ContainerSandboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.docker = self.workspace / "docker.exe"
        self.docker.write_bytes(b"placeholder")

    def test_missing_runtime_or_unpinned_image_fails_closed(self):
        with self.assertRaises(SandboxUnavailable):
            DockerSandboxRunner(executable="missing", image=IMAGE).run_tests(self.workspace)
        with self.assertRaises(SandboxUnavailable):
            DockerSandboxRunner(executable=self.docker, image="python:latest").run_tests(self.workspace)

    def test_proposal_records_isolation_unavailable_without_runtime(self):
        original_root = sandbox.SANDBOX_DIRECTORY
        try:
            sandbox.SANDBOX_DIRECTORY = self.workspace / "sandboxes"
            proposal, path = sandbox.create_sandbox_proposal("failure", "app.py", "test")
            result = sandbox.run_sandbox_tests(path, DockerSandboxRunner(executable="missing", image=IMAGE))
        finally:
            sandbox.SANDBOX_DIRECTORY = original_root
        self.assertEqual(result["status"], "isolation_unavailable")
        self.assertIn("Docker is required", result["test_output"])

    def test_command_enforces_container_boundaries(self):
        runner = DockerSandboxRunner(self.docker, IMAGE)
        command = runner.command(self.workspace)
        joined = " ".join(command)
        for required in ("--network none", "--read-only", "--cap-drop ALL", "no-new-privileges", "--pids-limit 128", "--memory 512m", "--cpus 1.0", "readonly", "--pull never"):
            self.assertIn(required, joined)
        self.assertNotIn(".git", joined)

    @patch("container_sandbox.subprocess.Popen")
    @patch("container_sandbox.subprocess.run")
    def test_preloaded_pinned_image_runs_without_pull(self, mock_run, mock_popen):
        mock_run.return_value = subprocess.CompletedProcess([], 0, "", "")
        process = mock_popen.return_value
        process.stdout = io.BytesIO(b"tests passed")
        process.stderr = io.BytesIO(b"")
        process.wait.return_value = 0
        result = DockerSandboxRunner(self.docker, IMAGE).run_tests(self.workspace)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "tests passed")
        self.assertEqual(mock_popen.call_args.args[0][1], "run")


if __name__ == "__main__":
    unittest.main()
