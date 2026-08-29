"""Platform 0.4 additive API layer.

This wrapper leaves the proven Alpha Stable API surface intact and adds only the
new governance-sensitive extension and skill lifecycle routes. Unknown routes fall
through to SadApiService unchanged.
"""

from __future__ import annotations

import re

from api import SadApiService
from platform_extensions import PlatformExtensionStore
from skill_library import SkillLibrary


class SadPlatform04Service(SadApiService):
    """SAD Platform 0.4 service with governed extension and skill contracts."""

    def __init__(self, *args, platform_extensions=None, skills=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.platform_extensions = platform_extensions or PlatformExtensionStore()
        self.skills = skills or SkillLibrary()

    def dispatch(self, method, path, headers, body):
        if path.startswith("/v1/platform/extensions"):
            token = self.token(headers)
            account = self.auth.require(token, "platform:manage")
            account_id = account["account_id"]

            if method == "GET" and path == "/v1/platform/extensions":
                return 200, {"extensions": self.platform_extensions.list()}

            if method == "POST" and path == "/v1/platform/extensions":
                record = self.platform_extensions.register(
                    body, self.platform, registered_by=account_id
                )
                self._publish(
                    "platform.extension.registered",
                    subject_id=record["extension_id"],
                    details={
                        "publisher": record["manifest"]["publisher"],
                        "version": record["manifest"]["version"],
                        "compatible": record["compatibility"]["compatible"],
                    },
                )
                return 201, record

            match = re.fullmatch(r"/v1/platform/extensions/([0-9a-f-]+)/revoke", path)
            if method == "POST" and match:
                record = self.platform_extensions.revoke(
                    match.group(1), revoked_by=account_id, reason=body.get("reason", "")
                )
                self._publish(
                    "platform.extension.revoked",
                    subject_id=record["extension_id"],
                    details={"state": record["state"]},
                )
                return 200, record

            raise KeyError("Endpoint not found.")

        if path == "/v1/skills" or path.startswith("/v1/skills/"):
            token = self.token(headers)
            account = self.auth.require(token)
            account_id = account["account_id"]

            if method == "GET" and path == "/v1/skills":
                self.auth.require(token, "development:view")
                return 200, {"skills": self.skills.list()}

            if method == "POST" and path == "/v1/skills":
                self.auth.require(token, "development:work")
                record = self.skills.propose(
                    title=body.get("title", ""),
                    summary=body.get("summary", ""),
                    task_signature=body.get("task_signature", ""),
                    configuration_fingerprint=body.get("configuration_fingerprint", ""),
                    producer_identity=body.get("producer_identity", ""),
                    source_failure_ids=body.get("source_failure_ids", []),
                    source_work_item_ids=body.get("source_work_item_ids", []),
                    repair_summary=body.get("repair_summary", ""),
                    execution_evidence_refs=body.get("execution_evidence_refs", []),
                    proposed_by=account_id,
                    diff_hash=body.get("diff_hash"),
                    source_snapshot=body.get("source_snapshot"),
                    supersedes=body.get("supersedes"),
                )
                self._publish(
                    "skill.candidate.created",
                    subject_id=record["skill_id"],
                    details={"state": record["state"], "version": record["version"]},
                )
                return 201, record

            match = re.fullmatch(r"/v1/skills/([0-9a-f-]+)/(validate|promote|revoke)", path)
            if method == "POST" and match:
                skill_id, action = match.groups()
                if action == "validate":
                    self.auth.require(token, "development:review")
                    record = self.skills.validate(
                        skill_id,
                        reviewed_by=account_id,
                        verifier_identity=body.get("verifier_identity", ""),
                        verification_evidence_refs=body.get("verification_evidence_refs", []),
                        verification_summary=body.get("verification_summary", ""),
                        verification_passed=body.get("verification_passed") is True,
                    )
                    event_type = "skill.validated"
                elif action == "promote":
                    self.auth.require(token, "development:govern")
                    record = self.skills.promote(
                        skill_id,
                        approved_by=account_id,
                        approved=body.get("approved") is True,
                    )
                    event_type = "skill.promoted"
                else:
                    self.auth.require(token, "development:govern")
                    record = self.skills.revoke(
                        skill_id,
                        revoked_by=account_id,
                        reason=body.get("reason", ""),
                    )
                    event_type = "skill.revoked"

                self._publish(
                    event_type,
                    subject_id=record["skill_id"],
                    details={"state": record["state"], "version": record["version"]},
                )
                return 200, record

            raise KeyError("Endpoint not found.")

        return super().dispatch(method, path, headers, body)
