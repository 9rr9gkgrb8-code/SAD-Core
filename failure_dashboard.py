"""Durable normalized Failure Inbox and shared Owner/Dev dashboard workflow."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import uuid
import threading
from functools import wraps

from live_apply import apply_approved_proposal, rollback_applied_proposal
from runtime_document import RuntimeJSONDocument
from sad_forge_contract import Artifact, ForgeResult, RepairRequest
from sandbox import approve_sandbox_proposal


DASHBOARD_STATE_FILE = Path(__file__).with_name("dashboard_state.json")
DASHBOARD_NAMESPACE = "dashboard_state"
MAX_DASHBOARD_BYTES = 12_000_000


def synchronized(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self.lock:
            return method(self, *args, **kwargs)
    return wrapper


class FailureState(str, Enum):
    NEW = "new"
    IN_REVIEW = "in_review"
    DISMISSED = "dismissed"
    PUSHED_TO_DEVELOPMENT = "pushed_to_development"
    CLOSED = "closed"


class DevState(str, Enum):
    TRIAGED = "triaged"
    APPROVED_FOR_ISOLATED_WORK = "approved_for_isolated_work"
    IN_FORGE = "in_forge"
    VERIFYING = "verifying"
    AWAITING_HUMAN_DECISION = "awaiting_human_decision"
    APPROVED = "approved"
    REJECTED = "rejected"
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
        if self.source not in {"sad", "forge", "test", "user"} or not self.evidence:
            raise ValueError("Failure source and evidence are required.")
        if not isinstance(self.category, str) or not 1 <= len(self.category) <= 100:
            raise ValueError("Failure category must be 1-100 characters.")
        if not isinstance(self.summary, str) or not 1 <= len(self.summary) <= 10_000:
            raise ValueError("Failure summary must be 1-10,000 characters.")
        if not isinstance(self.suggested_correction, str) or len(self.suggested_correction) > 10_000:
            raise ValueError("Suggested correction is too large.")
        if len(self.evidence) > 100 or len(json.dumps(self.evidence)) > 1_000_000:
            raise ValueError("Failure evidence exceeds the safe limit.")
        if not self.signature:
            normalized = " ".join(self.summary.lower().split())
            self.signature = hashlib.sha256(f"{self.category}\0{normalized}".encode()).hexdigest()


@dataclass
class DevWorkItem:
    work_item_id: str
    failure_id: str
    state: str = DevState.TRIAGED.value
    request: dict | None = None
    result: dict | None = None
    artifacts: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    human_decision: str | None = None
    assigned_to: str | None = None


def _validate_dashboard_data(data):
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported dashboard state schema.")
    if not isinstance(data.get("failures"), list) or not isinstance(data.get("development"), list):
        raise ValueError("Invalid dashboard state.")
    if len(data["failures"]) > 20_000 or len(data["development"]) > 20_000:
        raise ValueError("Dashboard state is unexpectedly large.")
    return data


def _is_live_dashboard_path(path):
    try:
        return Path(path).resolve() == DASHBOARD_STATE_FILE.resolve()
    except OSError:
        return Path(path) == DASHBOARD_STATE_FILE


class FailureDashboard:
    """One durable workflow; authentication determines available actions."""

    def __init__(self, auth_service=None, state_file=None, database=None):
        self.auth_service = auth_service
        self.persistence = None
        if state_file is None:
            self.state_file = None
        elif _is_live_dashboard_path(state_file):
            self.persistence = RuntimeJSONDocument(
                "dashboard_state.json",
                DASHBOARD_NAMESPACE,
                {"schema_version": 1, "event_sequence": 0, "failures": [], "development": []},
                _validate_dashboard_data,
                MAX_DASHBOARD_BYTES,
                database=database,
            )
            self.state_file = self.persistence.path
        else:
            self.state_file = Path(state_file)
        self.failures = {}
        self.by_signature = {}
        self.dev_items = {}
        self.event_sequence = 0
        self.lock = threading.RLock()
        self._load()

    def _load(self):
        if self.persistence is not None:
            data = self.persistence.load()
        elif self.state_file and self.state_file.exists():
            if self.state_file.is_symlink() or not self.state_file.is_file():
                raise ValueError("Dashboard state path must be a regular file.")
            if self.state_file.stat().st_size > MAX_DASHBOARD_BYTES:
                raise ValueError("Dashboard state is unexpectedly large.")
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
        else:
            return
        _validate_dashboard_data(data)
        self.event_sequence = data.get("event_sequence", 0)
        for raw in data.get("failures", []):
            event = FailureEvent(**raw)
            self.failures[event.failure_id] = event
            self.by_signature[event.signature] = event.failure_id
        for raw in data.get("development", []):
            item = DevWorkItem(**raw)
            self.dev_items[item.work_item_id] = item

    def _save(self):
        if not self.state_file:
            return
        data = {
            "schema_version": 1, "event_sequence": self.event_sequence,
            "failures": [asdict(item) for item in self.failures.values()],
            "development": [asdict(item) for item in self.dev_items.values()],
        }
        _validate_dashboard_data(data)
        if self.persistence is not None:
            self.persistence.save(data)
            return
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        os.replace(temporary, self.state_file)

    def _evidence(self, event, actor, details=None):
        self.event_sequence += 1
        return {
            "sequence": self.event_sequence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event, "actor": actor, "details": details or {},
        }

    def _require(self, token, permission):
        if self.auth_service is None:
            raise PermissionError("Dashboard access requires authentication.")
        return self.auth_service.require(token, permission)

    @synchronized
    def ingest(self, event):
        existing_id = self.by_signature.get(event.signature)
        if existing_id:
            existing = self.failures[existing_id]
            existing.evidence.extend(event.evidence)
            existing.evidence.append(self._evidence("failure_deduplicated", event.source))
            self._save()
            return existing
        event.evidence.append(self._evidence("failure_ingested", event.source))
        self.failures[event.failure_id] = event
        self.by_signature[event.signature] = event.failure_id
        self._save()
        return event

    @synchronized
    def mark_in_review(self, failure_id, token):
        actor = self._require(token, "development:review")
        failure = self.failures[failure_id]
        if failure.state != FailureState.NEW.value:
            raise ValueError("Only new failures may enter review.")
        failure.state = FailureState.IN_REVIEW.value
        failure.evidence.append(self._evidence("failure_reviewed", actor["account_id"]))
        self._save()
        return failure

    @synchronized
    def push_to_development(self, failure_id, actor_token, explicitly_approved=False):
        actor = self._require(actor_token, "development:govern")
        if not explicitly_approved:
            raise PermissionError("Explicit owner approval is required.")
        failure = self.failures[failure_id]
        existing = next((item for item in self.dev_items.values() if item.failure_id == failure_id), None)
        if existing:
            return existing
        item = DevWorkItem(str(uuid.uuid4()), failure_id)
        item.evidence.append(self._evidence("pushed_to_development", actor["account_id"]))
        self.dev_items[item.work_item_id] = item
        failure.state = FailureState.PUSHED_TO_DEVELOPMENT.value
        self._save()
        return item

    @synchronized
    def approve_isolated_work(self, work_item_id, actor_token, source_snapshot="unknown"):
        actor = self._require(actor_token, "development:govern")
        item = self.dev_items[work_item_id]
        if item.state != DevState.TRIAGED.value:
            raise ValueError("Only triaged work may be approved for isolation.")
        failure = self.failures[item.failure_id]
        request = RepairRequest(
            failure_id=failure.failure_id,
            objective=failure.suggested_correction or failure.summary,
            source_snapshot=source_snapshot,
            sandbox_scope="isolated_container",
            allowed_targets=tuple(failure.affected_files or ["app.py"]),
            test_plan=("python -m unittest -v",),
            approval_state="approved_for_isolated_work",
        )
        item.request = request.to_dict()
        item.state = DevState.APPROVED_FOR_ISOLATED_WORK.value
        item.evidence.append(self._evidence("isolated_work_approved", actor["account_id"], {"request_id": request.request_id}))
        self._save()
        return item

    @synchronized
    def start_forge(self, work_item_id, token):
        actor = self._require(token, "development:work")
        item = self.dev_items[work_item_id]
        if item.state != DevState.APPROVED_FOR_ISOLATED_WORK.value:
            raise ValueError("Work is not approved for Forge.")
        item.state = DevState.IN_FORGE.value
        item.assigned_to = actor["account_id"]
        item.evidence.append(self._evidence("forge_started", actor["account_id"]))
        self._save()
        return item

    @synchronized
    def record_forge_result(self, work_item_id, result, token):
        actor = self._require(token, "development:work")
        item = self.dev_items[work_item_id]
        if not item.request or result.request_id != item.request["request_id"] or result.correlation_id != item.request["correlation_id"]:
            raise ValueError("Forge result does not correlate to this work item.")
        item.result = result.to_dict()
        item.artifacts = [artifact.to_dict() for artifact in result.artifacts]
        item.state = DevState.AWAITING_HUMAN_DECISION.value if result.state in {"succeeded", "failed"} else DevState.VERIFYING.value
        item.evidence.append(self._evidence("forge_result_recorded", actor["account_id"], {"state": result.state}))
        self._save()
        return item

    def _proposal_id_for(self, item):
        receipt = next((artifact for artifact in item.artifacts if artifact.get("kind") == "execution_receipt"), None)
        proposal_id = ((receipt or {}).get("content") or {}).get("proposal_id")
        if not proposal_id:
            raise ValueError("Forge did not return an applyable proposal receipt.")
        return proposal_id

    @synchronized
    def decide(self, work_item_id, decision, token):
        permission = "development:decide" if decision in {"approve", "reject"} else "development:govern"
        actor = self._require(token, permission)
        item = self.dev_items[work_item_id]
        if item.state != DevState.AWAITING_HUMAN_DECISION.value:
            raise ValueError("Work is not awaiting a human decision.")
        if decision not in {"approve", "reject"}:
            raise ValueError("Decision must be approve or reject.")

        live_receipt = None
        proposal_id = None
        evidence_length = len(item.evidence)
        old_sequence = self.event_sequence
        if decision == "approve" and actor.get("role") == "owner":
            if not item.result or item.result.get("state") != "succeeded":
                raise ValueError("Owner approval cannot apply a repair that failed Forge verification.")
            proposal_id = self._proposal_id_for(item)
            approved = approve_sandbox_proposal(proposal_id)
            if not approved:
                raise ValueError("The tested Forge proposal is not eligible for human approval.")
            live_receipt = apply_approved_proposal(proposal_id)

        item.human_decision = decision
        item.state = DevState.APPROVED.value if decision == "approve" else DevState.REJECTED.value
        item.evidence.append(self._evidence(f"human_{decision}", actor["account_id"]))
        if live_receipt:
            item.evidence.append(self._evidence("live_patch_applied", actor["account_id"], live_receipt))
        try:
            self._save()
        except Exception:
            item.human_decision = None
            item.state = DevState.AWAITING_HUMAN_DECISION.value
            del item.evidence[evidence_length:]
            self.event_sequence = old_sequence
            if live_receipt and proposal_id:
                rollback_applied_proposal(proposal_id)
            raise
        return item

    @synchronized
    def close(self, work_item_id, token):
        actor = self._require(token, "development:govern")
        item = self.dev_items[work_item_id]
        if item.state not in {DevState.APPROVED.value, DevState.REJECTED.value}:
            raise ValueError("Only decided work may close.")
        item.state = DevState.CLOSED.value
        self.failures[item.failure_id].state = FailureState.CLOSED.value
        item.evidence.append(self._evidence("work_closed", actor["account_id"]))
        self._save()
        return item

    @synchronized
    def snapshot(self, actor_token):
        self._require(actor_token, "development:view")
        return {
            "failures": [asdict(item) for item in self.failures.values()],
            "development": [asdict(item) for item in self.dev_items.values()],
        }
