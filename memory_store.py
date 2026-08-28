"""User-controlled durable memory for SAD accounts.

Memory is explicit local data. SAD never auto-saves conversation text here.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
import uuid

from runtime_privacy import migrate_legacy_private_store, private_store_path


LEGACY_MEMORY_FILE = Path(__file__).with_name("memory.json")
MEMORY_FILE = private_store_path("memory.json")
MAX_MEMORY_FILE_BYTES = 4_000_000
MAX_MEMORIES_PER_ACCOUNT = 500
MAX_MEMORY_CONTENT = 8_000
MAX_MEMORY_TITLE = 120
CATEGORIES = {"fact", "preference", "goal", "project", "note"}


def _now():
    return datetime.now(timezone.utc)


def _text(value, label, maximum):
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text.")
    value = value.strip()
    if not value or len(value) > maximum:
        raise ValueError(f"{label} must be 1-{maximum} characters.")
    return value


def _expiry(value):
    if value in {None, ""}:
        return None
    if not isinstance(value, str):
        raise ValueError("expires_at must be an ISO timestamp or null.")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("expires_at must be an ISO timestamp or null.") from error
    if parsed.tzinfo is None:
        raise ValueError("expires_at must include a timezone.")
    return parsed.isoformat()


class MemoryStore:
    def __init__(self, path=MEMORY_FILE, now=None):
        self.path = Path(path)
        if self.path == MEMORY_FILE:
            migrate_legacy_private_store(self.path, LEGACY_MEMORY_FILE)
        self.now = now or _now
        self.lock = threading.RLock()

    def _load(self):
        if not self.path.exists():
            return {"schema_version": 1, "memories": {}}
        if self.path.is_symlink() or not self.path.is_file():
            raise ValueError("Memory path must be a regular file.")
        if self.path.stat().st_size > MAX_MEMORY_FILE_BYTES:
            raise ValueError("Memory file is unexpectedly large.")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or not isinstance(data.get("memories"), dict):
            raise ValueError("Unsupported or invalid memory file.")
        return data

    def _save(self, data):
        encoded = json.dumps(data, indent=2, ensure_ascii=False)
        if len(encoded.encode("utf-8")) > MAX_MEMORY_FILE_BYTES:
            raise ValueError("Memory storage limit reached.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(encoded, encoding="utf-8")
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        os.replace(temporary, self.path)

    def _owned(self, data, account_id, memory_id):
        item = data["memories"].get(memory_id)
        if not item or item.get("account_id") != account_id:
            raise KeyError("Memory not found.")
        return item

    def _active(self, item):
        expires_at = item.get("expires_at")
        if not expires_at:
            return True
        return self.now() < datetime.fromisoformat(expires_at)

    @staticmethod
    def _public(item):
        return {key: value for key, value in item.items() if key != "account_id"}

    def create(self, account_id, category, title, content, *, enabled=True, expires_at=None):
        if category not in CATEGORIES:
            raise ValueError("Unsupported memory category.")
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be true or false.")
        title = _text(title, "Memory title", MAX_MEMORY_TITLE)
        content = _text(content, "Memory content", MAX_MEMORY_CONTENT)
        expires_at = _expiry(expires_at)
        with self.lock:
            data = self._load()
            owned = [item for item in data["memories"].values() if item.get("account_id") == account_id]
            if len(owned) >= MAX_MEMORIES_PER_ACCOUNT:
                raise ValueError("Memory limit reached for this account.")
            timestamp = self.now().isoformat()
            memory_id = str(uuid.uuid4())
            item = {
                "memory_id": memory_id,
                "account_id": account_id,
                "category": category,
                "title": title,
                "content": content,
                "enabled": enabled,
                "expires_at": expires_at,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            data["memories"][memory_id] = item
            self._save(data)
            return self._public(item)

    def list(self, account_id):
        data = self._load()
        items = [self._public(item) for item in data["memories"].values() if item.get("account_id") == account_id]
        return sorted(items, key=lambda item: item["updated_at"], reverse=True)

    def search(self, account_id, query="", categories=None, *, limit=20, enabled_only=False):
        if not isinstance(query, str) or len(query) > 500:
            raise ValueError("Memory search query must be text up to 500 characters.")
        if not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("Memory search limit must be between 1 and 100.")
        selected = set(CATEGORIES if categories is None else categories)
        if not selected.issubset(CATEGORIES):
            raise ValueError("Unsupported memory category filter.")
        needle = query.strip().casefold()
        data = self._load()
        matches = []
        for item in data["memories"].values():
            if item.get("account_id") != account_id or item.get("category") not in selected:
                continue
            if enabled_only and (not item.get("enabled") or not self._active(item)):
                continue
            haystack = f"{item.get('title','')} {item.get('content','')}".casefold()
            if needle and needle not in haystack:
                continue
            matches.append(self._public(item))
        matches.sort(key=lambda item: item["updated_at"], reverse=True)
        return matches[:limit]

    def update(self, account_id, memory_id, patch):
        if not isinstance(patch, dict):
            raise ValueError("Memory update must be an object.")
        allowed = {"category", "title", "content", "enabled", "expires_at"}
        if not patch or not set(patch).issubset(allowed):
            raise ValueError("Memory update contains unsupported fields.")
        with self.lock:
            data = self._load()
            item = self._owned(data, account_id, memory_id)
            if "category" in patch:
                if patch["category"] not in CATEGORIES:
                    raise ValueError("Unsupported memory category.")
                item["category"] = patch["category"]
            if "title" in patch:
                item["title"] = _text(patch["title"], "Memory title", MAX_MEMORY_TITLE)
            if "content" in patch:
                item["content"] = _text(patch["content"], "Memory content", MAX_MEMORY_CONTENT)
            if "enabled" in patch:
                if not isinstance(patch["enabled"], bool):
                    raise ValueError("enabled must be true or false.")
                item["enabled"] = patch["enabled"]
            if "expires_at" in patch:
                item["expires_at"] = _expiry(patch["expires_at"])
            item["updated_at"] = self.now().isoformat()
            self._save(data)
            return self._public(item)

    def delete(self, account_id, memory_id):
        with self.lock:
            data = self._load()
            self._owned(data, account_id, memory_id)
            del data["memories"][memory_id]
            self._save(data)
            return {"deleted": True, "memory_id": memory_id}

    def context(self, account_id, limit=20):
        items = self.search(account_id, "", limit=limit, enabled_only=True)
        return [f"[{item['category']}] {item['title']}: {item['content']}" for item in items]
