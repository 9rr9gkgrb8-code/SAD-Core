"""Tiny standard-library SDK for local SAD Platform clients.

The SDK does not persist credentials and intentionally accepts only loopback core API
URLs. Mobile/PWA clients use the paired HTTPS gateway instead.
"""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class SadSdkError(RuntimeError):
    pass


def _validate_base_url(base_url):
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
        raise ValueError("SAD SDK base URL must be an uncredentialed HTTP(S) URL.")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("SAD SDK core client may connect only to loopback.")
    return base_url.rstrip("/")


class SadLocalClient:
    """Synchronous local client for user sessions or scoped SAD-App credentials."""

    def __init__(self, base_url="http://127.0.0.1:8765", *, session_token=None, client_id=None, client_secret=None, timeout=20):
        self.base_url = _validate_base_url(base_url)
        self.session_token = session_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout

    def _authorization(self, machine=False):
        if machine:
            if not self.client_id or not self.client_secret:
                raise SadSdkError("SAD-App credentials are required.")
            return f"SAD-App {self.client_id}.{self.client_secret}"
        if not self.session_token:
            raise SadSdkError("A signed-in SAD session is required.")
        return f"Bearer {self.session_token}"

    def _request(self, method, path, payload=None, *, authorization=None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if authorization:
            headers["Authorization"] = authorization
        request = Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            try:
                payload = json.loads(error.read().decode("utf-8"))
                message = payload.get("error", str(error))
            except (ValueError, UnicodeDecodeError):
                message = str(error)
            raise SadSdkError(message) from error
        except URLError as error:
            raise SadSdkError(str(error.reason)) from error

    def health(self):
        return self._request("GET", "/health")

    def login(self, username, password):
        result = self._request("POST", "/v1/auth/login", {"username": username, "password": password})
        self.session_token = result["token"]
        return result

    def platform(self):
        return self._request("GET", "/v1/platform", authorization=self._authorization())

    def compatibility(self, requirements):
        return self._request(
            "POST", "/v1/platform/compatibility", {"requirements": requirements},
            authorization=self._authorization(),
        )

    def voice_turn(self, transcript, session_id=None):
        payload = {"transcript": transcript}
        if session_id:
            payload["session_id"] = session_id
        return self._request("POST", "/v1/voice/turn", payload, authorization=self._authorization())

    def app_manifest(self):
        return self._request("POST", "/v1/platform/client/manifest", {}, authorization=self._authorization(machine=True))

    def app_compatibility(self, requirements):
        return self._request(
            "POST", "/v1/platform/client/compatibility", {"requirements": requirements},
            authorization=self._authorization(machine=True),
        )

    def app_events(self, after_seq=0, limit=100):
        return self._request(
            "POST", "/v1/platform/client/events", {"after_seq": after_seq, "limit": limit},
            authorization=self._authorization(machine=True),
        )
