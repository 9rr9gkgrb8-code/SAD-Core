# SAD Voice Runtime

SAD already has an authenticated transcript-to-conversation endpoint at
`POST /v1/voice/turn`. Foundation Stabilization adds a provider-neutral local audio
runtime around that contract without granting speech components account, tool, coding,
repair, or Git authority.

## Audio path

```text
WAV bytes
  -> loopback STT service /v1/stt
  -> transcript
  -> authenticated SAD /v1/voice/turn
  -> speech_text
  -> loopback TTS service /v1/tts
  -> WAV bytes
```

`voice_client.SadVoiceClient` orchestrates that flow for an already authenticated SAD
user client. It does not capture a microphone or play a speaker. Those OS/client actions
remain an explicit deployment milestone.

## STT contract

Configure:

```text
SAD_STT_URL=http://127.0.0.1:<port>
```

The configured value must be HTTP on `127.0.0.1`, `localhost`, or `::1`, with no
credentials, path, query, or fragment.

SAD calls:

- `GET /health` -> JSON with `status` equal to `ok` or `ready`.
- `POST /v1/stt` with `Content-Type: audio/wav` -> JSON `{ "text": "..." }`.

Input and transcript sizes are bounded and calls time out.

## TTS contract

Configure:

```text
SAD_TTS_URL=http://127.0.0.1:<port>
```

SAD calls:

- `GET /health` -> JSON with `status` equal to `ok` or `ready`.
- `POST /v1/tts` with JSON `{ "text": "...", "format": "wav" }` -> `audio/wav`.

Text and audio output sizes are bounded and calls time out.

## Security boundary

Voice services are treated as replaceable local infrastructure, not SAD principals.
They receive only the audio/text needed for the requested turn. They receive no SAD
password/session token, app credential, tool approval, filesystem access, Docker access,
or Git authority from `voice_runtime.py`.

The browser Permissions Policy still disables direct microphone access. Enabling browser
microphone capture requires a separate reviewed client/UAT milestone tracked in
`BROWSER_VOICE_INPUT.md`. The code in this milestone proves the audio transport/orchestration
contract, not the physical microphone or speaker on a particular computer/phone.

## Reply audio for the browser (Beta)

`GET /v1/voice/status` reports STT/TTS readiness and whether browser microphone input is
enabled. `POST /v1/voice/speak` with `{ "text": "..." }` returns `audio/wav` synthesized by
the same loopback TTS service, so the SAD Chat avatar can speak replies. When the TTS
service is not configured the avatar falls back to the browser's built-in speech synthesis.
Neither path adds microphone, account, tool, coding, repair, or Git authority.
