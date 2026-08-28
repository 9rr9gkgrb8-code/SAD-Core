import io
import json
import unittest
from urllib.request import Request

from voice_client import SadVoiceClient
from voice_runtime import VoiceRuntime, validated_voice_service_url


class FakeResponse:
    def __init__(self, payload, *, status=200, content_type="application/json"):
        self.payload = payload
        self.status = status
        self.headers = {"Content-Type": content_type}

    def read(self, _limit=-1):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class VoiceRuntimeTests(unittest.TestCase):
    def test_voice_services_are_loopback_only(self):
        self.assertEqual(validated_voice_service_url("http://127.0.0.1:9001", "STT URL"), "http://127.0.0.1:9001")
        for value in [
            "https://127.0.0.1:9001", "http://192.168.1.5:9001", "http://example.com",
            "http://user:pass@127.0.0.1:9001", "http://127.0.0.1:9001/path",
        ]:
            with self.assertRaises(ValueError):
                validated_voice_service_url(value, "voice URL")

    def test_transcription_and_synthesis_use_fixed_local_contracts(self):
        calls = []

        def opener(request, timeout):
            calls.append((request, timeout))
            if isinstance(request, str):
                return FakeResponse(json.dumps({"status": "ok"}).encode())
            self.assertIsInstance(request, Request)
            if request.full_url.endswith("/v1/stt"):
                self.assertEqual(request.headers["Content-type"], "audio/wav")
                return FakeResponse(json.dumps({"text": "hello SAD"}).encode())
            if request.full_url.endswith("/v1/tts"):
                return FakeResponse(b"RIFFfakewav", content_type="audio/wav")
            raise AssertionError(request.full_url)

        runtime = VoiceRuntime("http://127.0.0.1:9001", "http://localhost:9002", opener=opener)
        self.assertTrue(runtime.status()["stt_ready"])
        self.assertTrue(runtime.status()["tts_ready"])
        self.assertEqual(runtime.transcribe_wav(b"RIFFinput"), "hello SAD")
        self.assertEqual(runtime.synthesize_wav("reply"), b"RIFFfakewav")
        self.assertTrue(all(timeout <= 30 for _request, timeout in calls))

    def test_voice_client_runs_audio_to_sad_to_audio_without_extra_authority(self):
        class Runtime:
            def transcribe_wav(self, audio):
                self.audio_in = audio
                return "What is my task?"

            def synthesize_wav(self, text):
                self.text_out = text
                return b"RIFFreply"

        class Sad:
            def __init__(self):
                self.calls = []

            def request(self, method, path, payload):
                self.calls.append((method, path, payload))
                return {
                    "session_id": "s1", "reply": "Your task is ready.",
                    "speech_text": "Your task is ready.", "engine": "local_model", "memory_used": True,
                }

        sad = Sad()
        runtime = Runtime()
        result = SadVoiceClient(sad, runtime).turn(b"RIFFinput", use_memory=False)
        self.assertEqual(result["wav_audio"], b"RIFFreply")
        self.assertEqual(sad.calls, [("POST", "/v1/voice/turn", {"transcript": "What is my task?", "use_memory": False})])
        self.assertEqual(runtime.text_out, "Your task is ready.")


if __name__ == "__main__":
    unittest.main()
