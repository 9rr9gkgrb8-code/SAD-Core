"""Local one-time pairing and revocable device access for SAD mobile clients."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
import threading
import uuid

from runtime_document import RuntimeJSONDocument


MOBILE_FILENAME = "mobile_access.json"
MOBILE_NAMESPACE = "mobile_access"
PAIRING_MINUTES = 5
DEVICE_DAYS = 30
PAIRING_HASH_ITERATIONS = 200_000
MAX_ACTIVE_PAIRINGS = 10
MAX_ACTIVE_DEVICES = 50
MAX_STATE_BYTES = 2_000_000
DEVICE_MODES = {"learning", "full_role"}


def _now():
    return datetime.now(timezone.utc)


def _secret_hash(value):
    if not isinstance(value, str) or not value:
        raise ValueError("A non-empty secret is required.")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pairing_hash(value, salt=None):
    if not isinstance(value, str) or len(value) != 8 or not value.isdigit():
        raise ValueError("Pairing code must be exactly 8 digits.")
    salt_bytes = secrets.token_bytes(16) if salt is None else bytes.fromhex(salt)
    digest = hashlib.pbkdf2_hmac(
        "sha256", value.encode("utf-8"), salt_bytes, PAIRING_HASH_ITERATIONS,
    ).hex()
    return salt_bytes.hex(), digest


def _pairing_matches(item, code):
    salt = item.get("code_salt")
    if salt:
        try:
            _, candidate = _pairing_hash(code, salt)
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(candidate, item.get("code_hash", ""))
    try:
        candidate = _secret_hash(code)
    except ValueError:
        return False
    return hmac.compare_digest(candidate, item.get("code_hash", ""))


def _clean_label(value, field="label"):
    if not isinstance(value, str):
        raise ValueError(f"{field.capitalize()} must be text.")
    cleaned = value.strip()
    if not 1 <= len(cleaned) <= 80:
        raise ValueError(f"{field.capitalize()} must be 1-80 characters.")
    return cleaned


def _validate_mobile_data(data):
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported mobile access state.")
    if not isinstance(data.get("pairings"), list) or not isinstance(data.get("devices"), list):
        raise ValueError("Invalid mobile access state.")
    if len(data["pairings"]) > 1_000 or len(data["devices"]) > 5_000:
        raise ValueError("Mobile access state is unexpectedly large.")
    return data


class MobileAccessStore:
    """Persist only hashes of pairing codes/device tokens inside encrypted runtime state."""

    def __init__(self, state_file=None, now=None, database=None):
        self.now = now or _now
        self.persistence = RuntimeJSONDocument(
            MOBILE_FILENAME,
            MOBILE_NAMESPACE,
            {"schema_version": 1, "pairings": [], "devices": []},
            _validate_mobile_data,
            MAX_STATE_BYTES,
            path=state_file,
            database=database,
        )
        self.state_file = self.persistence.path
        self.lock = threading.RLock()

    def _empty(self):
        return {"schema_version": 1, "pairings": [], "devices": []}

    def _load(self):
        return self.persistence.load()

    def _save(self, data):
        self.persistence.save(data)

    def _prune_pairings(self, data):
        now = self.now()
        data["pairings"] = [
            item for item in data["pairings"]
            if not item.get("used_at") and datetime.fromisoformat(item["expires_at"]) > now
        ]

    def _active_devices(self, data):
        now = self.now()
        return [
            item for item in data["devices"]
            if not item.get("revoked_at") and datetime.fromisoformat(item["expires_at"]) > now
        ]

    def create_pairing(self, label, mode="learning"):
        label = _clean_label(label, "device label")
        if mode not in DEVICE_MODES:
            raise ValueError("Device mode must be learning or full_role.")
        with self.lock:
            data = self._load()
            self._prune_pairings(data)
            if len(data["pairings"]) >= MAX_ACTIVE_PAIRINGS:
                raise ValueError("Too many active pairing codes. Let one expire before creating another.")
            raw_code = f"{secrets.randbelow(100_000_000):08d}"
            salt, digest = _pairing_hash(raw_code)
            expires = self.now() + timedelta(minutes=PAIRING_MINUTES)
            pairing = {
                "pairing_id": str(uuid.uuid4()),
                "label": label,
                "mode": mode,
                "code_salt": salt,
                "code_hash": digest,
                "created_at": self.now().isoformat(),
                "expires_at": expires.isoformat(),
                "used_at": None,
            }
            data["pairings"].append(pairing)
            self._save(data)
            return {
                "pairing_id": pairing["pairing_id"],
                "code": raw_code,
                "label": label,
                "mode": mode,
                "expires_at": pairing["expires_at"],
            }

    def consume_pairing(self, code, device_label=None):
        if not isinstance(code, str) or len(code) != 8 or not code.isdigit():
            raise PermissionError("Pairing code is invalid or expired.")
        with self.lock:
            data = self._load()
            now = self.now()
            match = None
            for item in data["pairings"]:
                if item.get("used_at"):
                    continue
                if datetime.fromisoformat(item["expires_at"]) <= now:
                    continue
                if _pairing_matches(item, code):
                    match = item
                    break
            if match is None:
                raise PermissionError("Pairing code is invalid or expired.")
            if len(self._active_devices(data)) >= MAX_ACTIVE_DEVICES:
                raise PermissionError("Active paired-device limit reached.")

            raw_token = secrets.token_urlsafe(32)
            device = {
                "device_id": str(uuid.uuid4()),
                "label": _clean_label(device_label or match["label"], "device label"),
                "mode": match["mode"],
                "token_hash": _secret_hash(raw_token),
                "paired_at": now.isoformat(),
                "expires_at": (now + timedelta(days=DEVICE_DAYS)).isoformat(),
                "revoked_at": None,
            }
            match["used_at"] = now.isoformat()
            data["devices"].append(device)
            self._save(data)
            return {"device_token": raw_token, "device": self._public_device(device)}

    def require_device(self, raw_token):
        token_hash = _secret_hash(raw_token)
        with self.lock:
            data = self._load()
            now = self.now()
            for item in data["devices"]:
                if item.get("revoked_at") or datetime.fromisoformat(item["expires_at"]) <= now:
                    continue
                if hmac.compare_digest(item["token_hash"], token_hash):
                    return self._public_device(item)
        raise PermissionError("This phone is not paired or its access has expired.")

    def list_devices(self):
        with self.lock:
            return [self._public_device(item) for item in self._load()["devices"]]

    def revoke_device(self, device_id):
        with self.lock:
            data = self._load()
            device = next((item for item in data["devices"] if item["device_id"] == device_id), None)
            if not device:
                raise KeyError("Mobile device not found.")
            if not device.get("revoked_at"):
                device["revoked_at"] = self.now().isoformat()
                self._save(data)
            return self._public_device(device)

    @staticmethod
    def _public_device(device):
        return {
            key: device.get(key)
            for key in ("device_id", "label", "mode", "paired_at", "expires_at", "revoked_at")
        }
