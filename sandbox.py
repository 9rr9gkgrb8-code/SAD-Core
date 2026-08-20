"""Create isolated proposal copies for SAD's future self-correction work."""

import json
import difflib
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path


PROJECT_DIRECTORY = Path(__file__).parent
SANDBOX_DIRECTORY = PROJECT_DIRECTORY / ".sad_sandbox"
ALLOWED_TARGET_FILES = {"app.py", "evaluator.py", "personality.py", "settings.py"}


def create_sandbox_proposal(failure_id, target_file, proposal_summary):
    """Copy the Python project into an isolated proposal folder.

    This function never edits the live project. It only creates a separate copy
    for a human-reviewed proposal and later test run.
    """
    if target_file not in ALLOWED_TARGET_FILES:
        raise ValueError("The target file is not approved for sandbox proposals.")

    proposal_id = str(uuid.uuid4())
    sandbox_path = SANDBOX_DIRECTORY / proposal_id
    sandbox_path.mkdir(parents=True)

    for source_file in PROJECT_DIRECTORY.glob("*.py"):
        shutil.copy2(source_file, sandbox_path / source_file.name)

    proposal = {
        "proposal_id": proposal_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "failure_id": failure_id,
        "target_file": target_file,
        "proposal_summary": proposal_summary,
        "status": "sandbox_created",
    }

    with (sandbox_path / "proposal.json").open("w", encoding="utf-8") as file:
        json.dump(proposal, file, indent=2)

    return proposal, sandbox_path


def run_sandbox_tests(sandbox_path):
    """Run the project test suite in the isolated copy, never in the live project."""
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "-v"],
        cwd=sandbox_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    proposal_path = Path(sandbox_path) / "proposal.json"
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    proposal["status"] = (
        "sandbox_tests_passed" if result.returncode == 0 else "sandbox_tests_failed"
    )
    proposal["test_output"] = result.stdout + result.stderr
    proposal_path.write_text(json.dumps(proposal, indent=2), encoding="utf-8")

    return proposal


def create_draft_patch(sandbox_path, target_file, find_text, replacement_text):
    """Edit one approved file only inside a sandbox and save a reviewable diff."""
    sandbox_path = Path(sandbox_path).resolve()
    sandbox_root = SANDBOX_DIRECTORY.resolve()
    if not sandbox_path.is_relative_to(sandbox_root):
        raise ValueError("Draft patches must stay inside SAD's sandbox directory.")

    if target_file not in ALLOWED_TARGET_FILES:
        raise ValueError("The target file is not approved for sandbox proposals.")

    target_path = sandbox_path / target_file
    original = target_path.read_text(encoding="utf-8")
    if not find_text or find_text not in original:
        raise ValueError("The requested original text was not found in the sandbox file.")

    updated = original.replace(find_text, replacement_text, 1)
    target_path.write_text(updated, encoding="utf-8")
    diff = "".join(difflib.unified_diff(original.splitlines(keepends=True), updated.splitlines(keepends=True), fromfile=f"original/{target_file}", tofile=f"proposed/{target_file}"))
    patch_path = sandbox_path / "draft.patch"
    patch_path.write_text(diff, encoding="utf-8")

    proposal_path = sandbox_path / "proposal.json"
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    proposal["status"] = "draft_created"
    proposal["draft_diff"] = diff
    proposal["draft_patch_file"] = patch_path.name
    proposal_path.write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    return proposal, diff


def get_sandbox_proposal(proposal_id):
    """Return one saved sandbox proposal and its draft diff for human review."""
    sandbox_root = SANDBOX_DIRECTORY.resolve()
    sandbox_path = (sandbox_root / proposal_id).resolve()
    if not sandbox_path.is_relative_to(sandbox_root):
        raise ValueError("Proposal reviews must stay inside SAD's sandbox directory.")

    proposal_path = sandbox_path / "proposal.json"
    if not proposal_path.exists():
        raise ValueError("That sandbox proposal was not found.")

    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    return proposal, proposal.get("draft_diff", "")


def approve_sandbox_proposal(proposal_id):
    """Mark a passing sandbox draft approved by a human, without applying it."""
    proposal, _ = get_sandbox_proposal(proposal_id)
    if proposal.get("status") != "sandbox_tests_passed":
        return None

    sandbox_path = (SANDBOX_DIRECTORY.resolve() / proposal_id).resolve()
    proposal_path = sandbox_path / "proposal.json"
    proposal["status"] = "draft_approved_by_human"
    proposal["approved_at"] = datetime.now().isoformat(timespec="seconds")
    proposal_path.write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    return proposal


def export_approved_patch(proposal_id):
    """Export a human-approved draft as a patch; never apply it automatically."""
    proposal, diff = get_sandbox_proposal(proposal_id)
    if proposal.get("status") != "draft_approved_by_human":
        raise ValueError("That sandbox draft has not been approved by a human.")
    if not diff:
        raise ValueError("That sandbox proposal has no draft diff to export.")

    target_file = proposal["target_file"]
    exported_diff = diff.replace(
        f"--- original/{target_file}",
        f"--- a/{target_file}",
        1,
    ).replace(
        f"+++ proposed/{target_file}",
        f"+++ b/{target_file}",
        1,
    )
    if exported_diff == diff:
        raise ValueError("The sandbox draft has an unexpected patch format.")

    sandbox_path = (SANDBOX_DIRECTORY.resolve() / proposal_id).resolve()
    exported_path = sandbox_path / "approved.patch"
    exported_path.write_text(exported_diff, encoding="utf-8")
    return exported_path


def validate_approved_patch(proposal_id):
    """Check an approved patch against live files without applying anything."""
    exported_path = export_approved_patch(proposal_id)
    result = subprocess.run(
        ["git", "apply", "--check", str(exported_path)],
        cwd=PROJECT_DIRECTORY,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return {
        "proposal_id": proposal_id,
        "patch_path": exported_path,
        "is_valid": result.returncode == 0,
        "details": result.stdout + result.stderr,
    }
