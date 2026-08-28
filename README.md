# SAD — Sandbox Adaptive Dialogue

SAD is a local-first AI platform with human-controlled authority boundaries.

Its current Alpha combines one authenticated API, browser/mobile clients, general AI
conversation, a Voice transcript bridge, Personal Study, Forge learning,
failure/repair governance, a multi-file Developer Workspace, and scoped local-app
integration. Platform Core gives those surfaces one discoverable versioned contract.

## Platform Core v0.2-alpha

`platform_registry.py` defines the declarative SAD platform catalog.

After normal sign-in, clients can discover/verify the capabilities available to the
current role through:

- `GET /v1/platform`
- `GET /v1/platform/modules`
- `GET /v1/platform/capabilities`
- `POST /v1/platform/compatibility`

Current built-in modules include:

- **SAD Platform Core** — discovery, versions, local-app/event control plane
- **SAD Chat** — free-form multi-turn local AI conversation
- **Voice Client Bridge** — signed-in transcript transport using SAD Chat identity/history
- **Personal Study** — request-directed learning and writing assistance
- **Forge Learning** — quests, hints, mastery, XP, ranks, companion progression
- **Developer Workspace** — scoped multi-file coding and Docker verification
- **Accounts & Roles** — local identity, RBAC, account/device administration
- **Mobile Gateway** — paired TLS phone access while core API stays loopback-only

Platform metadata is descriptive only. A manifest cannot grant permissions, execute a
plugin, approve a repair, apply code, or gain Git authority. Concrete endpoints still
enforce SAD authentication/RBAC/workflow checks.

## Local app integration

Owner can create narrow **SAD-App** machine credentials for loopback companion
applications. Machine scopes are limited to Platform discovery/catalog/modules,
compatibility negotiation, and exact metadata-event subscriptions.

App secrets are returned once, salted/hashed at rest, rotatable, and revocable. A
machine credential cannot impersonate a SAD account or enter Chat, Voice, Study,
Forge, coding, repair, account, mobile-admin, or Git workflows.

`sad_sdk.py` is a standard-library-only helper for local integrations and rejects
non-loopback core URLs. `platform_events.py` exposes bounded privacy-minimized event
metadata without copying Chat text, code/diffs, passwords, tokens, or student work.

See `PLATFORM.md`, `PLATFORM_SDK.md`, and `PLATFORM_TIER2_UAT.md`.

## Voice Client Bridge

`POST /v1/voice/turn` accepts a signed-in person's transcript, uses the same
account-owned conversation engine/history as SAD Chat, and returns reply text plus
`speech_text` suitable for a future local TTS client.

This is the stable Voice transport layer. Direct browser microphone capture and bundled
STT/TTS engines are not yet part of the Alpha claim.

## Controlled repair and coding

Failure-driven repair follows:

`failure → human triage → scoped repair draft → isolated Docker tests → exact diff → Owner YES/NO → verified local apply/rollback`

General coding follows:

`task → scope suggestion → human-approved files → private multi-file workspace → local AI edits → Docker tests → exact diff → Owner apply/rollback`

Forge/coding agents do not receive Git commit, push, fetch, rebase, merge, branch, or
credential authority. Repository publication remains host/human controlled.

## Learning

- `personal_study.py` supports problem breakdowns, method teaching, walkthroughs, work
  checking, hints, direct answers when asked, proofreading, essay editing, rubric
  review, examples, and substantive word-count expansion without a forced quiz loop.
- `forge_student.py` provides game-first homework quests, a four-step hint ladder,
  mastery-gated XP/ranks, companion progression, and boss checks.

## SAD Chat

Chats are private to the signed-in account, persist locally across restarts, and use
recent conversational context. When the configured loopback local model is available
the UI reports **Local AI**; otherwise it reports **Built-in dialogue**.

Conversation text itself carries no repair, coding, app-management, file, shell,
approval, or Git authority.

## Accounts and governance

`auth.py` provides Student, Teacher, Owner, Developer, Reviewer, and Viewer roles.
Passwords use salted PBKDF2 hashes, repeated failures temporarily lock accounts,
sessions expire/revoke, and role permissions protect governance. Owner additionally
holds `platform:manage` for local-app/event administration.

## Isolation hardening

Repair and Developer Workspace verification require Docker plus a preloaded,
digest-pinned `SAD_SANDBOX_IMAGE`. Execution is networkless, non-root,
resource-limited, stripped of Git credentials, and denied Git control metadata.
Missing isolation fails closed.

Live apply rechecks source/test hashes, preserves backups, and performs verified
rollback when a transaction fails.

## Mobile

`mobile.py` provides an optional paired TLS phone gateway while the core API remains
loopback-only. Phones require device pairing plus normal SAD login.

Learning devices receive explicit Chat, Voice transcript, Study, Forge, account-self,
and own-progress routes. Full Role devices still receive only the signed-in person's
normal RBAC authority. Machine-client `/v1/platform/client/*` routes are blocked by the
mobile gateway in both modes.

See `MOBILE.md`.

## Local data

The following stay on the host and are ignored by Git:

- `settings.json`
- `failures.json`
- `accounts.json`
- `dashboard_state.json`
- `student_progress.json`
- `chat_history.json`
- `platform_clients.json`
- `platform_events.json`
- `.sad_sandbox/`
- `.sad_dev/`
- `local_data/`
- `.env`

Do not commit runtime data, app secrets, or private backups.

## Run SAD

Desktop Alpha:

```powershell
python alpha.py
```

Then open `http://127.0.0.1:8765/`.

Paired mobile mode after private-address/TLS setup:

```powershell
python mobile.py
```

Loopback API:

```powershell
python api.py
```

See `ALPHA1.md`, `API.md`, `PLATFORM.md`, `PLATFORM_SDK.md`, `SECURITY.md`,
`ALPHA_UAT.md`, and `PLATFORM_TIER2_UAT.md` for the release contract.

## Run tests

```powershell
python -m unittest -v
```
