# SAD + Forge v0.5.0-beta.1

**Public Beta / pre-release. Not production-ready.**

SAD is a local-first, human-governed AI platform. Forge is its game-first learning surface. This Beta is intended for evaluation, testing, feedback, and controlled local use.

## What to try

- SAD Chat and visible local-model/fallback behavior.
- Explicit Personal Memory.
- Governed Tool Actions with exact-argument approval for state changes.
- Owner/Developer failure evidence and controlled repair workflow.
- Forge quests, progressive hints, mastery checks, XP/ranks/companion progression, homework/study/check-work flows, and persistent student progress.
- Paired Mobile access in the documented private-TLS boundary.
- Native and portable encrypted backup/recovery workflows.

## The boundary that matters

Beta does not give agents unrestricted shell, Git, credential, network, package-install, or live-code authority. Coding and repair remain scoped, isolated, verified, diff-visible, and subject to human disposition.

## Known Beta limitations

- Physical Windows/device acceptance is separate from CI and must be performed on the evaluator's hardware.
- Voice depends on configured local loopback STT/TTS services and real microphone/speaker UAT.
- Mobile requires the documented private-network/TLS/pairing setup.
- Local-model tutoring quality varies by the configured model. Advanced factual or mathematical answers should not be treated as infallible when independent verification is unavailable.
- This release is not intended for production or unattended high-impact automation.

## Feedback

When reporting a problem, include the failing workflow, expected result, actual result, platform/environment, and privacy-safe failure evidence. Never post credentials, private runtime data, student PII, `.env` contents, backup passphrases, or encryption/recovery secrets.

See `BETA.md`, `BETA_ACCEPTANCE.md`, `ALPHA_STABLE.md`, and the security/operator documentation before evaluating the release.
