"""TLS-only paired mobile gateway that keeps the SAD Core API loopback-only."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
import ipaddress
import json
import mimetypes
import os
from pathlib import Path
import re
import ssl
import threading

from api import MAX_REQUEST_BYTES, SadApiService
from bounded_http import BoundedThreadingHTTPServer
from mobile_access import DEVICE_DAYS, MobileAccessStore
from request_security import validate_browser_request


DEFAULT_MOBILE_PORT = 8766
PAIR_FAILURE_LIMIT = 10
PAIR_FAILURE_WINDOW_MINUTES = 5
DEVICE_COOKIE = "SAD_DEVICE"
TRUSTED_PRIVATE_V4 = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),
)
LEARNING_EXACT_ROUTES = {
    ("GET", "/health"),
    ("POST", "/v1/auth/login"),
    ("GET", "/v1/auth/me"),
    ("POST", "/v1/auth/logout"),
    ("POST", "/v1/auth/password"),
    ("GET", "/v1/chat/sessions"),
    ("POST", "/v1/chat/sessions"),
    ("POST", "/v1/voice/turn"),
    ("GET", "/v1/memory"),
    ("POST", "/v1/memory"),
    ("POST", "/v1/memory/search"),
    ("GET", "/v1/tools"),
    ("GET", "/v1/tools/actions"),
    ("POST", "/v1/tools/actions"),
    ("POST", "/v1/study/plan"),
    ("POST", "/v1/forge/quests"),
    ("GET", "/v1/forge/progress"),
    ("POST", "/v1/forge/hint"),
    ("POST", "/v1/forge/complete"),
}
CHAT_SESSION_ROUTE = re.compile(r"/v1/chat/sessions/[0-9a-f-]+")
CHAT_ACTION_ROUTE = re.compile(r"/v1/chat/sessions/[0-9a-f-]+/(messages|archive)")
MEMORY_ITEM_ROUTE = re.compile(r"/v1/memory/[0-9a-f-]+(?:/delete)?")
TOOL_ACTION_ROUTE = re.compile(r"/v1/tools/actions/[0-9a-f-]+(?:/(?:decision|execute))?")


def _now():
    return datetime.now(timezone.utc)


def mobile_host_allowed(host):
    """Allow one explicit RFC1918/CGNAT IPv4 address, never wildcard/public/reserved."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    if address.version != 4:
        return False
    return any(address in network for network in TRUSTED_PRIVATE_V4)


def mobile_route_allowed(mode, method, path):
    """Learning devices get a narrow personal route set; machine-client auth stays loopback-only."""
    if path.startswith("/v1/platform/client/"):
        return False
    if mode == "full_role":
        return True
    if mode != "learning":
        return False
    if (method, path) in LEARNING_EXACT_ROUTES:
        return True
    if method == "GET" and CHAT_SESSION_ROUTE.fullmatch(path):
        return True
    if method == "POST" and CHAT_ACTION_ROUTE.fullmatch(path):
        return True
    if method == "POST" and MEMORY_ITEM_ROUTE.fullmatch(path):
        return True
    if method in {"GET", "POST"} and TOOL_ACTION_ROUTE.fullmatch(path):
        return True
    return False


class PairAttemptLimiter:
    def __init__(self, now=None):
        self.now = now or _now
        self.failures = defaultdict(deque)
        self.lock = threading.RLock()

    def _prune(self, address):
        cutoff = self.now() - timedelta(minutes=PAIR_FAILURE_WINDOW_MINUTES)
        bucket = self.failures[address]
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        return bucket

    def require_available(self, address):
        with self.lock:
            if len(self._prune(address)) >= PAIR_FAILURE_LIMIT:
                raise PermissionError("Too many pairing attempts. Try again later.")

    def failed(self, address):
        with self.lock:
            self._prune(address).append(self.now())

    def succeeded(self, address):
        with self.lock:
            self.failures.pop(address, None)


class MobileGatewayHandler(BaseHTTPRequestHandler):
    service = None
    access = None
    limiter = None
    expected_hostname = None

    def _respond(self, status, payload, extra_headers=None):
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(encoded)

    def _body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length < 0 or length > MAX_REQUEST_BYTES:
            raise ValueError("request_too_large")
        return json.loads(self.rfile.read(length) or b"{}")

    def _serve_ui(self):
        mapping = {"/": "index.html", "/manifest.webmanifest": "manifest.webmanifest", "/sw.js": "sw.js"}
        relative = mapping.get(self.path)
        if relative is None and self.path.startswith("/ui/"):
            relative = self.path.removeprefix("/ui/")
        if not relative:
            return self._respond(404, {"error": "UI asset not found."})
        root = Path(__file__).with_name("web").resolve()
        target = (root / relative).resolve()
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

    def _pair(self, body):
        address = self.client_address[0]
        self.limiter.require_available(address)
        try:
            result = self.access.consume_pairing(body.get("code", ""), body.get("device_label"))
        except (PermissionError, ValueError):
            self.limiter.failed(address)
            raise
        self.limiter.succeeded(address)
        raw_token = result.pop("device_token")
        cookie = f"{DEVICE_COOKIE}={raw_token}; Path=/; Max-Age={DEVICE_DAYS * 86400}; Secure; HttpOnly; SameSite=Strict"
        return self._respond(200, result, {"Set-Cookie": cookie})

    def _cookie_device_token(self):
        jar = SimpleCookie()
        jar.load(self.headers.get("Cookie", ""))
        item = jar.get(DEVICE_COOKIE)
        return item.value if item else ""

    def _paired_device(self):
        raw = self._cookie_device_token() or self.headers.get("X-SAD-Device", "")
        if not raw:
            raise PermissionError("device_pairing_required")
        return self.access.require_device(raw)

    def _forget(self):
        device = self._paired_device()
        self.access.revoke_device(device["device_id"])
        clear = f"{DEVICE_COOKIE}=; Path=/; Max-Age=0; Secure; HttpOnly; SameSite=Strict"
        return self._respond(200, {"forgotten": True}, {"Set-Cookie": clear})

    def _handle(self):
        try:
            if self.command == "GET" and (self.path in {"/", "/manifest.webmanifest", "/sw.js"} or self.path.startswith("/ui/")):
                return self._serve_ui()
            validate_browser_request(
                self.headers, self.command, expected_scheme="https", expected_hostname=self.expected_hostname,
            )
            if self.command == "GET" and self.path == "/mobile/status":
                return self._respond(200, {"device": self._paired_device()})
            body = self._body()
            if self.command == "POST" and self.path == "/mobile/pair":
                return self._pair(body)
            if self.command == "POST" and self.path == "/mobile/forget":
                return self._forget()
            device = self._paired_device()
            if not mobile_route_allowed(device["mode"], self.command, self.path):
                raise PermissionError("This paired phone is not authorized for that mobile route.")
            status, payload = self.service.dispatch(self.command, self.path, self.headers, body)
            self._respond(status, payload)
        except PermissionError as error:
            self._respond(403, {"error": str(error)})
        except KeyError as error:
            self._respond(404, {"error": str(error)})
        except json.JSONDecodeError as error:
            self._respond(400, {"error": str(error)})
        except (ValueError, TypeError) as error:
            status = 413 if str(error) == "request_too_large" else 400
            self._respond(status, {"error": str(error)})

    do_GET = _handle
    do_POST = _handle

    def log_message(self, format, *args):
        return


def _validated_tls_file(value, label):
    original = Path(value).expanduser()
    if original.is_symlink():
        raise ValueError(f"{label} must not be a symlink.")
    path = original.resolve()
    if not path.is_file():
        raise ValueError(f"{label} must be an existing regular file.")
    return path


def create_mobile_server(host, port=DEFAULT_MOBILE_PORT, certfile=None, keyfile=None, service=None, access=None):
    if not mobile_host_allowed(host):
        raise ValueError("Mobile gateway must bind to one explicit RFC1918/approved-overlay IPv4 address.")
    if not certfile or not keyfile:
        raise ValueError("Mobile gateway requires a TLS certificate and private key.")
    certificate = _validated_tls_file(certfile, "TLS certificate")
    private_key = _validated_tls_file(keyfile, "TLS private key")
    handler = type(
        "BoundMobileGatewayHandler", (MobileGatewayHandler,),
        {
            "service": service or SadApiService(),
            "access": access or MobileAccessStore(),
            "limiter": PairAttemptLimiter(),
            "expected_hostname": host,
        },
    )
    server = BoundedThreadingHTTPServer(
        (host, port), handler, max_concurrent_requests=32, connection_timeout=15,
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=str(certificate), keyfile=str(private_key))
    server.socket = context.wrap_socket(server.socket, server_side=True)
    return server


def main():
    host = os.environ.get("SAD_MOBILE_HOST", "")
    certfile = os.environ.get("SAD_MOBILE_CERT", "")
    keyfile = os.environ.get("SAD_MOBILE_KEY", "")
    port = int(os.environ.get("SAD_MOBILE_PORT", str(DEFAULT_MOBILE_PORT)))
    server = create_mobile_server(host, port, certfile, keyfile)
    print(f"SAD Mobile Gateway is ready at https://{host}:{port}/")
    print("Pair this phone from the local Owner Mobile Access screen before signing in.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSAD Mobile Gateway stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()