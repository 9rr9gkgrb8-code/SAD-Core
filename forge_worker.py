"""Host-controlled adapter from an approved Forge job to isolated repair evidence."""

import hashlib
import hmac
import os

from repair_planner import RepairPlanningError, plan_repair
from sad_forge_contract import Artifact, ForgeResult
from sandbox import (
    ALLOWED_TARGET_FILES,
    create_draft_patch,
    create_sandbox_proposal,
    run_sandbox_tests,
)


_WORKER_ATTESTATION_KEY = os.urandom(32)


def _attestation(job_id, request_id, correlation_id, proposal_id, tested_hash, state):
    message = "\0".join((job_id, request_id, correlation_id, proposal_id, tested_hash or "", state)).encode()
    return hmac.new(_WORKER_ATTESTATION_KEY, message, hashlib.sha256).hexdigest()


def verify_result_authenticity(result):
    receipt = next((artifact for artifact in result.artifacts if artifact.kind == "execution_receipt"), None)
    content = receipt.content if receipt and isinstance(receipt.content, dict) else {}
    supplied = content.get("worker_attestation", "")
    expected = _attestation(result.job_id, result.request_id, result.correlation_id, content.get("proposal_id", ""), content.get("tested_target_sha256", ""), result.state)
    return bool(supplied) and hmac.compare_digest(supplied, expected)


def _failed_result(request, job_id, message, diagnostic, proposal_id=""):
    receipt = Artifact("execution_receipt", {
        "proposal_id": proposal_id,
        "tested_target_sha256": None,
        "worker_attestation": _attestation(job_id, request["request_id"], request["correlation_id"], proposal_id, None, "failed"),
    })
    return ForgeResult(job_id, request["request_id"], request["correlation_id"], "failed", (receipt,), diagnostics=(diagnostic,), error=message)


def verify_approved_job(item, planner=None):
    """Generate one scoped draft, test it in isolation, and return evidence only."""
    request = item.request or {}
    job_id = request.get("forge_job_id", "")
    targets = request.get("allowed_targets")
    plan = request.get("test_plan")
    snapshot = request.get("source_snapshot", "")
    valid_snapshot = isinstance(snapshot, str) and 1 <= len(snapshot) <= 200 and snapshot == snapshot.strip()
    if not isinstance(targets, list) or len(targets) != 1 or targets[0] not in ALLOWED_TARGET_FILES or plan != ["python -m unittest -v"] or not valid_snapshot or not job_id:
        return _failed_result(request, job_id, "Invalid approved Forge job.", "The approved scope, source snapshot, or test plan is invalid.")
    allowed = targets[0]

    proposal, path = create_sandbox_proposal(item.failure_id, allowed, request["objective"])
    source = (path / allowed).read_text(encoding="utf-8")
    try:
        repair = (planner or plan_repair)(allowed, request["objective"], source)
        proposal, diff = create_draft_patch(
            path, allowed, repair["find_text"], repair["replacement_text"],
        )
    except (RepairPlanningError, ValueError, OSError) as error:
        return _failed_result(request, job_id, "Forge could not produce a safe repair draft.", f"Repair planning failed: {error}", proposal["proposal_id"])

    result = run_sandbox_tests(path)
    passed = result["status"] == "sandbox_tests_passed"
    state = "succeeded" if passed else "failed"
    artifacts = (
        Artifact("diff", {
            "target_file": allowed,
            "patch": diff,
            "rationale": repair.get("rationale", ""),
        }),
        Artifact("tests", {"status": result["status"], "output": result.get("test_output", "")}),
        Artifact("execution_receipt", {
            "proposal_id": proposal["proposal_id"],
            "live_project_integrity": result["live_project_integrity"],
            "git_topology_integrity": result["git_topology_integrity"],
            "host_only_git_authority": result["host_only_git_authority"],
            "context_execution_root_match": result["context_execution_root_match"],
            "ordered_evidence": result["ordered_evidence"],
            "tested_target_sha256": result.get("tested_target_sha256"),
            "worker_attestation": _attestation(job_id, request["request_id"], request["correlation_id"], proposal["proposal_id"], result.get("tested_target_sha256"), state),
        }),
    )
    return ForgeResult(
        job_id, request["request_id"], request["correlation_id"],
        state, artifacts,
        diagnostics=(f"Sandbox status: {result['status']}",),
        tests=({"name": "isolated_suite", "passed": passed},),
        error=None if passed else "Isolated verification did not pass.",
    )
