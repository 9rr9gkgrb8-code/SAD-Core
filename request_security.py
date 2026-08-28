"""Shared HTTP request-origin checks for SAD's local/private browser surfaces."""

from __future__ import annotations


JSON_CONTENT_TYPES = {"application/json"}


def _host_parts(value):
    if not isinstance(value, str) or not value.strip():
        raise PermissionError("A valid Host header is required.")
    raw = value.strip()
    if any(character.isspace() for character in raw) or any(character in raw for character in "/\\@?#"):
        raise PermissionError("Invalid Host header.")
    if raw.startswith("["):
        closing = raw.find("]")
        if closing <= 1:
            raise PermissionError("Invalid Host header.")
        hostname = raw[1:closing]
        remainder = raw[closing + 1:]
        if remainder:
            if not remainder.startswith(":") or not remainder[1:].isdigit():
                raise PermissionError("Invalid Host header.")
            port = int(remainder[1:])
        else:
            port = None
    else:
        if raw.count(":") > 1:
            raise PermissionError("IPv6 Host headers must use brackets.")
        if ":" in raw:
            hostname, port_text = raw.rsplit(":", 1)
            if not hostname or not port_text.isdigit():
                raise PermissionError("Invalid Host header.")
            port = int(port_text)
        else:
            hostname, port = raw, None
    if not hostname or (port is not None and not 1 <= port <= 65535):
        raise PermissionError("Invalid Host header.")
    return hostname.casefold(), port, raw


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
    if origin and origin.strip().casefold() != f"{expected_scheme}://{host_value}".casefold():
        raise PermissionError("Browser Origin does not match this SAD listener.")

    if method == "POST":
        content_type = headers.get("Content-Type", "").split(";", 1)[0].strip().casefold()
        if content_type not in JSON_CONTENT_TYPES:
            raise PermissionError("SAD POST requests require application/json.")
    return True
