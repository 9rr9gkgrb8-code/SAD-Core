"""Loopback-only speech-to-text and text-to-speech adapters for SAD Voice.

The adapter intentionally speaks only to explicitly configured HTTP services on the
same machine. It does not capture microphones, play speakers, spawn processes, or make
arbitrary network requests.
"""

from __future__ import annotations

import json
import os
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


STT_URL = os.getenv("SAD_STT_URL", "")
TTS_URL = os.getenv("SAD_TTS_URL", "")
MAX_AUDIO_INPUT_BYTES = 8_000_000
MAX_AUDIO_OUTPUT_BYTES = 16_000_000
MAX_TRANSCRIPT_BYTES = 256_000
MAX_TTS_TEXT = 20_000
VOICE_TIMEOUT_SECONDS = 30


def validated_voice_service_url(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is not configured.")
    raw = value.strip().rstrip("/")
    parsed = urlparse(raw)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError(f"{label} must use HTTP on the loopback interface.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError(f"{label} cannot contain credentials, a path, query, or fragment.")
    if parsed.port is not None and not 1 <= parsed.port <= 65535:
        raise ValueError(f"{label} has an invalid port.")
    return raw


class VoiceRuntime:
    """Provider-neutral local speech adapter using a tiny reviewed HTTP contract."""

    def __init__(self, stt_url=None, tts_url=None, opener=None):
        self.stt_url = STT_URL if stt_url is None else stt_url
        self.tts_url = TTS_URL if tts_url is None else tts_url
        self.opener = opener or urlopen

    def stt_configured(self):
        try:
            validated_voice_service_url(self.stt_url, "STT URL")
            return True
        except ValueError:
            return False

    def tts_configured(self):
        try:
            validated_voice_service_url(self.tts_url, "TTS URL")
            return True
        except ValueError:
            return False

    def _health(self, base, label):
        try:
            base = validated_voice_service_url(base, label)
            with self.opener(f"{base}/health", timeout=2) as response:
                raw = response.read(64_001)
                if len(raw) > 64_000 or response.status != 200:
                    return False
                payload = json.loads(raw.decode("utf-8"))
                return payload.get("status") in {"ok", "ready"}
        except (OSError, URLError, ValueError, json.JSONDecodeError):
            return False

    def status(self):
        return {
            "stt_configured": self.stt_configured(),
            "stt_ready": self._health(self.stt_url, "STT URL") if self.stt_configured() else False,
            "tts_configured": self.tts_configured(),
            "tts_ready": self._health(self.tts_url, "TTS URL") if self.tts_configured() else False,
            "transport": "loopback_http",
            "microphone_capture": False,
            "speaker_playback": False,
        }

    def transcribe_wav(self, audio):
        if not isinstance(audio, (bytes, bytearray)) or not audio:
            raise ValueError("Voice audio must be non-empty WAV bytes.")
        audio = bytes(audio)
        if len(audio) > MAX_AUDIO_INPUT_BYTES:
            raise ValueError("Voice audio exceeds the configured input limit.")
        base = validated_voice_service_url(self.stt_url, "STT URL")
        request = Request(
            f"{base}/v1/stt",
            data=audio,
            headers={"Content-Type": "audio/wav", "Accept": "application/json"},
            method="POST",
        )
        try:
            with self.opener(request, timeout=VOICE_TIMEOUT_SECONDS) as response:
                raw = response.read(MAX_TRANSCRIPT_BYTES + 1)
                if response.status != 200 or len(raw) > MAX_TRANSCRIPT_BYTES:
                    raise ValueError("STT service returned an invalid response.")
                payload = json.loads(raw.decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError) as error:
            raise RuntimeError("Local STT service is unavailable.") from error
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_TTS_TEXT:
            raise ValueError("STT service returned an invalid transcript.")
        return text.strip()

    def synthesize_wav(self, text):
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_TTS_TEXT:
            raise ValueError("TTS text must be 1-20000 characters.")
        base = validated_voice_service_url(self.tts_url, "TTS URL")
        request = Request(
            f"{base}/v1/tts",
            data=json.dumps({"text": text.strip(), "format": "wav"}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "audio/wav"},
            method="POST",
        )
        try:
            with self.opener(request, timeout=VOICE_TIMEOUT_SECONDS) as response:
                audio = response.read(MAX_AUDIO_OUTPUT_BYTES + 1)
                content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().casefold()
                if response.status != 200 or content_type != "audio/wav" or not audio or len(audio) > MAX_AUDIO_OUTPUT_BYTES:
                    raise ValueError("TTS service returned invalid WAV audio.")
                return audio
        except (OSError, URLError) as error:
            raise RuntimeError("Local TTS service is unavailable.") from error
