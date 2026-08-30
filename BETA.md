# SAD + Forge Beta Launch Contract

Beta means a new evaluator can clone SAD-Core, install it, launch it, exercise SAD and Forge's major user workflows, encounter failures safely, and understand how to report/recover without the project owner manually repairing the session.

Beta does **not** mean production-ready, unattended autonomy, or permission to widen SAD's human-governed authority boundaries.

## Beta release target

Initial public prerelease target: `v0.5.0-beta.1`.

The tag/release must not be published until the automated Beta gate passes and the human acceptance items below are explicitly recorded.

## SAD Beta contract

- Clean Windows installation and first-run path is documented and reproducible.
- Chat launches and clearly identifies local-model versus built-in fallback behavior.
- Voice transcript transport works; physical microphone/speaker behavior remains a human UAT item.
- Personal Memory remains explicit, account-owned, disableable, expirable, and never silently populated from ordinary chat.
- Memory context selection is observable and bounded when the context-ladder feature is integrated.
- State-changing Tool Actions remain approval-bound to exact arguments.
- Owner/Developer dashboard surfaces failure evidence and correction/repair proposals without granting workers merge/publish authority.
- Controlled repair remains isolated, independently verified, diff-visible, Owner-approved, and rollback-capable.
- Mobile remains paired/private-TLS with machine-client boundaries preserved.
- Native and portable backup/restore paths remain verified and fail closed.
- Accounts/RBAC, bounded HTTP admission, persistence protection, Protocol Black, supply-chain pinning, and release integrity remain green.

## Forge Beta contract

- A student can start a lesson/quest from a learning objective or homework request.
- Lessons use game-first progression rather than a plain chat-only tutoring loop.
- Progressive hints teach method before revealing a final answer where appropriate.
- Mastery checks and check-work flows are available without an arbitrary three-question ceiling.
- XP, ranks, companion evolution, and durable per-student progress remain functional.
- Math/science/factual uncertainty is surfaced rather than presented as guaranteed correctness when verification is unavailable.
- Essay support can explain, review, edit, provide examples, and help meet legitimate assignment requirements without falsely claiming external authorship or verification.
- Child-facing injection/PII screening and privacy-minimized failure reporting remain enforced.
- Forge failures/results can reach the shared Owner/Developer evidence flow without giving Forge authority to modify live SAD code.
- Desktop and paired-mobile learning paths remain covered by regression tests and human UAT.

## Beta evaluator journey

A release candidate must support this end-to-end journey:

1. Clone a clean copy of the tagged candidate.
2. Install pinned requirements.
3. Run preflight/readiness checks.
4. Launch SAD on the supported Windows host.
5. Sign in and use Chat.
6. Create and retrieve an explicit Personal Memory.
7. Exercise a governed mutating Tool Action and verify exact-argument approval.
8. Start a Forge learning quest and complete a hint/mastery/progress cycle.
9. Trigger or replay a safe test failure and verify dashboard evidence.
10. Produce a controlled repair proposal in isolation.
11. Verify exact diff plus Owner approve/reject behavior.
12. Restart and confirm protected state persists.
13. Create and verify a backup; perform the documented recovery drill in the appropriate test environment.

## Automated release gate

The existing Alpha contract remains mandatory. Beta candidates must run at least:

```text
python -m compileall -q .
python -m unittest -v
python protocol_black.py
python release_gate.py
python alpha_stable.py
python alpha_doctor.py
python windows_doctor.py
python docker_proof.py
```

A future `beta_gate.py` must fail closed over Beta-specific required files/tests and must never convert physical-device or human acceptance into a fake automated pass.

## Human acceptance required before public Beta

The release owner must explicitly verify on intended hardware:

- Windows 11 host startup and shutdown.
- BitLocker/recovery-key custody where BitLocker is part of the deployment boundary.
- Real microphone and speaker Voice UAT.
- Real phone certificate trust, pairing, reconnect, and logout/revocation behavior.
- Owner and Developer dashboard usability.
- Student/teacher/owner role boundaries with real accounts.
- Forge lesson usability, hints, mastery, progress persistence, and mobile experience.
- Native backup recovery and a cross-profile portable recovery drill.
- LAN/router exposure and TLS configuration.
- Accessibility smoke test with keyboard navigation and readable focus/state cues.

These items are recorded as human evidence. They are never inferred from CI.

## Public Beta packaging

Before tagging the first Beta candidate, the repository should contain:

- `README.md` with screenshots or a real demo captured from the running product.
- this `BETA.md` contract;
- a concise first-run/install path;
- troubleshooting guidance for common startup/model/Docker/TLS failures;
- security reporting guidance;
- contribution guidance if outside pull requests are desired;
- release notes describing known limitations and explicit non-production status.

## Release rule

`v0.5.0-beta.1` is a GitHub **pre-release**. It is not marked production-ready. Any failure in an authority, security, persistence, recovery, account isolation, or release-integrity gate blocks publication until resolved.
