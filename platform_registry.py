"""Declarative capability registry for the SAD local AI platform.

Registry metadata is descriptive. It never executes extension code, grants runtime
authority, or replaces endpoint-level authentication and authorization.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


PLATFORM_VERSION = "0.4-alpha"
PLATFORM_SCHEMA_VERSION = 4
CAPABILITY_LIFECYCLES = {"alpha", "stable", "deprecated"}


def _version_tuple(value):
    if not isinstance(value, str):
        raise ValueError("Capability version must be text.")
    parts = value.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError("Capability version must use numeric major.minor.patch format.")
    return tuple(int(part) for part in parts)


@dataclass(frozen=True)
class PlatformRoute:
    method: str
    path: str

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class PlatformCapability:
    capability_id: str
    title: str
    description: str
    permission: str | None
    routes: tuple[PlatformRoute, ...]
    mutates_state: bool = False
    human_approval_boundary: bool = False
    capability_version: str = "1.0.0"
    lifecycle: str = "alpha"
    replacement: str | None = None

    def to_dict(self):
        return {
            "capability_id": self.capability_id,
            "title": self.title,
            "description": self.description,
            "permission": self.permission,
            "routes": [route.to_dict() for route in self.routes],
            "mutates_state": self.mutates_state,
            "human_approval_boundary": self.human_approval_boundary,
            "capability_version": self.capability_version,
            "lifecycle": self.lifecycle,
            "replacement": self.replacement,
        }


@dataclass(frozen=True)
class PlatformModule:
    module_id: str
    name: str
    description: str
    kind: str
    capabilities: tuple[PlatformCapability, ...]
    status: str = "available"
    module_version: str = "1.0.0"

    def to_dict(self, allowed_capabilities=None):
        allowed = set(allowed_capabilities) if allowed_capabilities is not None else None
        capabilities = [
            capability.to_dict() for capability in self.capabilities
            if allowed is None or capability.capability_id in allowed
        ]
        return {
            "module_id": self.module_id,
            "name": self.name,
            "description": self.description,
            "kind": self.kind,
            "status": self.status,
            "module_version": self.module_version,
            "capabilities": capabilities,
        }


def _route(method, path):
    return PlatformRoute(method, path)


def _cap(
    capability_id, title, description, permission, routes, *,
    mutates=False, approval=False, version="1.0.0", lifecycle="alpha", replacement=None,
):
    return PlatformCapability(
        capability_id, title, description, permission, tuple(routes), mutates, approval,
        version, lifecycle, replacement,
    )


BUILTIN_MODULES = (
    PlatformModule(
        "sad.platform", "SAD Platform Core",
        "Discovers capabilities, negotiates versions, manages local app trust, declarative external extension contracts, and metadata-only events.",
        "core",
        (
            _cap("platform:discover", "Discover platform", "Read the signed-in platform manifest.", None,
                 (_route("GET", "/v1/platform"),)),
            _cap("platform:catalog", "Browse capabilities", "Read capabilities available to the signed-in account.", None,
                 (_route("GET", "/v1/platform/capabilities"),)),
            _cap("platform:modules", "Browse modules", "Read modules visible to the signed-in account.", None,
                 (_route("GET", "/v1/platform/modules"),)),
            _cap("platform:compatibility", "Negotiate compatibility", "Check required capability versions before using a client.", None,
                 (_route("POST", "/v1/platform/compatibility"),)),
            _cap("platform:clients", "Manage local apps", "Create, rotate, list, and revoke scoped machine credentials.", "platform:manage",
                 (_route("GET", "/v1/platform/clients"), _route("POST", "/v1/platform/clients"),
                  _route("POST", "/v1/platform/clients/{client_id}/rotate"),
                  _route("POST", "/v1/platform/clients/{client_id}/revoke")), mutates=True, approval=True),
            _cap("platform:events", "Read platform events", "Read privacy-minimized platform event metadata.", "platform:manage",
                 (_route("POST", "/v1/platform/events/read"),)),
            _cap("platform:extensions", "Manage extension contracts",
                 "Register, inspect, and revoke declarative out-of-process extension manifests. Registration grants no execution authority or credentials.",
                 "platform:manage",
                 (_route("GET", "/v1/platform/extensions"), _route("POST", "/v1/platform/extensions"),
                  _route("POST", "/v1/platform/extensions/{extension_id}/revoke")),
                 mutates=True, approval=True),
        ),
        module_version="4.0.0",
    ),
    PlatformModule(
        "sad.chat", "SAD Chat",
        "General multi-turn local AI conversation with durable per-account history and optional explicit memory context.",
        "experience",
        (
            _cap("chat:conversation", "Conversation", "Create, continue, read, and archive personal SAD chats.", None,
                 (_route("GET", "/v1/chat/sessions"), _route("POST", "/v1/chat/sessions"),
                  _route("GET", "/v1/chat/sessions/{session_id}"),
                  _route("POST", "/v1/chat/sessions/{session_id}/messages"),
                  _route("POST", "/v1/chat/sessions/{session_id}/archive")), mutates=True),
        ),
    ),
    PlatformModule(
        "sad.voice", "Voice Client Bridge",
        "Signed-in transcript-to-SAD conversation contract for local speech input/output clients.",
        "gateway",
        (
            _cap("voice:conversation", "Voice conversation bridge", "Submit a speech transcript and receive SAD reply text for local synthesis.", None,
                 (_route("POST", "/v1/voice/turn"),), mutates=True),
        ),
    ),
    PlatformModule(
        "sad.memory", "Personal Memory",
        "Explicit user-controlled long-term memory with per-account isolation, enable/disable, search, expiry, edit, and delete.",
        "core",
        (
            _cap("memory:own", "Manage personal memory", "Create, search, edit, enable, expire, and delete only your own saved memories.", None,
                 (_route("GET", "/v1/memory"), _route("POST", "/v1/memory"),
                  _route("POST", "/v1/memory/search"), _route("POST", "/v1/memory/{memory_id}"),
                  _route("POST", "/v1/memory/{memory_id}/delete")), mutates=True, approval=True),
        ),
    ),
    PlatformModule(
        "sad.tools", "Governed Tool Actions",
        "Reviewed internal tools with account ownership and explicit approval before state-changing personal actions.",
        "core",
        (
            _cap("tools:catalog", "Browse tools", "Read the internal tool actions available to the signed-in account.", None,
                 (_route("GET", "/v1/tools"),)),
            _cap("tools:actions", "Run governed tools", "Create, inspect, approve/reject, and execute only registered internal tools.", None,
                 (_route("GET", "/v1/tools/actions"), _route("POST", "/v1/tools/actions"),
                  _route("GET", "/v1/tools/actions/{action_id}"),
                  _route("POST", "/v1/tools/actions/{action_id}/decision"),
                  _route("POST", "/v1/tools/actions/{action_id}/execute")), mutates=True, approval=True),
        ),
    ),
    PlatformModule(
        "sad.study", "Personal Study",
        "Request-directed learning, writing, checking, and explanation assistance.",
        "experience",
        (
            _cap("study:personal", "Personal study", "Generate study help for the signed-in account.", "study:personal",
                 (_route("POST", "/v1/study/plan"),)),
        ),
    ),
    PlatformModule(
        "sad.forge", "Forge Learning",
        "Game-first quests, hints, mastery, XP, ranks, and student progress.",
        "experience",
        (
            _cap("forge:play", "Play Forge", "Create quests, unlock hints, and complete mastery checks.", "forge:play",
                 (_route("POST", "/v1/forge/quests"), _route("POST", "/v1/forge/hint"),
                  _route("POST", "/v1/forge/complete")), mutates=True),
            _cap("progress:own", "Own progress", "Read the signed-in learner's Forge progress.", "progress:own",
                 (_route("GET", "/v1/forge/progress"),)),
            _cap("progress:students", "Student progress", "Read student progress for authorized teaching/owner roles.", "progress:students",
                 (_route("GET", "/v1/forge/progress/{student_account_id}"), _route("GET", "/v1/students"))),
        ),
    ),
    PlatformModule(
        "sad.developer", "Developer Workspace",
        "Human-scoped multi-file coding with isolated generation, Docker verification, and Owner-controlled apply/rollback.",
        "development",
        (
            _cap("development:view", "Inspect development", "Inspect failures, jobs, and coding workspaces.", "development:view",
                 (_route("GET", "/v1/dashboard"), _route("GET", "/v1/dev/workspaces"),
                  _route("GET", "/v1/dev/workspaces/{workspace_id}"))),
            _cap("development:work", "Prepare development", "Plan and execute isolated coding work.", "development:work",
                 (_route("POST", "/v1/dev/workspaces/scope"), _route("POST", "/v1/dev/workspaces"),
                  _route("POST", "/v1/dev/workspaces/{workspace_id}/execute")), mutates=True),
            _cap("development:review", "Review development", "Review failure and repair evidence.", "development:review",
                 (_route("POST", "/v1/failures/{failure_id}/review"),), mutates=True),
            _cap("development:decide", "Decide repair evidence", "Approve or reject governed repair evidence.", "development:decide",
                 (_route("POST", "/v1/jobs/{work_item_id}/decision"),), mutates=True, approval=True),
            _cap("development:govern", "Govern live code", "Apply/rollback tested code and close governed work.", "development:govern",
                 (_route("POST", "/v1/dev/workspaces/{workspace_id}/apply"),
                  _route("POST", "/v1/dev/workspaces/{workspace_id}/rollback"),
                  _route("POST", "/v1/jobs/{work_item_id}/close")), mutates=True, approval=True),
        ),
    ),
    PlatformModule(
        "sad.skills", "Governed Skill Library",
        "Evidence-bound reusable procedures promoted separately from successful repairs.",
        "development",
        (
            _cap("skills:view", "Inspect skills", "Read candidate, validated, promoted, revoked, and superseded skills.", "development:view",
                 (_route("GET", "/v1/skills"),)),
            _cap("skills:propose", "Propose skill", "Create an evidence-bound skill candidate from repair/task provenance.", "development:work",
                 (_route("POST", "/v1/skills"),), mutates=True),
            _cap("skills:review", "Validate skill", "Attach independent verification evidence to a candidate skill.", "development:review",
                 (_route("POST", "/v1/skills/{skill_id}/validate"),), mutates=True),
            _cap("skills:govern", "Govern skill", "Human-promote or revoke a verified skill while preserving lineage.", "development:govern",
                 (_route("POST", "/v1/skills/{skill_id}/promote"),
                  _route("POST", "/v1/skills/{skill_id}/revoke")), mutates=True, approval=True),
        ),
        module_version="1.0.0",
    ),
    PlatformModule(
        "sad.accounts", "Accounts & Roles",
        "Local people, roles, passwords, and account lifecycle controls.",
        "core",
        (
            _cap("account:list", "List accounts", "List public local account records.", "account:list",
                 (_route("GET", "/v1/accounts"),)),
            _cap("account:manage", "Manage accounts/devices", "Manage non-owner accounts and mobile device trust.", "account:manage",
                 (_route("POST", "/v1/accounts/{account_id}/active"), _route("POST", "/v1/mobile/pairings"),
                  _route("GET", "/v1/mobile/devices"), _route("POST", "/v1/mobile/devices/{device_id}/revoke")), mutates=True),
            _cap("account:create_student", "Create student", "Create a student account.", "account:create_student",
                 (_route("POST", "/v1/accounts"),), mutates=True),
        ),
    ),
    PlatformModule(
        "sad.mobile", "Mobile Gateway",
        "Paired TLS phone access that preserves the core loopback API and signed-in RBAC.",
        "gateway",
        (
            _cap("mobile:paired_client", "Paired mobile client", "Use SAD through an already paired mobile device.", None,
                 (_route("GET", "/mobile/status"),)),
        ),
    ),
)


class PlatformRegistry:
    """Validate and expose declarative platform capability metadata."""

    def __init__(self, modules: Iterable[PlatformModule] = BUILTIN_MODULES):
        self.modules = tuple(modules)
        self._validate()
        self.capabilities = {
            capability.capability_id: capability
            for module in self.modules for capability in module.capabilities
        }

    def _validate(self):
        module_ids = set()
        capability_ids = set()
        for module in self.modules:
            if module.module_id in module_ids:
                raise ValueError(f"Duplicate platform module: {module.module_id}")
            module_ids.add(module.module_id)
            _version_tuple(module.module_version)
            if module.kind not in {"core", "experience", "development", "gateway", "extension"}:
                raise ValueError(f"Unsupported platform module kind: {module.kind}")
            if not module.capabilities:
                raise ValueError(f"Platform module has no capabilities: {module.module_id}")
            for capability in module.capabilities:
                if capability.capability_id in capability_ids:
                    raise ValueError(f"Duplicate platform capability: {capability.capability_id}")
                capability_ids.add(capability.capability_id)
                _version_tuple(capability.capability_version)
                if capability.lifecycle not in CAPABILITY_LIFECYCLES:
                    raise ValueError(f"Invalid capability lifecycle: {capability.capability_id}")
                if capability.lifecycle == "deprecated" and not capability.replacement:
                    raise ValueError(f"Deprecated capability requires a replacement: {capability.capability_id}")
                if not capability.routes:
                    raise ValueError(f"Capability has no routes: {capability.capability_id}")
                for route in capability.routes:
                    if route.method not in {"GET", "POST"} or not route.path.startswith("/"):
                        raise ValueError(f"Invalid platform route in {capability.capability_id}")

    def allowed_capability_ids(self, permissions):
        permissions = set(permissions)
        return {
            capability.capability_id
            for capability in self.capabilities.values()
            if capability.permission is None or capability.permission in permissions
        }

    def catalog(self, permissions):
        allowed = self.allowed_capability_ids(permissions)
        return [capability.to_dict() for capability in self.capabilities.values() if capability.capability_id in allowed]

    def visible_modules(self, permissions):
        allowed = self.allowed_capability_ids(permissions)
        modules = []
        for module in self.modules:
            visible = [cap.capability_id for cap in module.capabilities if cap.capability_id in allowed]
            if visible:
                modules.append(module.to_dict(visible))
        return modules

    def compatibility(self, requirements, allowed_capability_ids):
        if not isinstance(requirements, list) or len(requirements) > 100:
            raise ValueError("requirements must be a list of at most 100 entries.")
        allowed = set(allowed_capability_ids)
        results = []
        for requirement in requirements:
            if not isinstance(requirement, dict):
                raise ValueError("Each compatibility requirement must be an object.")
            capability_id = requirement.get("capability_id")
            minimum = requirement.get("min_version", "0.0.0")
            _version_tuple(minimum)
            capability = self.capabilities.get(capability_id)
            visible = capability is not None and capability_id in allowed
            compatible = visible and _version_tuple(capability.capability_version) >= _version_tuple(minimum)
            results.append({
                "capability_id": capability_id,
                "min_version": minimum,
                "available": visible,
                "compatible": compatible,
                "available_version": capability.capability_version if visible else None,
                "lifecycle": capability.lifecycle if visible else None,
                "replacement": capability.replacement if visible else None,
            })
        return {"compatible": all(item["compatible"] for item in results), "requirements": results}

    def manifest(self, role, permissions, api_version="v1"):
        modules = self.visible_modules(permissions)
        capabilities = [cap for module in modules for cap in module["capabilities"]]
        return {
            "product": "SAD",
            "platform_version": PLATFORM_VERSION,
            "platform_schema_version": PLATFORM_SCHEMA_VERSION,
            "api_version": api_version,
            "role": role,
            "module_count": len(modules),
            "capability_count": len(capabilities),
            "modules": modules,
            "authority_model": {
                "authentication": "local_account_session",
                "machine_authentication": "scoped_sad_app_secret",
                "authorization": "role_permissions_and_client_scopes",
                "platform_metadata_grants_authority": False,
                "dynamic_extension_execution": False,
                "extension_model": "declarative_external_sad_app_contract_only",
                "extension_registration_grants_authority": False,
                "host_fallback_on_extension_failure": False,
                "tool_execution": "registered_internal_tools_only",
                "memory_model": "explicit_user_controlled",
                "skill_promotion": "independent_verification_plus_human_approval",
                "repair_success_equals_skill_promotion": False,
                "git_authority": "human_host_only",
            },
        }
