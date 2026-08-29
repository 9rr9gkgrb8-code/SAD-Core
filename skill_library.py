"""Evidence-bound reusable skills for SAD controlled learning.

A successful repair and a reusable skill are separate state transitions. This store
persists the provenance needed to review, promote, supersede, or revoke a skill without
ever granting the skill execution authority by itself.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import re
import threading
import uuid

from runtime_document import RuntimeJSONDocument


SKILLS_NAMESPACE = "skills"
SKILLS_FILENAME = "skills.json"
MAX_SKILLS_FILE_BYTES = 3_000_000
MAX_SKILLS = 1_000
MAX_EVIDENCE_REFS = 64
SKILL_STATES = frozenset({"candidate", "validated", "promoted", "revoked", "superseded"})
HEX64 = re.compile(r"^[0-9a-f]{64}$")


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


def _ids(value, name, *, maximum=MAX_EVIDENCE_REFS):
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > maximum:
        raise ValueError(f"{name} must be a list of at most {maximum} entries.")
    normalized = []
    for item in value:
        normalized.append(_text(item, name, 160))
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{name} contains duplicate entries.")
    return normalized


def _optional_hash(value, name):
    if value is None or value == "":
        return None
    normalized = _text(value, name, 64).lower()
    if not HEX64.fullmatch(normalized):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest.")
    return normalized


def _validate_skill_record(record):
    if not isinstance(record, dict):
        raise ValueError("Skill record must be an object.")
    required = {
        "skill_id", "version", "title", "summary", "task_signature",
        "configuration_fingerprint", "producer_identity", "source_failure_ids",
        "source_work_item_ids", "repair_summary", "execution_evidence_refs",
        "verification_evidence_refs", "state", "proposed_by", "created_at", "updated_at",
    }
    if not required.issubset(record):
        raise ValueError("Skill record is missing required fields.")
    _text(record["skill_id"], "skill_id", 128)
    if not isinstance(record["version"], int) or record["version"] < 1:
        raise ValueError("Skill version must be a positive integer.")
    _text(record["title"], "title", 120)
    _text(record["summary"], "summary", 2_000)
    _text(record["task_signature"], "task_signature", 1_000)
    _text(record["configuration_fingerprint"], "configuration_fingerprint", 256)
    _text(record["producer_identity"], "producer_identity", 128)
    _ids(record["source_failure_ids"], "source_failure_ids")
    _ids(record["source_work_item_ids"], "source_work_item_ids")
    _text(record["repair_summary"], "repair_summary", 4_000)
    execution_refs = _ids(record["execution_evidence_refs"], "execution_evidence_refs")
    verification_refs = _ids(record["verification_evidence_refs"], "verification_evidence_refs")
    if not execution_refs:
        raise ValueError("A skill must retain execution evidence references.")
    if not record["source_failure_ids"] and not record["source_work_item_ids"]:
        raise ValueError("A skill must retain at least one source failure or work item reference.")
    if record["state"] not in SKILL_STATES:
        raise ValueError("Unsupported skill state.")
    _text(record["proposed_by"], "proposed_by", 128)
    _text(record["created_at"], "created_at", 80)
    _text(record["updated_at"], "updated_at", 80)
    _optional_hash(record.get("diff_hash"), "diff_hash")
    if record.get("source_snapshot") is not None:
        _text(record["source_snapshot"], "source_snapshot", 256)
    if record.get("supersedes") is not None:
        _text(record["supersedes"], "supersedes", 128)
        if record["supersedes"] == record["skill_id"]:
            raise ValueError("A skill cannot supersede itself.")
    if record.get("superseded_by") is not None:
        _text(record["superseded_by"], "superseded_by", 128)
        if record["superseded_by"] == record["skill_id"]:
            raise ValueError("A skill cannot be superseded by itself.")
    for key in (
        "reviewed_by", "approved_by", "revoked_by", "verifier_identity",
        "verification_summary", "revocation_reason",
    ):
        if record.get(key) is not None:
            _text(record[key], key, 2_000 if key in {"verification_summary", "revocation_reason"} else 128)
    for key in ("validated_at", "promoted_at", "revoked_at", "superseded_at"):
        if record.get(key) is not None:
            _text(record[key], key, 80)
    if record["state"] in {"validated", "promoted", "superseded"} and not verification_refs:
        raise ValueError("Validated skills must retain independent verification evidence references.")
    if record["state"] in {"validated", "promoted", "superseded"} and not record.get("verifier_identity"):
        raise ValueError("Validated skills must identify the verifier.")
    if record.get("verifier_identity") == record.get("producer_identity"):
        raise ValueError("Skill producer and verifier must be independent identities.")
    if record["state"] in {"promoted", "superseded"} and not record.get("approved_by"):
        raise ValueError("Promoted skills must retain the human approver identity.")
    if record["state"] == "revoked":
        if not record.get("revocation_reason"):
            raise ValueError("Revoked skills must retain a reason.")
        if not record.get("revoked_by"):
            raise ValueError("Revoked skills must retain the revoking actor identity.")


def _validate_skill_data(data):
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("skills"), list):
        raise ValueError("Unsupported or invalid skill library.")
    if len(data["skills"]) > MAX_SKILLS:
        raise ValueError("Skill library exceeds the installation limit.")
    seen = set()
    for record in data["skills"]:
        _validate_skill_record(record)
        if record["skill_id"] in seen:
            raise ValueError("Skill IDs must be unique.")
        seen.add(record["skill_id"])
    for record in data["skills"]:
        for relation in ("supersedes", "superseded_by"):
            target = record.get(relation)
            if target is not None and target not in seen:
                raise ValueError("Skill lineage references an unknown skill.")
    return data


class SkillLibrary:
    """Durable governed skill lifecycle with explicit human promotion."""

    def __init__(self, path=None, database=None):
        self.lock = threading.RLock()
        self.persistence = RuntimeJSONDocument(
            SKILLS_FILENAME,
            SKILLS_NAMESPACE,
            {"schema_version": 1, "skills": []},
            _validate_skill_data,
            MAX_SKILLS_FILE_BYTES,
            path=path,
            database=database,
        )
        self.path = self.persistence.path

    def _load(self):
        return self.persistence.load()

    def _save(self, data):
        self.persistence.save(data)

    @staticmethod
    def _public(record):
        return deepcopy(record)

    def list(self, states=None):
        selected = None
        if states is not None:
            if not isinstance(states, (list, tuple, set)):
                raise ValueError("states must be a collection.")
            selected = set(states)
            if not selected.issubset(SKILL_STATES):
                raise ValueError("Unsupported skill state filter.")
        records = self._load()["skills"]
        return [self._public(item) for item in records if selected is None or item["state"] in selected]

    def get(self, skill_id):
        record = next((item for item in self._load()["skills"] if item["skill_id"] == skill_id), None)
        if not record:
            raise KeyError("Skill not found.")
        return self._public(record)

    def propose(
        self, *, title, summary, task_signature, configuration_fingerprint,
        producer_identity, source_failure_ids=None, source_work_item_ids=None,
        repair_summary, execution_evidence_refs, proposed_by, diff_hash=None,
        source_snapshot=None, supersedes=None,
    ):
        title = _text(title, "title", 120)
        summary = _text(summary, "summary", 2_000)
        task_signature = _text(task_signature, "task_signature", 1_000)
        configuration_fingerprint = _text(configuration_fingerprint, "configuration_fingerprint", 256)
        producer_identity = _text(producer_identity, "producer_identity", 128)
        source_failure_ids = _ids(source_failure_ids, "source_failure_ids")
        source_work_item_ids = _ids(source_work_item_ids, "source_work_item_ids")
        repair_summary = _text(repair_summary, "repair_summary", 4_000)
        execution_evidence_refs = _ids(execution_evidence_refs, "execution_evidence_refs")
        proposed_by = _text(proposed_by, "proposed_by", 128)
        diff_hash = _optional_hash(diff_hash, "diff_hash")
        source_snapshot = None if source_snapshot is None else _text(source_snapshot, "source_snapshot", 256)
        if not source_failure_ids and not source_work_item_ids:
            raise ValueError("A skill candidate requires source failure or work item provenance.")
        if not execution_evidence_refs:
            raise ValueError("A skill candidate requires execution evidence references.")

        with self.lock:
            data = self._load()
            if len(data["skills"]) >= MAX_SKILLS:
                raise ValueError("Skill library limit reached.")
            version = 1
            if supersedes is not None:
                supersedes = _text(supersedes, "supersedes", 128)
                previous = next((item for item in data["skills"] if item["skill_id"] == supersedes), None)
                if not previous:
                    raise KeyError("Superseded skill not found.")
                if previous["state"] != "promoted":
                    raise ValueError("Only a promoted skill can be superseded.")
                version = previous["version"] + 1
            timestamp = _now()
            record = {
                "skill_id": str(uuid.uuid4()),
                "version": version,
                "title": title,
                "summary": summary,
                "task_signature": task_signature,
                "configuration_fingerprint": configuration_fingerprint,
                "producer_identity": producer_identity,
                "source_failure_ids": source_failure_ids,
                "source_work_item_ids": source_work_item_ids,
                "repair_summary": repair_summary,
                "execution_evidence_refs": execution_evidence_refs,
                "verification_evidence_refs": [],
                "verification_summary": None,
                "verifier_identity": None,
                "diff_hash": diff_hash,
                "source_snapshot": source_snapshot,
                "state": "candidate",
                "proposed_by": proposed_by,
                "reviewed_by": None,
                "approved_by": None,
                "revoked_by": None,
                "created_at": timestamp,
                "updated_at": timestamp,
                "validated_at": None,
                "promoted_at": None,
                "revoked_at": None,
                "superseded_at": None,
                "supersedes": supersedes,
                "superseded_by": None,
                "revocation_reason": None,
            }
            data["skills"].append(record)
            self._save(data)
            return self._public(record)

    def validate(
        self, skill_id, *, reviewed_by, verifier_identity,
        verification_evidence_refs, verification_summary, verification_passed,
    ):
        if verification_passed is not True:
            raise ValueError("Skill validation requires an explicit passing verification result.")
        reviewed_by = _text(reviewed_by, "reviewed_by", 128)
        verifier_identity = _text(verifier_identity, "verifier_identity", 128)
        verification_evidence_refs = _ids(verification_evidence_refs, "verification_evidence_refs")
        verification_summary = _text(verification_summary, "verification_summary", 2_000)
        if not verification_evidence_refs:
            raise ValueError("Independent verification evidence is required.")

        with self.lock:
            data = self._load()
            record = next((item for item in data["skills"] if item["skill_id"] == skill_id), None)
            if not record:
                raise KeyError("Skill not found.")
            if record["state"] != "candidate":
                raise ValueError("Only a candidate skill can be validated.")
            if verifier_identity == record["producer_identity"]:
                raise ValueError("Skill producer cannot also be the independent verifier.")
            timestamp = _now()
            record["verification_evidence_refs"] = verification_evidence_refs
            record["verification_summary"] = verification_summary
            record["verifier_identity"] = verifier_identity
            record["reviewed_by"] = reviewed_by
            record["state"] = "validated"
            record["validated_at"] = timestamp
            record["updated_at"] = timestamp
            self._save(data)
            return self._public(record)

    def promote(self, skill_id, *, approved_by, approved):
        if approved is not True:
            raise PermissionError("Skill promotion requires explicit human approval.")
        approved_by = _text(approved_by, "approved_by", 128)
        with self.lock:
            data = self._load()
            record = next((item for item in data["skills"] if item["skill_id"] == skill_id), None)
            if not record:
                raise KeyError("Skill not found.")
            if record["state"] != "validated":
                raise ValueError("Only a validated skill can be promoted.")
            timestamp = _now()
            if record.get("supersedes"):
                previous = next((item for item in data["skills"] if item["skill_id"] == record["supersedes"]), None)
                if not previous or previous["state"] != "promoted":
                    raise ValueError("Superseded skill is no longer in a promotable lineage state.")
                previous["state"] = "superseded"
                previous["superseded_by"] = record["skill_id"]
                previous["superseded_at"] = timestamp
                previous["updated_at"] = timestamp
            record["state"] = "promoted"
            record["approved_by"] = approved_by
            record["promoted_at"] = timestamp
            record["updated_at"] = timestamp
            self._save(data)
            return self._public(record)

    def revoke(self, skill_id, *, revoked_by, reason):
        revoked_by = _text(revoked_by, "revoked_by", 128)
        reason = _text(reason, "revocation_reason", 2_000)
        with self.lock:
            data = self._load()
            record = next((item for item in data["skills"] if item["skill_id"] == skill_id), None)
            if not record:
                raise KeyError("Skill not found.")
            if record["state"] not in {"validated", "promoted"}:
                raise ValueError("Only validated or promoted skills can be revoked.")
            timestamp = _now()
            record["state"] = "revoked"
            record["revoked_at"] = timestamp
            record["revoked_by"] = revoked_by
            record["revocation_reason"] = reason
            record["updated_at"] = timestamp
            self._save(data)
            return self._public(record)
