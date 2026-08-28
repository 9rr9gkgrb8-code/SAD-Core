# SAD + Forge milestone status

Updated: August 27, 2026

## Current architecture

**SAD is the platform.** SAD Chat, Voice, Personal Study, Forge Learning, Developer
Workspace, controlled repair, accounts/roles, and Mobile are governed SAD platform
surfaces. Forge is not required to become a separate repository for the current Alpha
architecture.

A prior Protocol White run remains truthfully recorded as blocked at its historical
Gate 2 because that legacy protocol expected an independent `Forge-Core` service. That
separate-service topology is paused under the current SAD-as-platform direction, not
retroactively marked as passing.

## Platform milestone

Current Platform Core version: **`0.2-alpha`**

Platform manifest schema: **`2`**

Core API contract: **`v1`**

### Platform Core completed

- One declarative `PlatformRegistry` describes SAD modules, capabilities, routes,
  permissions, state mutation, human approval boundaries, capability versions, and
  lifecycle state.
- Human discovery endpoints are authenticated and role-filtered:
  - `GET /v1/platform`
  - `GET /v1/platform/modules`
  - `GET /v1/platform/capabilities`
  - `POST /v1/platform/compatibility`
- `/health` keeps its established minimal `{status, api_version}` response for backward
  compatibility.
- Capability compatibility negotiation reports availability/version only within the
  requesting principal's existing authority. Hidden capabilities remain unavailable.
- Dynamic extension/plugin execution remains disabled. Platform metadata cannot execute
  Python/JavaScript/shell code, install packages, or mutate Git.
- SAD Platform browser surface shows module/capability versions, lifecycle, permission,
  mutation, and human-approval markers.

### Tier 2 local-app identity completed

- Owner-only `platform:manage` controls local machine-client registration.
- Machine credentials use a distinct `SAD-App <client-id>.<secret>` scheme and never
  become human Bearer sessions.
- Allowed machine scopes are deliberately limited to:
  - `platform:discover`
  - `platform:catalog`
  - `platform:modules`
  - `platform:compatibility`
  - `platform:events`
- App secrets are high-entropy, returned only at creation/rotation, salted/hashed at
  rest, rotatable, and revocable.
- Listing an app never returns its live secret, hash, or salt.
- Unknown or duplicate scopes fail closed.
- Machine clients cannot Chat, use Voice, Study, play Forge, run/apply Developer
  Workspace, approve/apply repairs, administer accounts/devices, or perform Git work.
- Machine endpoints stay on the loopback core API under `/v1/platform/client/*`.
- The mobile gateway rejects the machine-client endpoint family even for Full Role
  paired devices.
- `platform_clients.json` is private Git-ignored runtime data and excluded from release
  source scanning.

### Tier 2 platform events completed

- `PlatformEventStore` provides a bounded durable metadata-only event stream with
  monotonic sequence numbers and cursors.
- Exact Owner-approved event subscriptions are stored per app.
- Empty subscription means no events, never all events.
- Unknown event types fail closed.
- Current event types cover Chat session/message metadata, Developer Workspace state,
  failures, Forge quest lifecycle, app credential lifecycle, and Voice turn completion.
- Event payloads deliberately omit conversation text, prompts, generated code, diffs,
  passwords, tokens, app/device secrets, student work, and other high-value payloads.
- Event details and total history are size-bounded.
- `platform_events.json` is private Git-ignored runtime data and excluded from release
  source scanning.
- Event logging is auxiliary: an event-store write problem is surfaced diagnostically
  but does not corrupt or falsely roll back a primary action that already completed.

### Voice Client Bridge completed

- `POST /v1/voice/turn` is a signed-in transcript-to-conversation API.
- It uses the same account-owned durable conversation history and local-model/built-in
  fallback as SAD Chat.
- It may continue an existing owned chat session or create a new one.
- It returns `reply`, `speech_text`, response engine, session ID, and explicit
  transcript/text-for-local-TTS mode metadata.
- Voice transport grants no repair, coding, app-management, account, shell, file, or
  Git authority.
- Learning-mode phones may use Voice after pairing and normal login.
- Direct browser microphone capture, STT, and TTS are intentionally not bundled yet;
  the current milestone establishes the stable transport contract.

### Local SDK completed

- `sad_sdk.py` is a standard-library-only synchronous local integration SDK.
- It accepts only loopback SAD Core URLs and rejects remote or credentialed URLs.
- It keeps user-session and machine-client authorization schemes separate.
- It can perform health, user login, human Platform discovery/compatibility/Voice, and
  app manifest/compatibility/event calls.
- It does not persist credentials.
- The security-surface regression test explicitly enumerates it as a reviewed network
  client rather than widening network-module permission generally.

## Existing Alpha capabilities retained

### SAD Chat

- Dedicated free-form multi-turn conversation lane.
- Durable per-account sessions, history, archive, and account isolation.
- Recent-turn context to the configured loopback local model.
- Visible `Local AI` vs `Built-in dialogue` status.
- Conversation text does not grant governed authority.

### Personal Study

- Explanation, method teaching, walkthroughs, checking, hints, direct answers when
  requested, proofreading, essay editing, rubric review, examples, and substantive
  word-count expansion without a forced three-question loop.

### Forge Learning

- Homework-to-quest conversion, progressive hint ladder, mastery/boss gates, XP/ranks,
  companion progression, durable student progress, and game-first browser interface.

### Developer Workspace

- Task → scope suggestion → human-approved paths → multi-file local-model generation →
  digest-pinned networkless/non-root Docker full-suite verification → exact diff/test
  evidence → Owner-only apply/rollback.
- Up to 20 approved text-source paths per Alpha workspace.
- `.git`, `.github`, secrets, runtime data, control-plane paths, hidden paths, and
  unsupported/binary files remain excluded.
- Failed/unavailable isolation cannot become applyable.
- Stale live source or tampered tested worktree blocks application.
- Multi-file apply is transactional with backups and verified whole-set restore.
- Developer can prepare/test but cannot apply; Reviewer/Viewer inspect only;
  Student/Teacher have no Code Workspace authority.
- No Git authority is granted to the coding agent.

### Controlled self-repair

- Failure evidence → human review/push → explicit isolated-work approval → local-model
  single-file repair draft → Docker verification → exact diff/test evidence → human
  decision → Owner-only exact tested local application/rollback.
- Reviewer decision remains evidence-only.
- Forge cannot approve itself and has no Git credentials/authority.

### Accounts and roles

- Student, Teacher, Owner, Developer, Reviewer, Viewer.
- PBKDF2 password hashing, lockout, expiring in-memory sessions, password-change session
  revocation, role-based account creation and management.
- Owner now additionally has `platform:manage`; no lower role receives it.

### Mobile Preview

- Installable PWA shell with phone-first layout, safe areas, install hooks, and
  online/offline status.
- Owner-created one-time 8-digit pair codes, five-minute expiry, single use,
  rate-limited failures, 30-day device expiry, and revocation.
- Paired-device secret is hashed at rest and browser-invisible through a
  Secure/HttpOnly/SameSite=Strict cookie.
- Core SAD API remains loopback-only.
- Mobile gateway is separate TLS 1.2+ on one explicit private/approved overlay IPv4
  address, refusing wildcard/public/hostname/loopback binds.
- Learning mode admits explicit Chat, Voice, account-self, Study, Forge, and own-progress
  routes only.
- Full Role mode preserves normal human RBAC.
- Machine-client endpoints are blocked in both mobile modes.
- PWA never caches `/v1/*` or `/mobile/*` private traffic.

## Automated verification coverage

The repository suite covers, among other areas:

- authentication/role separation;
- Platform registry uniqueness and role filtering;
- capability version negotiation;
- app secret hashing, scope enforcement, rotation, and revocation;
- machine/user credential separation;
- exact event subscription filtering including empty-subscription fail-closed behavior;
- event size/type bounds;
- Voice account-owned conversation behavior;
- mobile Voice allowance and machine-client denial;
- SDK loopback-only networking;
- network/process module allow-listing;
- SAD Chat isolation/persistence;
- Developer Workspace scope, Docker, stale/tamper, transactional apply/rollback;
- repair planning/isolation/application/rollback;
- mobile pairing/bind/cache/privacy controls;
- browser accessibility structure;
- release-integrity required paths and private-runtime exclusions.

CI compiles Python, syntax-checks all browser JavaScript, runs the full unit/security/UI
suite, runs the Alpha release gate/operator preflight, then performs the digest-pinned
Docker isolation proof.

## Remaining operational work

### Deployment host

- Repeat Docker isolation proof on the actual Windows deployment computer using the
  reviewed image for that host.
- Configure and validate the intended local AI model on the deployment computer.
- Exercise a real Developer Workspace generation/test/apply/rollback cycle on a
  disposable or backed-up working copy.
- Exercise controlled repair on the deployment host.

### Platform Tier 2 human UAT

- Create an Owner local-app credential and verify the secret is visible only once.
- Verify list output never reveals secret/hash/salt.
- Rotate and prove the previous secret immediately fails.
- Revoke and prove the current secret fails.
- Prove Student/Teacher/Developer/Reviewer/Viewer cannot mint app credentials.
- Prove a machine credential cannot be used as a Bearer user session.
- Verify a machine app reads only its approved event types and an empty subscription
  yields no events.
- Verify compatibility negotiation hides unowned capabilities.
- Run the Python SDK from a real local companion process and confirm remote base URLs
  are rejected.
- Run a real Voice transcript turn with the intended local model and confirm the same
  account owns/continues the resulting Chat session.

### Human Alpha UAT

- Run representative Owner, Developer, Reviewer, Viewer, Teacher, and Student scenarios.
- Perform keyboard-only, screen-reader, 200% zoom, and narrow-viewport checks.
- Verify Platform app/event controls are usable and secrets are not accidentally
  retained by browser/PWA cache.

### Mobile host/phone UAT

- Provision phone-trusted TLS material and require `MOBILE GATEWAY: READY`.
- Pair/test iPhone and Android combinations intended to be claimed.
- Verify Chat and Voice transcript transport, learning-mode denial of Platform admin,
  coding, dashboard, account, repair, and machine-client endpoints.
- Verify Full Role human RBAC and explicit machine-client denial.
- Verify revoke/forget/reconnect/install/offline behavior and narrow-screen usability.

### Later platform work, not current Alpha claims

- Direct microphone capture in an approved browser/native client.
- Reviewed local STT/TTS engines.
- Richer local event delivery/subscription mechanisms.
- A separately sandboxed dynamic plugin/extension execution model, if desired.
- Plugin marketplace/package installation.
- Public-internet app credentials or hosted identity/secrets/recovery.

## Verification gate

For current SAD Platform Alpha run:

- `python -m compileall -q .`
- `python -m unittest -v`
- `python release_gate.py`
- `python alpha_doctor.py`
- `python docker_proof.py` when automatic-code readiness is claimed
- `python mobile_doctor.py` on the actual configured mobile host before mobile readiness
- `ALPHA_UAT.md` plus the Platform Tier 2 acceptance cases documented in
  `PLATFORM_SDK.md`/`PLATFORM.md`

A release is blocked by any core/security test failure, release-integrity failure,
automatic-code isolation failure when that feature is claimed ready, tested-code
source/hash failure, privilege/role/scope leak, machine-to-human credential escape,
private event payload leakage, or live/Git integrity failure.
