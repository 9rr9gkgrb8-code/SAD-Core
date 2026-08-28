"""Durable privacy-minimized event stream for SAD Platform clients."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
import uuid


EVENTS_FILE = Path(__file__).with_name("platform_events.json")
MAX_EVENT_FILE_BYTES = 2_000_000
MAX_EVENTS = 2_000
MAX_EVENT_DETAILS_BYTES = 8_000

EVENT_TYPES = frozenset({
    "chat.session.created",
    "chat.message.created",
    "chat.session.archived",
    "development.workspace.created",
    "development.workspace.executed",
    "development.workspace.applied",
    "development.workspace.rolled_back",
    "failure.created",
    "forge.quest.created",
    "forge.quest.completed",
    "platform.client.created",
    "platform.client.rotated",
    "platform.client.revoked",
    "voice.turn.completed",
})


def _now():
    return datetime.now(timezone.utc).isoformat()


def _safe_details(details):
    value = details or {}
    if not isinstance(value, dict):
        raise ValueError("Platform event details must be an object.")
    encoded = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(encoded) > MAX_EVENT_DETAILS_BYTES:
        raise ValueError("Platform event details are too large.")
    return value


class PlatformEventStore:
    """Append a bounded metadata-only event log with monotonic sequence numbers."""

    def __init__(self, path=EVENTS_FILE):
        self.path = Path(path)
        self.lock = threading.RLock()

    def _load(self):
        if not self.path.exists():
            return {"schema_version": 1, "next_seq": 1, "events": []}
        if self.path.stat().st_size > MAX_EVENT_FILE_BYTES:
            raise ValueError("Platform event file is unexpectedly large.")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or not isinstance(data.get("events"), list):
            raise ValueError("Unsupported or invalid platform event file.")
        if not isinstance(data.get("next_seq"), int) or data["next_seq"] < 1:
            raise ValueError("Invalid platform event sequence.")
        return data

    def _save(self, data):
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
                "seq": data["next_seq"],
                "event_id": str(uuid.uuid4()),
                "event_type": event_type,
                "created_at": _now(),
                "subject_id": subject_id,
                "details": safe_details,
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
        selected = set(event_types or EVENT_TYPES)
        if not selected.issubset(EVENT_TYPES):
            raise ValueError("Unsupported event subscription.")
        data = self._load()
        events = [
            dict(event) for event in data["events"]
            if event.get("seq", 0) > after_seq and event.get("event_type") in selected
        ][:limit]
        cursor = events[-1]["seq"] if events else after_seq
        return {"events": events, "cursor": cursor, "available_event_types": sorted(selected)}
