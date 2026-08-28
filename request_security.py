"""Shared HTTP request-origin checks for SAD's local/private browser surfaces."""

from __future__ import annotations

from urllib.parse import urlsplit


JSON_CONTENT_TYPES = {"application/json"}


def _host_parts(value):
    if not isinstance(value, str) or not value.strip():
        raise PermissionError("A valid Host header is required.")
    parsed = urlsplit("//" + value.strip())
    if not parsed.hostname or parsed.username or parsed.password:
        raise PermissionError("Invalid Host header.")
    try:
        port = parsed.port
    except ValueError as error:
        raise PermissionError("Invalid Host header.") from error
    return parsed.hostname.casefold(), port, value.strip()


def validate_browser_request(
    headers, method, *, expected_scheme, expected_hostname=None, allowed_hostnames=None,
):
    """Reject cross-site/rebinding browser traffic before it reaches SAD state.

    Non-browser/native clients may omit Origin and Sec-Fetch-Site, but still need a valid
    Host and JSON for POST. Browsers that provide Origin/fetch metadata must prove the
    request is same-origin.
    """
    hostname, _port, host_value = _host_parts(headers.get("Host", ""))
    if expected_hostname is not None and hostname != str(expected_hostname).casefold():
        raise PermissionError("Host header does not match this SAD listener.")
    if allowed_hostnames is not None and hostname not in {item.casefold() for item in allowed_hostnames}:
        raise PermissionError("Host header is outside the approved SAD listener names.")

    fetch_site = headers.get("Sec-Fetch-Site")
    if fetch_site and fetch_site.casefold() != "same-origin":
        raise PermissionError("Cross-site browser requests are not allowed.")

    origin = headers.get("Origin")
    if origin:
        parsed = urlsplit(origin)
        if parsed.scheme.casefold() != expected_scheme.casefold() or parsed.netloc.casefold() != host_value.casefold():
            raise PermissionError("Browser Origin does not match this SAD listener.")

    if method == "POST":
        content_type = headers.get("Content-Type", "").split(";", 1)[0].strip().casefold()
        if content_type not in JSON_CONTENT_TYPES:
            raise PermissionError("SAD POST requests require application/json.")
    return True
