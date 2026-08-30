import json
import tempfile
import unittest
from pathlib import Path

from api import RawResponse, SadApiService
from auth import AuthService
from avatar import (
    AVATAR_STATES,
    MAX_MOUTH_FRAMES,
    companion_persona,
    companion_stage_appearance,
    estimated_speech_ms,
    mouth_shapes_for_text,
    next_avatar_state,
    sasha_avatar_descriptor,
)
from browser_voice import browser_microphone_enabled, browser_permissions_policy

ROOT = Path(__file__).parent
WEB = ROOT / "web"


class AvatarStateMachineTests(unittest.TestCase):
    def test_events_move_through_the_expected_states(self):
        self.assertEqual(next_avatar_state("idle", "focus"), "listening")
        self.assertEqual(next_avatar_state("listening", "submit"), "thinking")
        self.assertEqual(next_avatar_state("thinking", "reply"), "speaking")
        self.assertEqual(next_avatar_state("speaking", "speech_end"), "idle")
        self.assertEqual(next_avatar_state("listening", "error"), "idle")

    def test_typing_does_not_interrupt_thinking_or_speaking(self):
        self.assertEqual(next_avatar_state("thinking", "user_typing"), "thinking")
        self.assertEqual(next_avatar_state("speaking", "focus"), "speaking")

    def test_unknown_event_or_state_is_safe(self):
        self.assertEqual(next_avatar_state("speaking", "does_not_exist"), "speaking")
        self.assertEqual(next_avatar_state("bogus", "reset"), "idle")
        self.assertIn(next_avatar_state("bogus", "unknown"), AVATAR_STATES)


class MouthTimelineTests(unittest.TestCase):
    def test_empty_or_blank_text_has_no_frames(self):
        self.assertEqual(mouth_shapes_for_text(""), [])
        self.assertEqual(mouth_shapes_for_text("   \n"), [])
        self.assertEqual(mouth_shapes_for_text(None), [])
        self.assertEqual(estimated_speech_ms(""), 0)

    def test_vowels_open_and_spaces_close_the_mouth(self):
        shapes = [frame["shape"] for frame in mouth_shapes_for_text("a b")]
        self.assertEqual(shapes[0], "open")
        self.assertEqual(shapes[1], "closed")
        self.assertEqual(shapes[2], "mid")

    def test_timeline_is_deterministic_and_bounded(self):
        long_text = "la " * 5000
        first = mouth_shapes_for_text(long_text)
        self.assertEqual(first, mouth_shapes_for_text(long_text))
        self.assertLessEqual(len(first), MAX_MOUTH_FRAMES)
        self.assertGreater(estimated_speech_ms("hello there"), 0)


class CompanionStageTests(unittest.TestCase):
    def test_appearance_is_clamped_and_titled(self):
        self.assertEqual(companion_stage_appearance(0)["title"], "Initiate")
        self.assertEqual(companion_stage_appearance(4)["css_class"], "stage-4")
        self.assertEqual(companion_stage_appearance(9)["stage"], 0)
        self.assertEqual(companion_stage_appearance("nope")["stage"], 0)

    def test_persona_never_implies_an_unearned_pass(self):
        text = companion_persona(2)
        self.assertIn("Journeyman", text)
        self.assertIn("boss check", text)


class DescriptorTests(unittest.TestCase):
    def test_descriptor_is_json_safe_and_declares_no_microphone(self):
        descriptor = sasha_avatar_descriptor()
        json.dumps(descriptor)
        self.assertEqual(descriptor["name"], "Sasha")
        self.assertTrue(descriptor["is_persona_not_person"])
        self.assertFalse(descriptor["audio"]["microphone_capture"])
        self.assertTrue(descriptor["audio"]["speaker_playback"])
        self.assertEqual(tuple(descriptor["states"]), AVATAR_STATES)
        self.assertEqual(len(descriptor["companion_stages"]), 5)


class BrowserMicrophoneGateTests(unittest.TestCase):
    def test_microphone_is_disabled_by_default(self):
        self.assertFalse(browser_microphone_enabled({}))
        self.assertIn("microphone=()", browser_permissions_policy({}))

    def test_microphone_needs_an_explicit_host_opt_in(self):
        self.assertFalse(browser_microphone_enabled({"SAD_BROWSER_MIC": "maybe"}))
        self.assertTrue(browser_microphone_enabled({"SAD_BROWSER_MIC": "1"}))
        policy = browser_permissions_policy({"SAD_BROWSER_MIC": "true"})
        self.assertIn("microphone=(self)", policy)
        self.assertNotIn("microphone=(*)", policy)


class FakeVoiceRuntime:
    def __init__(self, ready=True):
        self.ready = ready
        self.spoken = []

    def status(self):
        return {"tts_configured": self.ready, "tts_ready": self.ready, "microphone_capture": False}

    def tts_configured(self):
        return self.ready

    def synthesize_wav(self, text):
        self.spoken.append(text)
        return b"RIFF----WAVEfmt "


class AvatarVoiceApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        auth = AuthService(Path(self.temp.name) / "accounts.json")
        auth.bootstrap_owner("owner", "StrongOwner123", True)
        self.token = auth.login("owner", "StrongOwner123")
        self.voice = FakeVoiceRuntime()
        self.service = SadApiService(auth, voice=self.voice)

    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def test_status_reports_tts_readiness_and_browser_microphone(self):
        status, payload = self.service.dispatch("GET", "/v1/voice/status", self.headers(), {})
        self.assertEqual(status, 200)
        self.assertTrue(payload["tts_ready"])
        self.assertFalse(payload["browser_microphone"])

    def test_speak_returns_wav_bytes_from_the_loopback_service(self):
        status, payload = self.service.dispatch("POST", "/v1/voice/speak", self.headers(), {"text": "Hello"})
        self.assertEqual(status, 200)
        self.assertIsInstance(payload, RawResponse)
        self.assertEqual(payload.content_type, "audio/wav")
        self.assertEqual(self.voice.spoken, ["Hello"])

    def test_speak_rejects_empty_text_and_unconfigured_tts(self):
        with self.assertRaises(ValueError):
            self.service.dispatch("POST", "/v1/voice/speak", self.headers(), {"text": "  "})
        self.service.voice = FakeVoiceRuntime(ready=False)
        with self.assertRaises(KeyError):
            self.service.dispatch("POST", "/v1/voice/speak", self.headers(), {"text": "Hi"})

    def test_speak_requires_authentication(self):
        with self.assertRaises(PermissionError):
            self.service.dispatch("POST", "/v1/voice/speak", {}, {"text": "Hello"})


class AvatarWebAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = (WEB / "avatar.js").read_text(encoding="utf-8")
        cls.css = (WEB / "avatar.css").read_text(encoding="utf-8")
        cls.chat_js = (WEB / "chat.js").read_text(encoding="utf-8")
        cls.app_js = (WEB / "app.js").read_text(encoding="utf-8")
        cls.mobile_js = (WEB / "mobile.js").read_text(encoding="utf-8")
        cls.sw = (WEB / "sw.js").read_text(encoding="utf-8")

    def test_assets_exist_and_are_small(self):
        self.assertLess(len(self.js), 20_000)
        self.assertLess(len(self.css), 8_000)

    def test_avatar_never_touches_a_microphone_or_third_party_host(self):
        for needle in ("http://", "https://", "getUserMedia", "mediaDevices",
                       "MediaRecorder", "navigator.permissions"):
            self.assertNotIn(needle, self.js, needle)

    def test_avatar_audio_is_loopback_tts_then_browser_speech(self):
        self.assertIn("/v1/voice/speak", self.js)
        self.assertIn("/v1/voice/status", self.js)
        self.assertIn("speechSynthesis", self.js)
        self.assertIn("SpeechSynthesisUtterance", self.js)
        self.assertIn("createAnalyser", self.js)

    def test_avatar_respects_reduced_motion_and_stays_aria_hidden(self):
        self.assertIn("prefers-reduced-motion", self.js)
        self.assertIn("prefers-reduced-motion", self.css)
        self.assertIn('aria-hidden', self.js)

    def test_avatar_surface_is_registered_and_precached(self):
        self.assertIn('avatar:{css:"/ui/avatar.css",js:"/ui/avatar.js"}', self.mobile_js)
        self.assertIn('loadSurface("avatar")', self.mobile_js)
        self.assertIn("/ui/avatar.js", self.sw)
        self.assertIn("/ui/avatar.css", self.sw)

    def test_chat_and_forge_drive_the_avatar(self):
        self.assertIn('window.SadAvatar?.setState("thinking")', self.chat_js)
        self.assertIn("window.SadAvatar?.speak(data.reply)", self.chat_js)
        self.assertIn('window.SadAvatar?.setState("idle")', self.chat_js)
        self.assertIn("window.SadAvatar?.setCompanionStage(stage)", self.app_js)


if __name__ == "__main__":
    unittest.main()
