"""Local authentication and role authorization for SAD and Forge."""

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
import threading

from runtime_document import RuntimeJSONDocument


PASSWORD_ITERATIONS = 600_000
SESSION_HOURS = 12
MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15
MAX_ACCOUNTS_FILE_BYTES = 2_000_000
MAX_ACCOUNTS = 500
MAX_SESSIONS_PER_ACCOUNT = 10
MAX_TOTAL_SESSIONS = 1_000
ACCOUNTS_NAMESPACE = "accounts"
ACCOUNTS_FILENAME = "accounts.json"


class Role(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    OWNER = "owner"
    DEVELOPER = "developer"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


ROLE_PERMISSIONS = {
    Role.STUDENT.value: {"study:personal", "forge:play", "progress:own"},
    Role.TEACHER.value: {
        "study:personal", "forge:play", "progress:own", "progress:students",
        "account:create_student",
    },
    Role.DEVELOPER.value: {
        "study:personal", "development:view", "development:work", "development:work_assigned",
    },
    Role.REVIEWER.value: {
        "development:view", "development:review", "development:decide",
    },
    Role.VIEWER.value: {
        "development:view",
    },
    Role.OWNER.value: {
        "study:personal", "forge:play", "progress:own", "progress:students",
        "account:create_student", "account:create_teacher", "account:create_developer",
        "account:create_reviewer", "account:create_viewer",
        "account:list", "account:manage", "platform:manage",
        "development:view", "development:review", "development:work",
        "development:work_assigned", "development:decide", "development:govern",
    },
}


def _now():
    return datetime.now(timezone.utc)


def _normalized_username(username):
    if not isinstance(username, str):
        raise ValueError("Username must be text.")
    value = username.strip().lower()
    if not 3 <= len(value) <= 64 or not all(character.isalnum() or character in ".-_" for character in value):
        raise ValueError("Username must be 3-64 characters using letters, numbers, dot, dash, or underscore.")
    return value


def _validate_password(password):
    if not isinstance(password, str) or not 12 <= len(password) <= 1024:
        raise ValueError("Password must be 12-1024 characters.")
    if not any(character.isalpha() for character in password) or not any(character.isdigit() for character in password):
        raise ValueError("Password must contain at least one letter and one number.")


def _password_hash(password, salt=None):
    salt_bytes = secrets.token_bytes(16) if salt is None else bytes.fromhex(salt)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, PASSWORD_ITERATIONS)
    return salt_bytes.hex(), digest.hex()


def _validate_accounts_data(data):
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("accounts"), list):
        raise ValueError("Unsupported or invalid accounts data.")
    if len(data["accounts"]) > MAX_ACCOUNTS:
        raise ValueError("Accounts data exceeds the installation account limit.")
    seen_ids = set()
    seen_users = set()
    for account in data["accounts"]:
        if not isinstance(account, dict):
            raise ValueError("Invalid account record.")
        if account.get("role") not in ROLE_PERMISSIONS:
            raise ValueError("Account record contains an unsupported role.")
        account_id = account.get("account_id")
        username = account.get("username")
        if not isinstance(account_id, str) or not account_id or account_id in seen_ids:
            raise ValueError("Account IDs must be unique non-empty strings.")
        if not isinstance(username, str) or not username or username in seen_users:
            raise ValueError("Account usernames must be unique non-empty strings.")
        if not isinstance(account.get("password_salt"), str) or not isinstance(account.get("password_hash"), str):
            raise ValueError("Account password verifier data is invalid.")
        seen_ids.add(account_id)
        seen_users.add(username)
    return data


class AuthService:
    """Persist accounts in encrypted runtime state while keeping login sessions in memory."""

    def __init__(self, accounts_file=None, now=None, database=None):
        self.now = now or _now
        self.persistence = RuntimeJSONDocument(
            ACCOUNTS_FILENAME,
            ACCOUNTS_NAMESPACE,
            {"schema_version": 1, "accounts": []},
            _validate_accounts_data,
            MAX_ACCOUNTS_FILE_BYTES,
            path=accounts_file,
            database=database,
        )
        self.accounts_file = self.persistence.path
        self.sessions = {}
        self.lock = threading.RLock()

    def _load(self):
        return self.persistence.load()

    def _save(self, data):
        self.persistence.save(data)

    def _prune_sessions(self, now=None):
        now = now or self.now()
        self.sessions = {
            key: value for key, value in self.sessions.items()
            if value.get("expires_at") and now < value["expires_at"]
        }

    @staticmethod
    def _session_order(item):
        session = item[1]
        return session.get("created_at") or session.get("expires_at")

    def _make_session_room(self, account_id, now):
        self._prune_sessions(now)
        account_sessions = sorted(
            ((key, value) for key, value in self.sessions.items() if value.get("account_id") == account_id),
            key=self._session_order,
        )
        while len(account_sessions) >= MAX_SESSIONS_PER_ACCOUNT:
            key, _ = account_sessions.pop(0)
            self.sessions.pop(key, None)
        while len(self.sessions) >= MAX_TOTAL_SESSIONS:
            key, _ = min(self.sessions.items(), key=self._session_order)
            self.sessions.pop(key, None)

    def has_owner(self):
        return any(account.get("role") == Role.OWNER.value for account in self._load()["accounts"])

    def _find(self, data, username):
        return next((account for account in data["accounts"] if account["username"] == username), None)

    def bootstrap_owner(self, username, password, explicitly_approved=False):
        """Create the first owner only through an explicit local approval action."""
        with self.lock:
            if not explicitly_approved:
                raise PermissionError("Explicit approval is required to bootstrap an owner.")
            data = self._load()
            if any(account["role"] == Role.OWNER.value for account in data["accounts"]):
                raise PermissionError("An owner already exists.")
            return self._create(data, username, password, Role.OWNER.value)

    def create_account(self, username, password, role, actor_token):
        with self.lock:
            role_value = Role(role).value
            actor = self.require(actor_token)
            required = {
                Role.STUDENT.value: "account:create_student",
                Role.TEACHER.value: "account:create_teacher",
                Role.DEVELOPER.value: "account:create_developer",
                Role.REVIEWER.value: "account:create_reviewer",
                Role.VIEWER.value: "account:create_viewer",
                Role.OWNER.value: None,
            }[role_value]
            if required is None or required not in ROLE_PERMISSIONS[actor["role"]]:
                raise PermissionError("The signed-in account cannot create that role.")
            return self._create(self._load(), username, password, role_value)

    def _create(self, data, username, password, role):
        normalized = _normalized_username(username)
        _validate_password(password)
        if len(data["accounts"]) >= MAX_ACCOUNTS:
            raise ValueError("Account limit reached for this Alpha installation.")
        if self._find(data, normalized):
            raise ValueError("That username already exists.")
        salt, password_hash = _password_hash(password)
        account = {
            "account_id": str(uuid.uuid4()), "username": normalized, "role": role,
            "password_salt": salt, "password_hash": password_hash,
            "created_at": self.now().isoformat(), "active": True,
            "failed_attempts": 0, "locked_until": None,
            "profile": {"display_name": normalized, "level": 0},
        }
        data["accounts"].append(account)
        self._save(data)
        return self.public_account(account)

    def login(self, username, password):
        with self.lock:
            normalized = _normalized_username(username)
            data = self._load()
            account = self._find(data, normalized)
            if not account:
                return None
            now = self.now()
            locked_until = datetime.fromisoformat(account["locked_until"]) if account.get("locked_until") else None
            if locked_until and now < locked_until:
                return None
            _, candidate = _password_hash(password, account["password_salt"])
            valid = account.get("active", False) and hmac.compare_digest(candidate, account["password_hash"])
            if not valid:
                account["failed_attempts"] = account.get("failed_attempts", 0) + 1
                if account["failed_attempts"] >= MAX_FAILED_ATTEMPTS:
                    account["locked_until"] = (now + timedelta(minutes=LOCK_MINUTES)).isoformat()
                    account["failed_attempts"] = 0
                self._save(data)
                return None
            account["failed_attempts"] = 0
            account["locked_until"] = None
            self._save(data)
            self._make_session_room(account["account_id"], now)
            token = secrets.token_urlsafe(32)
            self.sessions[token] = {
                "account_id": account["account_id"],
                "created_at": now,
                "expires_at": now + timedelta(hours=SESSION_HOURS),
            }
            return token

    def require(self, token, permission=None):
        session = self.sessions.get(token)
        if not session or self.now() >= session["expires_at"]:
            self.sessions.pop(token, None)
            raise PermissionError("A valid login session is required.")
        data = self._load()
        account = next((item for item in data["accounts"] if item["account_id"] == session["account_id"] and item.get("active")), None)
        if not account:
            raise PermissionError("That account is unavailable.")
        if permission and permission not in ROLE_PERMISSIONS[account["role"]]:
            raise PermissionError("That role does not have the required permission.")
        return self.public_account(account)

    def logout(self, token):
        return self.sessions.pop(token, None) is not None

    def list_accounts(self, token):
        """Return public account records to an authorized local administrator."""
        self.require(token, "account:list")
        return [self.public_account(account) for account in self._load()["accounts"]]

    def list_students(self, token):
        self.require(token, "progress:students")
        return [
            self.public_account(account) for account in self._load()["accounts"]
            if account["role"] == Role.STUDENT.value and account.get("active")
        ]

    def set_account_active(self, account_id, active, token):
        """Enable or disable a non-owner account and revoke its live sessions."""
        actor = self.require(token, "account:manage")
        if not isinstance(active, bool):
            raise ValueError("Active must be true or false.")
        with self.lock:
            data = self._load()
            account = next((item for item in data["accounts"] if item["account_id"] == account_id), None)
            if not account:
                raise KeyError("Account not found.")
            if account["role"] == Role.OWNER.value or account["account_id"] == actor["account_id"]:
                raise PermissionError("Owner accounts cannot be disabled through this endpoint.")
            account["active"] = active
            self._save(data)
            if not active:
                self.sessions = {
                    key: value for key, value in self.sessions.items()
                    if value["account_id"] != account_id
                }
            return self.public_account(account)

    def change_password(self, token, current_password, new_password):
        """Change the signed-in account password and revoke every other session."""
        actor = self.require(token)
        _validate_password(new_password)
        with self.lock:
            data = self._load()
            account = next(item for item in data["accounts"] if item["account_id"] == actor["account_id"])
            _, candidate = _password_hash(current_password, account["password_salt"])
            if not hmac.compare_digest(candidate, account["password_hash"]):
                raise PermissionError("Current password is incorrect.")
            salt, digest = _password_hash(new_password)
            account["password_salt"], account["password_hash"] = salt, digest
            self._save(data)
            self.sessions = {token: self.sessions[token]}
            return True

    def get_profile(self, token):
        account = self.require(token)
        data = self._load()
        stored = next(item for item in data["accounts"] if item["account_id"] == account["account_id"])
        profile = stored.get("profile", {})
        display_name = profile.get("display_name", account["username"])
        level = profile.get("level", 0)
        return {
            "display_name": display_name if isinstance(display_name, str) and display_name.strip() else account["username"],
            "level": level if level in {0, 1, 2} else 0,
        }

    def update_profile(self, token, display_name=None, level=None):
        account = self.require(token)
        data = self._load()
        stored = next(item for item in data["accounts"] if item["account_id"] == account["account_id"])
        profile = stored.setdefault("profile", {"display_name": account["username"], "level": 0})
        if display_name is not None:
            if not isinstance(display_name, str) or not display_name.strip() or len(display_name.strip()) > 80:
                raise ValueError("Display name must be 1-80 characters.")
            profile["display_name"] = display_name.strip()
        if level is not None:
            if level not in {0, 1, 2}:
                raise ValueError("Dialogue level must be 0, 1, or 2.")
            profile["level"] = level
        self._save(data)
        return dict(profile)

    @staticmethod
    def public_account(account):
        return {key: account[key] for key in ("account_id", "username", "role", "created_at", "active")}
