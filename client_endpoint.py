"""Portable SAD client endpoint configuration.

Clients can move between local, temporary cloud, and future private-server endpoints without
changing API logic. Only HTTPS remote endpoints are accepted; loopback HTTP remains allowed
for local development.
"""

from dataclasses import dataclass
from urllib.parse import urlparse


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


@dataclass(frozen=True)
class ClientEndpoint:
    name: str
    base_url: str

    def api_url(self, path=""):
        clean = str(path or "").lstrip("/")
        return f"{self.base_url.rstrip('/')}/{clean}" if clean else self.base_url.rstrip("/")


def validate_client_endpoint(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Client endpoint must be a non-empty URL.")
    value = value.strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.username or parsed.password:
        raise ValueError("Credentials must not be embedded in the client endpoint URL.")
    if parsed.query or parsed.fragment:
        raise ValueError("Client endpoint must not include query parameters or fragments.")
    if parsed.hostname in LOOPBACK_HOSTS:
        if parsed.scheme != "http":
            raise ValueError("Local loopback client endpoints use http.")
    elif parsed.scheme != "https":
        raise ValueError("Remote SAD client endpoints must use HTTPS.")
    if not parsed.hostname:
        raise ValueError("Client endpoint must include a hostname.")
    return value


def endpoint_profile(name, base_url):
    label = str(name or "").strip()
    if not label or len(label) > 64:
        raise ValueError("Endpoint profile name must be 1-64 characters.")
    return ClientEndpoint(label, validate_client_endpoint(base_url))
