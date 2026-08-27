"""Loopback-only stable HTTP/JSON API for SAD Core."""

from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import uuid

from auth import AuthService
from failure_dashboard import DASHBOARD_STATE_FILE, FailureDashboard, FailureEvent
from forge_student import Quest, complete_quest, homework_to_quest, next_hint
from personal_study import StudyAction, StudyRequest, build_study_plan
from sad_forge_contract import Artifact, ForgeResult
from student_progress import ProgressStore


API_VERSION = "v1"
MAX_REQUEST_BYTES = 2_000_000


class SadApiService:
    def __init__(self, auth=None, dashboard=None, progress=None):
        self.auth = auth or AuthService()
        self.dashboard = dashboard or FailureDashboard(self.auth, DASHBOARD_STATE_FILE)
        self.progress = progress or ProgressStore(Path(__file__).with_name("student_progress.json"))

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
        if method == "POST" and path == "/v1/failures":
            event = FailureEvent(
                body.get("source", "user"), body["category"], body["summary"],
                body.get("evidence") or [{"reported_by": account["account_id"]}],
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

        match = re.fullmatch(r"/v1/jobs/([0-9a-f-]+)(?:/(approve-isolated|start|result|decision|close))?", path)
        if match:
            work_id, action = match.groups()
            if method == "GET" and not action:
                self.auth.require(token, "development:view")
                return 200, asdict(self.dashboard.dev_items[work_id])
            if method == "POST" and action == "approve-isolated":
                return 200, asdict(self.dashboard.approve_isolated_work(work_id, token, body.get("source_snapshot", "unknown")))
            if method == "POST" and action == "start":
                return 200, asdict(self.dashboard.start_forge(work_id, token))
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
            return 200, build_study_plan(request).to_dict()
        if method == "POST" and path == "/v1/forge/quests":
            self.auth.require(token, "forge:play")
            quest = homework_to_quest(body["subject"], body["assignment"], body.get("learning_objective", ""))
            return 201, asdict(quest)
        if method == "GET" and path == "/v1/forge/progress":
            self.auth.require(token, "progress:own")
            return 200, self.progress.get(account["account_id"]).to_dict()
        match = re.fullmatch(r"/v1/forge/progress/([0-9a-f-]+)", path)
        if method == "GET" and match:
            self.auth.require(token, "progress:students")
            return 200, self.progress.get(match.group(1)).to_dict()
        if method == "POST" and path == "/v1/forge/hint":
            self.auth.require(token, "forge:play")
            progress = self.progress.get(account["account_id"])
            hint = next_hint(progress, body["quest_id"])
            self.progress.save(progress)
            return 200, {"hint_level": hint, "progress": progress.to_dict()}
        if method == "POST" and path == "/v1/forge/complete":
            self.auth.require(token, "forge:play")
            quest = Quest(**body["quest"])
            progress = self.progress.get(account["account_id"])
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
