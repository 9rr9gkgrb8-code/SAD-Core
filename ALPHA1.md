# SAD + Forge Alpha 1

## Preflight

Run `python alpha_doctor.py` before first launch or after changing local model or
sandbox configuration. The doctor reports Alpha core readiness separately from
automatic-code isolation readiness.

- `ALPHA CORE: READY` means the local browser product can start.
- An unconfigured local model is optional for basic Alpha use. SAD Chat and Voice
  visibly fall back to the built-in dialogue layer, while full AI conversation,
  repair drafting, and Developer Workspace planning/coding require the configured
  loopback-only model.
- `REPAIR ISOLATION: BLOCKED` means automatic code verification remains disabled
  until Docker and a preloaded digest-pinned `SAD_SANDBOX_IMAGE` are available. SAD
  never silently falls back to same-user execution.

The optional paired mobile preview has its own `python mobile_doctor.py` preflight and
is not ready until it reports `MOBILE GATEWAY: READY` on the actual host.

Use `.env.example` as configuration reference. Never commit a real `.env` file.

## Start

For desktop Alpha, run `python alpha.py`, complete one-time Owner setup, then open
`http://127.0.0.1:8765/`. The core API remains loopback-only.

For paired mobile preview, configure the private bind address and trusted TLS
certificate/key described in `MOBILE.md`, then run `python mobile.py`.

Owner can create Student, Teacher, Developer, Reviewer, and Viewer accounts. Each
person receives a separate credential.

## Included surfaces

- **SAD Platform Core v0.2-alpha** with role-filtered module/capability discovery,
  capability versions/lifecycle metadata, compatibility negotiation, scoped local-app
  identity, metadata-only platform events, and Owner app/event controls.
- **SAD Chat** with durable per-account conversations, recent-turn context, history,
  archive/new-conversation controls, and visible `Local AI` versus `Built-in dialogue`
  response status.
- **Voice Client Bridge** through `POST /v1/voice/turn`, using a signed-in person's
  normal account-owned SAD conversation and returning reply text suitable for future
  local speech synthesis.
- **SAD Developer Workspace** for task → scope plan → human-approved files → multi-file
  isolated generation → Docker full-suite test → exact diff → Owner apply/rollback.
- **Personal Study** with request-directed learning/writing/checking assistance and
  optional local-model output.
- **Forge Student** game-first quests, hints, mastery, XP/ranks, companion progression,
  boss checks, and durable student progress.
- Teacher student-progress roster.
- Owner account administration and mobile-device trust controls.
- Owner Repair Inbox with exact tested repair diff before YES/NO.
- Shared role-filtered failure/development dashboard.
- Optional Mobile Preview with installable PWA shell, one-time pairing, revocable
  device trust, learning/full-role modes, SAD Chat, Voice transcript transport,
  Study, Forge, and private TLS gateway while the core API stays on loopback.
- Password change and session revocation.
- Standard-library `sad_sdk.py` for reviewed loopback local integrations.

## Platform Core v0.2 boundary

SAD is the platform. Chat, Study, Forge, Voice, coding, repair, accounts, Mobile, and
future local clients are governed surfaces of that platform rather than independent
authority systems.

Human discovery:

- `GET /v1/platform`
- `GET /v1/platform/modules`
- `GET /v1/platform/capabilities`
- `POST /v1/platform/compatibility`

The registry filters human capabilities through the same `ROLE_PERMISSIONS` map used
by live endpoints. Discovery metadata cannot create accounts, run code, approve
repairs, apply files, bypass Docker, or exercise Git authority.

Every capability reports a numeric capability version plus lifecycle state. Clients
may negotiate minimum versions; hidden capabilities remain unavailable rather than
being leaked through compatibility responses.

Platform modules remain declarative. Tier 2 does **not** dynamically load third-party
Python/JavaScript, install packages, or create a plugin marketplace.

See `PLATFORM.md`.

## Local app boundary

Owner-only `platform:manage` can create scoped machine credentials for local software.
These credentials are separate from human sessions.

Allowed machine scopes are intentionally narrow:

- `platform:discover`
- `platform:catalog`
- `platform:modules`
- `platform:compatibility`
- `platform:events`

Creation and rotation return the app secret once. SAD persists only a salted hash in
ignored `platform_clients.json`. Rotation invalidates the prior secret; revocation
disables the app.

A machine credential:

- cannot impersonate a SAD account;
- cannot use Chat, Voice, Study, Forge, Developer Workspace, repair, accounts, or
  mobile administration;
- cannot run state-changing platform work;
- cannot receive Git credentials or Git authority;
- cannot use the mobile gateway machine endpoint family.

Machine endpoints live only on the loopback core API under `/v1/platform/client/*`.
The mobile gateway blocks that path family even for a Full Role paired phone.

See `PLATFORM_SDK.md`.

## Platform event boundary

`platform_events.json` is a bounded private metadata stream for integrations and Owner
inspection. Events include a monotonic sequence, UUID, type, time, optional subject ID,
and a small details object.

Events deliberately exclude conversation text, prompts, generated code, diffs,
passwords, user/app/device/session secrets, student work, and other high-value data.

A local app sees only exact event types approved on its registration. An empty event
subscription means no events. Event-store failure is surfaced diagnostically but does
not roll back an already completed primary action merely because auxiliary telemetry
could not be written.

## Voice Client Bridge boundary

`POST /v1/voice/turn` is conversation transport, not a tool-execution shortcut.

- It requires a normal human Bearer session.
- It accepts transcript text and an optional existing chat session ID.
- Without a session ID, SAD creates a normal account-owned chat session.
- It uses the same conversation engine/history isolation as SAD Chat.
- It returns `reply` and identical `speech_text` for a future local TTS engine.
- It reports `local_model` or `built_in` truthfully.
- It does not approve repairs, run coding workspaces, manage apps/accounts, apply
  files, or perform Git operations.

Learning-mode phones may use the Voice turn route after normal device pairing and user
login. The current browser security policy still disables direct microphone capture,
so this milestone is the stable transcript API, not bundled microphone/STT/TTS.

## SAD Chat boundary

- Every chat belongs to one authenticated account.
- Cross-account session-ID access is denied/not found.
- `chat_history.json` is local, Git-ignored, atomically written, bounded, and excluded
  from the PWA cache.
- Only recent turns needed for context go to the local model.
- If the model is unavailable, SAD labels the response `Built-in dialogue`.
- Conversation wording cannot itself invoke repair, code, app-management, approval,
  file, shell, or Git authority.

## Developer Workspace authority boundary

Developer Workspace is the broad coding lane; failure-driven repair remains the narrow
self-correction lane.

- Scope planning suggests paths but writes no code.
- A human submits the explicit approved path list before the workspace exists.
- The model sees source only for approved paths and edits only the private `.sad_dev`
  worktree.
- `.git`, `.github`, secrets, runtime data, hidden/control-plane paths, other SAD
  workspaces/sandboxes, and unsupported/binary files are excluded.
- At most 20 approved paths/edits are admitted per Alpha workspace.
- The complete unittest suite runs through the digest-pinned, networkless, non-root
  Docker boundary. Failed/unavailable isolation cannot be applied.
- Developer may plan/create/execute/inspect; Reviewer/Viewer inspect only;
  Student/Teacher have no Code Workspace access.
- Only Owner may apply/rollback the exact tested workspace.
- Live base hashes and post-test worktree hashes are rechecked before application.
- Existing changed files are backed up. A failed multi-file apply restores/verifies
  the original set.
- Developer Workspace never invokes Git.

See `DEVELOPER_WORKSPACE.md`.

## Repair authority boundary

Forge may draft one tightly scoped repair in one approved root Python file and test it
inside the configured Docker boundary. Owner reviews the actual diff before approval.

Owner approval applies only the exact passing proposal after stale-source validation,
atomic replacement, resulting-hash verification, and proposal-local backup. Failure
triggers verified rollback where possible.

Reviewer approval remains evidence-only. Developer/Forge cannot approve/apply their
own repair. Live repair never invokes Git commit, push, rebase, or merge.

## Mobile authority boundary

Pairing does not create a user session. A phone must pass paired-device trust and then
normal SAD account authentication.

`learning` mode permits explicit account-self, SAD Chat, Voice turn, Personal Study,
Forge play, and own-progress routes. Developer Workspace, dashboard/admin, Platform
app administration, and all machine-client routes are blocked.

`full_role` mode admits normal human routes, then SAD RBAC decides authority. A
Developer phone can prepare/test code but cannot apply; Owner remains required.
Machine-client `/v1/platform/client/*` routes are still blocked.

Device credentials remain revocable and browser-invisible through a
Secure/HttpOnly/SameSite=Strict cookie. The PWA service worker excludes `/v1/*` and
`/mobile/*` traffic, including app secrets, event responses, Chat/Voice, coding,
student, account, repair, session, and pairing data.

## Private data and backups

Private runtime data includes:

- `accounts.json`
- `dashboard_state.json`
- `student_progress.json`
- `chat_history.json`
- `failures.json`
- `platform_clients.json`
- `platform_events.json`
- `.env`
- `local_data/`
- `.sad_sandbox/`
- `.sad_dev/`

These are Git-ignored. Stop SAD before taking an encrypted backup. Never put runtime
backups in the public repository.

## Acceptance

Before widening a local pilot, run `ALPHA_UAT.md`. It covers role boundaries,
Platform discovery/versioning, local-app identity/scopes/rotation/revocation, event
privacy/subscription filtering, Voice account isolation, Chat, Developer Workspace,
repair, mobile, security, keyboard/screen-reader use, 200% zoom, and narrow-screen use.

Automation is a regression net, not a substitute for the manual host/phone UAT.

## Isolation

Automatic repair and Developer Workspace verification require Docker plus a preloaded
digest-pinned image in `SAD_SANDBOX_IMAGE`. Without it, execution stops fail-closed.
AI components produce drafts/evidence only; human roles retain approval and Git
authority.

## Alpha boundary

The core Alpha remains local-first and refuses non-loopback core binding. Mobile is a
separate paired TLS gateway restricted to one explicit private/approved overlay
address and must not be router-port-forwarded to the public internet.

Platform Tier 2 adds scoped **loopback local-app credentials**, not public API keys.
Public hosting, remote app credentials, hosted TLS termination, hosted secrets, email
recovery, external identity, marketplace/plugin execution, and automatic package
installation remain outside Alpha.
