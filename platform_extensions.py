"""Declarative external extension contracts for SAD Platform.

Extensions remain out-of-process SAD clients. Registering a manifest never loads code,
starts a process, grants credentials, grants human permissions, falls back to host
execution, or grants Git authority.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re
import threading
import uuid

from platform_events import EVENT_TYPES
from runtime_document import RuntimeJSONDocument


EXTENSIONS_NAMESPACE = "platform_extensions"
EXTENSIONS_FILENAME = "platform_extensions.json"
MAX_EXTENSIONS_FILE_BYTES = 2_000_000
MAX_EXTENSIONS = 250
MAX_REQUIREMENTS = 64
EXTENSION_STATES = frozenset({"registered", "revoked"})
ALLOWED_MANIFEST_KEYS = frozenset({
    "name", "publisher", "version", "description", "required_capabilities",
    "requested_event_types", "execution_model", "transport", "network_scope",
    "core_code_loading", "host_fallback", "git_authority",
})
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, name, maximum, *, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError(f"{name} must be text.")
    normalized = value.strip()
    if not allow_empty and not normalized:
        raise ValueError(f"{name} must not be empty.")
    if len(normalized) > maximum:
        raise ValueError(f"{name} exceeds {maximum} characters.")
    return normalized


def _normalize_requirements(requirements):
    if not isinstance(requirements, list) or len(requirements) > MAX_REQUIREMENTS:
        raise ValueError(f"required_capabilities must be a list of at most {MAX_REQUIREMENTS} entries.")
    normalized = []
    seen = set()
    for requirement in requirements:
        if not isinstance(requirement, dict) or set(requirement) - {"capability_id", "min_version"}:
            raise ValueError("Each capability requirement may contain only capability_id and min_version.")
        capability_id = _text(requirement.get("capability_id"), "capability_id", 128)
        minimum = _text(requirement.get("min_version", "0.0.0"), "min_version", 32)
        if not SEMVER.fullmatch(minimum):
            raise ValueError("min_version must use numeric major.minor.patch format.")
        if capability_id in seen:
            raise ValueError("Duplicate extension capability requirement.")
        seen.add(capability_id)
        normalized.append({"capability_id": capability_id, "min_version": minimum})
    return normalized


def _normalize_events(event_types):
    if event_types is None:
        return []
    if not isinstance(event_types, list):
        raise ValueError("requested_event_types must be a list.")
    selected = []
    seen = set()
    for event_type in event_types:
        event_type = _text(event_type, "event_type", 128)
        if event_type not in EVENT_TYPES:
            raise ValueError("Unsupported platform event subscription.")
        if event_type in seen:
            raise ValueError("Duplicate platform event subscription.")
        seen.add(event_type)
        selected.append(event_type)
    return sorted(selected)


def normalize_extension_manifest(manifest):
    if not isinstance(manifest, dict):
        raise ValueError("Extension manifest must be an object.")
    unknown = set(manifest) - ALLOWED_MANIFEST_KEYS
    if unknown:
        raise ValueError("Extension manifest contains unsupported fields: " + ", ".join(sorted(unknown)))
    name = _text(manifest.get("name"), "name", 100)
    publisher = _text(manifest.get("publisher"), "publisher", 120)
    version = _text(manifest.get("version"), "version", 32)
    if not SEMVER.fullmatch(version):
        raise ValueError("Extension version must use numeric major.minor.patch format.")
    description = _text(manifest.get("description", ""), "description", 2_000, allow_empty=True)
    requirements = _normalize_requirements(manifest.get("required_capabilities", []))
    events = _normalize_events(manifest.get("requested_event_types", []))

    if manifest.get("execution_model", "external_process") != "external_process":
        raise ValueError("SAD extensions must execute outside the SAD Core process.")
    if manifest.get("transport", "sad_app_http") != "sad_app_http":
        raise ValueError("SAD extensions must use the reviewed SAD-App HTTP contract.")
    if manifest.get("network_scope", "loopback_only") != "loopback_only":
        raise ValueError("SAD extension network scope must remain loopback_only in Platform Alpha.")
    if manifest.get("core_code_loading", False) is not False:
        raise ValueError("Dynamic extension code loading into SAD Core is disabled.")
    if manifest.get("host_fallback", False) is not False:
        raise ValueError("Extensions may not silently fall back to host execution.")
    if manifest.get("git_authority", "none") != "none":
        raise ValueError("Extensions receive no Git authority.")

    return {
        "name": name,
        "publisher": publisher,
        "version": version,
        "description": description,
        "required_capabilities": requirements,
        "requested_event_types": events,
        "execution_model": "external_process",
        "transport": "sad_app_http",
        "network_scope": "loopback_only",
        "core_code_loading": False,
        "host_fallback": False,
        "git_authority": "none",
    }


def _fingerprint(manifest):
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_extension_data(data):
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("extensions"), list):
        raise ValueError("Unsupported or invalid platform extension registry.")
    if len(data["extensions"]) > MAX_EXTENSIONS:
        raise ValueError("Platform extension registry exceeds the installation limit.")
    seen = set()
    for record in data["extensions"]:
        if not isinstance(record, dict):
            raise ValueError("Platform extension record must be an object.")
        extension_id = _text(record.get("extension_id"), "extension_id", 128)
        if extension_id in seen:
            raise ValueError("Platform extension IDs must be unique.")
        seen.add(extension_id)
        normalized = normalize_extension_manifest(record.get("manifest"))
        if _fingerprint(normalized) != record.get("manifest_fingerprint"):
            raise ValueError("Platform extension manifest fingerprint mismatch.")
        if record.get("state") not in EXTENSION_STATES:
            raise ValueError("Unsupported platform extension state.")
        _text(record.get("registered_by"), "registered_by", 128)
        _text(record.get("created_at"), "created_at", 80)
        _text(record.get("updated_at"), "updated_at", 80)
        compatibility = record.get("compatibility")
        if not isinstance(compatibility, dict) or not isinstance(compatibility.get("compatible"), bool):
            raise ValueError("Platform extension compatibility snapshot is invalid.")
        if record["state"] == "revoked":
            _text(record.get("revocation_reason"), "revocation_reason", 2_000)
            _text(record.get("revoked_at"), "revoked_at", 80)
            _text(record.get("revoked_by"), "revoked_by", 128)
    return data


class PlatformExtensionStore:
    """Persist declarative extension contracts without executing them."""

    def __init__(self, path=None, database=None):
        self.lock = threading.RLock()
        self.persistence = RuntimeJSONDocument(
            EXTENSIONS_FILENAME,
            EXTENSIONS_NAMESPACE,
            {"schema_version": 1, "extensions": []},
            _validate_extension_data,
            MAX_EXTENSIONS_FILE_BYTES,
            path=path,
            database=database,
        )
        self.path = self.persistence.path

    def _load(self):
        return self.persistence.load()

    def _save(self, data):
        self.persistence.save(data)

    def list(self):
        return deepcopy(self._load()["extensions"])

    def get(self, extension_id):
        record = next((item for item in self._load()["extensions"] if item["extension_id"] == extension_id), None)
        if not record:
            raise KeyError("Platform extension not found.")
        return deepcopy(record)

    def register(self, manifest, registry, *, registered_by):
        registered_by = _text(registered_by, "registered_by", 128)
        normalized = normalize_extension_manifest(manifest)
        fingerprint = _fingerprint(normalized)
        compatibility = registry.compatibility(normalized["required_capabilities"], registry.capabilities.keys())
        with self.lock:
            data = self._load()
            if len(data["extensions"]) >= MAX_EXTENSIONS:
                raise ValueError("Platform extension registry limit reached.")
            duplicate = next(
                (
                    item for item in data["extensions"]
                    if item["manifest_fingerprint"] == fingerprint and item["state"] == "registered"
                ),
                None,
            )
            if duplicate:
                raise ValueError("This extension manifest is already registered.")
            timestamp = _now()
            record = {
                "extension_id": str(uuid.uuid4()),
                "contract_version": 1,
                "manifest": normalized,
                "manifest_fingerprint": fingerprint,
                "compatibility": compatibility,
                "state": "registered",
                "registered_by": registered_by,
                "created_at": timestamp,
                "updated_at": timestamp,
                "revoked_at": None,
                "revoked_by": None,
                "revocation_reason": None,
                "authority_model": {
                    "registration_grants_authority": False,
                    "credentials_created": False,
                    "dynamic_core_loading": False,
                    "host_fallback": False,
                    "git_authority": "none",
                    "execution_model": "external_process",
                },
            }
            data["extensions"].append(record)
            self._save(data)
            return deepcopy(record)

    def revoke(self, extension_id, *, revoked_by, reason):
        revoked_by = _text(revoked_by, "revoked_by", 128)
        reason = _text(reason, "revocation_reason", 2_000)
        with self.lock:
            data = self._load()
            record = next((item for item in data["extensions"] if item["extension_id"] == extension_id), None)
            if not record:
                raise KeyError("Platform extension not found.")
            if record["state"] == "revoked":
                raise ValueError("Platform extension is already revoked.")
            timestamp = _now()
            record["state"] = "revoked"
            record["revoked_at"] = timestamp
            record["revoked_by"] = revoked_by
            record["revocation_reason"] = reason
            record["updated_at"] = timestamp
            self._save(data)
            return deepcopy(record)
