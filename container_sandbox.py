"""Fail-closed Docker execution boundary for untrusted repair verification."""

from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading


PINNED_IMAGE = re.compile(r"^[a-zA-Z0-9._/-]+@sha256:[0-9a-f]{64}$")
MAX_OUTPUT_BYTES = 2_000_000


def _trusted_default_docker():
    candidates = []
    if os.name == "nt":
        program_files = os.environ.get("ProgramFiles")
        if program_files:
            candidates.append(Path(program_files) / "Docker" / "Docker" / "resources" / "bin" / "docker.exe")
        system_root = os.environ.get("SystemRoot")
        if system_root:
            candidates.append(Path(system_root) / "System32" / "docker.exe")
    else:
        candidates.extend((Path("/usr/bin/docker"), Path("/usr/local/bin/docker")))
    return next((path.resolve() for path in candidates if path.is_file() and not path.is_symlink()), None)


class SandboxUnavailable(OSError):
    """Raised when a genuine container boundary cannot be established."""


@dataclass(frozen=True)
class SandboxResult:
    returncode: int
    stdout: str
    stderr: str


class DockerSandboxRunner:
    """Run tests in a resource-limited container with no network or host authority."""

    def __init__(self, executable=None, image=None):
        # Never trust a workspace-controlled PATH entry. Callers may supply an explicit
        # absolute runtime; otherwise only conventional system installation paths qualify.
        self.executable = Path(executable).resolve() if executable else _trusted_default_docker()
        self.image = image or os.getenv("SAD_SANDBOX_IMAGE", "")

    def _preflight(self, workspace):
        if not self.executable or not self.executable.is_absolute() or not self.executable.is_file() or self.executable.is_symlink():
            raise SandboxUnavailable("Docker is required; unsafe local execution is disabled.")
        if not PINNED_IMAGE.fullmatch(self.image):
            raise SandboxUnavailable("SAD_SANDBOX_IMAGE must be pinned as name@sha256:<64 lowercase hex characters>.")
        workspace = Path(workspace).resolve(strict=True)
        if self.executable.resolve().is_relative_to(workspace):
            raise SandboxUnavailable("The container runtime cannot come from the untrusted workspace.")
        if "," in str(workspace):
            raise SandboxUnavailable("Docker bind source paths cannot contain commas.")
        inspect = subprocess.run(
            [str(self.executable), "image", "inspect", self.image],
            capture_output=True, text=True, timeout=10, check=False,
            env={"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")},
        )
        if inspect.returncode != 0:
            raise SandboxUnavailable("The pinned sandbox image must already exist locally; automatic pulls are disabled.")
        return workspace

    def preflight(self, workspace):
        """Verify that the real container boundary is ready without executing tests."""
        return self._preflight(workspace)

    def command(self, workspace):
        workspace = Path(workspace).resolve(strict=True)
        mount = f"type=bind,source={workspace},target=/workspace,readonly"
        return [
            str(self.executable), "run", "--rm", "--pull", "never",
            "--network", "none", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--pids-limit", "128",
            "--memory", "512m", "--memory-swap", "512m", "--cpus", "1.0",
            "--user", "65534:65534", "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--mount", mount, "--workdir", "/workspace",
            "--env", "HOME=/tmp", "--env", "PYTHONDONTWRITEBYTECODE=1",
            self.image, "python", "-B", "-m", "unittest", "-v",
        ]

    def run_tests(self, workspace, timeout=60):
        workspace = self._preflight(workspace)
        process = subprocess.Popen(
            self.command(workspace), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")},
        )
        buffers = {"stdout": bytearray(), "stderr": bytearray()}
        overflow = threading.Event()
        lock = threading.Lock()

        def drain(name, stream):
            while True:
                chunk = stream.read(65536)
                if not chunk:
                    return
                with lock:
                    remaining = MAX_OUTPUT_BYTES - len(buffers[name])
                    buffers[name].extend(chunk[:max(0, remaining)])
                    if len(chunk) > remaining:
                        overflow.set()
                        process.kill()
                        return

        threads = [
            threading.Thread(target=drain, args=("stdout", process.stdout), daemon=True),
            threading.Thread(target=drain, args=("stderr", process.stderr), daemon=True),
        ]
        for thread in threads:
            thread.start()
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            returncode = 124
        for thread in threads:
            thread.join(timeout=2)
        stdout = bytes(buffers["stdout"]).decode("utf-8", errors="replace")
        stderr = bytes(buffers["stderr"]).decode("utf-8", errors="replace")
        if overflow.is_set():
            return SandboxResult(125, stdout, stderr + "\nSandbox output exceeded the safe limit.")
        if returncode == 124:
            stderr += "\nSandbox execution timed out."
        return SandboxResult(returncode, stdout, stderr)
