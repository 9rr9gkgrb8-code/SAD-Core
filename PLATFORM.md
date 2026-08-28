# SAD Platform Core

SAD Platform Core turns SAD's working product surfaces into one discoverable,
role-governed local AI platform. Chat, Personal Study, Forge, repair governance,
Developer Workspace, accounts, Mobile, Voice, and local app integrations share one
platform contract rather than inventing separate authority systems.

## Platform objective

A SAD client should be able to discover what it can use, verify that the capability
version it expects is available, and then call the specific governed endpoint. Client
metadata never replaces the server-side security check.

Human discovery endpoints:

- `GET /health` — established public minimal `{status, api_version}` contract
- `GET /v1/platform` — signed-in role-filtered platform manifest
- `GET /v1/platform/modules` — signed-in visible modules/capabilities
- `GET /v1/platform/capabilities` — signed-in flattened capability catalog
- `POST /v1/platform/compatibility` — role-filtered version compatibility check

Owner platform-management endpoints:

- `GET /v1/platform/clients`
- `POST /v1/platform/clients`
- `POST /v1/platform/clients/{client_id}/rotate`
- `POST /v1/platform/clients/{client_id}/revoke`
- `POST /v1/platform/events/read`

Machine-client endpoints are documented in `PLATFORM_SDK.md`.

## Platform version

Current Platform Core version: `0.2-alpha`

Platform manifest schema version: `2`

The API remains `v1`. Platform and API versions remain separate so SAD can evolve
module discovery and compatibility metadata without silently changing an established
route contract.

Every capability now includes:

- `capability_version` using numeric `major.minor.patch`
- `lifecycle`: `alpha`, `stable`, or `deprecated`
- optional `replacement`
- routes
- permission requirement
- state-mutation marker
- human-approval-boundary marker

Compatibility checks are filtered to the requesting principal. A hidden capability is
reported unavailable rather than leaked through the negotiation endpoint.

## Built-in modules

### `sad.platform`

Platform discovery, module/catalog metadata, version negotiation, Owner-governed local
app credentials, and metadata-only event inspection.

### `sad.chat`

General free-form multi-turn SAD conversation with durable per-account history.

### `sad.voice`

A signed-in transcript bridge into the same account-owned SAD conversation engine.
It returns reply text suitable for a later local TTS client. Browser microphone capture,
STT, and TTS engines are not bundled in this milestone.

### `sad.study`

Personal Study actions including explanation, method teaching, walkthroughs, work
checking, proofreading, essay help, rubric review, examples, and expansion.

### `sad.forge`

Forge learning game features: quests, hints, mastery, XP, rank, companion state, and
student progress.

### `sad.developer`

Failure/development visibility, isolated Developer Workspace coding, repair review,
human decisions, Owner live apply, and rollback.

### `sad.accounts`

Account lifecycle and Owner-controlled mobile-device trust administration.

### `sad.mobile`

Paired TLS gateway/client surface. The core SAD API remains loopback-only.

## Principal model

SAD now distinguishes three trust principals.

### Human account

A person signs in with a local SAD account and receives an expiring in-memory Bearer
session. Existing role permissions determine which concrete endpoints that person may
use.

### Local app

An Owner can create a loopback-only `SAD-App` credential with explicitly selected
machine scopes and event subscriptions. The secret is returned once, salted/hashed at
rest, rotatable, and revocable.

Tier 2 app credentials are intentionally read-only/control-plane credentials. They can
only receive approved platform discovery, compatibility, and event metadata. They
cannot impersonate a SAD account or enter Chat, Study, Forge, coding, repair, account,
mobile-administration, or Git workflows.

### AI component

An AI model receives no identity merely because it generated text, a repair proposal,
or code. AI output must still pass the existing explicit human and isolation boundaries.

## Event stream

SAD emits a bounded local event stream for integrations that need to know that
something happened without receiving the private payload itself.

Events include a sequence, event ID, type, timestamp, optional subject ID, and a small
bounded metadata object. They deliberately exclude conversation text, generated code,
diffs, passwords, session tokens, app secrets, student work, and other high-value data.

App event reads are intersected with the exact event types approved by Owner. An empty
event subscription returns no events.

Runtime event data lives in Git-ignored `platform_events.json`.

## Voice client contract

`POST /v1/voice/turn` accepts an authenticated user's transcript and optional existing
chat session ID. It uses the same SAD conversation engine and account ownership rules as
SAD Chat, then returns:

- conversation `session_id`
- `reply`
- `speech_text`
- response `engine`
- `input_mode: transcript`
- `output_mode: text_for_local_tts`

The endpoint does not grant tool, code, repair, approval, app-management, or Git
authority. It is a conversation transport contract.

Learning-mode phones may call the voice route after pairing and normal user login.
Machine-client `/v1/platform/client/*` endpoints are blocked by the mobile gateway even
for full-role paired devices, keeping app credentials loopback-only.

## Python SDK

`sad_sdk.py` provides a small standard-library-only synchronous client for loopback SAD
integrations. It supports normal user-session platform/compatibility/voice calls and
scoped app manifest/compatibility/event calls. It does not persist credentials and
refuses non-loopback core URLs.

See `PLATFORM_SDK.md` for examples and the app trust contract.

## Role-filtered discovery

The registry still uses the same role-permission map as the live API.

Examples:

- Student: discovery, compatibility, SAD Chat, Voice bridge, Personal Study, Forge play,
  own progress.
- Teacher: Student capabilities plus student progress and allowed student-account work.
- Viewer: discovery/compatibility plus read-only development visibility.
- Reviewer: discovery/compatibility plus authorized development review/decision.
- Developer: discovery/compatibility plus development work, but no Owner governance.
- Owner: all role-permitted Alpha modules plus local-app/event management.

The platform catalog does not invent a second human permission system.

## Extension boundary

Platform Core remains **declarative, not a dynamic plugin loader**.

Tier 2 creates an integration SDK and machine credentials, but registering a local app
still cannot cause arbitrary Python, JavaScript, shell commands, packages, or extension
code to execute. There is no extension marketplace, remote package installation, OAuth,
or public-internet app token surface.

A future dynamic extension/plugin system requires a separate reviewed execution
boundary. It must not be smuggled in through the app registry.

## Authority model

Platform manifests explicitly state that:

- platform metadata does not grant authority;
- human authorization is role based;
- machine authorization is scope based;
- machine credentials do not impersonate users;
- dynamic extension execution is disabled;
- Git authority remains human-host controlled.

No Platform Tier 2 feature can:

- elevate an account;
- approve or apply a repair;
- run or apply Developer Workspace code as a machine client;
- bypass Docker isolation;
- expose private runtime payloads through events;
- turn an app secret into a user session;
- commit, push, merge, fetch, rebase, or alter Git;
- dynamically load arbitrary extension code.

## Mobile

The Platform dashboard remains available to trusted full-role development accounts,
and Owner now gets explicit local-app/event controls. API responses and one-time app
secrets are not service-worker cached because every `/v1/*` response remains excluded.

Learning-mode phones keep their smaller route allow-list plus `/v1/voice/turn`.
They do not gain Platform admin or machine-client routes.

## Security and privacy

- `/health` keeps the established minimal response.
- Detailed human platform metadata requires a valid user session.
- App management requires Owner-only `platform:manage`.
- App secrets are shown only at creation/rotation and stored only as salted hashes.
- `platform_clients.json` and `platform_events.json` are private Git-ignored runtime data.
- Event payloads are bounded and privacy-minimized.
- Machine endpoints remain on the loopback core API only.
- No Tier 2 route changes the core server's loopback binding.

## What Tier 2 changes

Platform Core v0.1 made SAD discoverable as one platform.

Platform Core v0.2 makes that platform **integratable** without giving integrations the
keys to the house: scoped local app identity, exact event subscriptions, compatibility
negotiation, a loopback SDK, and a voice-client conversation contract.

## Still later

Remaining later-platform work includes:

- a separately sandboxed dynamic extension/plugin execution model, if desired;
- richer event delivery such as local subscriptions/webhooks without weakening
  loopback/private-network boundaries;
- optional browser/native microphone capture;
- reviewed local speech-to-text and text-to-speech engines;
- formal capability deprecation windows/migration tooling;
- deployment-host UAT and eventual Beta packaging.

Those additions must preserve SAD's local-first, least-authority, and human-approval
boundaries.
