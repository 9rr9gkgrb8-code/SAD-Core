"""User-controlled durable memory for SAD accounts.

Memory is explicit local data. SAD never auto-saves conversation text here. The default
runtime now uses the transactional SAD SQLite database; explicit test/compatibility paths
may still use the legacy JSON format.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import threading
import uuid

from runtime_database import RuntimeDatabase
from runtime_privacy import migrate_legacy_private_store, private_store_path


LEGACY_MEMORY_FILE = Path(__file__).with_name("memory.json")
MEMORY_FILE = private_store_path("memory.json")
MEMORY_NAMESPACE = "memory"
MAX_MEMORY_FILE_BYTES = 4_000_000
MAX_MEMORIES_PER_ACCOUNT = 500
MAX_MEMORY_CONTENT = 8_000
MAX_MEMORY_TITLE = 120
CATEGORIES = {"fact", "preference", "goal", "project", "note"}
CONTEXT_LEVELS = {"abstract", "overview", "full"}
DEFAULT_CONTEXT_BUDGET = 4_000
OVERVIEW_CHARS = 240


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


def _validate_memory_data(data):
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("memories"), dict):
        raise ValueError("Unsupported or invalid memory store.")
    return data


def _tokens(value):
    if not isinstance(value, str):
        return set()
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


def _clip(value, maximum):
    value = value.strip()
    if len(value) <= maximum:
        return value
    return value[: max(1, maximum - 1)].rstrip() + "…"


class MemoryStore:
    def __init__(self, path=None, now=None, database=None):
        self.now = now or _now
        self.lock = threading.RLock()
        self.database = None
        if path is None:
            migrate_legacy_private_store(MEMORY_FILE, LEGACY_MEMORY_FILE)
            self.database = database or RuntimeDatabase()
            if MEMORY_FILE.exists():
                self.database.import_json_document(
                    MEMORY_NAMESPACE,
                    MEMORY_FILE,
                    _validate_memory_data,
                    max_bytes=MAX_MEMORY_FILE_BYTES,
                )
            self.path = self.database.path
        else:
            self.path = Path(path)

    def _load(self):
        if self.database is not None:
            data = self.database.read_document(
                MEMORY_NAMESPACE, {"schema_version": 1, "memories": {}}, document_schema=1
            )
            return _validate_memory_data(data)
        if not self.path.exists():
            return {"schema_version": 1, "memories": {}}
        if self.path.is_symlink() or not self.path.is_file():
            raise ValueError("Memory path must be a regular file.")
        if self.path.stat().st_size > MAX_MEMORY_FILE_BYTES:
            raise ValueError("Memory file is unexpectedly large.")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return _validate_memory_data(data)

    def _save(self, data):
        _validate_memory_data(data)
        if self.database is not None:
            self.database.write_document(
                MEMORY_NAMESPACE, data, document_schema=1, max_bytes=MAX_MEMORY_FILE_BYTES
            )
            return
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

    def context_plan(self, account_id, query="", *, limit=20, budget_chars=DEFAULT_CONTEXT_BUDGET):
        """Build a bounded, observable context ladder without changing saved memory.

        Every selected memory starts at the abstract level. Relevant memories may be
        promoted to overview or full detail while the character budget permits. The
        returned trace explains each selection so callers can inspect why context was
        injected instead of treating retrieval as a hidden side effect.
        """
        if not isinstance(query, str) or len(query) > 500:
            raise ValueError("Memory context query must be text up to 500 characters.")
        if not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("Memory context limit must be between 1 and 100.")
        if not isinstance(budget_chars, int) or not 200 <= budget_chars <= 50_000:
            raise ValueError("Memory context budget must be between 200 and 50000 characters.")

        items = self.search(account_id, "", limit=100, enabled_only=True)
        query_tokens = _tokens(query)
        ranked = []
        for position, item in enumerate(items):
            title_tokens = _tokens(item.get("title", ""))
            content_tokens = _tokens(item.get("content", ""))
            title_hits = len(query_tokens & title_tokens)
            content_hits = len(query_tokens & content_tokens)
            score = (title_hits * 3) + content_hits
            ranked.append((score, -position, item, title_hits, content_hits))
        ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)

        selected = []
        trace = []
        used = 0
        for score, _, item, title_hits, content_hits in ranked[:limit]:
            abstract = f"[{item['category']}] {item['title']}"
            overview = f"{abstract}: {_clip(item['content'], OVERVIEW_CHARS)}"
            full = f"{abstract}: {item['content']}"

            if query_tokens and score >= 4:
                desired_level, candidate = "full", full
                reason = f"strong relevance: {title_hits} title token hits, {content_hits} content token hits"
            elif query_tokens and score > 0:
                desired_level, candidate = "overview", overview
                reason = f"partial relevance: {title_hits} title token hits, {content_hits} content token hits"
            else:
                desired_level, candidate = "abstract", abstract
                reason = "recency fallback; no query token match" if query_tokens else "recent active memory"

            remaining = budget_chars - used
            if len(candidate) > remaining and desired_level == "full":
                desired_level, candidate = "overview", overview
                reason += "; downgraded to overview by context budget"
            if len(candidate) > remaining and desired_level == "overview":
                desired_level, candidate = "abstract", abstract
                reason += "; downgraded to abstract by context budget"
            if len(candidate) > remaining:
                trace.append({
                    "memory_id": item["memory_id"],
                    "selected": False,
                    "level": None,
                    "score": score,
                    "reason": "skipped because context budget was exhausted",
                })
                continue

            selected.append(candidate)
            used += len(candidate)
            trace.append({
                "memory_id": item["memory_id"],
                "selected": True,
                "level": desired_level,
                "score": score,
                "reason": reason,
            })

        return {
            "query": query,
            "budget_chars": budget_chars,
            "used_chars": used,
            "context": selected,
            "trace": trace,
        }
