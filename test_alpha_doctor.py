import unittest
from unittest.mock import patch

from alpha_doctor import (
    check_local_model,
    check_python,
    check_repair_isolation,
    check_release_integrity,
    core_ready,
    repair_ready,
)
from container_sandbox import SandboxUnavailable


class ReadyRunner:
    def __init__(self, image=None):
        self.image = image

    def preflight(self, workspace):
        return workspace


class MissingDockerRunner:
    def __init__(self, image=None):
        self.image = image

    def preflight(self, workspace):
        raise SandboxUnavailable("Docker is required; unsafe local execution is disabled.")


class InvalidImageRunner:
    def __init__(self, image=None):
        self.image = image

    def preflight(self, workspace):
        raise SandboxUnavailable(
            "SAD_SANDBOX_IMAGE must be pinned as name@sha256:<64 lowercase hex characters>."
        )


class AlphaDoctorTests(unittest.TestCase):
    def test_python_311_is_ready(self):
        self.assertEqual(check_python((3, 11)).status, "pass")
        self.assertEqual(check_python((3, 10)).status, "block")

    def test_local_model_is_optional_when_unconfigured(self):
        check = check_local_model({})
        self.assertEqual(check.scope, "optional")
        self.assertEqual(check.status, "warn")

    def test_local_model_rejects_non_loopback_url(self):
        check = check_local_model({
            "SAD_LOCAL_MODEL": "model",
            "SAD_LOCAL_MODEL_URL": "http://example.com:11434",
        })
        self.assertEqual(check.scope, "core")
        self.assertEqual(check.status, "block")

    def test_local_model_accepts_loopback_url(self):
        check = check_local_model({
            "SAD_LOCAL_MODEL": "model",
            "SAD_LOCAL_MODEL_URL": "http://127.0.0.1:11434",
        })
        self.assertEqual(check.status, "pass")

    def test_repair_isolation_warns_without_docker(self):
        check = check_repair_isolation({}, runner_factory=MissingDockerRunner)
        self.assertEqual(check.scope, "repair")
        self.assertEqual(check.status, "warn")
        self.assertIn("Docker is required", check.detail)

    def test_repair_isolation_surfaces_digest_requirement(self):
        check = check_repair_isolation(
            {"SAD_SANDBOX_IMAGE": "python:3.11"},
            runner_factory=InvalidImageRunner,
        )
        self.assertEqual(check.status, "warn")
        self.assertIn("sha256", check.detail)

    def test_repair_isolation_passes_when_sandbox_boundary_is_ready(self):
        image = "sad-sandbox@sha256:" + ("a" * 64)
        check = check_repair_isolation(
            {"SAD_SANDBOX_IMAGE": image},
            runner_factory=ReadyRunner,
        )
        self.assertEqual(check.status, "pass")

    def test_release_integrity_blocks_on_gate_problem(self):
        with patch("alpha_doctor.run_release_gate", return_value=["problem"]):
            self.assertEqual(check_release_integrity().status, "block")

    def test_readiness_separates_core_from_repair(self):
        checks = [
            check_python((3, 11)),
            check_local_model({}),
            check_repair_isolation({}, runner_factory=MissingDockerRunner),
        ]
        self.assertTrue(core_ready(checks))
        self.assertFalse(repair_ready(checks))


if __name__ == "__main__":
    unittest.main()
