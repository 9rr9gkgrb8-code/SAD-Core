"""Host-controlled adapter from an approved Forge job to isolated test evidence."""

import uuid

from sad_forge_contract import Artifact, ForgeResult
from sandbox import ALLOWED_TARGET_FILES, create_sandbox_proposal, run_sandbox_tests


def verify_approved_job(item):
    """Run an approved request in isolation; never apply, approve, export, or merge."""
    request = item.request or {}
    allowed = next((name for name in request.get("allowed_targets", []) if name in ALLOWED_TARGET_FILES), None)
    if not allowed:
        return ForgeResult(
            str(uuid.uuid4()), request["request_id"], request["correlation_id"], "failed",
            diagnostics=("No requested target is eligible for the isolated worker.",),
            error="No eligible sandbox target.",
        )
    proposal, path = create_sandbox_proposal(item.failure_id, allowed, request["objective"])
    result = run_sandbox_tests(path)
    passed = result["status"] == "sandbox_tests_passed"
    artifacts = (
        Artifact("tests", {"status": result["status"], "output": result.get("test_output", "")}),
        Artifact("execution_receipt", {
            "proposal_id": proposal["proposal_id"],
            "live_project_integrity": result["live_project_integrity"],
            "git_topology_integrity": result["git_topology_integrity"],
            "host_only_git_authority": result["host_only_git_authority"],
            "context_execution_root_match": result["context_execution_root_match"],
            "ordered_evidence": result["ordered_evidence"],
        }),
    )
    return ForgeResult(
        str(uuid.uuid4()), request["request_id"], request["correlation_id"],
        "succeeded" if passed else "failed", artifacts,
        diagnostics=(f"Sandbox status: {result['status']}",),
        tests=({"name": "isolated_suite", "passed": passed},),
        error=None if passed else "Isolated verification did not pass.",
    )
