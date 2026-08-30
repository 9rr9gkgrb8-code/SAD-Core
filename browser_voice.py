"""Browser voice-input milestone gate.

Browser microphone capture is a separate reviewed client/UAT milestone (see
`BROWSER_VOICE_INPUT.md`). It stays fully disabled unless an operator explicitly opts in
on the deployment host. This module only decides the response headers; no capture code
ships in the browser bundle until the milestone passes human UAT.
"""

from __future__ import annotations

import os

_ENABLED_VALUES = {"1", "true", "yes", "on"}
_DISABLED_POLICY = "camera=(), microphone=(), geolocation=()"
_MIC_ENABLED_POLICY = "camera=(), microphone=(self), geolocation=()"


def browser_microphone_enabled(env=None) -> bool:
    """True only when the host operator has explicitly opted in. Default is False."""
    source = os.environ if env is None else env
    return str(source.get("SAD_BROWSER_MIC", "")).strip().casefold() in _ENABLED_VALUES


def browser_permissions_policy(env=None) -> str:
    """Permissions-Policy for the UI. Microphone is `()` unless opted in, never `*`."""
    return _MIC_ENABLED_POLICY if browser_microphone_enabled(env) else _DISABLED_POLICY
