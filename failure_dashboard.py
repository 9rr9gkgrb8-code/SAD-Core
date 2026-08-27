"""Normalized failure inbox and approval-gated owner/developer workflow."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
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

    def __init__(self):
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

    def push_to_development(self, failure_id, actor_role, explicitly_approved=False):
        if actor_role != "owner" or not explicitly_approved:
            raise PermissionError("Only an owner may explicitly push a failure to development.")
        failure = self.failures[failure_id]
        existing = next((item for item in self.dev_items.values() if item.failure_id == failure_id), None)
        if existing:
            return existing
        item = DevWorkItem(str(uuid.uuid4()), failure_id)
        self.dev_items[item.work_item_id] = item
        failure.state = FailureState.PUSHED_TO_DEVELOPMENT.value
        return item

    def approve_isolated_work(self, work_item_id, actor_role):
        if actor_role != "owner":
            raise PermissionError("Owner approval is required for isolated work.")
        item = self.dev_items[work_item_id]
        item.state = DevState.APPROVED_FOR_ISOLATED_WORK.value
        return item

    def snapshot(self):
        return {"failures": [asdict(item) for item in self.failures.values()], "development": [asdict(item) for item in self.dev_items.values()]}
