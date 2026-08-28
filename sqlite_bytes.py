"""Small in-memory SQLite byte helpers for backup verification."""

from __future__ import annotations

from contextlib import closing
import sqlite3


MAX_SQLITE_BYTES = 128_000_000


def verify_sqlite_bytes(raw):
    if not isinstance(raw, (bytes, bytearray, memoryview)):
        return False
    data = bytes(raw)
    if not data or len(data) > MAX_SQLITE_BYTES:
        return False
    try:
        with closing(sqlite3.connect(":memory:")) as connection:
            connection.deserialize(data)
            rows = connection.execute("PRAGMA quick_check").fetchall()
        return bool(rows) and all(row[0] == "ok" for row in rows)
    except (AttributeError, sqlite3.DatabaseError, ValueError):
        return False
