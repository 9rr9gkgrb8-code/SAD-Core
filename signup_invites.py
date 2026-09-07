"""Invite-only self-service student enrollment for Forge private alpha."""

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import threading
import uuid

from runtime_document import RuntimeJSONDocument

INVITES_NAMESPACE = "signup_invites"
INVITES_FILENAME = "signup_invites.json"
MAX_INVITES_FILE_BYTES = 1_000_000
MAX_INVITES = 500
DEFAULT_INVITE_MINUTES = 60 * 24 * 7


def _now():
    return datetime.now(timezone.utc)


def _hash_code(code):
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _validate(data):
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("invites"), list):
        raise ValueError("Unsupported signup invite data.")
    if len(data["invites"]) > MAX_INVITES:
        raise ValueError("Signup invite limit exceeded.")
    return data


class SignupInviteStore:
    def __init__(self, path=None, now=None, database=None):
        self.now = now or _now
        self.persistence = RuntimeJSONDocument(
            INVITES_FILENAME, INVITES_NAMESPACE, {"schema_version": 1, "invites": []},
            _validate, MAX_INVITES_FILE_BYTES, path=path, database=database,
        )
        self.lock = threading.RLock()

    def _load(self):
        return self.persistence.load()

    def _save(self, data):
        self.persistence.save(data)

    def create(self, created_by, *, expires_minutes=DEFAULT_INVITE_MINUTES, max_uses=1, guardian_required=True):
        if not isinstance(expires_minutes, int) or not 5 <= expires_minutes <= 60 * 24 * 30:
            raise ValueError("Invite expiry must be 5 minutes to 30 days.")
        if not isinstance(max_uses, int) or not 1 <= max_uses <= 25:
            raise ValueError("Invite max uses must be 1-25.")
        with self.lock:
            data = self._load()
            if len(data["invites"]) >= MAX_INVITES:
                raise ValueError("Signup invite limit reached.")
            code = secrets.token_urlsafe(24)
            item = {
                "invite_id": str(uuid.uuid4()), "code_hash": _hash_code(code),
                "created_by": created_by, "created_at": self.now().isoformat(),
                "expires_at": (self.now() + timedelta(minutes=expires_minutes)).isoformat(),
                "max_uses": max_uses, "uses": 0, "revoked": False,
                "guardian_required": bool(guardian_required),
            }
            data["invites"].append(item)
            self._save(data)
            return {"code": code, **self.public(item)}

    def list(self):
        return [self.public(item) for item in self._load()["invites"]]

    def revoke(self, invite_id):
        with self.lock:
            data = self._load()
            item = next((x for x in data["invites"] if x["invite_id"] == invite_id), None)
            if not item:
                raise KeyError("Invite not found.")
            item["revoked"] = True
            self._save(data)
            return self.public(item)

    def consume(self, code, *, guardian_consent=False):
        if not isinstance(code, str) or not code.strip():
            raise PermissionError("A valid signup invite is required.")
        with self.lock:
            data = self._load()
            digest = _hash_code(code.strip())
            item = next((x for x in data["invites"] if secrets.compare_digest(x["code_hash"], digest)), None)
            if not item or item.get("revoked"):
                raise PermissionError("Signup invite is invalid.")
            if self.now() >= datetime.fromisoformat(item["expires_at"]):
                raise PermissionError("Signup invite has expired.")
            if item.get("uses", 0) >= item.get("max_uses", 1):
                raise PermissionError("Signup invite has already been used.")
            if item.get("guardian_required") and guardian_consent is not True:
                raise PermissionError("Guardian consent confirmation is required for this invite.")
            item["uses"] = item.get("uses", 0) + 1
            self._save(data)
            return self.public(item)

    @staticmethod
    def public(item):
        return {key: item[key] for key in (
            "invite_id", "created_by", "created_at", "expires_at", "max_uses", "uses", "revoked", "guardian_required"
        )}
