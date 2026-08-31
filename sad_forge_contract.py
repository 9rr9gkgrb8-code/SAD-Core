"""Versioned durable message contract between SAD governance and Forge execution."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import uuid
from pathlib import PurePosixPath, PureWindowsPath


SCHEMA_VERSION = "1.0"
JOB_STATES = {
    "submitted", "approved_for_isolated_work", "running", "verifying",
    "awaiting_human_decision", "succeeded", "failed", "cancelled",
}
TERMINAL_JOB_STATES = {"succeeded", "failed", "cancelled"}
ARTIFACT_KINDS = {"diff", "tests", "diagnostics", "execution_receipt"}


def _uuid(value, field_name):
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError(f"{field_name} must be a UUID.") from error


def _timestamp():
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Artifact:
    kind: str
    content: dict | list | str
    artifact_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_timestamp)
    sha256: str = ""

    def __post_init__(self):
        _uuid(self.artifact_id, "artifact_id")
        if self.kind not in ARTIFACT_KINDS:
            raise ValueError("Unsupported artifact kind.")
        encoded = json.dumps(self.content, sort_keys=True, separators=(",", ":")).encode()
        if len(encoded) > 2_000_000:
            raise ValueError("Artifact exceeds the durable size limit.")
        digest = hashlib.sha256(encoded).hexdigest()
        if self.sha256 and self.sha256 != digest:
            raise ValueError("Artifact digest does not match its content.")
        object.__setattr__(self, "sha256", digest)

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class RepairRequest:
    failure_id: str
    objective: str
    source_snapshot: str
    sandbox_scope: str
    allowed_targets: tuple[str, ...]
    test_plan: tuple[str, ...]
    approval_state: str
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: str = SCHEMA_VERSION
    created_at: str = field(default_factory=_timestamp)

    def __post_init__(self):
        _uuid(self.request_id, "request_id")
        _uuid(self.correlation_id, "correlation_id")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("Unsupported RepairRequest schema version.")
        if self.approval_state != "approved_for_isolated_work":
            raise ValueError("Forge requests require prior human approval for isolated work.")
        if not self.objective.strip() or not self.source_snapshot.strip():
            raise ValueError("Objective and source snapshot are required.")
        if not self.allowed_targets or any(not _repository_relative_target(target) for target in self.allowed_targets):
            raise ValueError("Allowed targets must be repository-relative paths.")
        if not self.test_plan:
            raise ValueError("A deterministic test plan is required.")

    def to_dict(self):
        data = asdict(self)
        data["allowed_targets"] = list(self.allowed_targets)
        data["test_plan"] = list(self.test_plan)
        return data


def _repository_relative_target(target):
    if not isinstance(target, str) or not target or target != target.strip() or "\0" in target:
        return False
    if "\\" in target:
        return False
    posix = PurePosixPath(target)
    windows = PureWindowsPath(target)
    return (
        not posix.is_absolute()
        and not windows.is_absolute()
        and not windows.drive
        and all(part not in {"", ".", ".."} for part in posix.parts)
        and posix.as_posix() == target
    )


@dataclass(frozen=True)
class ForgeResult:
    job_id: str
    request_id: str
    correlation_id: str
    state: str
    artifacts: tuple[Artifact, ...] = ()
    diagnostics: tuple[str, ...] = ()
    tests: tuple[dict, ...] = ()
    error: str | None = None
    schema_version: str = SCHEMA_VERSION
    updated_at: str = field(default_factory=_timestamp)

    def __post_init__(self):
        _uuid(self.job_id, "job_id")
        _uuid(self.request_id, "request_id")
        _uuid(self.correlation_id, "correlation_id")
        if self.schema_version != SCHEMA_VERSION or self.state not in JOB_STATES:
            raise ValueError("Unsupported ForgeResult schema or state.")
        if self.state == "failed" and not self.error:
            raise ValueError("Failed Forge results require an error.")
        if len(self.artifacts) > 100 or len(self.diagnostics) > 100 or len(self.tests) > 1000:
            raise ValueError("Forge result exceeds durable collection limits.")

    def to_dict(self):
        data = asdict(self)
        data["artifacts"] = [artifact.to_dict() for artifact in self.artifacts]
        data["diagnostics"] = list(self.diagnostics)
        data["tests"] = list(self.tests)
        return data
