"""Declarative platform registry for SAD Core.

Platform modules describe capabilities and routes; registry metadata never executes
module code or grants authority. Existing authentication/RBAC remains the enforcement
layer for every concrete endpoint.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


PLATFORM_VERSION = "0.1-alpha"
PLATFORM_SCHEMA_VERSION = 1


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

    def to_dict(self):
        return {
            "capability_id": self.capability_id,
            "title": self.title,
            "description": self.description,
            "permission": self.permission,
            "routes": [route.to_dict() for route in self.routes],
            "mutates_state": self.mutates_state,
            "human_approval_boundary": self.human_approval_boundary,
        }


@dataclass(frozen=True)
class PlatformModule:
    module_id: str
    name: str
    description: str
    kind: str
    capabilities: tuple[PlatformCapability, ...]
    status: str = "available"

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
            "capabilities": capabilities,
        }


def _route(method, path):
    return PlatformRoute(method, path)


def _cap(capability_id, title, description, permission, routes, *, mutates=False, approval=False):
    return PlatformCapability(
        capability_id, title, description, permission, tuple(routes), mutates, approval,
    )


BUILTIN_MODULES = (
    PlatformModule(
        "sad.platform", "SAD Platform Core",
        "Discovers the platform, modules, capabilities, versions, and signed-in access surface.",
        "core",
        (
            _cap("platform:discover", "Discover platform", "Read the signed-in platform manifest.", None,
                 (_route("GET", "/v1/platform"),)),
            _cap("platform:catalog", "Browse capabilities", "Read capabilities available to the signed-in account.", None,
                 (_route("GET", "/v1/platform/capabilities"),)),
            _cap("platform:modules", "Browse modules", "Read modules visible to the signed-in account.", None,
                 (_route("GET", "/v1/platform/modules"),)),
        ),
    ),
    PlatformModule(
        "sad.chat", "SAD Chat",
        "General multi-turn local AI conversation with durable per-account history.",
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
        "sad.study", "Personal Study",
        "Request-directed learning, writing, checking, and explanation assistance.",
        "experience",
        (
            _cap("study:personal", "Personal study", "Generate study help for the signed-in account.", "study:personal",
                 (_route("POST", "/v1/study/plan"),), mutates=False),
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
            if module.kind not in {"core", "experience", "development", "gateway", "extension"}:
                raise ValueError(f"Unsupported platform module kind: {module.kind}")
            if not module.capabilities:
                raise ValueError(f"Platform module has no capabilities: {module.module_id}")
            for capability in module.capabilities:
                if capability.capability_id in capability_ids:
                    raise ValueError(f"Duplicate platform capability: {capability.capability_id}")
                capability_ids.add(capability.capability_id)
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
        return [
            capability.to_dict()
            for capability in self.capabilities.values()
            if capability.capability_id in allowed
        ]

    def visible_modules(self, permissions):
        allowed = self.allowed_capability_ids(permissions)
        modules = []
        for module in self.modules:
            visible = [cap.capability_id for cap in module.capabilities if cap.capability_id in allowed]
            if visible:
                modules.append(module.to_dict(visible))
        return modules

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
                "authorization": "role_permissions",
                "platform_metadata_grants_authority": False,
                "git_authority": "human_host_only",
            },
        }
