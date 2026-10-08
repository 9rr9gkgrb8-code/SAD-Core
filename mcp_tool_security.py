"""Fail-closed MCP tool admission and replay policy.

Use at the MCP adapter boundary BEFORE SDK schema validation. This module does
not expose unauthorized tool schemas and does not execute arbitrary tools.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import threading
import sqlite3
from pathlib import Path


class ToolUnavailable(PermissionError):
    """Generic denial, intentionally indistinguishable from an unknown tool."""


class ReplayConflict(PermissionError):
    """A retry key was reused for a different operation."""


@dataclass(frozen=True)
class Admission:
    tool_id: str
    arguments: dict
    correlation_id: str


class ToolAdmission:
    def __init__(self, tools, *, max_argument_bytes=32000):
        self._tools = dict(tools)
        self._max_argument_bytes = max_argument_bytes

    def catalog(self, permissions):
        allowed = set(permissions)
        return [spec for spec in self._tools.values()
                if spec.permission is None or spec.permission in allowed]

    def admit(self, tool_id, arguments, permissions, correlation_id):
        spec = self._tools.get(tool_id)
        if spec is None or (spec.permission is not None and spec.permission not in set(permissions)):
            raise ToolUnavailable("Tool unavailable.")
        # Validate shape only AFTER visibility authorization.
        if not isinstance(arguments, dict):
            raise ValueError("Invalid tool arguments.")
        encoded = json.dumps(arguments, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        if len(encoded) > self._max_argument_bytes:
            raise ValueError("Tool arguments too large.")
        if not isinstance(correlation_id, str) or not correlation_id or len(correlation_id) > 128:
            raise ValueError("Invalid correlation ID.")
        return Admission(tool_id, arguments, correlation_id)


class RetryLedger:
    """Process-local replay guard. Persist transactions for crash-safe exactly-once effects.

    Never interpret this as durable idempotency across restarts or workers.
    """
    def __init__(self):
        self._lock = threading.RLock()
        self._entries = {}

    def run_once(self, *, account_id, admission, approval_id, execute):
        if not account_id or not callable(execute):
            raise ValueError("Invalid execution context.")
        fingerprint = hashlib.sha256(json.dumps(
            [admission.tool_id, admission.arguments, approval_id],
            sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode()).hexdigest()
        key = (account_id, admission.correlation_id)
        with self._lock:
            if key in self._entries:
                previous_hash, status, result = self._entries[key]
                if previous_hash != fingerprint:
                    raise ReplayConflict("Retry conflicts with original request.")
                if status != "completed":
                    raise ReplayConflict("Original request is pending or failed.")
                return result
            # Fail closed on execution failure, including uncertain side effects.
            self._entries[key] = (fingerprint, "pending", None)
            result = execute()
            self._entries[key] = (fingerprint, "completed", result)
            return result


class DurableRetryLedger:
    """SQLite replay journal shared across processes.

    Pending claims never automatically rerun after crashes. External side effects
    require transactional outbox/reconciliation before claiming exactly-once delivery.
    """
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS mcp_replay (
                account_id TEXT NOT NULL, correlation_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL, state TEXT NOT NULL, result_json TEXT,
                PRIMARY KEY(account_id, correlation_id))""")

    def _connect(self):
        db = sqlite3.connect(str(self.path), timeout=10, isolation_level=None)
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA synchronous=FULL")
        return db

    def run_once(self, *, account_id, admission, approval_id, execute):
        if not isinstance(account_id, str) or not account_id or not callable(execute):
            raise ValueError("Invalid execution context.")
        fingerprint = hashlib.sha256(json.dumps(
            [admission.tool_id, admission.arguments, approval_id],
            sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode()).hexdigest()
        with self._connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute(
                    "SELECT fingerprint,state,result_json FROM mcp_replay WHERE account_id=? AND correlation_id=?",
                    (account_id, admission.correlation_id)).fetchone()
                if row is not None:
                    if row[0] != fingerprint:
                        raise ReplayConflict("Retry conflicts with original request.")
                    if row[1] != "completed":
                        raise ReplayConflict("Original request requires reconciliation.")
                    result = json.loads(row[2])
                    db.commit()
                    return result
                db.execute("INSERT INTO mcp_replay VALUES(?,?,?,?,NULL)",
                           (account_id, admission.correlation_id, fingerprint, "pending"))
                db.commit()
            except BaseException:
                db.rollback()
                raise
        # Execute only after durable claim. Crash or exception leaves a pending
        # record and prevents a second execution; manual reconciliation required.
        result = execute()
        encoded = json.dumps(result, sort_keys=True, allow_nan=False)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE mcp_replay SET state='completed', result_json=? WHERE account_id=? AND correlation_id=? AND fingerprint=? AND state='pending'",
                       (encoded, account_id, admission.correlation_id, fingerprint))
            db.commit()
        return result
