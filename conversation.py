"""Durable per-account SAD conversation sessions for browser and mobile chat."""

from __future__ import annotations

from datetime import datetime, timezone
import threading
import uuid

from model_adapter import generate_local_response
from personality import (
    detect_conversation_topic,
    detect_topic_detail,
    get_contextual_follow_up,
    get_response,
)
from runtime_document import RuntimeJSONDocument


CHAT_FILENAME = "chat_history.json"
CHAT_NAMESPACE = "chat_history"
MAX_CHAT_FILE_BYTES = 12_000_000
MAX_ACTIVE_SESSIONS_PER_ACCOUNT = 30
MAX_MESSAGES_PER_SESSION = 500
MAX_MESSAGE_CHARACTERS = 50_000
MAX_TITLE_CHARACTERS = 72


def _now():
    return datetime.now(timezone.utc)


def _validate_message(message):
    if not isinstance(message, str):
        raise ValueError("Chat message must be text.")
    value = message.strip()
    if not value:
        raise ValueError("Chat message cannot be empty.")
    if len(value) > MAX_MESSAGE_CHARACTERS:
        raise ValueError("Chat message is too long.")
    return value


def _session_title(message):
    compact = " ".join(message.split())
    if len(compact) <= MAX_TITLE_CHARACTERS:
        return compact
    return compact[: MAX_TITLE_CHARACTERS - 1].rstrip() + "…"


def _validate_chat_data(data):
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("sessions"), dict):
        raise ValueError("Unsupported or invalid chat history data.")
    for session_id, session in data["sessions"].items():
        if not isinstance(session_id, str) or not isinstance(session, dict):
            raise ValueError("Invalid conversation record.")
        if session.get("session_id") != session_id or not isinstance(session.get("account_id"), str):
            raise ValueError("Conversation ownership metadata is invalid.")
        messages = session.get("messages")
        if not isinstance(messages, list) or len(messages) > MAX_MESSAGES_PER_SESSION:
            raise ValueError("Conversation message list is invalid or oversized.")
    return data


class ConversationStore:
    """Persist private chat history while enforcing account ownership."""

    def __init__(self, path=None, now=None, database=None):
        self.now = now or _now
        self.persistence = RuntimeJSONDocument(
            CHAT_FILENAME,
            CHAT_NAMESPACE,
            {"schema_version": 1, "sessions": {}},
            _validate_chat_data,
            MAX_CHAT_FILE_BYTES,
            path=path,
            database=database,
        )
        self.path = self.persistence.path
        self.lock = threading.RLock()

    def _load(self):
        return self.persistence.load()

    def _save(self, data):
        self.persistence.save(data)

    @staticmethod
    def _public_session(session, include_messages=False):
        payload = {
            "session_id": session["session_id"],
            "title": session["title"],
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
            "archived_at": session.get("archived_at"),
            "message_count": len(session.get("messages", [])),
        }
        if include_messages:
            payload["messages"] = [dict(message) for message in session.get("messages", [])]
        return payload

    @staticmethod
    def _owned(data, account_id, session_id):
        session = data["sessions"].get(session_id)
        if not session or session.get("account_id") != account_id:
            raise KeyError("Conversation not found.")
        return session

    def create_session(self, account_id):
        with self.lock:
            data = self._load()
            active = [
                session for session in data["sessions"].values()
                if session.get("account_id") == account_id and not session.get("archived_at")
            ]
            if len(active) >= MAX_ACTIVE_SESSIONS_PER_ACCOUNT:
                raise ValueError("Archive an older conversation before starting another one.")
            timestamp = self.now().isoformat()
            session_id = str(uuid.uuid4())
            session = {
                "session_id": session_id,
                "account_id": account_id,
                "title": "New conversation",
                "created_at": timestamp,
                "updated_at": timestamp,
                "archived_at": None,
                "messages": [],
            }
            data["sessions"][session_id] = session
            self._save(data)
            return self._public_session(session, include_messages=True)

    def list_sessions(self, account_id):
        with self.lock:
            data = self._load()
            sessions = [
                self._public_session(session)
                for session in data["sessions"].values()
                if session.get("account_id") == account_id and not session.get("archived_at")
            ]
            return sorted(sessions, key=lambda session: session["updated_at"], reverse=True)

    def get_session(self, account_id, session_id):
        with self.lock:
            data = self._load()
            session = self._owned(data, account_id, session_id)
            if session.get("archived_at"):
                raise KeyError("Conversation not found.")
            return self._public_session(session, include_messages=True)

    def raw_session(self, account_id, session_id):
        """Return a detached session copy for response generation."""
        return self.get_session(account_id, session_id)

    def append_turn(self, account_id, session_id, user_text, assistant_text, engine):
        user_text = _validate_message(user_text)
        assistant_text = _validate_message(assistant_text)
        if engine not in {"local_model", "built_in"}:
            raise ValueError("Unsupported chat engine.")
        with self.lock:
            data = self._load()
            session = self._owned(data, account_id, session_id)
            if session.get("archived_at"):
                raise KeyError("Conversation not found.")
            if len(session["messages"]) + 2 > MAX_MESSAGES_PER_SESSION:
                raise ValueError("This conversation is full. Start a new conversation to continue.")
            timestamp = self.now().isoformat()
            session["messages"].append({"role": "user", "text": user_text, "created_at": timestamp})
            session["messages"].append({
                "role": "assistant", "text": assistant_text, "created_at": timestamp, "engine": engine,
            })
            if session["title"] == "New conversation":
                session["title"] = _session_title(user_text)
            session["updated_at"] = timestamp
            self._save(data)
            return self._public_session(session, include_messages=True)

    def archive_session(self, account_id, session_id):
        with self.lock:
            data = self._load()
            session = self._owned(data, account_id, session_id)
            if not session.get("archived_at"):
                timestamp = self.now().isoformat()
                session["archived_at"] = timestamp
                session["updated_at"] = timestamp
                self._save(data)
            return self._public_session(session)


def generate_chat_reply(message, profile, session, memories=None):
    """Use the configured local model, with the built-in dialogue layer as fallback.

    `memories` contains only explicitly saved, enabled memory strings selected by the
    caller. Built-in dialogue does not claim to consume this separate memory context.
    """
    message = _validate_message(message)
    display_name = profile.get("display_name") or ""
    level = profile.get("level", 0)
    if level not in {0, 1, 2}:
        level = 0

    messages = session.get("messages", [])
    recent_history = [
        ("User" if item.get("role") == "user" else "Sasha", item.get("text", ""))
        for item in messages[-12:]
        if item.get("role") in {"user", "assistant"} and isinstance(item.get("text"), str)
    ]
    memory_history = []
    if memories:
        for item in list(memories)[-3:]:
            if isinstance(item, str) and item.strip():
                memory_history.append(("Saved memory", item.strip()[:8_000]))
    history = memory_history + (recent_history[-3:] if memory_history else recent_history)
    local_reply = generate_local_response(message, display_name, history)
    if local_reply:
        return local_reply, "local_model"

    previous_response = next(
        (item.get("text") for item in reversed(messages) if item.get("role") == "assistant"),
        None,
    )
    previous_user = next(
        (item.get("text") for item in reversed(messages) if item.get("role") == "user"),
        None,
    )
    previous_topic = detect_conversation_topic(previous_user or "")
    previous_detail = detect_topic_detail(previous_user or "", previous_topic) if previous_topic else None
    contextual = get_contextual_follow_up(
        message,
        level,
        display_name,
        previous_topic,
        previous_detail,
        previous_response,
    )
    reply = contextual or get_response(message, level, display_name, previous_response)
    return reply, "built_in"
