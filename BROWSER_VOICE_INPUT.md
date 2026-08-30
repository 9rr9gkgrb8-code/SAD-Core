# Browser Voice Input — reviewed milestone (not yet enabled)

`VOICE.md` proves the audio transport and orchestration contract. It deliberately does
**not** turn on microphone capture in the browser. This document tracks the separate
milestone that would, and the human review and UAT it must pass first.

## Current state

- The SAD Chat UI ships **no** microphone capture code. `web/avatar.js` contains no
  `getUserMedia`, `mediaDevices`, or `MediaRecorder`; `test_avatar.py` enforces that.
- The UI `Permissions-Policy` header is decided by `browser_voice.py`:
  - default — `camera=(), microphone=(), geolocation=()` (capture blocked outright).
  - `SAD_BROWSER_MIC=1` on the deployment host — `microphone=(self)` (same-origin only,
    never `*`). This flag only changes the header; it ships no capture code.
- The paired **mobile gateway keeps microphone hard-disabled** regardless of the flag.
- `GET /v1/voice/status` reports `browser_microphone` so a future UI can show or hide a
  push-to-talk control without guessing.

## What the milestone must add

1. A push-to-talk control in SAD Chat (press-and-hold, never always-listening), gated on
   `voice/status.browser_microphone` and `stt_ready`.
2. Capture to a bounded WAV, posted to a new authenticated audio-in endpoint that feeds
   `voice_runtime.transcribe_wav` then the existing `/v1/voice/turn` flow. Request size
   and duration are bounded; audio is never persisted.
3. A visible in-progress indicator and an immediate, obvious way to stop and discard.
4. Learning-mode phones stay excluded until a further review.

## Review gate (all required before `SAD_BROWSER_MIC` is documented as supported)

- [ ] Threat review: origin binding, DNS-rebinding, autoplay/permission-prompt abuse,
      and that a revoked STT service fails closed.
- [ ] Privacy review: no audio at rest, no audio in events/logs, child-facing consent
      copy reviewed.
- [ ] Accessibility review: keyboard operable, captions, reduced-motion, screen-reader
      announcements.
- [ ] Human UAT on real Windows + a real STT service: capture, transcribe, turn, stop,
      deny-permission, and offline paths.
- [ ] `SECURITY.md` and `VOICE.md` updated to describe the enabled capability.
