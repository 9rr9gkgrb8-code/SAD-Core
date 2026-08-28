"""In-memory export/re-key helpers for portable SAD disaster recovery.

A native Windows runtime database contains current-user DPAPI envelopes and cannot simply
be copied to another Windows profile. Portable backup export therefore creates a
plaintext SQLite representation only in memory, inside the separately encrypted backup
container. Restore re-protects every document for the destination Windows user before
any runtime database bytes are written to their final location.
"""

from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sqlite3

from runtime_database import (
    AT_REST_META_KEY,
    AT_REST_SCHEME,
    DATABASE_SCHEMA_VERSION,
    RUNTIME_DB_FILE,
    RuntimeDatabase,
    _canonical,
    _is_protected_envelope,
    _protect_payload,
    _validate_namespace,
)


MAX_PORTABLE_DATABASE_BYTES = 128_000_000


def _now():
    return datetime.now(timezone.utc).isoformat()


def _memory_connection(raw=None):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    if raw is not None:
        if not isinstance(raw, (bytes, bytearray, memoryview)):
            connection.close()
            raise TypeError("Portable runtime database must be bytes-like.")
        value = bytes(raw)
        if not value or len(value) > MAX_PORTABLE_DATABASE_BYTES:
            connection.close()
            raise ValueError("Portable runtime database size is invalid.")
        try:
            connection.deserialize(value)
        except (AttributeError, sqlite3.DatabaseError) as error:
            connection.close()
            raise ValueError("Portable runtime database could not be opened in memory.") from error
    return connection


def _create_schema(connection, *, protected=False):
    connection.execute("CREATE TABLE runtime_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    connection.execute(
        """CREATE TABLE runtime_documents (
            namespace TEXT PRIMARY KEY,
            document_schema INTEGER NOT NULL,
            payload_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    connection.execute(
        "INSERT INTO runtime_meta(key, value) VALUES('database_schema_version', ?)",
        (str(DATABASE_SCHEMA_VERSION),),
    )
    if protected:
        connection.execute(
            "INSERT INTO runtime_meta(key, value) VALUES(?, ?)",
            (AT_REST_META_KEY, AT_REST_SCHEME),
        )


def _portable_rows(connection):
    meta = {
        row["key"]: row["value"]
        for row in connection.execute("SELECT key, value FROM runtime_meta").fetchall()
    }
    if meta.get("database_schema_version") != str(DATABASE_SCHEMA_VERSION):
        raise ValueError("Portable runtime database schema is unsupported.")
    if AT_REST_META_KEY in meta:
        raise ValueError("Portable runtime database must not contain host-bound at-rest metadata.")
    rows = connection.execute(
        "SELECT namespace, document_schema, payload_json, updated_at FROM runtime_documents ORDER BY namespace"
    ).fetchall()
    for row in rows:
        _validate_namespace(row["namespace"])
        try:
            value = json.loads(row["payload_json"])
        except json.JSONDecodeError as error:
            raise ValueError(f"Portable runtime document is invalid JSON: {row['namespace']}.") from error
        if _is_protected_envelope(value):
            raise ValueError("Portable runtime database contains a host-bound protected document.")
    quick = connection.execute("PRAGMA quick_check").fetchall()
    if not quick or not all(row[0] == "ok" for row in quick):
        raise ValueError("Portable runtime database failed SQLite integrity verification.")
    return rows


def verify_portable_runtime_bytes(raw):
    with closing(_memory_connection(raw)) as connection:
        _portable_rows(connection)
    return True


def export_portable_runtime_bytes(path=RUNTIME_DB_FILE, *, database=None):
    """Export all runtime documents without host-bound DPAPI, only into memory."""
    database = database or RuntimeDatabase(path)
    path = Path(database.path)
    if not path.exists():
        with closing(_memory_connection()) as target:
            _create_schema(target, protected=False)
            target.commit()
            return target.serialize()

    with closing(sqlite3.connect(str(path), timeout=5.0)) as source:
        source.row_factory = sqlite3.Row
        rows = source.execute(
            "SELECT namespace, document_schema, updated_at FROM runtime_documents ORDER BY namespace"
        ).fetchall()

    with closing(_memory_connection()) as target:
        _create_schema(target, protected=False)
        for row in rows:
            namespace = _validate_namespace(row["namespace"])
            schema = int(row["document_schema"])
            value = database.read_document(namespace, {}, document_schema=schema)
            payload = _canonical(value)
            target.execute(
                "INSERT INTO runtime_documents(namespace, document_schema, payload_json, updated_at) VALUES(?, ?, ?, ?)",
                (namespace, schema, payload, row["updated_at"] or _now()),
            )
        target.commit()
        raw = target.serialize()
    if len(raw) > MAX_PORTABLE_DATABASE_BYTES:
        raise ValueError("Portable runtime database exceeds its size limit.")
    verify_portable_runtime_bytes(raw)
    return raw


def reprotect_portable_runtime_bytes(raw):
    """Bind a portable runtime database to the current destination Windows user."""
    if platform.system() != "Windows":
        raise OSError("Portable SAD runtime restore must re-protect data on a Windows host.")
    with closing(_memory_connection(raw)) as source:
        rows = _portable_rows(source)
        with closing(_memory_connection()) as target:
            _create_schema(target, protected=True)
            for row in rows:
                namespace = _validate_namespace(row["namespace"])
                try:
                    value = json.loads(row["payload_json"])
                except json.JSONDecodeError as error:
                    raise ValueError(f"Portable runtime document is invalid JSON: {namespace}.") from error
                plaintext = _canonical(value)
                target.execute(
                    "INSERT INTO runtime_documents(namespace, document_schema, payload_json, updated_at) VALUES(?, ?, ?, ?)",
                    (
                        namespace,
                        int(row["document_schema"]),
                        _protect_payload(namespace, plaintext),
                        row["updated_at"] or _now(),
                    ),
                )
            target.commit()
            protected = target.serialize()
    if len(protected) > MAX_PORTABLE_DATABASE_BYTES:
        raise ValueError("Re-protected runtime database exceeds its size limit.")
    return protected
