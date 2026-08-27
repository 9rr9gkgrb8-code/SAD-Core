"""Loopback-only stable HTTP/JSON API for SAD Core."""

from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import mimetypes

from auth import AuthService
from conversation import ConversationStore, generate_chat_reply
from failure_dashboard import DASHBOARD_STATE_FILE, FailureDashboard, FailureEvent
from forge_student import Quest, complete_quest, homework_to_quest, next_hint
from mobile_access import MobileAccessStore
from personal_study import StudyAction, StudyRequest, build_study_plan
from sad_forge_contract import Artifact, ForgeResult
from student_progress import ProgressStore
from study_generator import generate_study_result
from forge_worker import verify_approved_job


API_VERSION = "v1"
MAX_REQUEST_BYTES = 2_000_000


class SadApiService:
    def __init__(self, auth=None, dashboard=None, progress=None, mobile_access=None, conversations=None):
        self.auth = auth or AuthService()
        self.dashboard = dashboard or FailureDashboard(self.auth, DASHBOARD_STATE_FILE)
        self.progress = progress or ProgressStore(Path(__file__).with_name("student_progress.json"))
        self.mobile_access = mobile_access or MobileAccessStore()
        self.conversations = conversations or ConversationStore()

    def token(self, headers):
        value = headers.get("Authorization", "")
        if not value.startswith("Bearer "):
            raise PermissionError("Bearer authentication is required.")
        return value[7:]

    def dispatch(self, method, path, headers, body):
        if method == "GET" and path == "/health":
            return 200, {"status": "ok", "api_version": API_VERSION}
        if method == "POST" and path == "/v1/auth/login":
            token = self.auth.login(body.get("username", ""), body.get("password", ""))
            if not token:
                raise PermissionError("Login failed.")
            return 200, {"token": token, "account": self.auth.require(token)}

        token = self.token(headers)
        account = self.auth.require(token)
        account_id = account["account_id"]
        if method == "GET" and path == "/v1/auth/me":
            return 200, {"account": account, "profile": self.auth.get_profile(token)}
        if method == "POST" and path == "/v1/auth/logout":
            self.auth.logout(token)
            return 200, {"logged_out": True}
        if method == "POST" and path == "/v1/auth/password":
            self.auth.change_password(token, body.get("current_password", ""), body.get("new_password", ""))
            return 200, {"changed": True}

        if method == "GET" and path == "/v1/chat/sessions":
            return 200, {"sessions": self.conversations.list_sessions(account_id)}
        if method == "POST" and path == "/v1/chat/sessions":
            return 201, self.conversations.create_session(account_id)
        match = re.fullmatch(r"/v1/chat/sessions/([0-9a-f-]+)", path)
        if method == "GET" and match:
            return 200, self.conversations.get_session(account_id, match.group(1))
        match = re.fullmatch(r"/v1/chat/sessions/([0-9a-f-]+)/(messages|archive)", path)
        if method == "POST" and match:
            session_id, action = match.groups()
            if action == "archive":
                return 200, self.conversations.archive_session(account_id, session_id)
            session = self.conversations.raw_session(account_id, session_id)
            profile = self.auth.get_profile(token)
            reply, engine = generate_chat_reply(body.get("message", ""), profile, session)
            updated = self.conversations.append_turn(account_id, session_id, body.get("message", ""), reply, engine)
            return 200, {"reply": reply, "engine": engine, "session": updated}

        if method == "GET" and path == "/v1/accounts":
            return 200, {"accounts": self.auth.list_accounts(token)}
        if method == "GET" and path == "/v1/students":
            students = self.auth.list_students(token)
            return 200, {"students": [
                {**student, "progress": self.progress.get(student["account_id"]).to_dict()}
                for student in students
            ]}
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
            return 201, asdict(self.dashboard.ingest(event))
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
                    body["job_id"], body["request_id"], body["correlation_id"], body["state"],
                    artifacts, tuple(body.get("diagnostics", [])), tuple(body.get("tests", [])), body.get("error"),
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
            return 201, asdict(quest)
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
        self.end_headers()
        self.wfile.write(encoded)

    def _handle(self):
        try:
            if self.command == "GET" and (self.path in {"/", "/manifest.webmanifest", "/sw.js"} or self.path.startswith("/ui/")):
                return self._serve_ui()
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
    if host not in {"127.0.0.1", "::1", "localhost"}:
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
