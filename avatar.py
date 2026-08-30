"""Sasha avatar core: a provider-neutral visual + audio presence for SAD Chat.

This module carries no account, tool, coding, repair, network, or Git authority. It only
describes how the browser should render Sasha and turns reply text into a coarse mouth
timeline the browser uses when it cannot measure spoken audio amplitude directly.
"""

from __future__ import annotations

AVATAR_STATES = ("idle", "listening", "thinking", "speaking")
DEFAULT_STATE = "idle"

_TRANSITIONS = {
    "focus": "listening", "user_typing": "listening", "blur": "idle",
    "submit": "thinking", "reply": "speaking", "speech_end": "idle",
    "stop": "idle", "error": "idle", "reset": "idle",
}

_OPEN_VOWELS = set("aeiouyAEIOUY")
_CLOSED = set(" \t\n.,;:!?-—…\"'()[]")
MAX_MOUTH_FRAMES = 4000
_FRAME_MS = 55

COMPANION_STAGE_TITLES = ("Initiate", "Apprentice", "Journeyman", "Expert", "Master")
COMPANION_STAGE_ACCENTS = ("#6ee7b7", "#7ddccf", "#8ad0f0", "#c7b3f5", "#f6c76b")


def next_avatar_state(current: str, event: str) -> str:
    """Return the next avatar state, or the unchanged state for an unknown pairing."""
    if current not in AVATAR_STATES:
        current = DEFAULT_STATE
    target = _TRANSITIONS.get(event)
    if target is None:
        return current
    if event in {"focus", "user_typing"} and current in {"thinking", "speaking"}:
        return current
    return target


def mouth_shapes_for_text(text: str):
    """Coarse per-character mouth timeline: open on vowels, mid on voiced consonants,
    closed on spacing and punctuation. Bounded so a long reply cannot balloon the frame
    list. Deterministic; the browser uses live audio amplitude when it is available."""
    if not isinstance(text, str) or not text.strip():
        return []
    frames = []
    for char in text.strip()[:MAX_MOUTH_FRAMES]:
        if char in _OPEN_VOWELS:
            frames.append({"shape": "open", "weight": 1.0, "ms": _FRAME_MS})
        elif char in _CLOSED:
            frames.append({"shape": "closed", "weight": 0.0, "ms": _FRAME_MS})
        elif char.isalnum():
            frames.append({"shape": "mid", "weight": 0.45, "ms": _FRAME_MS})
    return frames


def estimated_speech_ms(text: str) -> int:
    """Rough spoken duration used to drive the fallback animation when no voice plays."""
    frames = mouth_shapes_for_text(text)
    return sum(frame["ms"] for frame in frames) if frames else 0


def companion_stage_appearance(stage) -> dict:
    """Face accent + label for a Forge companion stage (0-4), clamped for out-of-range."""
    index = stage if isinstance(stage, int) and 0 <= stage <= 4 else 0
    return {
        "stage": index, "title": COMPANION_STAGE_TITLES[index],
        "accent": COMPANION_STAGE_ACCENTS[index], "css_class": f"stage-{index}",
    }


def companion_persona(stage) -> str:
    """Coaching guidance that keeps Sasha honest about a student's Forge rank."""
    look = companion_stage_appearance(stage)
    return (
        f"Sasha is coaching a Forge student at the {look['title']} rank. Celebrate real "
        "mastery without inflating it, keep the next challenge honest, and never imply the "
        "student passed a boss check they have not passed."
    )


def sasha_avatar_descriptor() -> dict:
    """JSON-safe description of Sasha's presence for the browser renderer."""
    return {
        "name": "Sasha",
        "is_persona_not_person": True,
        "renderer": "browser_svg",
        "states": list(AVATAR_STATES),
        "default_state": DEFAULT_STATE,
        "audio": {"microphone_capture": False, "speaker_playback": True, "source": "loopback_tts_or_browser_speech"},
        "palette": {"skin": "#163329", "accent": "#6ee7b7", "line": "#294139", "ink": "#f3f7f5"},
        "companion_stages": [companion_stage_appearance(index) for index in range(5)],
        "notes": "Chat text stays the announced source of truth; the avatar never captures a microphone.",
    }
