"""Optional connection to a local language model.

SAD keeps using its built-in conversation layer unless a local model is both
configured and explicitly enabled during a session.
"""

import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse

from sasha_voice import build_sasha_voice


LOCAL_MODEL_URL = os.getenv("SAD_LOCAL_MODEL_URL", "http://127.0.0.1:11434")
LOCAL_MODEL_NAME = os.getenv("SAD_LOCAL_MODEL", "")
MAX_MODEL_RESPONSE_BYTES = 2_000_000
MAX_PROMPT_CHARACTERS = 1_000_000


def validated_local_model_url(url=None):
    """Allow conversation data to be sent only to a loopback HTTP endpoint."""
    value = (url or LOCAL_MODEL_URL).rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("The local model URL must use HTTP on the loopback interface.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("The local model URL cannot contain credentials, a path, query, or fragment.")
    if parsed.port is not None and not 1 <= parsed.port <= 65535:
        raise ValueError("The local model URL has an invalid port.")
    return value


def build_system_prompt(user_name):
    name = user_name or "the user"
    prompt = (
        "You are Sasha, a local dialogue assistant. "
        f"You are speaking with {name}. Keep responses concise, natural, and helpful. "
        "Do not claim to change files, run tools, or take actions unless the user "
        "has explicitly asked and the application confirms it."
    )
    prompt = f"{prompt}\n\n{build_sasha_voice(user_name)}"
    return prompt


def local_model_is_configured():
    """A model name must be explicitly configured before any request is made."""
    return bool(LOCAL_MODEL_NAME)


def local_model_is_available():
    """Check a local Ollama-compatible endpoint without sending conversation data."""
    if not local_model_is_configured():
        return False

    try:
        base_url = validated_local_model_url()
        with urlopen(f"{base_url}/api/tags", timeout=1) as response:
            return response.status == 200
    except (OSError, URLError, ValueError):
        return False


def generate_local_response(message, user_name, history):
    """Generate a reply locally, returning None when the local service is unavailable."""
    if not local_model_is_available():
        return None

    prompt_history = "\n".join(
        f"{speaker}: {text}" for speaker, text in history[-6:]
    )
    prompt = (
        f"{build_system_prompt(user_name)}\n\n"
        f"Recent conversation:\n{prompt_history}\n"
        f"User: {message}\nSasha:"
    )
    if len(prompt) > MAX_PROMPT_CHARACTERS:
        return None
    payload = json.dumps(
        {"model": LOCAL_MODEL_NAME, "prompt": prompt, "stream": False}
    ).encode("utf-8")
    try:
        base_url = validated_local_model_url()
    except ValueError:
        return None
    request = Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read(MAX_MODEL_RESPONSE_BYTES + 1)
            if len(raw) > MAX_MODEL_RESPONSE_BYTES:
                return None
            result = json.loads(raw.decode("utf-8"))
            return result.get("response", "").strip() or None
    except (OSError, URLError, json.JSONDecodeError):
        return None
