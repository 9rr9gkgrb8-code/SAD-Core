import unittest
import uuid

from sad_forge_contract import Artifact, ForgeResult, RepairRequest


class SadForgeContractTests(unittest.TestCase):
    def request(self):
        return RepairRequest(
            failure_id="failure", objective="Repair safely", source_snapshot="abc123",
            sandbox_scope="isolated_container", allowed_targets=("app.py",),
            test_plan=("python -m unittest -v",), approval_state="approved_for_isolated_work",
        )

    def test_request_is_versioned_and_correlatable(self):
        request = self.request()
        self.assertEqual(request.schema_version, "1.0")
        uuid.UUID(request.request_id)
        uuid.UUID(request.correlation_id)

    def test_request_requires_prior_human_approval(self):
        with self.assertRaises(ValueError):
            RepairRequest("f", "repair", "sha", "scope", ("app.py",), ("tests",), "forge_approved")

    def test_result_has_durable_artifacts_and_no_authority_field(self):
        request = self.request()
        artifact = Artifact("diff", {"patch": "--- a/app.py"})
        result = ForgeResult(str(uuid.uuid4()), request.request_id, request.correlation_id, "succeeded", (artifact,), tests=({"passed": True},))
        data = result.to_dict()
        self.assertEqual(data["artifacts"][0]["sha256"], artifact.sha256)
        self.assertNotIn("approved", data)
        self.assertNotIn("merge", data)

    def test_failed_result_requires_error(self):
        request = self.request()
        with self.assertRaises(ValueError):
            ForgeResult(str(uuid.uuid4()), request.request_id, request.correlation_id, "failed")


if __name__ == "__main__":
    unittest.main()
