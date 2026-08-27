"""Create isolated proposal copies for SAD's future self-correction work."""

import json
import difflib
import hashlib
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from container_sandbox import DockerSandboxRunner, SandboxResult, SandboxUnavailable


PROJECT_DIRECTORY = Path(__file__).parent
SANDBOX_DIRECTORY = PROJECT_DIRECTORY / ".sad_sandbox"
ALLOWED_TARGET_FILES = {"app.py", "evaluator.py", "personality.py", "settings.py"}
PROTECTED_GIT_PATHS = (
    "HEAD", "config", "commondir", "config.worktree", "hooks", "modules"
)
GIT_CREDENTIAL_ENVIRONMENT = {"GITHUB_TOKEN", "GH_TOKEN", "GIT_ASKPASS", "SSH_AUTH_SOCK"}
SAFE_WORKER_ENVIRONMENT = {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "LANG", "LC_ALL", "PYTHONUTF8"}


def validate_sandbox_path(path, must_exist=True):
    """Resolve a path and prove it is below the configured sandbox root."""
    candidate = Path(path).resolve(strict=must_exist)
    root = SANDBOX_DIRECTORY.resolve()
    if candidate == root or not candidate.is_relative_to(root):
        raise ValueError("The path must identify a proposal inside SAD's sandbox directory.")
    return candidate


def _validated_proposal_id(proposal_id):
    try:
        return str(uuid.UUID(str(proposal_id)))
    except (ValueError, AttributeError, TypeError) as error:
        raise ValueError("Proposal ID must be a valid UUID.") from error


def _validated_target_path(sandbox_path, target_file):
    if target_file not in ALLOWED_TARGET_FILES:
        raise ValueError("The target file is not approved for sandbox proposals.")
    target = sandbox_path / target_file
    if target.is_symlink() or not target.is_file() or target.resolve() != target.absolute():
        raise ValueError("The sandbox target must be a regular file directly inside the proposal.")
    return target


def _hash_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_live_project():
    """Fingerprint live project files, excluding disposable sandbox and Git state."""
    manifest = {}
    for path in PROJECT_DIRECTORY.rglob("*"):
        if not path.is_file() or ".git" in path.parts or SANDBOX_DIRECTORY in path.parents:
            continue
        manifest[path.relative_to(PROJECT_DIRECTORY).as_posix()] = _hash_file(path)
    return manifest


def _git_directory():
    dot_git = PROJECT_DIRECTORY / ".git"
    if dot_git.is_dir():
        return dot_git.resolve()
    if dot_git.is_file():
        value = dot_git.read_text(encoding="utf-8").strip()
        if value.lower().startswith("gitdir:"):
            return (PROJECT_DIRECTORY / value.split(":", 1)[1].strip()).resolve()
    return None


def snapshot_git_topology():
    """Fingerprint the repository control plane independently of source files."""
    git_dir = _git_directory()
    manifest = {"git_dir": str(git_dir) if git_dir else None}
    if not git_dir:
        return manifest
    for name in PROTECTED_GIT_PATHS:
        path = git_dir / name
        if path.is_file():
            manifest[name] = {"type": "file", "sha256": _hash_file(path)}
        elif path.is_dir():
            manifest[name] = {
                "type": "directory",
                "entries": {
                    child.relative_to(path).as_posix(): _hash_file(child)
                    for child in sorted(path.rglob("*")) if child.is_file()
                },
            }
        else:
            manifest[name] = {"type": "missing"}
    lfs = PROJECT_DIRECTORY / ".lfsconfig"
    manifest[".lfsconfig"] = _hash_file(lfs) if lfs.is_file() else None
    return manifest


def verify_context_execution_root(context_root, execution_root):
    """Reject prompt context sourced from a different tree than execution."""
    return Path(context_root).resolve() == Path(execution_root).resolve()


def sandbox_has_host_only_git_authority(sandbox_path, environment=None):
    """Prove the worker copy lacks Git control metadata and common credentials."""
    path = validate_sandbox_path(sandbox_path)
    env = os.environ if environment is None else environment
    return not (path / ".git").exists() and not any(env.get(name) for name in GIT_CREDENTIAL_ENVIRONMENT)


def build_worker_environment(environment=None):
    """Return a worker environment with Git credentials explicitly removed."""
    source = os.environ if environment is None else environment
    clean = {name: value for name, value in source.items() if name.upper() in SAFE_WORKER_ENVIRONMENT}
    clean["GIT_TERMINAL_PROMPT"] = "0"
    return clean


def _evidence(event_type, details):
    return {"sequence": 0, "timestamp": datetime.now().isoformat(timespec="milliseconds"), "event": event_type, "details": details}


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
        "base_target_sha256": _hash_file(PROJECT_DIRECTORY / target_file),
    }

    with (sandbox_path / "proposal.json").open("w", encoding="utf-8") as file:
        json.dump(proposal, file, indent=2)

    return proposal, sandbox_path


def run_sandbox_tests(sandbox_path, runner=None):
    """Run tests through a genuine container boundary; never fall back locally."""
    sandbox_path = validate_sandbox_path(sandbox_path)
    live_before = snapshot_live_project()
    git_before = snapshot_git_topology()
    worker_environment = build_worker_environment()
    context_ok = verify_context_execution_root(sandbox_path, sandbox_path)
    authority_ok = sandbox_has_host_only_git_authority(sandbox_path, worker_environment)
    evidence = [
        _evidence("boundary_validated", {"sandbox_path": str(sandbox_path)}),
        _evidence("live_project_snapshotted", {"file_count": len(live_before)}),
        _evidence("git_topology_snapshotted", {"git_dir": git_before.get("git_dir")}),
        _evidence("context_execution_root_checked", {"passed": context_ok}),
        _evidence("host_only_git_authority_checked", {"passed": authority_ok}),
    ]
    runner = runner or DockerSandboxRunner()
    isolation_unavailable = None
    try:
        result = runner.run_tests(sandbox_path)
    except SandboxUnavailable as error:
        isolation_unavailable = str(error)
        result = SandboxResult(126, "", isolation_unavailable)

    live_after = snapshot_live_project()
    git_after = snapshot_git_topology()
    integrity_ok = live_before == live_after and git_before == git_after
    evidence.append(_evidence("tests_finished", {"returncode": result.returncode}))
    if isolation_unavailable:
        evidence.append(_evidence("container_isolation_unavailable", {"reason": isolation_unavailable}))
    evidence.append(_evidence("integrity_verified", {"passed": integrity_ok}))
    for sequence, event in enumerate(evidence, 1):
        event["sequence"] = sequence

    proposal_path = sandbox_path / "proposal.json"
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    if isolation_unavailable:
        proposal["status"] = "isolation_unavailable"
    elif not integrity_ok or not authority_ok or not context_ok:
        proposal["status"] = "isolation_failed"
    else:
        proposal["status"] = "sandbox_tests_passed" if result.returncode == 0 else "sandbox_tests_failed"
    proposal["test_output"] = result.stdout + result.stderr
    proposal["ordered_evidence"] = evidence
    proposal["live_project_integrity"] = live_before == live_after
    proposal["git_topology_integrity"] = git_before == git_after
    proposal["host_only_git_authority"] = authority_ok
    proposal["context_execution_root_match"] = context_ok
    proposal_path.write_text(json.dumps(proposal, indent=2), encoding="utf-8")

    return proposal


def create_draft_patch(sandbox_path, target_file, find_text, replacement_text):
    """Edit one approved file only inside a sandbox and save a reviewable diff."""
    sandbox_path = validate_sandbox_path(sandbox_path)

    target_path = _validated_target_path(sandbox_path, target_file)
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
    proposal_id = _validated_proposal_id(proposal_id)
    sandbox_path = validate_sandbox_path(SANDBOX_DIRECTORY / proposal_id, must_exist=False)

    proposal_path = sandbox_path / "proposal.json"
    if not proposal_path.exists():
        raise ValueError("That sandbox proposal was not found.")

    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    if proposal.get("proposal_id") != proposal_id:
        raise ValueError("Proposal identity does not match its directory.")
    _validated_target_path(sandbox_path, proposal.get("target_file"))
    return proposal, proposal.get("draft_diff", "")


def _validate_patch_scope(diff, target_file):
    """Allow a text patch for exactly one approved repository-root file."""
    if not isinstance(diff, str) or "GIT binary patch" in diff or "\0" in diff:
        raise ValueError("Only a text patch is allowed.")
    old_headers = [line for line in diff.splitlines() if line.startswith("--- ")]
    new_headers = [line for line in diff.splitlines() if line.startswith("+++ ")]
    if old_headers != [f"--- original/{target_file}"] or new_headers != [f"+++ proposed/{target_file}"]:
        raise ValueError("The patch must modify exactly its approved target file.")


def approve_sandbox_proposal(proposal_id):
    """Mark a passing sandbox draft approved by a human, without applying it."""
    proposal, _ = get_sandbox_proposal(proposal_id)
    if proposal.get("status") != "sandbox_tests_passed":
        return None

    _validate_patch_scope(proposal.get("draft_diff", ""), proposal["target_file"])
    sandbox_path = validate_sandbox_path(SANDBOX_DIRECTORY / _validated_proposal_id(proposal_id))
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
    _validate_patch_scope(diff, target_file)
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

    sandbox_path = validate_sandbox_path(SANDBOX_DIRECTORY / _validated_proposal_id(proposal_id))
    exported_path = sandbox_path / "approved.patch"
    exported_path.write_text(exported_diff, encoding="utf-8")
    return exported_path


def validate_approved_patch(proposal_id):
    """Check an approved patch against live files without applying anything."""
    exported_path = export_approved_patch(proposal_id)
    proposal, diff = get_sandbox_proposal(proposal_id)
    target_file = proposal["target_file"]
    _validate_patch_scope(diff, target_file)
    live_target = PROJECT_DIRECTORY / target_file
    expected_hash = proposal.get("base_target_sha256")
    is_valid = bool(expected_hash) and live_target.is_file() and not live_target.is_symlink() and hmac_compare_hash(_hash_file(live_target), expected_hash)
    return {
        "proposal_id": proposal_id,
        "patch_path": exported_path,
        "is_valid": is_valid,
        "details": "" if is_valid else "The live target no longer matches the proposal's recorded source hash.",
    }


def hmac_compare_hash(actual, expected):
    """Constant-time comparison keeps integrity checks uniform."""
    import hmac
    return hmac.compare_digest(actual, expected)
