"""Transactional SQLite foundation for SAD private runtime state.

The database is local-only application state. It is not a source file, capability grant,
or authority boundary. Stores may migrate validated legacy JSON documents into named
SQLite documents while preserving a protected import archive for recovery.
"""

from __future__ import annotations

from contextlib import closing
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import threading

from runtime_privacy import LOCAL_DATA_DIRECTORY


RUNTIME_DB_FILE = LOCAL_DATA_DIRECTORY / "sad_runtime.sqlite3"
LEGACY_IMPORT_DIRECTORY = LOCAL_DATA_DIRECTORY / "legacy_imported"
DATABASE_SCHEMA_VERSION = 1
MAX_DATABASE_BYTES = 128_000_000
MAX_DOCUMENT_BYTES = 8_000_000


def _now():
    return datetime.now(timezone.utc).isoformat()


def _canonical(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as error:
        raise ValueError("Runtime document must be JSON serializable.") from error


def _validate_namespace(namespace):
    if not isinstance(namespace, str) or not namespace or len(namespace) > 80:
        raise ValueError("Runtime namespace must be 1-80 characters.")
    if not all(character.isalnum() or character in "._-" for character in namespace):
        raise ValueError("Runtime namespace contains unsupported characters.")
    return namespace


class RuntimeDatabase:
    """Small local SQLite document database with explicit schema and integrity checks."""

    def __init__(self, path=RUNTIME_DB_FILE):
        self.path = Path(path)
        self.lock = threading.RLock()
        self._initialize()

    def _validate_path(self):
        if self.path.exists() and (self.path.is_symlink() or not self.path.is_file()):
            raise ValueError("Runtime database path must be a regular file.")
        if self.path.exists() and self.path.stat().st_size > MAX_DATABASE_BYTES:
            raise ValueError("Runtime database is unexpectedly large.")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self):
        self._validate_path()
        connection = sqlite3.connect(str(self.path), timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self):
        with self.lock, closing(self._connect()) as connection:
            try:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS runtime_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
                )
                connection.execute(
                    """CREATE TABLE IF NOT EXISTS runtime_documents (
                        namespace TEXT PRIMARY KEY,
                        document_schema INTEGER NOT NULL,
                        payload_json TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )"""
                )
                row = connection.execute(
                    "SELECT value FROM runtime_meta WHERE key='database_schema_version'"
                ).fetchone()
                if row is None:
                    connection.execute(
                        "INSERT INTO runtime_meta(key, value) VALUES('database_schema_version', ?)",
                        (str(DATABASE_SCHEMA_VERSION),),
                    )
                elif int(row["value"]) != DATABASE_SCHEMA_VERSION:
                    raise ValueError("Unsupported SAD runtime database schema.")
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        self._restrict_permissions()

    def _restrict_permissions(self):
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def has_document(self, namespace):
        namespace = _validate_namespace(namespace)
        with self.lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT 1 FROM runtime_documents WHERE namespace=?", (namespace,)
            ).fetchone()
        return row is not None

    def read_document(self, namespace, default, *, document_schema=1):
        namespace = _validate_namespace(namespace)
        with self.lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT document_schema, payload_json FROM runtime_documents WHERE namespace=?",
                (namespace,),
            ).fetchone()
        if row is None:
            return deepcopy(default)
        if int(row["document_schema"]) != int(document_schema):
            raise ValueError(f"Unsupported runtime document schema for {namespace}.")
        try:
            value = json.loads(row["payload_json"])
        except json.JSONDecodeError as error:
            raise ValueError(f"Corrupt runtime document: {namespace}.") from error
        return value

    def write_document(self, namespace, value, *, document_schema=1, max_bytes=MAX_DOCUMENT_BYTES):
        namespace = _validate_namespace(namespace)
        if not isinstance(max_bytes, int) or not 1 <= max_bytes <= MAX_DOCUMENT_BYTES:
            raise ValueError("Invalid runtime document size limit.")
        payload = _canonical(value)
        if len(payload.encode("utf-8")) > max_bytes:
            raise ValueError(f"Runtime document {namespace} exceeded its storage limit.")
        with self.lock, closing(self._connect()) as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """INSERT INTO runtime_documents(namespace, document_schema, payload_json, updated_at)
                       VALUES(?, ?, ?, ?)
                       ON CONFLICT(namespace) DO UPDATE SET
                         document_schema=excluded.document_schema,
                         payload_json=excluded.payload_json,
                         updated_at=excluded.updated_at""",
                    (namespace, int(document_schema), payload, _now()),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        self._restrict_permissions()

    def import_json_document(self, namespace, source, validator, *, document_schema=1, max_bytes=MAX_DOCUMENT_BYTES):
        """Import one validated JSON store exactly once, then archive the source privately."""
        namespace = _validate_namespace(namespace)
        source = Path(source)
        if not source.exists():
            return False
        if source.is_symlink() or not source.is_file():
            raise ValueError("Legacy runtime store must be a regular file.")
        if source.stat().st_size > max_bytes:
            raise ValueError("Legacy runtime store is unexpectedly large.")
        if self.has_document(namespace):
            raise ValueError(
                f"Both SQLite state and legacy JSON exist for {namespace}; reconcile them before starting SAD."
            )
        try:
            value = json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Legacy runtime store for {namespace} is invalid JSON.") from error
        validator(value)
        self.write_document(namespace, value, document_schema=document_schema, max_bytes=max_bytes)
        imported = self.read_document(namespace, {}, document_schema=document_schema)
        if _canonical(imported) != _canonical(value):
            raise OSError(f"SQLite migration verification failed for {namespace}.")

        LEGACY_IMPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)
        archive = LEGACY_IMPORT_DIRECTORY / f"{source.name}.imported"
        if archive.exists():
            raise ValueError(f"Legacy import archive already exists for {source.name}; reconcile it manually.")
        os.replace(source, archive)
        try:
            os.chmod(archive, 0o600)
        except OSError:
            pass
        return True

    def quick_check(self):
        with self.lock, closing(self._connect()) as connection:
            rows = connection.execute("PRAGMA quick_check").fetchall()
        return bool(rows) and all(row[0] == "ok" for row in rows)

    def document_names(self):
        with self.lock, closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT namespace FROM runtime_documents ORDER BY namespace"
            ).fetchall()
        return [row["namespace"] for row in rows]

    def snapshot(self, destination):
        """Create a transactionally consistent standalone SQLite snapshot."""
        destination = Path(destination)
        if destination.exists() and destination.is_symlink():
            raise ValueError("Database snapshot destination must not be a symlink.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.unlink(missing_ok=True)
        try:
            with self.lock, closing(self._connect()) as source:
                with closing(sqlite3.connect(str(temporary), timeout=5.0)) as target:
                    source.backup(target)
                    rows = target.execute("PRAGMA quick_check").fetchall()
                    if not rows or not all(row[0] == "ok" for row in rows):
                        raise OSError("SQLite snapshot integrity verification failed.")
                    target.commit()
            # Both SQLite handles are closed before Windows is asked to replace the file.
            os.replace(temporary, destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        try:
            os.chmod(destination, 0o600)
        except OSError:
            pass
        return destination

    @staticmethod
    def verify_snapshot(path):
        path = Path(path)
        if path.is_symlink() or not path.is_file():
            return False
        try:
            with closing(sqlite3.connect(str(path), timeout=5.0)) as connection:
                rows = connection.execute("PRAGMA quick_check").fetchall()
            return bool(rows) and all(row[0] == "ok" for row in rows)
        except (OSError, sqlite3.DatabaseError):
            return False
