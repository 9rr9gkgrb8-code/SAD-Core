"""Verified native and portable encrypted backup/restore for SAD private runtime state.

Native Windows backups use current-user DPAPI. Portable disaster-recovery backups use a
passphrase-derived AES-256-GCM key and export the runtime SQLite database to a host-neutral
form only in memory. Portable restore re-protects that database for the destination
Windows user before writing live runtime bytes.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import tempfile
import zipfile

from portable_crypto import (
    PORTABLE_MAGIC,
    PORTABLE_SCHEME,
    decrypt_portable,
    encrypt_portable,
)
from portable_runtime import (
    export_portable_runtime_bytes,
    reprotect_portable_runtime_bytes,
    verify_portable_runtime_bytes,
)
from runtime_database import AT_REST_SCHEME, RUNTIME_DB_FILE, RuntimeDatabase
from runtime_privacy import PRIVATE_RUNTIME_FILES, ROOT
from windows_crypto import protect_data, unprotect_data


BACKUP_FORMAT_VERSION = 2
SUPPORTED_BACKUP_FORMAT_VERSIONS = {1, 2}
MAX_BACKUP_FILES = 5_000
MAX_BACKUP_BYTES = 512_000_000
MANIFEST_NAME = "SAD_BACKUP_MANIFEST.json"
BACKUP_DPAPI_MAGIC = b"SAD-DPAPI-BACKUP\x00\x01\n"
BACKUP_DPAPI_PURPOSE = "backup-container:v1"
RUNTIME_MODE_NATIVE = "native-host-bound"
RUNTIME_MODE_PORTABLE = "portable-host-neutral"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _safe_relative(path):
    pure = PurePosixPath(str(path).replace("\\", "/"))
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("Backup contains an unsafe path.")
    return pure.as_posix()


def _runtime_candidates(root=ROOT, *, include_legacy_archives=True):
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
            if not path.is_file() or path.name in {RUNTIME_DB_FILE.name + "-wal", RUNTIME_DB_FILE.name + "-shm"}:
                continue
            relative = path.relative_to(root)
            if not include_legacy_archives and len(relative.parts) >= 2 and relative.parts[:2] == ("local_data", "legacy_imported"):
                continue
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


def _build_plain_backup_bytes(*, root=ROOT, runtime_mode=RUNTIME_MODE_NATIVE):
    if runtime_mode not in {RUNTIME_MODE_NATIVE, RUNTIME_MODE_PORTABLE}:
        raise ValueError("Unsupported backup runtime database mode.")
    root = Path(root).resolve()
    files = []
    total = 0
    with tempfile.TemporaryDirectory() as temporary_dir:
        temporary_dir = Path(temporary_dir)
        db_snapshot = None
        portable_db = None
        live_db = root / "local_data" / RUNTIME_DB_FILE.name
        if live_db.exists():
            if runtime_mode == RUNTIME_MODE_PORTABLE:
                portable_db = export_portable_runtime_bytes(live_db, database=RuntimeDatabase(live_db))
            else:
                db_snapshot = temporary_dir / RUNTIME_DB_FILE.name
                RuntimeDatabase(live_db).snapshot(db_snapshot)

        payloads = []
        candidates = _runtime_candidates(
            root, include_legacy_archives=runtime_mode == RUNTIME_MODE_NATIVE
        )
        for path in candidates:
            relative = _validate_source(path, root)
            if path.resolve() == live_db.resolve() and portable_db is not None:
                data = portable_db
            else:
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
            "runtime_database_mode": runtime_mode,
            "file_count": len(files),
            "total_bytes": total,
            "files": files,
        }
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2))
            for relative, data in payloads:
                archive.writestr(relative, data)
        raw = stream.getvalue()
        if len(raw) > MAX_BACKUP_BYTES + 16_000_000:
            raise ValueError("Backup container exceeds the configured size limit.")
        return raw


def _decode_backup_container(raw, *, allow_plaintext=False, passphrase=None):
    if raw.startswith(BACKUP_DPAPI_MAGIC):
        if platform.system() != "Windows":
            raise OSError("DPAPI-protected SAD backups can be opened only in their Windows protection context.")
        protected = raw[len(BACKUP_DPAPI_MAGIC):]
        if not protected:
            raise ValueError("Encrypted SAD backup payload is missing.")
        try:
            return unprotect_data(protected, purpose=BACKUP_DPAPI_PURPOSE), AT_REST_SCHEME
        except OSError as error:
            raise ValueError("SAD backup could not be decrypted in this Windows protection context.") from error
    if raw.startswith(PORTABLE_MAGIC):
        if passphrase is None:
            raise PermissionError("Portable SAD backup passphrase is required.")
        return decrypt_portable(raw, passphrase), PORTABLE_SCHEME
    if not allow_plaintext:
        raise ValueError("Plaintext/legacy SAD backup is blocked unless explicitly allowed for migration or compatibility.")
    return raw, "plaintext-legacy"


def _verify_plain_backup_bytes(raw):
    if len(raw) > MAX_BACKUP_BYTES + 16_000_000:
        raise ValueError("Backup container exceeds the configured size limit.")
    try:
        archive_context = zipfile.ZipFile(io.BytesIO(raw), "r")
    except zipfile.BadZipFile as error:
        raise ValueError("SAD backup payload is not a valid ZIP container.") from error
    with archive_context as archive:
        names = archive.namelist()
        if names.count(MANIFEST_NAME) != 1 or len(names) != len(set(names)):
            raise ValueError("Backup manifest is missing or archive paths are duplicated.")
        try:
            manifest = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("Backup manifest is invalid.") from error
        if manifest.get("format") != "sad-runtime-backup" or manifest.get("format_version") not in SUPPORTED_BACKUP_FORMAT_VERSIONS:
            raise ValueError("Unsupported SAD backup format.")
        runtime_mode = manifest.get("runtime_database_mode", RUNTIME_MODE_NATIVE)
        if runtime_mode not in {RUNTIME_MODE_NATIVE, RUNTIME_MODE_PORTABLE}:
            raise ValueError("Backup runtime database mode is unsupported.")
        if manifest.get("format_version") == 1 and runtime_mode != RUNTIME_MODE_NATIVE:
            raise ValueError("Legacy backup cannot claim portable runtime state.")
        entries = manifest.get("files")
        if not isinstance(entries, list) or len(entries) > MAX_BACKUP_FILES:
            raise ValueError("Invalid SAD backup manifest.")
        expected_names = {MANIFEST_NAME}
        total = 0
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("Invalid SAD backup entry.")
            relative = _safe_relative(entry.get("path", ""))
            if relative in expected_names:
                raise ValueError("Backup manifest contains duplicate file declarations.")
            expected_names.add(relative)
            try:
                data = archive.read(relative)
            except KeyError as error:
                raise ValueError(f"Backup manifest references missing file: {relative}.") from error
            total += len(data)
            if total > MAX_BACKUP_BYTES:
                raise ValueError("Backup exceeds the configured size limit.")
            if len(data) != entry.get("size") or _sha256(data) != entry.get("sha256"):
                raise ValueError(f"Backup integrity check failed for {relative}.")
            if relative == f"local_data/{RUNTIME_DB_FILE.name}":
                if runtime_mode == RUNTIME_MODE_PORTABLE:
                    verify_portable_runtime_bytes(data)
                elif not RuntimeDatabase.verify_snapshot_bytes(data):
                    raise ValueError("Runtime database snapshot failed SQLite integrity verification.")
        if set(names) != expected_names:
            raise ValueError("Backup contains files not declared by its manifest.")
        if manifest.get("file_count") != len(entries) or manifest.get("total_bytes") != total:
            raise ValueError("Backup manifest totals do not match archive contents.")
    return manifest


def create_backup(destination, *, root=ROOT, allow_plaintext=False):
    """Create a verified native backup. Windows defaults to current-user DPAPI."""
    root = Path(root).resolve()
    destination = Path(destination).expanduser().resolve()
    if destination.is_relative_to(root):
        raise ValueError("Store backups outside the SAD project/runtime tree.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.is_symlink():
        raise ValueError("Backup destination must not be a symlink.")

    plain = _build_plain_backup_bytes(root=root, runtime_mode=RUNTIME_MODE_NATIVE)
    if platform.system() == "Windows" and not allow_plaintext:
        protected = protect_data(plain, purpose=BACKUP_DPAPI_PURPOSE)
        output = BACKUP_DPAPI_MAGIC + protected
    elif allow_plaintext:
        output = plain
    else:
        raise OSError("Encrypted SAD backup creation currently requires Windows DPAPI; plaintext creation must be explicit.")
    _atomic_backup_write(destination, output)
    return verify_backup(destination, allow_plaintext=allow_plaintext)


def create_portable_backup(destination, passphrase, *, root=ROOT):
    """Create a host-neutral passphrase-encrypted disaster-recovery backup."""
    root = Path(root).resolve()
    destination = Path(destination).expanduser().resolve()
    if destination.is_relative_to(root):
        raise ValueError("Store backups outside the SAD project/runtime tree.")
    if destination.exists() and destination.is_symlink():
        raise ValueError("Portable backup destination must not be a symlink.")
    plain = _build_plain_backup_bytes(root=root, runtime_mode=RUNTIME_MODE_PORTABLE)
    output = encrypt_portable(plain, passphrase)
    _atomic_backup_write(destination, output)
    return verify_backup(destination, passphrase=passphrase)


def _atomic_backup_write(destination, output):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    temporary.write_bytes(output)
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    os.replace(temporary, destination)


def verify_backup(path, *, allow_plaintext=False, passphrase=None):
    path = Path(path).expanduser().resolve()
    if path.is_symlink() or not path.is_file():
        raise ValueError("Backup must be an existing regular file.")
    raw = path.read_bytes()
    plain, protection = _decode_backup_container(
        raw, allow_plaintext=allow_plaintext, passphrase=passphrase
    )
    manifest = _verify_plain_backup_bytes(plain)
    if protection == PORTABLE_SCHEME and manifest.get("runtime_database_mode") != RUNTIME_MODE_PORTABLE:
        raise ValueError("Portable backup container does not contain host-neutral runtime state.")
    if protection != PORTABLE_SCHEME and manifest.get("runtime_database_mode", RUNTIME_MODE_NATIVE) == RUNTIME_MODE_PORTABLE:
        raise ValueError("Host-neutral runtime state must be inside a portable encrypted container.")
    result = dict(manifest)
    result["container_protection"] = protection
    return result


def encrypt_legacy_backup(source, destination):
    """Convert a verified legacy plaintext backup into a Windows DPAPI container."""
    if platform.system() != "Windows":
        raise OSError("Legacy backup encryption requires Windows DPAPI.")
    source = Path(source).expanduser().resolve()
    destination = Path(destination).expanduser().resolve()
    if source == destination:
        raise ValueError("Write the encrypted backup to a different destination first.")
    if source.is_symlink() or not source.is_file():
        raise ValueError("Legacy backup must be an existing regular file.")
    raw = source.read_bytes()
    if raw.startswith(BACKUP_DPAPI_MAGIC) or raw.startswith(PORTABLE_MAGIC):
        raise ValueError("Backup is already encrypted.")
    _verify_plain_backup_bytes(raw)
    protected = BACKUP_DPAPI_MAGIC + protect_data(raw, purpose=BACKUP_DPAPI_PURPOSE)
    _atomic_backup_write(destination, protected)
    return verify_backup(destination)


def _portable_runtime_entry(relative, data):
    return relative == f"local_data/{RUNTIME_DB_FILE.name}", data


def restore_backup(
    path,
    *,
    root=ROOT,
    explicitly_approved=False,
    allow_plaintext=False,
    passphrase=None,
):
    """Restore verified private state. SAD should be stopped while this runs."""
    if not explicitly_approved:
        raise PermissionError("Explicit approval is required before restoring SAD private state.")
    root = Path(root).resolve()
    backup_path = Path(path).expanduser().resolve()
    if backup_path.is_symlink() or not backup_path.is_file():
        raise ValueError("Backup must be an existing regular file.")
    plain, protection = _decode_backup_container(
        backup_path.read_bytes(), allow_plaintext=allow_plaintext, passphrase=passphrase
    )
    manifest = _verify_plain_backup_bytes(plain)
    runtime_mode = manifest.get("runtime_database_mode", RUNTIME_MODE_NATIVE)
    if runtime_mode == RUNTIME_MODE_PORTABLE and protection != PORTABLE_SCHEME:
        raise ValueError("Portable runtime state must be restored from a portable encrypted container.")
    if protection == PORTABLE_SCHEME and platform.system() != "Windows":
        raise OSError("Portable SAD restore requires Windows so runtime data can be re-protected for the destination user.")

    with zipfile.ZipFile(io.BytesIO(plain), "r") as archive, tempfile.TemporaryDirectory() as stage_dir:
        stage_dir = Path(stage_dir)
        staged = []
        for entry in manifest["files"]:
            relative = _safe_relative(entry["path"])
            target = (root / relative).resolve()
            if not target.is_relative_to(root):
                raise ValueError("Restore target escaped the SAD root.")
            data = archive.read(relative)
            if relative == f"local_data/{RUNTIME_DB_FILE.name}" and runtime_mode == RUNTIME_MODE_PORTABLE:
                data = reprotect_portable_runtime_bytes(data)
            staged_path = stage_dir / relative
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            staged_path.write_bytes(data)
            if relative == f"local_data/{RUNTIME_DB_FILE.name}":
                if runtime_mode == RUNTIME_MODE_PORTABLE:
                    database = RuntimeDatabase(staged_path, protect_at_rest=True)
                    status = database.at_rest_status()
                    if not database.quick_check() or not status["protected"] or status["scheme"] != AT_REST_SCHEME:
                        raise ValueError("Re-protected runtime database failed destination integrity/protection verification.")
                elif not RuntimeDatabase.verify_snapshot(staged_path):
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
    return {
        "restored": True,
        "file_count": manifest["file_count"],
        "created_at": manifest["created_at"],
        "container_protection": protection,
        "runtime_database_mode": runtime_mode,
    }
