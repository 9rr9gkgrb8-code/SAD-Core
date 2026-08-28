"""Governed internal tool actions for SAD.

This module does not execute shell commands, import plugins, access the network, or
invoke Git. Built-in tools are explicit Python call paths with per-account ownership.
Default runtime persistence is transactional SQLite; explicit compatibility/test paths
may still use the legacy JSON document format.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import threading
import uuid

from memory_store import MemoryStore
from platform_registry import PLATFORM_SCHEMA_VERSION, PLATFORM_VERSION, PlatformRegistry
from runtime_database import RuntimeDatabase
from runtime_privacy import migrate_legacy_private_store, private_store_path


LEGACY_TOOL_ACTION_FILE = Path(__file__).with_name("tool_actions.json")
TOOL_ACTION_FILE = private_store_path("tool_actions.json")
TOOL_ACTION_NAMESPACE = "tool_actions"
MAX_TOOL_ACTION_FILE_BYTES = 4_000_000
MAX_ACTIONS = 2_000
MAX_ARGS_BYTES = 32_000
MAX_OUTPUT_BYTES = 64_000


@dataclass(frozen=True)
class ToolSpec:
    tool_id: str
    title: str
    description: str
    permission: str | None
    mutates_state: bool
    approval_required: bool

    def to_dict(self):
        return asdict(self)


BUILTIN_TOOLS = (
    ToolSpec("platform.status", "Platform status", "Read the signed-in account's SAD platform status.", None, False, False),
    ToolSpec("memory.search", "Search memory", "Search only the signed-in account's saved memories.", None, False, False),
    ToolSpec("memory.remember", "Save memory", "Save one explicit memory for the signed-in account.", None, True, True),
    ToolSpec("memory.forget", "Forget memory", "Delete one owned memory by ID.", None, True, True),
)
TOOL_MAP = {tool.tool_id: tool for tool in BUILTIN_TOOLS}


def _now():
    return datetime.now(timezone.utc)


def _canonical_json(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError("Value must be JSON serializable.") from error


def _bounded_json(value, maximum, label):
    encoded = _canonical_json(value)
    if len(encoded) > maximum:
        raise ValueError(f"{label} is too large.")
    return value


def _args_hash(args):
    return hashlib.sha256(_canonical_json(args)).hexdigest()


def _validate_action_data(data):
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("actions"), dict):
        raise ValueError("Unsupported or invalid tool action store.")
    return data


class ToolActionStore:
    def __init__(self, path=None, memory=None, platform=None, now=None, database=None):
        self.memory = memory or MemoryStore(database=database)
        self.platform = platform or PlatformRegistry()
        self.now = now or _now
        self.lock = threading.RLock()
        self.database = None
        if path is None:
            migrate_legacy_private_store(TOOL_ACTION_FILE, LEGACY_TOOL_ACTION_FILE)
            self.database = database or RuntimeDatabase()
            if TOOL_ACTION_FILE.exists():
                self.database.import_json_document(
                    TOOL_ACTION_NAMESPACE, TOOL_ACTION_FILE, _validate_action_data,
                    max_bytes=MAX_TOOL_ACTION_FILE_BYTES,
                )
            self.path = self.database.path
        else:
            self.path = Path(path)

    def _load(self):
        if self.database is not None:
            data = self.database.read_document(
                TOOL_ACTION_NAMESPACE, {"schema_version": 1, "actions": {}}, document_schema=1
            )
            return _validate_action_data(data)
        if not self.path.exists():
            return {"schema_version": 1, "actions": {}}
        if self.path.is_symlink() or not self.path.is_file():
            raise ValueError("Tool action path must be a regular file.")
        if self.path.stat().st_size > MAX_TOOL_ACTION_FILE_BYTES:
            raise ValueError("Tool action file is unexpectedly large.")
        return _validate_action_data(json.loads(self.path.read_text(encoding="utf-8")))

    def _save(self, data):
        _validate_action_data(data)
        if len(data["actions"]) > MAX_ACTIONS:
            ordered = sorted(data["actions"].values(), key=lambda item: item.get("created_at", ""))
            data["actions"] = {item["action_id"]: item for item in ordered[-MAX_ACTIONS:]}
        if self.database is not None:
            self.database.write_document(
                TOOL_ACTION_NAMESPACE, data, document_schema=1, max_bytes=MAX_TOOL_ACTION_FILE_BYTES
            )
            return
        encoded = json.dumps(data, indent=2, ensure_ascii=False)
        if len(encoded.encode("utf-8")) > MAX_TOOL_ACTION_FILE_BYTES:
            raise ValueError("Tool action storage limit reached.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(encoded, encoding="utf-8")
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        os.replace(temporary, self.path)

    @staticmethod
    def available_tools(permissions):
        permissions = set(permissions)
        return [tool.to_dict() for tool in BUILTIN_TOOLS if tool.permission is None or tool.permission in permissions]

    def _owned(self, data, account_id, action_id):
        action = data["actions"].get(action_id)
        if not action or action.get("account_id") != account_id:
            raise KeyError("Tool action not found.")
        return action

    @staticmethod
    def _public(action):
        return {key: value for key, value in action.items() if key != "account_id"}

    @staticmethod
    def _integrity_matches(action, tool):
        return (
            action.get("tool_id") == tool.tool_id
            and action.get("mutates_state") is tool.mutates_state
            and action.get("approval_required") is tool.approval_required
            and action.get("args_sha256") == _args_hash(action.get("args"))
        )

    def create(self, account_id, permissions, tool_id, args):
        tool = TOOL_MAP.get(tool_id)
        if not tool:
            raise ValueError("Unknown tool action.")
        if tool.permission and tool.permission not in set(permissions):
            raise PermissionError("The signed-in role cannot use that tool.")
        if not isinstance(args, dict):
            raise ValueError("Tool arguments must be an object.")
        _bounded_json(args, MAX_ARGS_BYTES, "Tool arguments")
        timestamp = self.now().isoformat()
        action = {
            "action_id": str(uuid.uuid4()), "account_id": account_id, "tool_id": tool_id,
            "args": args, "args_sha256": _args_hash(args), "approved_args_sha256": None,
            "mutates_state": tool.mutates_state, "approval_required": tool.approval_required,
            "state": "awaiting_approval" if tool.approval_required else "ready",
            "decision": None, "created_at": timestamp, "updated_at": timestamp,
            "output": None, "error": None,
        }
        with self.lock:
            data = self._load()
            data["actions"][action["action_id"]] = action
            self._save(data)
        return self._public(action)

    def list(self, account_id):
        data = self._load()
        actions = [self._public(item) for item in data["actions"].values() if item.get("account_id") == account_id]
        return sorted(actions, key=lambda item: item["updated_at"], reverse=True)

    def get(self, account_id, action_id):
        data = self._load()
        return self._public(self._owned(data, account_id, action_id))

    def decide(self, account_id, action_id, decision):
        if decision not in {"approve", "reject"}:
            raise ValueError("Tool decision must be approve or reject.")
        with self.lock:
            data = self._load()
            action = self._owned(data, account_id, action_id)
            tool = TOOL_MAP.get(action.get("tool_id"))
            if not tool or not self._integrity_matches(action, tool):
                action["state"] = "tampered"
                action["updated_at"] = self.now().isoformat()
                self._save(data)
                raise PermissionError("Tool action integrity check failed.")
            if not action.get("approval_required") or action.get("state") != "awaiting_approval":
                raise ValueError("That tool action is not awaiting approval.")
            action["decision"] = decision
            action["approved_args_sha256"] = action["args_sha256"] if decision == "approve" else None
            action["state"] = "ready" if decision == "approve" else "rejected"
            action["updated_at"] = self.now().isoformat()
            self._save(data)
            return self._public(action)

    def execute(self, account, permissions, action_id):
        account_id = account["account_id"]
        with self.lock:
            data = self._load()
            action = self._owned(data, account_id, action_id)
            tool = TOOL_MAP.get(action.get("tool_id"))
            if not tool or not self._integrity_matches(action, tool):
                action["state"] = "tampered"
                action["updated_at"] = self.now().isoformat()
                self._save(data)
                raise PermissionError("Tool action integrity check failed.")
            if tool.permission and tool.permission not in set(permissions):
                raise PermissionError("The signed-in role cannot use that tool.")
            if action["state"] != "ready":
                raise PermissionError("Tool action is not approved and ready.")
            if tool.approval_required and action.get("approved_args_sha256") != action.get("args_sha256"):
                action["state"] = "tampered"
                action["updated_at"] = self.now().isoformat()
                self._save(data)
                raise PermissionError("Approved tool arguments no longer match execution arguments.")
            try:
                output = self._run(tool.tool_id, account, permissions, action["args"])
                _bounded_json(output, MAX_OUTPUT_BYTES, "Tool output")
                action["output"] = output
                action["state"] = "completed"
                action["error"] = None
            except (ValueError, KeyError, PermissionError) as error:
                action["state"] = "failed"
                action["error"] = str(error)
                action["output"] = None
                action["updated_at"] = self.now().isoformat()
                self._save(data)
                raise
            action["updated_at"] = self.now().isoformat()
            self._save(data)
            return self._public(action)

    def _run(self, tool_id, account, permissions, args):
        account_id = account["account_id"]
        if tool_id == "platform.status":
            manifest = self.platform.manifest(account["role"], permissions)
            return {
                "product": "SAD", "platform_version": PLATFORM_VERSION,
                "platform_schema_version": PLATFORM_SCHEMA_VERSION, "role": account["role"],
                "module_count": manifest["module_count"], "capability_count": manifest["capability_count"],
            }
        if tool_id == "memory.search":
            return {"memories": self.memory.search(
                account_id, args.get("query", ""), args.get("categories"),
                limit=args.get("limit", 20), enabled_only=bool(args.get("enabled_only", False)),
            )}
        if tool_id == "memory.remember":
            return {"memory": self.memory.create(
                account_id, args.get("category", "note"), args.get("title", ""), args.get("content", ""),
                enabled=args.get("enabled", True), expires_at=args.get("expires_at"),
            )}
        if tool_id == "memory.forget":
            return self.memory.delete(account_id, args.get("memory_id", ""))
        raise ValueError("Tool implementation is unavailable.")
