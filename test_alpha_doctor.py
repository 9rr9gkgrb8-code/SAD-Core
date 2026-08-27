import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from alpha_doctor import (
    check_local_model,
    check_python,
    check_repair_isolation,
    check_release_integrity,
    core_ready,
    repair_ready,
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
        check = check_repair_isolation({}, which=lambda _: None)
        self.assertEqual(check.scope, "repair")
        self.assertEqual(check.status, "warn")

    def test_repair_isolation_requires_digest_pinned_image(self):
        check = check_repair_isolation(
            {"SAD_SANDBOX_IMAGE": "python:3.11"},
            which=lambda _: "/usr/bin/docker",
        )
        self.assertEqual(check.status, "warn")
        self.assertIn("sha256", check.detail)

    def test_repair_isolation_passes_with_preloaded_digest(self):
        image = "sad-sandbox@sha256:" + ("a" * 64)
        runner = lambda *args, **kwargs: SimpleNamespace(returncode=0)
        check = check_repair_isolation(
            {"SAD_SANDBOX_IMAGE": image},
            which=lambda _: "/usr/bin/docker",
            runner=runner,
        )
        self.assertEqual(check.status, "pass")

    def test_repair_isolation_handles_docker_failure(self):
        image = "sad-sandbox@sha256:" + ("a" * 64)

        def runner(*args, **kwargs):
            raise subprocess.TimeoutExpired("docker", 10)

        check = check_repair_isolation(
            {"SAD_SANDBOX_IMAGE": image},
            which=lambda _: "/usr/bin/docker",
            runner=runner,
        )
        self.assertEqual(check.status, "warn")

    def test_release_integrity_blocks_on_gate_problem(self):
        with patch("alpha_doctor.run_release_gate", return_value=["problem"]):
            self.assertEqual(check_release_integrity().status, "block")

    def test_readiness_separates_core_from_repair(self):
        checks = [
            check_python((3, 11)),
            check_local_model({}),
            check_repair_isolation({}, which=lambda _: None),
        ]
        self.assertTrue(core_ready(checks))
        self.assertFalse(repair_ready(checks))


if __name__ == "__main__":
    unittest.main()
