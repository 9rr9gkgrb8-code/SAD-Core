"""Normalized failure inbox and approval-gated owner/developer workflow."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import uuid


class FailureState(str, Enum):
    NEW = "new"
    IN_REVIEW = "in_review"
    DISMISSED = "dismissed"
    PUSHED_TO_DEVELOPMENT = "pushed_to_development"


class DevState(str, Enum):
    TRIAGED = "triaged"
    APPROVED_FOR_ISOLATED_WORK = "approved_for_isolated_work"
    IN_FORGE = "in_forge"
    VERIFYING = "verifying"
    AWAITING_HUMAN_DECISION = "awaiting_human_decision"
    APPROVED = "approved"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"
    CLOSED = "closed"


@dataclass
class FailureEvent:
    source: str
    category: str
    summary: str
    evidence: list[dict]
    suggested_correction: str
    affected_files: list[str] = field(default_factory=list)
    failure_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: str = FailureState.NEW.value
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    signature: str = ""

    def __post_init__(self):
        if self.source not in {"sad", "forge", "test", "user"}:
            raise ValueError("Failure source must be sad, forge, test, or user.")
        if not self.evidence:
            raise ValueError("Normalized failures require evidence.")
        if not isinstance(self.category, str) or not 1 <= len(self.category) <= 100:
            raise ValueError("Failure category must be 1-100 characters.")
        if not isinstance(self.summary, str) or not 1 <= len(self.summary) <= 10_000:
            raise ValueError("Failure summary must be 1-10,000 characters.")
        if not isinstance(self.suggested_correction, str) or len(self.suggested_correction) > 10_000:
            raise ValueError("Suggested correction is too large.")
        if len(self.evidence) > 100 or len(json.dumps(self.evidence)) > 1_000_000:
            raise ValueError("Failure evidence exceeds the safe limit.")
        if len(self.affected_files) > 100 or any(not isinstance(path, str) or len(path) > 500 for path in self.affected_files):
            raise ValueError("Affected file metadata exceeds the safe limit.")
        if not self.signature:
            raw = f"{self.category}\0{self.summary.strip().lower()}"
            self.signature = hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class DevWorkItem:
    work_item_id: str
    failure_id: str
    state: str = DevState.TRIAGED.value
    artifacts: list[dict] = field(default_factory=list)
    human_decision: str | None = None


class FailureDashboard:
    """One dashboard; role permissions determine available authority."""

    def __init__(self, auth_service=None):
        self.auth_service = auth_service
        self.failures = {}
        self.by_signature = {}
        self.dev_items = {}

    def ingest(self, event):
        existing_id = self.by_signature.get(event.signature)
        if existing_id:
            existing = self.failures[existing_id]
            existing.evidence.extend(event.evidence)
            return existing
        self.failures[event.failure_id] = event
        self.by_signature[event.signature] = event.failure_id
        return event

    def _require_governance(self, actor_token):
        if self.auth_service is None:
            raise PermissionError("Dashboard governance requires an authentication service.")
        return self.auth_service.require(actor_token, "development:govern")

    def push_to_development(self, failure_id, actor_token, explicitly_approved=False):
        self._require_governance(actor_token)
        if not explicitly_approved:
            raise PermissionError("Only an owner may explicitly push a failure to development.")
        failure = self.failures[failure_id]
        existing = next((item for item in self.dev_items.values() if item.failure_id == failure_id), None)
        if existing:
            return existing
        item = DevWorkItem(str(uuid.uuid4()), failure_id)
        self.dev_items[item.work_item_id] = item
        failure.state = FailureState.PUSHED_TO_DEVELOPMENT.value
        return item

    def approve_isolated_work(self, work_item_id, actor_token):
        self._require_governance(actor_token)
        item = self.dev_items[work_item_id]
        item.state = DevState.APPROVED_FOR_ISOLATED_WORK.value
        return item

    def snapshot(self, actor_token):
        if self.auth_service is None:
            raise PermissionError("Dashboard reads require an authentication service.")
        self.auth_service.require(actor_token, "development:view")
        return {"failures": [asdict(item) for item in self.failures.values()], "development": [asdict(item) for item in self.dev_items.values()]}
