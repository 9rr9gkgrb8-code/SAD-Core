"""Local one-time pairing and revocable device access for SAD mobile clients."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import threading
import uuid


MOBILE_STATE_FILE = Path(__file__).with_name("local_data") / "mobile_access.json"
PAIRING_MINUTES = 5
DEVICE_DAYS = 30
MAX_STATE_BYTES = 2_000_000
DEVICE_MODES = {"learning", "full_role"}


def _now():
    return datetime.now(timezone.utc)


def _secret_hash(value):
    if not isinstance(value, str) or not value:
        raise ValueError("A non-empty secret is required.")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _clean_label(value, field="label"):
    if not isinstance(value, str):
        raise ValueError(f"{field.capitalize()} must be text.")
    cleaned = value.strip()
    if not 1 <= len(cleaned) <= 80:
        raise ValueError(f"{field.capitalize()} must be 1-80 characters.")
    return cleaned


class MobileAccessStore:
    """Persist hashes of pairing codes and device tokens, never the raw secrets."""

    def __init__(self, state_file=MOBILE_STATE_FILE, now=None):
        self.state_file = Path(state_file)
        self.now = now or _now
        self.lock = threading.RLock()

    def _empty(self):
        return {"schema_version": 1, "pairings": [], "devices": []}

    def _load(self):
        if not self.state_file.exists():
            return self._empty()
        if self.state_file.stat().st_size > MAX_STATE_BYTES:
            raise ValueError("Mobile access state is unexpectedly large.")
        data = json.loads(self.state_file.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported mobile access state.")
        if not isinstance(data.get("pairings"), list) or not isinstance(data.get("devices"), list):
            raise ValueError("Invalid mobile access state.")
        return data

    def _save(self, data):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_file.with_suffix(self.state_file.suffix + ".tmp")
        temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        os.replace(temporary, self.state_file)

    def _prune_pairings(self, data):
        now = self.now()
        data["pairings"] = [
            item for item in data["pairings"]
            if not item.get("used_at") and datetime.fromisoformat(item["expires_at"]) > now
        ]

    def create_pairing(self, label, mode="learning"):
        label = _clean_label(label, "device label")
        if mode not in DEVICE_MODES:
            raise ValueError("Device mode must be learning or full_role.")
        with self.lock:
            data = self._load()
            self._prune_pairings(data)
            raw_code = f"{secrets.randbelow(100_000_000):08d}"
            expires = self.now() + timedelta(minutes=PAIRING_MINUTES)
            pairing = {
                "pairing_id": str(uuid.uuid4()),
                "label": label,
                "mode": mode,
                "code_hash": _secret_hash(raw_code),
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
        code_hash = _secret_hash(code)
        with self.lock:
            data = self._load()
            now = self.now()
            match = None
            for item in data["pairings"]:
                if item.get("used_at"):
                    continue
                if datetime.fromisoformat(item["expires_at"]) <= now:
                    continue
                if hmac.compare_digest(item["code_hash"], code_hash):
                    match = item
                    break
            if match is None:
                raise PermissionError("Pairing code is invalid or expired.")

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
