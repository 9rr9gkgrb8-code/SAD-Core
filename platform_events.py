"""Durable privacy-minimized event stream for SAD Platform clients.

Default runtime persistence uses the shared transactional SQLite database. Explicit
compatibility/test paths may still use the legacy JSON document format.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
import uuid

from runtime_database import RuntimeDatabase
from runtime_privacy import migrate_legacy_private_store, private_store_path


LEGACY_EVENTS_FILE = Path(__file__).with_name("platform_events.json")
EVENTS_FILE = private_store_path("platform_events.json")
EVENTS_NAMESPACE = "platform_events"
MAX_EVENT_FILE_BYTES = 2_000_000
MAX_EVENTS = 2_000
MAX_EVENT_DETAILS_BYTES = 8_000
SENSITIVE_DETAIL_KEYS = frozenset({
    "args", "authorization", "content", "cookie", "diff", "material", "message",
    "output", "password", "prompt", "secret", "source_code", "token", "transcript",
})

EVENT_TYPES = frozenset({
    "chat.session.created", "chat.message.created", "chat.session.archived",
    "development.workspace.created", "development.workspace.executed",
    "development.workspace.applied", "development.workspace.rolled_back",
    "failure.created", "forge.quest.created", "forge.quest.completed",
    "memory.created", "memory.updated", "memory.deleted",
    "platform.client.created", "platform.client.rotated", "platform.client.revoked",
    "tool.action.created", "tool.action.decided", "tool.action.completed",
    "voice.turn.completed",
})


def _now():
    return datetime.now(timezone.utc).isoformat()


def _reject_sensitive_detail_keys(value):
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).strip().casefold().replace("-", "_")
            if normalized in SENSITIVE_DETAIL_KEYS:
                raise ValueError(f"Sensitive platform event detail key is not allowed: {key}")
            _reject_sensitive_detail_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_sensitive_detail_keys(nested)


def _safe_details(details):
    value = details or {}
    if not isinstance(value, dict):
        raise ValueError("Platform event details must be an object.")
    _reject_sensitive_detail_keys(value)
    encoded = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(encoded) > MAX_EVENT_DETAILS_BYTES:
        raise ValueError("Platform event details are too large.")
    return value


def _validate_event_data(data):
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("events"), list):
        raise ValueError("Unsupported or invalid platform event store.")
    if not isinstance(data.get("next_seq"), int) or data["next_seq"] < 1:
        raise ValueError("Invalid platform event sequence.")
    return data


class PlatformEventStore:
    """Append a bounded metadata-only event log with monotonic sequence numbers."""

    def __init__(self, path=None, database=None):
        self.lock = threading.RLock()
        self.database = None
        if path is None:
            migrate_legacy_private_store(EVENTS_FILE, LEGACY_EVENTS_FILE)
            self.database = database or RuntimeDatabase()
            if EVENTS_FILE.exists():
                self.database.import_json_document(
                    EVENTS_NAMESPACE, EVENTS_FILE, _validate_event_data, max_bytes=MAX_EVENT_FILE_BYTES
                )
            self.path = self.database.path
        else:
            self.path = Path(path)

    def _load(self):
        if self.database is not None:
            data = self.database.read_document(
                EVENTS_NAMESPACE,
                {"schema_version": 1, "next_seq": 1, "events": []},
                document_schema=1,
            )
            return _validate_event_data(data)
        if not self.path.exists():
            return {"schema_version": 1, "next_seq": 1, "events": []}
        if self.path.is_symlink() or not self.path.is_file():
            raise ValueError("Platform event path must be a regular file.")
        if self.path.stat().st_size > MAX_EVENT_FILE_BYTES:
            raise ValueError("Platform event file is unexpectedly large.")
        return _validate_event_data(json.loads(self.path.read_text(encoding="utf-8")))

    def _save(self, data):
        _validate_event_data(data)
        if self.database is not None:
            self.database.write_document(
                EVENTS_NAMESPACE, data, document_schema=1, max_bytes=MAX_EVENT_FILE_BYTES
            )
            return
        encoded = json.dumps(data, indent=2, ensure_ascii=False)
        if len(encoded.encode("utf-8")) > MAX_EVENT_FILE_BYTES:
            raise ValueError("Platform event history exceeded its storage limit.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(encoded, encoding="utf-8")
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        os.replace(temporary, self.path)

    def publish(self, event_type, *, subject_id=None, details=None):
        if event_type not in EVENT_TYPES:
            raise ValueError("Unsupported platform event type.")
        if subject_id is not None and (not isinstance(subject_id, str) or len(subject_id) > 128):
            raise ValueError("Invalid event subject.")
        safe_details = _safe_details(details)
        with self.lock:
            data = self._load()
            event = {
                "seq": data["next_seq"], "event_id": str(uuid.uuid4()), "event_type": event_type,
                "created_at": _now(), "subject_id": subject_id, "details": safe_details,
            }
            data["next_seq"] += 1
            data["events"].append(event)
            if len(data["events"]) > MAX_EVENTS:
                data["events"] = data["events"][-MAX_EVENTS:]
            self._save(data)
            return dict(event)

    def read(self, *, after_seq=0, limit=100, event_types=None):
        if not isinstance(after_seq, int) or after_seq < 0:
            raise ValueError("after_seq must be a non-negative integer.")
        if not isinstance(limit, int) or not 1 <= limit <= 250:
            raise ValueError("limit must be between 1 and 250.")
        selected = set(EVENT_TYPES if event_types is None else event_types)
        if not selected.issubset(EVENT_TYPES):
            raise ValueError("Unsupported event subscription.")
        data = self._load()
        events = [
            dict(event) for event in data["events"]
            if event.get("seq", 0) > after_seq and event.get("event_type") in selected
        ][:limit]
        cursor = events[-1]["seq"] if events else after_seq
        return {"events": events, "cursor": cursor, "available_event_types": sorted(selected)}
