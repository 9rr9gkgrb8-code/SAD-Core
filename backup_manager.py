"""Verified backup and restore for SAD private runtime state.

Backups are explicit operator artifacts. They contain private local data and must be
stored somewhere the operator trusts. Restore is offline-oriented and requires an
explicit approval flag.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

from runtime_database import RUNTIME_DB_FILE, RuntimeDatabase
from runtime_privacy import LOCAL_DATA_DIRECTORY, PRIVATE_RUNTIME_FILES, ROOT


BACKUP_FORMAT_VERSION = 1
MAX_BACKUP_FILES = 5_000
MAX_BACKUP_BYTES = 512_000_000
MANIFEST_NAME = "SAD_BACKUP_MANIFEST.json"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _safe_relative(path):
    pure = PurePosixPath(str(path).replace("\\", "/"))
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("Backup contains an unsafe path.")
    return pure.as_posix()


def _runtime_candidates(root=ROOT):
    root = Path(root).resolve()
    candidates = []
    for name in sorted(PRIVATE_RUNTIME_FILES):
        path = root / name
        if path.exists():
            candidates.append(path)
    env = root / ".env"
    if env.exists():
        candidates.append(env)
    local_data = root / "local_data"
    if local_data.exists():
        for path in sorted(local_data.rglob("*")):
            if path.is_file() and path.name not in {RUNTIME_DB_FILE.name + "-wal", RUNTIME_DB_FILE.name + "-shm"}:
                candidates.append(path)
    unique = []
    seen = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def _validate_source(path, root):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Backup source must be a regular file: {path}")
    resolved = path.resolve()
    root = Path(root).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Backup source escaped the SAD root.")
    return resolved.relative_to(root).as_posix()


def create_backup(destination, *, root=ROOT):
    """Create a hash-manifested ZIP, using SQLite's backup API for the runtime DB."""
    root = Path(root).resolve()
    destination = Path(destination).expanduser().resolve()
    if destination.is_relative_to(root):
        raise ValueError("Store backups outside the SAD project/runtime tree.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.is_symlink():
        raise ValueError("Backup destination must not be a symlink.")

    files = []
    total = 0
    with tempfile.TemporaryDirectory() as temporary_dir:
        temporary_dir = Path(temporary_dir)
        db_snapshot = None
        live_db = root / "local_data" / RUNTIME_DB_FILE.name
        if live_db.exists():
            db_snapshot = temporary_dir / RUNTIME_DB_FILE.name
            RuntimeDatabase(live_db).snapshot(db_snapshot)

        payloads = []
        for path in _runtime_candidates(root):
            relative = _validate_source(path, root)
            source = db_snapshot if db_snapshot is not None and path.resolve() == live_db.resolve() else path
            data = source.read_bytes()
            total += len(data)
            if total > MAX_BACKUP_BYTES:
                raise ValueError("Runtime backup exceeds the configured size limit.")
            payloads.append((relative, data))
            files.append({"path": relative, "size": len(data), "sha256": _sha256(data)})
        if len(payloads) > MAX_BACKUP_FILES:
            raise ValueError("Runtime backup contains too many files.")

        manifest = {
            "format": "sad-runtime-backup",
            "format_version": BACKUP_FORMAT_VERSION,
            "created_at": _now(),
            "file_count": len(files),
            "total_bytes": total,
            "files": files,
        }
        temporary_zip = destination.with_suffix(destination.suffix + ".tmp")
        temporary_zip.unlink(missing_ok=True)
        with zipfile.ZipFile(temporary_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2))
            for relative, data in payloads:
                archive.writestr(relative, data)
        os.replace(temporary_zip, destination)
    return verify_backup(destination)


def verify_backup(path):
    path = Path(path).expanduser().resolve()
    if path.is_symlink() or not path.is_file():
        raise ValueError("Backup must be an existing regular file.")
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        if names.count(MANIFEST_NAME) != 1 or len(names) != len(set(names)):
            raise ValueError("Backup manifest is missing or archive paths are duplicated.")
        manifest = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
        if manifest.get("format") != "sad-runtime-backup" or manifest.get("format_version") != BACKUP_FORMAT_VERSION:
            raise ValueError("Unsupported SAD backup format.")
        entries = manifest.get("files")
        if not isinstance(entries, list) or len(entries) > MAX_BACKUP_FILES:
            raise ValueError("Invalid SAD backup manifest.")
        expected_names = {MANIFEST_NAME}
        total = 0
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("Invalid SAD backup entry.")
            relative = _safe_relative(entry.get("path", ""))
            expected_names.add(relative)
            data = archive.read(relative)
            total += len(data)
            if total > MAX_BACKUP_BYTES:
                raise ValueError("Backup exceeds the configured size limit.")
            if len(data) != entry.get("size") or _sha256(data) != entry.get("sha256"):
                raise ValueError(f"Backup integrity check failed for {relative}.")
            if relative == f"local_data/{RUNTIME_DB_FILE.name}":
                with tempfile.TemporaryDirectory() as temporary_dir:
                    snapshot = Path(temporary_dir) / RUNTIME_DB_FILE.name
                    snapshot.write_bytes(data)
                    if not RuntimeDatabase.verify_snapshot(snapshot):
                        raise ValueError("Runtime database snapshot failed SQLite integrity verification.")
        if set(names) != expected_names:
            raise ValueError("Backup contains files not declared by its manifest.")
        if manifest.get("file_count") != len(entries) or manifest.get("total_bytes") != total:
            raise ValueError("Backup manifest totals do not match archive contents.")
    return manifest


def restore_backup(path, *, root=ROOT, explicitly_approved=False):
    """Restore verified private state. SAD should be stopped while this runs."""
    if not explicitly_approved:
        raise PermissionError("Explicit approval is required before restoring SAD private state.")
    root = Path(root).resolve()
    manifest = verify_backup(path)
    with zipfile.ZipFile(Path(path).expanduser().resolve(), "r") as archive, tempfile.TemporaryDirectory() as stage_dir:
        stage_dir = Path(stage_dir)
        staged = []
        for entry in manifest["files"]:
            relative = _safe_relative(entry["path"])
            target = (root / relative).resolve()
            if not target.is_relative_to(root):
                raise ValueError("Restore target escaped the SAD root.")
            staged_path = stage_dir / relative
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            staged_path.write_bytes(archive.read(relative))
            if relative == f"local_data/{RUNTIME_DB_FILE.name}" and not RuntimeDatabase.verify_snapshot(staged_path):
                raise ValueError("Staged runtime database failed integrity verification.")
            staged.append((staged_path, target))

        originals = {}
        replaced = []
        try:
            for staged_path, target in staged:
                if target.exists():
                    if target.is_symlink() or not target.is_file():
                        raise ValueError(f"Restore target is not a regular file: {target}")
                    originals[target] = target.read_bytes()
                else:
                    originals[target] = None
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_suffix(target.suffix + ".restore-tmp")
                temporary.write_bytes(staged_path.read_bytes())
                try:
                    os.chmod(temporary, 0o600)
                except OSError:
                    pass
                os.replace(temporary, target)
                replaced.append(target)
        except Exception:
            for target in reversed(replaced):
                prior = originals[target]
                if prior is None:
                    target.unlink(missing_ok=True)
                else:
                    temporary = target.with_suffix(target.suffix + ".rollback-tmp")
                    temporary.write_bytes(prior)
                    os.replace(temporary, target)
            raise
    return {"restored": True, "file_count": manifest["file_count"], "created_at": manifest["created_at"]}
