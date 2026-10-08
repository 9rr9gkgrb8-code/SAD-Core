"""Fail-closed MCP dispatch gate. Integration into the live dispatcher is required."""
from dataclasses import dataclass
from typing import Callable, Any
import hashlib
import json


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
