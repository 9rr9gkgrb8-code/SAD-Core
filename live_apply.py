"""Owner-controlled application of a tested and approved sandbox proposal."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import uuid

from sandbox import (
    PROJECT_DIRECTORY,
    SANDBOX_DIRECTORY,
    get_sandbox_proposal,
    validate_approved_patch,
    validate_sandbox_path,
    hmac_compare_hash,
)


def _hash_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _live_target(target_file):
    target = PROJECT_DIRECTORY / target_file
    if target.parent.resolve() != PROJECT_DIRECTORY.resolve():
        raise ValueError("Live repair target must be a repository-root file.")
    if target.is_symlink() or not target.is_file():
        raise ValueError("Live repair target must be a regular file.")
    return target


def apply_approved_proposal(proposal_id):
    """Atomically copy the exact tested sandbox target into the live project.

    No Git command is run here. A backup is retained inside the proposal directory.
    If the live write or verification fails, the original target is restored.
    """
    proposal, _ = get_sandbox_proposal(proposal_id)
    if proposal.get("status") != "draft_approved_by_human":
        raise ValueError("The proposal must be human-approved before live application.")

    validation = validate_approved_patch(proposal_id)
    if not validation["is_valid"]:
        raise ValueError(validation["details"] or "The approved patch is stale.")

    target_file = proposal["target_file"]
    sandbox_path = validate_sandbox_path(Path(validation["patch_path"]).parent)
    proposed_target = sandbox_path / target_file
    live_target = _live_target(target_file)
    if proposed_target.is_symlink() or not proposed_target.is_file():
        raise ValueError("The tested sandbox target is unavailable.")

    proposed_hash = _hash_file(proposed_target)
    tested_hash = proposal.get("tested_target_sha256")
    if not tested_hash or not hmac_compare_hash(proposed_hash, tested_hash):
        raise ValueError("The approved bytes no longer match the tested target hash.")
    original_hash = _hash_file(live_target)
    if proposed_hash == original_hash:
        raise ValueError("The approved proposal does not change the live target.")

    backup_path = sandbox_path / f"live_backup.{target_file}"
    shutil.copy2(live_target, backup_path)
    temporary = live_target.with_name(f".{live_target.name}.sad-apply-{uuid.uuid4().hex}.tmp")

    try:
        shutil.copy2(proposed_target, temporary)
        os.replace(temporary, live_target)
        applied_hash = _hash_file(live_target)
        if applied_hash != proposed_hash:
            raise OSError("Applied target hash does not match the tested proposal.")
    except Exception:
        if temporary.exists():
            temporary.unlink()
        restore = live_target.with_name(f".{live_target.name}.sad-restore-{uuid.uuid4().hex}.tmp")
        shutil.copy2(backup_path, restore)
        os.replace(restore, live_target)
        if _hash_file(live_target) != original_hash:
            raise RuntimeError("Live repair failed and automatic rollback could not be verified.")
        raise

    receipt = {
        "proposal_id": proposal_id,
        "target_file": target_file,
        "base_sha256": original_hash,
        "applied_sha256": proposed_hash,
        "backup_file": backup_path.name,
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "git_authority_used": False,
    }
    proposal_path = sandbox_path / "proposal.json"
    proposal["status"] = "applied_to_live_project"
    proposal["live_application"] = receipt
    proposal_path.write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    return receipt


def rollback_applied_proposal(proposal_id):
    """Restore a previously applied proposal from its preserved local backup."""
    proposal, _ = get_sandbox_proposal(proposal_id)
    receipt = proposal.get("live_application") or {}
    if proposal.get("status") != "applied_to_live_project" or receipt.get("proposal_id") != proposal_id:
        raise ValueError("That proposal is not an applied live repair.")
    target_file = proposal["target_file"]
    sandbox_path = validate_sandbox_path(SANDBOX_DIRECTORY / proposal_id, must_exist=True)
    backup_path = sandbox_path / receipt.get("backup_file", "")
    live_target = _live_target(target_file)
    if not backup_path.is_file() or _hash_file(live_target) != receipt.get("applied_sha256"):
        raise ValueError("Rollback refused because the live target or backup no longer matches the receipt.")
    temporary = live_target.with_name(f".{live_target.name}.sad-rollback-{uuid.uuid4().hex}.tmp")
    shutil.copy2(backup_path, temporary)
    os.replace(temporary, live_target)
    if _hash_file(live_target) != receipt.get("base_sha256"):
        raise RuntimeError("Rollback verification failed.")
    proposal["status"] = "rolled_back"
    proposal["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
    (sandbox_path / "proposal.json").write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    return {"proposal_id": proposal_id, "target_file": target_file, "rolled_back": True}
