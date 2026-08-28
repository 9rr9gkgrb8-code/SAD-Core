"""Shared encrypted document persistence for legacy SAD JSON stores.

Live/default stores migrate into the transactional runtime database. Explicit paths remain
available for isolated tests and compatibility tools. Legacy source files are archived
only after a verified import; on Windows protected deployments the archive bytes are
DPAPI-protected as well.
"""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import platform

from runtime_database import LEGACY_IMPORT_DIRECTORY, RuntimeDatabase
from runtime_privacy import ROOT, migrate_legacy_private_store, private_store_path
from windows_crypto import protect_data


LEGACY_ARCHIVE_MAGIC = b"SAD-DPAPI-LEGACY\x00\x01\n"
MAX_LEGACY_ARCHIVE_BYTES = 128_000_000


def _canonical(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as error:
        raise ValueError("Runtime document must be JSON serializable.") from error


def _archive_purpose(name):
    value = f"legacy-import-archive:v1:{name}"
    if len(value) > 160:
        raise ValueError("Legacy archive name is too long for protected storage.")
    return value


def _atomic_private_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    temporary.write_bytes(data)
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    os.replace(temporary, path)


def archive_imported_source(source, database):
    """Archive a verified legacy source, DPAPI-protecting it on protected Windows."""
    source = Path(source)
    if source.is_symlink() or not source.is_file():
        raise ValueError("Legacy import source must be a regular file.")
    if source.stat().st_size > MAX_LEGACY_ARCHIVE_BYTES:
        raise ValueError("Legacy import source is unexpectedly large.")
    LEGACY_IMPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    archive = LEGACY_IMPORT_DIRECTORY / f"{source.name}.imported"
    if archive.exists():
        raise ValueError(f"Legacy import archive already exists for {source.name}; reconcile it manually.")
    if database.protect_at_rest:
        raw = source.read_bytes()
        protected = LEGACY_ARCHIVE_MAGIC + protect_data(raw, purpose=_archive_purpose(archive.name))
        _atomic_private_write(archive, protected)
        source.unlink()
    else:
        os.replace(source, archive)
        try:
            os.chmod(archive, 0o600)
        except OSError:
            pass
    return archive


def protect_existing_legacy_archives():
    """Upgrade prior plaintext import archives to current-user DPAPI on Windows."""
    if platform.system() != "Windows" or not LEGACY_IMPORT_DIRECTORY.exists():
        return 0
    changed = 0
    for archive in sorted(LEGACY_IMPORT_DIRECTORY.glob("*.imported")):
        if archive.is_symlink() or not archive.is_file():
            raise ValueError("Legacy import archive must be a regular file.")
        if archive.stat().st_size > MAX_LEGACY_ARCHIVE_BYTES:
            raise ValueError("Legacy import archive is unexpectedly large.")
        raw = archive.read_bytes()
        if raw.startswith(LEGACY_ARCHIVE_MAGIC):
            continue
        protected = LEGACY_ARCHIVE_MAGIC + protect_data(raw, purpose=_archive_purpose(archive.name))
        _atomic_private_write(archive, protected)
        changed += 1
    return changed


class RuntimeJSONDocument:
    """One bounded JSON document backed by encrypted SQLite in the live runtime."""

    def __init__(
        self,
        filename,
        namespace,
        default,
        validator,
        max_bytes,
        *,
        path=None,
        database=None,
    ):
        self.filename = filename
        self.namespace = namespace
        self.default = deepcopy(default)
        self.validator = validator
        self.max_bytes = max_bytes
        self.database = None

        if path is None:
            private_path = private_store_path(filename)
            legacy_path = ROOT / filename
            migrate_legacy_private_store(private_path, legacy_path)
            self.database = database or RuntimeDatabase()
            if private_path.exists():
                self._import_legacy_json(private_path)
            self.path = self.database.path
            protect_existing_legacy_archives()
        else:
            self.path = Path(path)

    def _import_legacy_json(self, source):
        source = Path(source)
        if source.is_symlink() or not source.is_file():
            raise ValueError("Legacy runtime document must be a regular file.")
        if source.stat().st_size > self.max_bytes:
            raise ValueError("Legacy runtime document is unexpectedly large.")
        if self.database.has_document(self.namespace):
            raise ValueError(
                f"Both SQLite state and legacy JSON exist for {self.namespace}; reconcile them before starting SAD."
            )
        try:
            value = json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Legacy runtime store for {self.namespace} is invalid JSON.") from error
        self.validator(value)
        self.database.write_document(self.namespace, value, document_schema=1, max_bytes=self.max_bytes)
        imported = self.database.read_document(self.namespace, self.default, document_schema=1)
        if _canonical(imported) != _canonical(value):
            raise OSError(f"Runtime migration verification failed for {self.namespace}.")
        archive_imported_source(source, self.database)

    def load(self):
        if self.database is not None:
            data = self.database.read_document(self.namespace, self.default, document_schema=1)
            self.validator(data)
            return data
        if not self.path.exists():
            return deepcopy(self.default)
        if self.path.is_symlink() or not self.path.is_file():
            raise ValueError("Runtime document path must be a regular file.")
        if self.path.stat().st_size > self.max_bytes:
            raise ValueError("Runtime document is unexpectedly large.")
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError("Runtime document contains invalid JSON.") from error
        self.validator(data)
        return data

    def save(self, data):
        self.validator(data)
        encoded = json.dumps(data, indent=2, ensure_ascii=False)
        if len(encoded.encode("utf-8")) > self.max_bytes:
            raise ValueError("Runtime document exceeded its storage limit.")
        if self.database is not None:
            self.database.write_document(
                self.namespace, data, document_schema=1, max_bytes=self.max_bytes
            )
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(encoded, encoding="utf-8")
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        os.replace(temporary, self.path)
