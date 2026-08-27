"""Governed multi-file coding workspace for SAD.

The local model may plan and edit only an explicitly approved file scope inside a
private copy of the project. Docker verifies that copy. Only the host-side Owner
API may later apply the exact tested files to the live project. No Git command or
repository credential is available to the workspace.
"""

from __future__ import annotations

from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import threading
import uuid

from container_sandbox import DockerSandboxRunner, SandboxResult, SandboxUnavailable
from model_adapter import generate_local_response
from sandbox import PROJECT_DIRECTORY, snapshot_git_topology, snapshot_live_project


DEV_WORKSPACE_DIRECTORY = PROJECT_DIRECTORY / ".sad_dev"
MAX_ALLOWED_PATHS = 20
MAX_EDITS = 20
MAX_TASK_CHARACTERS = 20_000
MAX_CONTEXT_CHARACTERS = 1_000_000
MAX_FILE_CHARACTERS = 300_000
MAX_GENERATED_CHARACTERS = 1_200_000
MAX_TEST_OUTPUT_CHARACTERS = 300_000
ALLOWED_SUFFIXES = {
    ".py", ".js", ".css", ".html", ".md", ".json", ".yml", ".yaml",
    ".ps1", ".svg", ".webmanifest", ".txt",
}
PROTECTED_TOP_LEVEL = {
    ".git", ".github", ".sad_sandbox", ".sad_dev", "local_data", "__pycache__",
}
PRIVATE_RUNTIME_FILES = {
    "accounts.json", "chat_history.json", "dashboard_state.json", "student_progress.json",
    "failures.json", "settings.json",
}


class DeveloperWorkspaceError(ValueError):
    """Raised when a developer workspace request cannot be proven safe."""


def _now():
    return datetime.now(timezone.utc)


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_task(task):
    if not isinstance(task, str):
        raise DeveloperWorkspaceError("Coding task must be text.")
    value = task.strip()
    if not value or len(value) > MAX_TASK_CHARACTERS:
        raise DeveloperWorkspaceError("Coding task must be 1-20000 characters.")
    return value


def normalize_scope_path(value):
    """Return one repository-relative source path or reject it fail-closed."""
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise DeveloperWorkspaceError("Workspace paths must be non-empty text.")
    normalized = value.strip().replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise DeveloperWorkspaceError("Workspace paths must be clean repository-relative paths.")
    if len(path.parts) > 8 or len(normalized) > 240:
        raise DeveloperWorkspaceError("Workspace path is too deep or too long.")
    if path.parts[0] in PROTECTED_TOP_LEVEL or path.name in PRIVATE_RUNTIME_FILES:
        raise DeveloperWorkspaceError("That path is protected from the coding workspace.")
    if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
        raise DeveloperWorkspaceError("Environment secret files are protected from the coding workspace.")
    if any(part.startswith(".") for part in path.parts if part != ".env.example"):
        raise DeveloperWorkspaceError("Hidden repository paths are protected from the coding workspace.")
    if path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise DeveloperWorkspaceError("That file type is not approved for automatic coding.")
    return path.as_posix()


def _scope(values):
    if not isinstance(values, list) or not values:
        raise DeveloperWorkspaceError("At least one approved workspace path is required.")
    if len(values) > MAX_ALLOWED_PATHS:
        raise DeveloperWorkspaceError(f"A workspace may approve at most {MAX_ALLOWED_PATHS} paths.")
    paths = [normalize_scope_path(value) for value in values]
    if len(set(paths)) != len(paths):
        raise DeveloperWorkspaceError("Approved workspace paths must be unique.")
    return paths


def _safe_live_path(project_root, relative, allow_missing=False):
    root = Path(project_root).resolve()
    relative = normalize_scope_path(relative)
    target = root.joinpath(*PurePosixPath(relative).parts)
    current = root
    for part in PurePosixPath(relative).parts[:-1]:
        current = current / part
        if current.exists() and current.is_symlink():
            raise DeveloperWorkspaceError("Workspace path crosses a symbolic link.")
    if target.exists() and target.is_symlink():
        raise DeveloperWorkspaceError("Workspace targets may not be symbolic links.")
    resolved_parent = target.parent.resolve()
    if resolved_parent != root and not resolved_parent.is_relative_to(root):
        raise DeveloperWorkspaceError("Workspace path escaped the project root.")
    if not allow_missing and not target.is_file():
        raise DeveloperWorkspaceError("Expected workspace source file is missing.")
    return target


def _copy_excluded(relative):
    parts = relative.parts
    if any(part in PROTECTED_TOP_LEVEL for part in parts):
        return True
    if relative.name in PRIVATE_RUNTIME_FILES:
        return True
    if relative.name == ".env" or (relative.name.startswith(".env.") and relative.name != ".env.example"):
        return True
    return False


def _copy_project(project_root, destination):
    project_root = Path(project_root).resolve()
    destination = Path(destination)
    for source in project_root.rglob("*"):
        if source.is_symlink() or not source.is_file():
            continue
        relative = source.relative_to(project_root)
        if _copy_excluded(relative):
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _source_tree(project_root):
    paths = []
    root = Path(project_root).resolve()
    for source in root.rglob("*"):
        if source.is_symlink() or not source.is_file():
            continue
        relative = source.relative_to(root)
        if _copy_excluded(relative):
            continue
        try:
            paths.append(normalize_scope_path(relative.as_posix()))
        except DeveloperWorkspaceError:
            continue
    return sorted(set(paths))


def _parse_scope_plan(raw):
    if not isinstance(raw, str) or not raw.strip():
        raise DeveloperWorkspaceError("The local coding model did not return a scope plan.")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise DeveloperWorkspaceError("The local coding model must return JSON only for scope planning.") from error
    if not isinstance(data, dict):
        raise DeveloperWorkspaceError("The coding scope plan has an invalid shape.")
    paths = _scope(data.get("paths"))
    summary = data.get("summary", "")
    if not isinstance(summary, str) or len(summary) > 10_000:
        raise DeveloperWorkspaceError("The coding scope summary is invalid.")
    return {"summary": summary.strip(), "paths": paths}


def suggest_scope(task, project_root=PROJECT_DIRECTORY, generator=None):
    """Ask the local model for file names only. A human must still approve the scope."""
    task = _clean_task(task)
    tree = _source_tree(project_root)
    rendered = "\n".join(tree)
    prompt = (
        "You are SAD's coding scope planner. Choose the smallest set of project files needed "
        "for the task below. You may include new source-file paths. Return ONLY one JSON object "
        "with fields summary (string) and paths (array of repository-relative file strings). "
        f"Use at most {MAX_ALLOWED_PATHS} paths. Do not include .git, .github, hidden paths, "
        "runtime/private data, credentials, or environment secrets. Do not write code yet.\n\n"
        f"TASK:\n{task}\n\nCURRENT PROJECT FILES:\n{rendered}"
    )
    generate = generator or (lambda text: generate_local_response(text, "SAD coding scope planner", []))
    return _parse_scope_plan(generate(prompt))


def _parse_edit_plan(raw, allowed_paths, existing_paths):
    if not isinstance(raw, str) or not raw.strip():
        raise DeveloperWorkspaceError("The local coding model did not return an implementation plan.")
    if len(raw) > MAX_GENERATED_CHARACTERS:
        raise DeveloperWorkspaceError("The generated implementation plan is too large.")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise DeveloperWorkspaceError("The local coding model must return JSON only for implementation.") from error
    if not isinstance(data, dict) or not isinstance(data.get("edits"), list):
        raise DeveloperWorkspaceError("The coding implementation plan has an invalid shape.")
    edits = data["edits"]
    if not 1 <= len(edits) <= MAX_EDITS:
        raise DeveloperWorkspaceError(f"The coding plan must contain 1-{MAX_EDITS} edits.")
    allowed = set(allowed_paths)
    seen = set()
    parsed = []
    total = 0
    for item in edits:
        if not isinstance(item, dict):
            raise DeveloperWorkspaceError("Every coding edit must be an object.")
        path = normalize_scope_path(item.get("path"))
        if path not in allowed or path in seen:
            raise DeveloperWorkspaceError("Every coding edit must target one unique human-approved path.")
        seen.add(path)
        action = item.get("action")
        if action not in {"write", "delete"}:
            raise DeveloperWorkspaceError("Coding edit action must be write or delete.")
        exists = path in existing_paths
        if action == "delete":
            if not exists:
                raise DeveloperWorkspaceError("The coding model cannot delete a file that did not exist in the approved snapshot.")
            content = None
        else:
            content = item.get("content")
            if not isinstance(content, str) or len(content) > MAX_FILE_CHARACTERS:
                raise DeveloperWorkspaceError("Generated file content is invalid or too large.")
            total += len(content)
            if total > MAX_GENERATED_CHARACTERS:
                raise DeveloperWorkspaceError("Generated source exceeds the workspace size limit.")
        parsed.append({"path": path, "action": action, "content": content})
    summary = data.get("summary", "")
    if not isinstance(summary, str) or len(summary) > 10_000:
        raise DeveloperWorkspaceError("Implementation summary is invalid.")
    return {"summary": summary.strip(), "edits": parsed}


def _diff_text(path, before, after):
    return "".join(difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    ))


class DeveloperWorkspaceStore:
    """Persist and execute isolated multi-file coding workspaces."""

    def __init__(self, project_root=PROJECT_DIRECTORY, workspace_root=None, runner_factory=None, now=None):
        self.project_root = Path(project_root).resolve()
        self.workspace_root = Path(workspace_root or (self.project_root / ".sad_dev")).resolve()
        if self.workspace_root == self.project_root or not self.workspace_root.is_relative_to(self.project_root):
            raise DeveloperWorkspaceError("Developer workspace root must be inside the project root.")
        self.runner_factory = runner_factory or DockerSandboxRunner
        self.now = now or _now
        self.lock = threading.RLock()

    def _workspace_dir(self, workspace_id, must_exist=True):
        try:
            workspace_id = str(uuid.UUID(str(workspace_id)))
        except (ValueError, TypeError, AttributeError) as error:
            raise DeveloperWorkspaceError("Workspace ID must be a valid UUID.") from error
        path = (self.workspace_root / workspace_id).resolve(strict=False)
        if path.parent != self.workspace_root:
            raise DeveloperWorkspaceError("Workspace path escaped the workspace root.")
        if must_exist and not path.is_dir():
            raise KeyError("Developer workspace not found.")
        return path

    def _load(self, workspace_id):
        root = self._workspace_dir(workspace_id)
        path = root / "workspace.json"
        if not path.is_file() or path.stat().st_size > 4_000_000:
            raise DeveloperWorkspaceError("Developer workspace metadata is missing or invalid.")
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or data.get("workspace_id") != root.name:
            raise DeveloperWorkspaceError("Developer workspace identity is invalid.")
        return data

    def _save(self, data):
        root = self._workspace_dir(data["workspace_id"])
        path = root / "workspace.json"
        payload = json.dumps(data, indent=2)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(payload, encoding="utf-8")
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        os.replace(temporary, path)

    @staticmethod
    def _public(data, detailed=False):
        keys = (
            "workspace_id", "created_at", "updated_at", "created_by", "task", "allowed_paths",
            "state", "summary", "changed_paths", "tests", "applied_at", "rolled_back_at",
        )
        payload = {key: data.get(key) for key in keys if key in data}
        if detailed:
            payload["diff"] = data.get("diff", "")
            payload["test_output"] = data.get("test_output", "")
            payload["evidence"] = data.get("evidence", [])
            payload["application"] = data.get("application")
        return payload

    def create(self, task, allowed_paths, actor_account_id):
        task = _clean_task(task)
        allowed_paths = _scope(allowed_paths)
        if not isinstance(actor_account_id, str) or not actor_account_id:
            raise DeveloperWorkspaceError("Workspace creator account is required.")
        with self.lock:
            workspace_id = str(uuid.uuid4())
            root = self._workspace_dir(workspace_id, must_exist=False)
            root.mkdir(parents=True)
            worktree = root / "worktree"
            baseline = root / "baseline"
            worktree.mkdir()
            baseline.mkdir()
            _copy_project(self.project_root, worktree)
            base_manifest = {}
            for relative in allowed_paths:
                live = _safe_live_path(self.project_root, relative, allow_missing=True)
                if live.exists():
                    if not live.is_file():
                        raise DeveloperWorkspaceError("Approved workspace target must be a regular file or a new file path.")
                    base_manifest[relative] = _sha256(live)
                    saved = baseline.joinpath(*PurePosixPath(relative).parts)
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(live, saved)
                else:
                    base_manifest[relative] = None
            timestamp = self.now().isoformat()
            data = {
                "schema_version": 1,
                "workspace_id": workspace_id,
                "created_at": timestamp,
                "updated_at": timestamp,
                "created_by": actor_account_id,
                "task": task,
                "allowed_paths": allowed_paths,
                "base_manifest": base_manifest,
                "state": "scope_approved",
                "summary": "",
                "changed_paths": [],
                "tested_manifest": {},
                "diff": "",
                "test_output": "",
                "tests": None,
                "evidence": [],
            }
            self._save(data)
            return self._public(data, detailed=True)

    def list(self):
        with self.lock:
            if not self.workspace_root.exists():
                return []
            items = []
            for child in self.workspace_root.iterdir():
                if not child.is_dir():
                    continue
                try:
                    items.append(self._public(self._load(child.name)))
                except (DeveloperWorkspaceError, KeyError, json.JSONDecodeError):
                    continue
            return sorted(items, key=lambda item: item.get("updated_at", ""), reverse=True)

    def get(self, workspace_id):
        with self.lock:
            return self._public(self._load(workspace_id), detailed=True)

    def _context(self, data, worktree):
        parts = []
        total = 0
        existing = set()
        for relative in data["allowed_paths"]:
            target = worktree.joinpath(*PurePosixPath(relative).parts)
            if target.exists():
                if target.is_symlink() or not target.is_file():
                    raise DeveloperWorkspaceError("Approved worktree target is not a regular file.")
                text = target.read_text(encoding="utf-8")
                if len(text) > MAX_FILE_CHARACTERS:
                    raise DeveloperWorkspaceError(f"{relative} is too large for automatic coding.")
                existing.add(relative)
                rendered = f"\n===== {relative} =====\n{text}"
            else:
                rendered = f"\n===== {relative} (NEW FILE) =====\n"
            total += len(rendered)
            if total > MAX_CONTEXT_CHARACTERS:
                raise DeveloperWorkspaceError("Approved coding context is too large; use a smaller file scope.")
            parts.append(rendered)
        return "".join(parts), existing

    def execute(self, workspace_id, generator=None, runner=None):
        """Generate multi-file edits, apply them only to the copy, then run Docker tests."""
        with self.lock:
            data = self._load(workspace_id)
            if data["state"] != "scope_approved":
                raise DeveloperWorkspaceError("Only a newly approved scope can be executed.")
            root = self._workspace_dir(workspace_id)
            worktree = root / "worktree"
            context, existing = self._context(data, worktree)
            prompt = (
                "You are SAD's isolated coding agent. Implement the task using ONLY the human-approved "
                "paths below. Return ONLY one JSON object with summary (string) and edits (array). Each "
                "edit must contain path, action, and for write actions content. action is write or delete. "
                "For write, content must be the COMPLETE final contents of that file. Do not use markdown "
                "fences. Do not touch files outside the approved list. Preserve security boundaries, tests, "
                "authentication, local-first behavior, and human approval controls unless the task explicitly "
                "and safely requires a scoped change. Never add Git commands, credentials, remote shells, "
                "public-network binding, or self-approval.\n\n"
                f"TASK:\n{data['task']}\n\nAPPROVED PATHS:\n" + "\n".join(data["allowed_paths"]) +
                "\n\nAPPROVED SOURCE CONTEXT:" + context
            )
            generate = generator or (lambda text: generate_local_response(text, "SAD isolated coding agent", []))
            plan = _parse_edit_plan(generate(prompt), data["allowed_paths"], existing)

            changed = []
            diffs = []
            for edit in plan["edits"]:
                relative = edit["path"]
                target = worktree.joinpath(*PurePosixPath(relative).parts)
                baseline = root.joinpath("baseline", *PurePosixPath(relative).parts)
                before = baseline.read_text(encoding="utf-8") if baseline.is_file() else ""
                if edit["action"] == "delete":
                    if not target.is_file() or target.is_symlink():
                        raise DeveloperWorkspaceError("Delete target is unavailable in the isolated workspace.")
                    target.unlink()
                    after = ""
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists() and (target.is_symlink() or not target.is_file()):
                        raise DeveloperWorkspaceError("Write target is not a regular workspace file.")
                    target.write_text(edit["content"], encoding="utf-8")
                    after = edit["content"]
                if before == after:
                    raise DeveloperWorkspaceError("The coding plan contains a no-op edit.")
                changed.append(relative)
                diffs.append(_diff_text(relative, before, after))

            live_before = snapshot_live_project()
            git_before = snapshot_git_topology()
            test_runner = runner or self.runner_factory()
            isolation_error = None
            try:
                result = test_runner.run_tests(worktree)
            except SandboxUnavailable as error:
                isolation_error = str(error)
                result = SandboxResult(126, "", isolation_error)
            live_after = snapshot_live_project()
            git_after = snapshot_git_topology()
            integrity = live_before == live_after and git_before == git_after
            passed = result.returncode == 0 and integrity and isolation_error is None
            tested_manifest = {}
            for relative in changed:
                target = worktree.joinpath(*PurePosixPath(relative).parts)
                tested_manifest[relative] = _sha256(target) if target.is_file() else None

            timestamp = self.now().isoformat()
            data.update({
                "updated_at": timestamp,
                "state": "tests_passed" if passed else ("isolation_unavailable" if isolation_error else "tests_failed"),
                "summary": plan["summary"],
                "changed_paths": changed,
                "tested_manifest": tested_manifest,
                "diff": "\n".join(diffs),
                "test_output": (result.stdout + result.stderr)[-MAX_TEST_OUTPUT_CHARACTERS:],
                "tests": {"returncode": result.returncode, "passed": passed},
                "evidence": [
                    {"event": "scope_enforced", "details": {"paths": list(data["allowed_paths"]) }},
                    {"event": "docker_tests_finished", "details": {"returncode": result.returncode}},
                    {"event": "live_and_git_integrity_verified", "details": {"passed": integrity}},
                    {"event": "git_authority_used", "details": {"value": False}},
                ],
            })
            if isolation_error:
                data["evidence"].append({"event": "isolation_unavailable", "details": {"reason": isolation_error}})
            self._save(data)
            return self._public(data, detailed=True)

    def _validate_for_apply(self, data):
        if data.get("state") != "tests_passed" or not data.get("tests", {}).get("passed"):
            raise DeveloperWorkspaceError("Only a passing tested workspace may be applied.")
        root = self._workspace_dir(data["workspace_id"])
        worktree = root / "worktree"
        changed = data.get("changed_paths") or []
        if not changed or not set(changed).issubset(set(data["allowed_paths"])):
            raise DeveloperWorkspaceError("Tested workspace scope is invalid.")
        for relative in changed:
            live = _safe_live_path(self.project_root, relative, allow_missing=True)
            base_hash = data["base_manifest"].get(relative)
            current_hash = _sha256(live) if live.is_file() else None
            if current_hash != base_hash:
                raise DeveloperWorkspaceError(f"Live source changed after workspace creation: {relative}")
            tested = data["tested_manifest"].get(relative)
            proposed = worktree.joinpath(*PurePosixPath(relative).parts)
            proposed_hash = _sha256(proposed) if proposed.is_file() else None
            if proposed_hash != tested:
                raise DeveloperWorkspaceError(f"Tested workspace content was modified after verification: {relative}")
        return root, worktree, changed

    def apply(self, workspace_id):
        """Atomically apply the exact tested file set, rolling back all files on failure."""
        with self.lock:
            data = self._load(workspace_id)
            root, worktree, changed = self._validate_for_apply(data)
            backups = root / "backups"
            backups.mkdir(exist_ok=True)
            created_dirs = []
            originals = {}
            for relative in changed:
                live = _safe_live_path(self.project_root, relative, allow_missing=True)
                originals[relative] = _sha256(live) if live.is_file() else None
                if live.is_file():
                    backup = backups.joinpath(*PurePosixPath(relative).parts)
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(live, backup)

            def restore_all():
                for relative in reversed(changed):
                    live = _safe_live_path(self.project_root, relative, allow_missing=True)
                    base_hash = originals[relative]
                    if base_hash is None:
                        if live.exists():
                            if live.is_file() and not live.is_symlink():
                                live.unlink()
                            else:
                                raise RuntimeError("Rollback encountered an unexpected created target.")
                    else:
                        backup = backups.joinpath(*PurePosixPath(relative).parts)
                        if not backup.is_file() or _sha256(backup) != base_hash:
                            raise RuntimeError("Developer workspace backup verification failed.")
                        live.parent.mkdir(parents=True, exist_ok=True)
                        temp = live.with_name(f".{live.name}.sad-dev-restore-{uuid.uuid4().hex}.tmp")
                        shutil.copy2(backup, temp)
                        os.replace(temp, live)
                for relative, base_hash in originals.items():
                    live = _safe_live_path(self.project_root, relative, allow_missing=True)
                    restored = _sha256(live) if live.is_file() else None
                    if restored != base_hash:
                        raise RuntimeError("Developer workspace rollback could not be verified.")
                for directory in sorted(created_dirs, key=lambda value: len(value.parts), reverse=True):
                    try:
                        directory.rmdir()
                    except OSError:
                        pass

            try:
                for relative in changed:
                    live = _safe_live_path(self.project_root, relative, allow_missing=True)
                    proposed = worktree.joinpath(*PurePosixPath(relative).parts)
                    tested_hash = data["tested_manifest"][relative]
                    if tested_hash is None:
                        if live.is_file():
                            live.unlink()
                        continue
                    missing_parents = []
                    parent = live.parent
                    while parent != self.project_root and not parent.exists():
                        missing_parents.append(parent)
                        parent = parent.parent
                    live.parent.mkdir(parents=True, exist_ok=True)
                    created_dirs.extend(missing_parents)
                    temp = live.with_name(f".{live.name}.sad-dev-apply-{uuid.uuid4().hex}.tmp")
                    shutil.copy2(proposed, temp)
                    os.replace(temp, live)
                    if _sha256(live) != tested_hash:
                        raise OSError("Applied file hash does not match the tested workspace.")
                for relative in changed:
                    live = _safe_live_path(self.project_root, relative, allow_missing=True)
                    current = _sha256(live) if live.is_file() else None
                    if current != data["tested_manifest"][relative]:
                        raise OSError("Applied workspace verification failed.")
            except Exception:
                restore_all()
                raise

            receipt = {
                "workspace_id": workspace_id,
                "paths": list(changed),
                "base_manifest": originals,
                "applied_manifest": {path: data["tested_manifest"][path] for path in changed},
                "backup_directory": "backups",
                "git_authority_used": False,
                "applied_at": self.now().isoformat(),
            }
            data["state"] = "applied"
            data["updated_at"] = receipt["applied_at"]
            data["applied_at"] = receipt["applied_at"]
            data["application"] = receipt
            try:
                self._save(data)
            except Exception:
                restore_all()
                raise
            return self._public(data, detailed=True)

    def rollback(self, workspace_id):
        """Owner-controlled rollback of an applied multi-file workspace."""
        with self.lock:
            data = self._load(workspace_id)
            receipt = data.get("application") or {}
            if data.get("state") != "applied" or receipt.get("workspace_id") != workspace_id:
                raise DeveloperWorkspaceError("Only an applied workspace may be rolled back.")
            root = self._workspace_dir(workspace_id)
            backups = root / receipt.get("backup_directory", "backups")
            for relative in receipt["paths"]:
                live = _safe_live_path(self.project_root, relative, allow_missing=True)
                expected_applied = receipt["applied_manifest"].get(relative)
                current = _sha256(live) if live.is_file() else None
                if current != expected_applied:
                    raise DeveloperWorkspaceError(f"Rollback refused because live code changed after application: {relative}")
            for relative in reversed(receipt["paths"]):
                live = _safe_live_path(self.project_root, relative, allow_missing=True)
                base_hash = receipt["base_manifest"].get(relative)
                if base_hash is None:
                    if live.is_file():
                        live.unlink()
                else:
                    backup = backups.joinpath(*PurePosixPath(relative).parts)
                    if not backup.is_file() or _sha256(backup) != base_hash:
                        raise DeveloperWorkspaceError("Rollback backup is missing or corrupted.")
                    live.parent.mkdir(parents=True, exist_ok=True)
                    temp = live.with_name(f".{live.name}.sad-dev-rollback-{uuid.uuid4().hex}.tmp")
                    shutil.copy2(backup, temp)
                    os.replace(temp, live)
            for relative in receipt["paths"]:
                live = _safe_live_path(self.project_root, relative, allow_missing=True)
                current = _sha256(live) if live.is_file() else None
                if current != receipt["base_manifest"].get(relative):
                    raise RuntimeError("Developer workspace rollback verification failed.")
            timestamp = self.now().isoformat()
            data["state"] = "rolled_back"
            data["updated_at"] = timestamp
            data["rolled_back_at"] = timestamp
            self._save(data)
            return self._public(data, detailed=True)
