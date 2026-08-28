"""Owner-governed machine credentials for local SAD Platform clients."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import threading
import uuid

from platform_events import EVENT_TYPES
from runtime_privacy import migrate_legacy_private_store, private_store_path


LEGACY_CLIENTS_FILE = Path(__file__).with_name("platform_clients.json")
CLIENTS_FILE = private_store_path("platform_clients.json")
MAX_CLIENTS_FILE_BYTES = 1_000_000
MAX_CLIENTS = 100
MACHINE_CAPABILITIES = frozenset({
    "platform:discover",
    "platform:catalog",
    "platform:modules",
    "platform:compatibility",
    "platform:events",
})


def _now():
    return datetime.now(timezone.utc).isoformat()


def _hash_secret(secret, salt=None):
    if not isinstance(secret, str) or not secret:
        raise ValueError("Client secret must be non-empty text.")
    salt_bytes = secrets.token_bytes(16) if salt is None else bytes.fromhex(salt)
    digest = hashlib.sha256(salt_bytes + secret.encode("utf-8")).hexdigest()
    return salt_bytes.hex(), digest


def _public(record):
    return {key: value for key, value in record.items() if key not in {"secret_salt", "secret_hash"}}


class PlatformClientStore:
    """Persist local app registrations while returning each secret only at creation/rotation."""

    def __init__(self, path=CLIENTS_FILE):
        self.path = Path(path)
        if self.path == CLIENTS_FILE:
            migrate_legacy_private_store(self.path, LEGACY_CLIENTS_FILE)
        self.lock = threading.RLock()

    def _load(self):
        if not self.path.exists():
            return {"schema_version": 1, "clients": []}
        if self.path.is_symlink() or not self.path.is_file():
            raise ValueError("Platform client path must be a regular file.")
        if self.path.stat().st_size > MAX_CLIENTS_FILE_BYTES:
            raise ValueError("Platform client file is unexpectedly large.")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or not isinstance(data.get("clients"), list):
            raise ValueError("Unsupported or invalid platform client file.")
        return data

    def _save(self, data):
        encoded = json.dumps(data, indent=2)
        if len(encoded.encode("utf-8")) > MAX_CLIENTS_FILE_BYTES:
            raise ValueError("Platform client registry exceeded its storage limit.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(encoded, encoding="utf-8")
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        os.replace(temporary, self.path)

    @staticmethod
    def _validate_name(name):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
            raise ValueError("Client name must be 1-80 characters.")
        return name.strip()

    @staticmethod
    def _validate_capabilities(capability_ids):
        if not isinstance(capability_ids, list) or not capability_ids:
            raise ValueError("At least one machine capability is required.")
        selected = set(capability_ids)
        if len(selected) != len(capability_ids) or not selected.issubset(MACHINE_CAPABILITIES):
            raise ValueError("Unsupported or duplicate machine capability.")
        return sorted(selected)

    @staticmethod
    def _validate_events(event_types):
        if event_types is None:
            return []
        if not isinstance(event_types, list):
            raise ValueError("event_types must be a list.")
        selected = set(event_types)
        if len(selected) != len(event_types) or not selected.issubset(EVENT_TYPES):
            raise ValueError("Unsupported or duplicate event subscription.")
        return sorted(selected)

    def create(self, name, capability_ids, event_types=None):
        name = self._validate_name(name)
        capabilities = self._validate_capabilities(capability_ids)
        events = self._validate_events(event_types)
        if events and "platform:events" not in capabilities:
            raise ValueError("Event subscriptions require platform:events capability.")
        with self.lock:
            data = self._load()
            if len(data["clients"]) >= MAX_CLIENTS:
                raise ValueError("Platform client limit reached.")
            client_id = str(uuid.uuid4())
            raw_secret = secrets.token_urlsafe(32)
            salt, digest = _hash_secret(raw_secret)
            record = {
                "client_id": client_id,
                "name": name,
                "capability_ids": capabilities,
                "event_types": events,
                "active": True,
                "created_at": _now(),
                "updated_at": _now(),
                "secret_salt": salt,
                "secret_hash": digest,
            }
            data["clients"].append(record)
            self._save(data)
            result = _public(record)
            result["client_secret"] = raw_secret
            return result

    def list(self):
        return [_public(record) for record in self._load()["clients"]]

    def get(self, client_id):
        record = next((item for item in self._load()["clients"] if item["client_id"] == client_id), None)
        if not record:
            raise KeyError("Platform client not found.")
        return _public(record)

    def rotate(self, client_id):
        with self.lock:
            data = self._load()
            record = next((item for item in data["clients"] if item["client_id"] == client_id), None)
            if not record:
                raise KeyError("Platform client not found.")
            if not record.get("active"):
                raise PermissionError("Inactive platform client cannot rotate credentials.")
            raw_secret = secrets.token_urlsafe(32)
            salt, digest = _hash_secret(raw_secret)
            record["secret_salt"] = salt
            record["secret_hash"] = digest
            record["updated_at"] = _now()
            self._save(data)
            result = _public(record)
            result["client_secret"] = raw_secret
            return result

    def revoke(self, client_id):
        with self.lock:
            data = self._load()
            record = next((item for item in data["clients"] if item["client_id"] == client_id), None)
            if not record:
                raise KeyError("Platform client not found.")
            record["active"] = False
            record["updated_at"] = _now()
            self._save(data)
            return _public(record)

    def authenticate_header(self, authorization):
        if not isinstance(authorization, str) or not authorization.startswith("SAD-App "):
            raise PermissionError("SAD-App authentication is required.")
        credential = authorization.removeprefix("SAD-App ").strip()
        if "." not in credential:
            raise PermissionError("Invalid SAD-App credential.")
        client_id, raw_secret = credential.split(".", 1)
        data = self._load()
        record = next((item for item in data["clients"] if item["client_id"] == client_id and item.get("active")), None)
        if not record:
            raise PermissionError("Invalid SAD-App credential.")
        _, candidate = _hash_secret(raw_secret, record["secret_salt"])
        if not hmac.compare_digest(candidate, record["secret_hash"]):
            raise PermissionError("Invalid SAD-App credential.")
        return _public(record)

    def require(self, authorization, capability_id):
        client = self.authenticate_header(authorization)
        if capability_id not in client["capability_ids"]:
            raise PermissionError("Platform client lacks the required scope.")
        return client
