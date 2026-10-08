"""Fail-closed MCP dispatch gate. Integration into the live dispatcher is required."""
from dataclasses import dataclass
from typing import Callable, Any
import hashlib
import json
import sqlite3
from pathlib import Path


class MCPAuthorizationError(PermissionError):
    pass


class MCPDuplicateOperationError(RuntimeError):
    pass


@dataclass(frozen=True)
class MCPGrant:
    principal: str
    tool: str
    argument_digest: str
    approval_id: str
    authorized: bool = False


def argument_digest(arguments: dict) -> str:
    payload = json.dumps(arguments, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class GovernedMCPDispatcher:
    """Never authorize from tools/list visibility or tool annotations.

    The caller must supply an independently verified, current grant.
    The check_grant callback must validate approval revocation at call time.
    For mutating operations, reserve_once must be atomic and durable.
    """

    def __init__(self, check_grant: Callable[[MCPGrant], bool],
                 reserve_once: Callable[[str], bool]):
        self.check_grant = check_grant
        self.reserve_once = reserve_once

    def call(self, *, principal: str, tool: str, arguments: dict,
             grant: MCPGrant | None, execute: Callable[[], Any],
             mutating: bool = True) -> Any:
        digest = argument_digest(arguments)
        if (grant is None or not grant.authorized or
            grant.principal != principal or grant.tool != tool or
            grant.argument_digest != digest or not grant.approval_id or
            not self.check_grant(grant)):
            raise MCPAuthorizationError("MCP tool call denied")
        if mutating:
            operation_key = hashlib.sha256(
                json.dumps([principal, tool, digest, grant.approval_id],
                           separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            if not self.reserve_once(operation_key):
                raise MCPDuplicateOperationError("Duplicate or ambiguous operation")
        return execute()

class SQLiteOperationReservations:
    """Crash-durable, cross-process at-most-once reservation.

    An interrupted execution remains reserved. Never automatically retry it:
    external effects cannot generally be rolled back or reliably detected.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS mcp_operation_reservations
                       (operation_key TEXT PRIMARY KEY, reserved_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP)""")

    def _connect(self):
        db = sqlite3.connect(str(self.path), timeout=30, isolation_level=None)
        db.execute("PRAGMA busy_timeout=30000")
        db.execute("PRAGMA synchronous=FULL")
        return db

    def __call__(self, operation_key):
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cursor = db.execute(
                "INSERT OR IGNORE INTO mcp_operation_reservations (operation_key) VALUES (?)",
                (operation_key,),
            )
            db.commit()
            return cursor.rowcount == 1
