"""Optional connection to a private local language model.

SAD keeps using its built-in conversation layer unless a local model is both
configured and explicitly enabled during a session.
"""

import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen

from sasha_voice import build_sasha_voice


LOCAL_MODEL_URL = os.getenv("SAD_LOCAL_MODEL_URL", "http://127.0.0.1:11434")
LOCAL_MODEL_NAME = os.getenv("SAD_LOCAL_MODEL", "")


def build_system_prompt(user_name, adult_mode=False):
    name = user_name or "the user"
    prompt = (
        "You are Sasha, a local dialogue assistant. "
        f"You are speaking with {name}. Keep responses concise, natural, and helpful. "
        "Do not claim to change files, run tools, or take actions unless the user "
        "has explicitly asked and the application confirms it."
    )
    prompt = f"{prompt}\n\n{build_sasha_voice(user_name)}"
    if adult_mode:
        from private.adult_mode import adult_mode_rules

        prompt = f"{prompt}\n\n{adult_mode_rules()}"
    return prompt


def local_model_is_configured():
    """A model name must be explicitly configured before any request is made."""
    return bool(LOCAL_MODEL_NAME)


def local_model_is_available():
    """Check a local Ollama-compatible endpoint without sending conversation data."""
    if not local_model_is_configured():
        return False

    try:
        with urlopen(f"{LOCAL_MODEL_URL}/api/tags", timeout=1) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


def generate_local_response(message, user_name, history, adult_mode=False):
    """Generate a reply locally, returning None when the local service is unavailable."""
    if not local_model_is_available():
        return None

    prompt_history = "\n".join(
        f"{speaker}: {text}" for speaker, text in history[-6:]
    )
    prompt = (
        f"{build_system_prompt(user_name, adult_mode)}\n\n"
        f"Recent conversation:\n{prompt_history}\n"
        f"User: {message}\nSasha:"
    )
    payload = json.dumps(
        {"model": LOCAL_MODEL_NAME, "prompt": prompt, "stream": False}
    ).encode("utf-8")
    request = Request(
        f"{LOCAL_MODEL_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "").strip() or None
    except (OSError, URLError, json.JSONDecodeError):
        return None
