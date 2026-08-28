"""End-to-end local Voice turn orchestration for SAD.

Input/output are WAV bytes. Microphone capture and speaker playback belong to the future
OS/client shell, not to the platform authority layer.
"""

from __future__ import annotations

from voice_runtime import VoiceRuntime


class SadVoiceClient:
    def __init__(self, sad_client, runtime=None):
        if not hasattr(sad_client, "request"):
            raise ValueError("SAD Voice requires an authenticated SAD user client.")
        self.sad = sad_client
        self.runtime = runtime or VoiceRuntime()

    def turn(self, wav_audio, *, session_id=None, use_memory=True, synthesize=True):
        transcript = self.runtime.transcribe_wav(wav_audio)
        payload = {"transcript": transcript, "use_memory": bool(use_memory)}
        if session_id:
            payload["session_id"] = session_id
        response = self.sad.request("POST", "/v1/voice/turn", payload)
        if not isinstance(response, dict) or not isinstance(response.get("speech_text"), str):
            raise ValueError("SAD Voice endpoint returned an invalid response.")
        output = {
            "session_id": response.get("session_id"),
            "transcript": transcript,
            "reply": response.get("reply", response["speech_text"]),
            "speech_text": response["speech_text"],
            "engine": response.get("engine"),
            "memory_used": bool(response.get("memory_used")),
            "wav_audio": None,
        }
        if synthesize:
            output["wav_audio"] = self.runtime.synthesize_wav(output["speech_text"])
        return output
