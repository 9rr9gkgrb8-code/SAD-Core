"""Loopback-only stable HTTP/JSON API for the SAD local AI platform."""

from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re

from auth import AuthService, ROLE_PERMISSIONS
from conversation import ConversationStore, generate_chat_reply
from developer_workspace import DeveloperWorkspaceStore, suggest_scope
from failure_dashboard import DASHBOARD_STATE_FILE, FailureDashboard, FailureEvent
from forge_student import Quest, complete_quest, homework_to_quest, next_hint
from forge_worker import verify_approved_job
from memory_store import MemoryStore
from mobile_access import MobileAccessStore
from personal_study import StudyAction, StudyRequest, build_study_plan
from platform_clients import PlatformClientStore
from platform_events import PlatformEventStore
from platform_registry import PLATFORM_SCHEMA_VERSION, PLATFORM_VERSION, PlatformRegistry
from request_security import validate_browser_request
from sad_forge_contract import Artifact, ForgeResult
from student_progress import ProgressStore
from study_generator import generate_study_result
from tool_actions import ToolActionStore


API_VERSION = "v1"
MAX_REQUEST_BYTES = 2_000_000
LOOPBACK_HOSTNAMES = {"127.0.0.1", "localhost", "::1"}


class SadApiService:
    def __init__(
        self, auth=None, dashboard=None, progress=None, mobile_access=None,
        conversations=None, developer_workspaces=None, platform=None,
        platform_clients=None, platform_events=None, memory=None, tool_actions=None,
    ):
        self.auth = auth or AuthService()
        self.dashboard = dashboard or FailureDashboard(self.auth, DASHBOARD_STATE_FILE)
        self.progress = progress or ProgressStore(Path(__file__).with_name("student_progress.json"))
        self.mobile_access = mobile_access or MobileAccessStore()
        self.conversations = conversations or ConversationStore()
        self.developer_workspaces = developer_workspaces or DeveloperWorkspaceStore()
        self.memory = memory or MemoryStore()
        self.platform = platform or PlatformRegistry()
        self.platform_clients = platform_clients or PlatformClientStore()
        self.platform_events = platform_events or PlatformEventStore()
        self.tool_actions = tool_actions or ToolActionStore(memory=self.memory, platform=self.platform)
        self.last_event_error = None

    def token(self, headers):
        value = headers.get("Authorization", "")
        if not value.startswith("Bearer "):
            raise PermissionError("Bearer authentication is required.")
        return value[7:]

    def _publish(self, event_type, *, subject_id=None, details=None):
        """Events are auxiliary metadata; event failure cannot corrupt a completed primary action."""
        try:
            self.platform_events.publish(event_type, subject_id=subject_id, details=details)
            self.last_event_error = None
        except (OSError, ValueError, json.JSONDecodeError) as error:
            self.last_event_error = str(error)

    def _machine_manifest(self, client):
        route_map = {
            "platform:discover": [{"method": "POST", "path": "/v1/platform/client/manifest"}],
            "platform:catalog": [{"method": "POST", "path": "/v1/platform/client/catalog"}],
            "platform:modules": [{"method": "POST", "path": "/v1/platform/client/modules"}],
            "platform:compatibility": [{"method": "POST", "path": "/v1/platform/client/compatibility"}],
            "platform:events": [{"method": "POST", "path": "/v1/platform/client/events"}],
        }
        capabilities = []
        for capability_id in client["capability_ids"]:
            capability = self.platform.capabilities.get(capability_id)
            if not capability:
                continue
            item = capability.to_dict()
            item["routes"] = route_map.get(capability_id, [])
            capabilities.append(item)
        return {
            "product": "SAD",
            "platform_version": PLATFORM_VERSION,
            "platform_schema_version": PLATFORM_SCHEMA_VERSION,
            "api_version": API_VERSION,
            "principal": {"kind": "local_app", "client_id": client["client_id"], "name": client["name"]},
            "capability_count": len(capabilities),
            "capabilities": capabilities,
            "event_types": list(client["event_types"]),
            "authority_model": {
                "authentication": "scoped_sad_app_secret",
                "user_impersonation": False,
                "state_mutation": False,
                "dynamic_extension_execution": False,
                "git_authority": "none",
            },
        }

    def _dispatch_platform_client(self, method, path, headers, body):
        if method != "POST":
            raise KeyError("Endpoint not found.")
        authorization = headers.get("Authorization", "")
        if path == "/v1/platform/client/manifest":
            client = self.platform_clients.require(authorization, "platform:discover")
            return 200, self._machine_manifest(client)
        if path == "/v1/platform/client/catalog":
            client = self.platform_clients.require(authorization, "platform:catalog")
            manifest = self._machine_manifest(client)
            return 200, {"capabilities": manifest["capabilities"]}
        if path == "/v1/platform/client/modules":
            client = self.platform_clients.require(authorization, "platform:modules")
            manifest = self._machine_manifest(client)
            return 200, {"modules": [{
                "module_id": "sad.platform", "name": "SAD Platform Core", "kind": "core",
                "status": "available", "module_version": "3.0.0", "capabilities": manifest["capabilities"],
            }]}
        if path == "/v1/platform/client/compatibility":
            client = self.platform_clients.require(authorization, "platform:compatibility")
            return 200, self.platform.compatibility(body.get("requirements", []), client["capability_ids"])
        if path == "/v1/platform/client/events":
            client = self.platform_clients.require(authorization, "platform:events")
            return 200, self.platform_events.read(
                after_seq=body.get("after_seq", 0), limit=body.get("limit", 100), event_types=client["event_types"],
            )
        raise KeyError("Endpoint not found.")

    def dispatch(self, method, path, headers, body):
        if method == "GET" and path == "/health":
            return 200, {"status": "ok", "api_version": API_VERSION}
        if path.startswith("/v1/platform/client/"):
            return self._dispatch_platform_client(method, path, headers, body)
        if method == "POST" and path == "/v1/auth/login":
            token = self.auth.login(body.get("username", ""), body.get("password", ""))
            if not token:
                raise PermissionError("Login failed.")
            return 200, {"token": token, "account": self.auth.require(token)}

        token = self.token(headers)
        account = self.auth.require(token)
        account_id = account["account_id"]
        permissions = ROLE_PERMISSIONS[account["role"]]

        if method == "GET" and path == "/v1/auth/me":
            return 200, {"account": account, "profile": self.auth.get_profile(token)}
        if method == "POST" and path == "/v1/auth/logout":
            self.auth.logout(token)
            return 200, {"logged_out": True}
        if method == "POST" and path == "/v1/auth/password":
            self.auth.change_password(token, body.get("current_password", ""), body.get("new_password", ""))
            return 200, {"changed": True}

        if method == "GET" and path == "/v1/platform":
            return 200, self.platform.manifest(account["role"], permissions, API_VERSION)
        if method == "GET" and path == "/v1/platform/capabilities":
            return 200, {"capabilities": self.platform.catalog(permissions)}
        if method == "GET" and path == "/v1/platform/modules":
            return 200, {"modules": self.platform.visible_modules(permissions)}
        if method == "POST" and path == "/v1/platform/compatibility":
            return 200, self.platform.compatibility(body.get("requirements", []), self.platform.allowed_capability_ids(permissions))
        if method == "GET" and path == "/v1/platform/clients":
            self.auth.require(token, "platform:manage")
            return 200, {"clients": self.platform_clients.list()}
        if method == "POST" and path == "/v1/platform/clients":
            self.auth.require(token, "platform:manage")
            client = self.platform_clients.create(body.get("name", ""), body.get("capability_ids", []), body.get("event_types", []))
            self._publish("platform.client.created", subject_id=client["client_id"], details={"name": client["name"]})
            return 201, client
        match = re.fullmatch(r"/v1/platform/clients/([0-9a-f-]+)/(rotate|revoke)", path)
        if method == "POST" and match:
            self.auth.require(token, "platform:manage")
            client_id, action = match.groups()
            if action == "rotate":
                client = self.platform_clients.rotate(client_id)
                self._publish("platform.client.rotated", subject_id=client_id)
            else:
                client = self.platform_clients.revoke(client_id)
                self._publish("platform.client.revoked", subject_id=client_id)
            return 200, client
        if method == "POST" and path == "/v1/platform/events/read":
            self.auth.require(token, "platform:manage")
            return 200, self.platform_events.read(
                after_seq=body.get("after_seq", 0), limit=body.get("limit", 100), event_types=body.get("event_types"),
            )

        # User-controlled memory. No cross-account ID can be used successfully.
        if method == "GET" and path == "/v1/memory":
            return 200, {"memories": self.memory.list(account_id)}
        if method == "POST" and path == "/v1/memory":
            item = self.memory.create(
                account_id, body.get("category", "note"), body.get("title", ""), body.get("content", ""),
                enabled=body.get("enabled", True), expires_at=body.get("expires_at"),
            )
            self._publish("memory.created", subject_id=item["memory_id"], details={"category": item["category"]})
            return 201, item
        if method == "POST" and path == "/v1/memory/search":
            return 200, {"memories": self.memory.search(
                account_id, body.get("query", ""), body.get("categories"),
                limit=body.get("limit", 20), enabled_only=bool(body.get("enabled_only", False)),
            )}
        match = re.fullmatch(r"/v1/memory/([0-9a-f-]+)(?:/(delete))?", path)
        if method == "POST" and match:
            memory_id, action = match.groups()
            if action == "delete":
                result = self.memory.delete(account_id, memory_id)
                self._publish("memory.deleted", subject_id=memory_id)
                return 200, result
            item = self.memory.update(account_id, memory_id, body)
            self._publish("memory.updated", subject_id=memory_id, details={"category": item["category"], "enabled": item["enabled"]})
            return 200, item

        # Governed internal tools. No arbitrary tool registration/execution exists here.
        if method == "GET" and path == "/v1/tools":
            return 200, {"tools": self.tool_actions.available_tools(permissions)}
        if method == "GET" and path == "/v1/tools/actions":
            return 200, {"actions": self.tool_actions.list(account_id)}
        if method == "POST" and path == "/v1/tools/actions":
            action = self.tool_actions.create(account_id, permissions, body.get("tool_id", ""), body.get("args", {}))
            self._publish("tool.action.created", subject_id=action["action_id"], details={"tool_id": action["tool_id"], "state": action["state"]})
            return 201, action
        match = re.fullmatch(r"/v1/tools/actions/([0-9a-f-]+)(?:/(decision|execute))?", path)
        if match:
            action_id, action_name = match.groups()
            if method == "GET" and not action_name:
                return 200, self.tool_actions.get(account_id, action_id)
            if method == "POST" and action_name == "decision":
                action = self.tool_actions.decide(account_id, action_id, body.get("decision"))
                self._publish("tool.action.decided", subject_id=action_id, details={"decision": action["decision"]})
                return 200, action
            if method == "POST" and action_name == "execute":
                action = self.tool_actions.execute(account, permissions, action_id)
                self._publish("tool.action.completed", subject_id=action_id, details={"tool_id": action["tool_id"], "state": action["state"]})
                return 200, action

        if method == "GET" and path == "/v1/chat/sessions":
            return 200, {"sessions": self.conversations.list_sessions(account_id)}
        if method == "POST" and path == "/v1/chat/sessions":
            session = self.conversations.create_session(account_id)
            self._publish("chat.session.created", subject_id=session.get("session_id"))
            return 201, session
        match = re.fullmatch(r"/v1/chat/sessions/([0-9a-f-]+)", path)
        if method == "GET" and match:
            return 200, self.conversations.get_session(account_id, match.group(1))
        match = re.fullmatch(r"/v1/chat/sessions/([0-9a-f-]+)/(messages|archive)", path)
        if method == "POST" and match:
            session_id, action = match.groups()
            if action == "archive":
                archived = self.conversations.archive_session(account_id, session_id)
                self._publish("chat.session.archived", subject_id=session_id)
                return 200, archived
            session = self.conversations.raw_session(account_id, session_id)
            profile = self.auth.get_profile(token)
            memories = [] if body.get("use_memory") is False else self.memory.context(account_id)
            reply, engine = generate_chat_reply(body.get("message", ""), profile, session, memories)
            updated = self.conversations.append_turn(account_id, session_id, body.get("message", ""), reply, engine)
            self._publish("chat.message.created", subject_id=session_id, details={"engine": engine, "memory_context": bool(memories)})
            return 200, {"reply": reply, "engine": engine, "memory_used": bool(memories) and engine == "local_model", "session": updated}

        if method == "POST" and path == "/v1/voice/turn":
            transcript = body.get("transcript", "")
            if not isinstance(transcript, str) or not transcript.strip() or len(transcript) > 20_000:
                raise ValueError("Voice transcript must be 1-20000 characters.")
            session_id = body.get("session_id")
            if session_id is None:
                created = self.conversations.create_session(account_id)
                session_id = created["session_id"]
                self._publish("chat.session.created", subject_id=session_id)
            session = self.conversations.raw_session(account_id, session_id)
            profile = self.auth.get_profile(token)
            memories = [] if body.get("use_memory") is False else self.memory.context(account_id)
            reply, engine = generate_chat_reply(transcript.strip(), profile, session, memories)
            self.conversations.append_turn(account_id, session_id, transcript.strip(), reply, engine)
            self._publish("voice.turn.completed", subject_id=session_id, details={"engine": engine, "memory_context": bool(memories)})
            return 200, {
                "session_id": session_id, "reply": reply, "speech_text": reply, "engine": engine,
                "memory_used": bool(memories) and engine == "local_model",
                "input_mode": "transcript", "output_mode": "text_for_local_tts",
            }

        if method == "POST" and path == "/v1/dev/workspaces/scope":
            self.auth.require(token, "development:work")
            return 200, suggest_scope(body.get("task", ""))
        if method == "GET" and path == "/v1/dev/workspaces":
            self.auth.require(token, "development:view")
            return 200, {"workspaces": self.developer_workspaces.list()}
        if method == "POST" and path == "/v1/dev/workspaces":
            self.auth.require(token, "development:work")
            workspace = self.developer_workspaces.create(body.get("task", ""), body.get("allowed_paths", []), account_id)
            self._publish("development.workspace.created", subject_id=workspace.get("workspace_id"))
            return 201, workspace
        match = re.fullmatch(r"/v1/dev/workspaces/([0-9a-f-]+)(?:/(execute|apply|rollback))?", path)
        if match:
            workspace_id, action = match.groups()
            if method == "GET" and not action:
                self.auth.require(token, "development:view")
                return 200, self.developer_workspaces.get(workspace_id)
            if method == "POST" and action == "execute":
                self.auth.require(token, "development:work")
                workspace_meta = self.developer_workspaces.get(workspace_id)
                if account["role"] != "owner" and workspace_meta.get("created_by") != account_id:
                    raise PermissionError("Developers may execute only workspaces they created.")
                workspace = self.developer_workspaces.execute(workspace_id)
                self._publish("development.workspace.executed", subject_id=workspace_id, details={"state": workspace.get("state")})
                return 200, workspace
            if method == "POST" and action == "apply":
                self.auth.require(token, "development:govern")
                workspace = self.developer_workspaces.apply(workspace_id)
                self._publish("development.workspace.applied", subject_id=workspace_id)
                return 200, workspace
            if method == "POST" and action == "rollback":
                self.auth.require(token, "development:govern")
                workspace = self.developer_workspaces.rollback(workspace_id)
                self._publish("development.workspace.rolled_back", subject_id=workspace_id)
                return 200, workspace

        if method == "GET" and path == "/v1/accounts":
            return 200, {"accounts": self.auth.list_accounts(token)}
        if method == "GET" and path == "/v1/students":
            students = self.auth.list_students(token)
            return 200, {"students": [{**student, "progress": self.progress.get(student["account_id"]).to_dict()} for student in students]}
        if method == "POST" and path == "/v1/accounts":
            return 201, self.auth.create_account(body["username"], body["password"], body["role"], token)
        match = re.fullmatch(r"/v1/accounts/([0-9a-f-]+)/active", path)
        if method == "POST" and match:
            return 200, self.auth.set_account_active(match.group(1), body.get("active"), token)

        if method == "POST" and path == "/v1/mobile/pairings":
            self.auth.require(token, "account:manage")
            return 201, self.mobile_access.create_pairing(body.get("label", "Phone"), body.get("mode", "learning"))
        if method == "GET" and path == "/v1/mobile/devices":
            self.auth.require(token, "account:manage")
            return 200, {"devices": self.mobile_access.list_devices()}
        match = re.fullmatch(r"/v1/mobile/devices/([0-9a-f-]+)/revoke", path)
        if method == "POST" and match:
            self.auth.require(token, "account:manage")
            return 200, self.mobile_access.revoke_device(match.group(1))

        if method == "POST" and path == "/v1/failures":
            event = FailureEvent(
                body.get("source", "user"), body["category"], body["summary"],
                body.get("evidence") or [{"reported_by": account_id}],
                body.get("suggested_correction", "Review the evidence."), body.get("affected_files", []),
            )
            failure = asdict(self.dashboard.ingest(event))
            self._publish("failure.created", subject_id=failure.get("failure_id"), details={"category": body["category"]})
            return 201, failure
        if method == "GET" and path == "/v1/dashboard":
            return 200, self.dashboard.snapshot(token)
        if method == "GET" and path in {"/v1/dashboard/failures", "/v1/dashboard/jobs"}:
            snapshot = self.dashboard.snapshot(token)
            key = "failures" if path.endswith("failures") else "development"
            return 200, {key: snapshot[key]}
        if method == "POST" and path == "/v1/jobs":
            return 201, asdict(self.dashboard.push_to_development(body["failure_id"], token, body.get("approved") is True))

        match = re.fullmatch(r"/v1/failures/([0-9a-f-]+)/(review|push)", path)
        if method == "POST" and match:
            failure_id, action = match.groups()
            if action == "review":
                return 200, asdict(self.dashboard.mark_in_review(failure_id, token))
            return 201, asdict(self.dashboard.push_to_development(failure_id, token, body.get("approved") is True))

        match = re.fullmatch(r"/v1/jobs/([0-9a-f-]+)(?:/(approve-isolated|start|execute|result|decision|close))?", path)
        if match:
            work_id, action = match.groups()
            if method == "GET" and not action:
                self.auth.require(token, "development:view")
                return 200, asdict(self.dashboard.dev_items[work_id])
            if method == "POST" and action == "approve-isolated":
                return 200, asdict(self.dashboard.approve_isolated_work(work_id, token, body.get("source_snapshot", "unknown")))
            if method == "POST" and action == "start":
                return 200, asdict(self.dashboard.start_forge(work_id, token))
            if method == "POST" and action == "execute":
                item = self.dashboard.start_forge(work_id, token)
                result = verify_approved_job(item)
                return 200, asdict(self.dashboard.record_forge_result(work_id, result, token))
            if method == "POST" and action == "result":
                artifacts = tuple(Artifact(**artifact) for artifact in body.get("artifacts", []))
                result = ForgeResult(
                    body["job_id"], body["request_id"], body["correlation_id"], body["state"], artifacts,
                    tuple(body.get("diagnostics", [])), tuple(body.get("tests", [])), body.get("error"),
                )
                return 200, asdict(self.dashboard.record_forge_result(work_id, result, token))
            if method == "POST" and action == "decision":
                return 200, asdict(self.dashboard.decide(work_id, body["decision"], token))
            if method == "POST" and action == "close":
                return 200, asdict(self.dashboard.close(work_id, token))

        if method == "POST" and path == "/v1/study/plan":
            self.auth.require(token, "study:personal")
            request = StudyRequest(
                StudyAction(body["action"]), body["material"], body.get("course", ""),
                body.get("requested_depth", "standard"), body.get("target_word_count"),
                body.get("preserve_voice", True), body.get("graded", False),
            )
            plan = build_study_plan(request)
            payload = plan.to_dict()
            if body.get("generate") is True:
                profile = self.auth.get_profile(token)
                payload["result"] = generate_study_result(request, plan, profile["display_name"])
            return 200, payload
        if method == "POST" and path == "/v1/forge/quests":
            self.auth.require(token, "forge:play")
            quest = homework_to_quest(body["subject"], body["assignment"], body.get("learning_objective", ""))
            payload = asdict(quest)
            self._publish("forge.quest.created", subject_id=payload.get("quest_id"), details={"subject": body["subject"]})
            return 201, payload
        if method == "GET" and path == "/v1/forge/progress":
            self.auth.require(token, "progress:own")
            return 200, self.progress.get(account_id).to_dict()
        match = re.fullmatch(r"/v1/forge/progress/([0-9a-f-]+)", path)
        if method == "GET" and match:
            self.auth.require(token, "progress:students")
            return 200, self.progress.get(match.group(1)).to_dict()
        if method == "POST" and path == "/v1/forge/hint":
            self.auth.require(token, "forge:play")
            progress = self.progress.get(account_id)
            hint = next_hint(progress, body["quest_id"])
            self.progress.save(progress)
            return 200, {"hint_level": hint, "progress": progress.to_dict()}
        if method == "POST" and path == "/v1/forge/complete":
            self.auth.require(token, "forge:play")
            quest = Quest(**body["quest"])
            progress = self.progress.get(account_id)
            outcome = complete_quest(progress, quest, body["score"], body["boss_passed"])
            self.progress.save(progress)
            self._publish("forge.quest.completed", subject_id=quest.quest_id, details={"mastered": bool(outcome.get("mastered")) if isinstance(outcome, dict) else False})
            return 200, {"outcome": outcome, "progress": progress.to_dict()}
        raise KeyError("Endpoint not found.")


class SadApiHandler(BaseHTTPRequestHandler):
    service = None

    def _respond(self, status, payload):
        encoded = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.end_headers()
        self.wfile.write(encoded)

    def _handle(self):
        try:
            if self.command == "GET" and (self.path in {"/", "/manifest.webmanifest", "/sw.js"} or self.path.startswith("/ui/")):
                return self._serve_ui()
            validate_browser_request(
                self.headers, self.command, expected_scheme="http", allowed_hostnames=LOOPBACK_HOSTNAMES,
            )
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > MAX_REQUEST_BYTES:
                return self._respond(413, {"error": "request_too_large"})
            body = json.loads(self.rfile.read(length) or b"{}")
            status, payload = self.service.dispatch(self.command, self.path, self.headers, body)
            self._respond(status, payload)
        except PermissionError as error:
            self._respond(403, {"error": str(error)})
        except KeyError as error:
            self._respond(404, {"error": str(error)})
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._respond(400, {"error": str(error)})

    def _serve_ui(self):
        mapping = {"/": "index.html", "/manifest.webmanifest": "manifest.webmanifest", "/sw.js": "sw.js"}
        relative = mapping.get(self.path)
        if relative is None and self.path.startswith("/ui/"):
            relative = self.path.removeprefix("/ui/")
        root = Path(__file__).with_name("web").resolve()
        target = (root / (relative or "")).resolve()
        if target == root or not target.is_relative_to(root) or not target.is_file():
            return self._respond(404, {"error": "UI asset not found."})
        content = target.read_bytes()
        content_type = "application/manifest+json" if target.name.endswith(".webmanifest") else mimetypes.guess_type(target.name)[0]
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; manifest-src 'self'; worker-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if target.name == "sw.js":
            self.send_header("Service-Worker-Allowed", "/")
        self.end_headers()
        self.wfile.write(content)

    do_GET = _handle
    do_POST = _handle

    def log_message(self, format, *args):
        return


def create_server(host="127.0.0.1", port=8765, service=None):
    if host not in LOOPBACK_HOSTNAMES:
        raise ValueError("SAD API may bind only to loopback.")
    handler = type("BoundSadApiHandler", (SadApiHandler,), {"service": service or SadApiService()})
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server


def main():
    server = create_server()
    print(f"SAD API listening on http://127.0.0.1:{server.server_port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
