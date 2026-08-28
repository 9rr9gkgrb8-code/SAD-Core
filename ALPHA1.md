# SAD Platform Alpha 1

SAD Alpha 1 is a local-first AI platform candidate. The normal Core API remains
loopback-only. Optional phone access uses a separate paired TLS gateway on an explicit
private/approved-overlay address.

## Preflight

Run:

```text
python alpha_doctor.py
```

Interpretation:

- `ALPHA CORE: READY` means the local browser/API product can start.
- A Local AI model is optional for basic UI/built-in dialogue but required for full AI
  conversation, Memory-aware Local AI responses, automatic repair drafting, and
  Developer Workspace planning/coding.
- Automatic repair/coding verification requires Docker plus a preloaded digest-pinned
  `SAD_SANDBOX_IMAGE`. Missing required isolation fails closed.

Mobile Preview additionally requires:

```text
python mobile_doctor.py
MOBILE GATEWAY: READY
```

Never commit a real `.env` file.

## Start

Desktop/Core:

```text
python alpha.py
```

Open `http://127.0.0.1:8765/`.

Paired mobile mode after private-address/TLS setup:

```text
python mobile.py
```

## Included platform surfaces

### Platform Core `0.3-alpha`

- manifest schema `3`
- role-filtered module/capability discovery
- capability version/lifecycle metadata
- compatibility negotiation
- Owner-scoped local app credential management
- privacy-minimized platform event inspection

Platform metadata is descriptive only and cannot grant concrete endpoint authority.

### SAD Chat

- private per-account conversations
- durable history/new/archive
- recent-turn context
- Local AI vs Built-in dialogue labeling
- optional enabled Personal Memory context
- per-turn `use_memory: false` opt-out

### Voice Client Bridge

- authenticated transcript input
- same Chat ownership/history
- same optional Memory rules
- reply text plus `speech_text` for later local TTS

Direct microphone/STT/TTS is not bundled yet.

### Personal Memory

- explicit user-created long-term Memory
- categories: fact/preference/goal/project/note
- create/list/search/edit/enable/disable/expiry/delete
- per-account isolation
- enabled/non-expired context only
- local ignored `memory.json`

Ordinary Chat is not silently promoted into long-term Memory.

### Governed Tool Actions

Tier 3 fixed catalog:

- `platform.status`
- `memory.search`
- `memory.remember`
- `memory.forget`

Read-only actions can run when ready. State-changing personal tools require explicit
approve/reject before execution. There is no generic shell, arbitrary network, dynamic
plugin/Python loader, package install, unrestricted filesystem action, or Git tool.

### Personal Study

Request-directed explanation, method teaching, direct answers when asked, work checking,
proofreading, essay/rubric help, examples, and expansion with optional Local AI output.

### Forge Learning

Game-first quests, hints, mastery/boss checks, XP/ranks, companion progression, and
durable learner progress.

### Developer Workspace

`task → scope suggestion → human-approved paths → private multi-file generation → Docker
verification → exact diff/test evidence → Owner apply/rollback`

Developer may prepare/test but cannot cross Owner live-application governance.

### Controlled repair

`failure → human triage → scoped repair draft → isolated verification → exact tested
diff → Owner YES/NO → verified local apply/rollback`

Forge/AI cannot approve its own work or use Git authority.

### Accounts and roles

Local Owner, Developer, Reviewer, Viewer, Teacher, and Student identities use separate
credentials and existing RBAC. Password/session/account protections remain enforced.

### Local apps/events

Owner may create scoped loopback `SAD-App` credentials for Platform metadata clients.
Secrets are one-time at creation/rotation and hashed at rest. Machine credentials do
not impersonate humans. Event subscriptions are exact and metadata-only.

### Mobile Preview

- paired device + normal account login required
- TLS 1.2+
- explicit private/approved-overlay IPv4 binding
- Learning mode: own Chat, Voice, Memory, governed Tools, Study, Forge, own progress
- Full role: normal human route surface + normal RBAC
- machine `/v1/platform/client/*` routes blocked in every mobile mode
- static-shell-only PWA cache

## Private runtime data

Git-ignored/private host data includes accounts, settings, failures/dashboard/progress,
Chat history, `memory.json`, `tool_actions.json`, platform client/event state, mobile
pairing state, `.sad_sandbox/`, `.sad_dev/`, local data, and `.env`.

Do not put runtime data or private backups in the public repository.

## Authority boundaries

SAD Alpha does not grant AI or Tool Actions generic host authority.

- Dynamic third-party plugin execution: disabled.
- Generic shell/network/filesystem/Git Tool Actions: absent.
- Local app machine credentials: read-only/control-plane scoped.
- Automatic coding: explicit file scope + Docker verification.
- Live code apply/rollback: Owner governance.
- Git commit/push/fetch/rebase/merge: outside AI and automatic application paths.
- Public internet hosting: unsupported.

## Acceptance

Automated gates:

```text
python -m compileall -q .
python -m unittest -v
python release_gate.py
python alpha_doctor.py
```

Automatic-code readiness also requires `python docker_proof.py` with the reviewed
pinned image.

Human deployment acceptance requires the scenarios in:

- `ALPHA_UAT.md`
- `PLATFORM_TIER2_UAT.md`
- `PLATFORM_TIER3_UAT.md`
- `MOBILE.md` for any phone/device support claim

Automated accessibility and security tests are regression nets, not substitutes for
keyboard/screen-reader/zoom/narrow-screen and actual host/device validation.

## Alpha exit truth

A code candidate is blocked by any failing test, release-integrity failure, authority
leak, cross-account Memory/Tool access, mutating Tool execution without approval,
private-data cache/source leakage, missing required coding isolation, stale/tampered
tested code, or failed live/Git integrity evidence.

A real deployment is not called operational until host-specific Local AI, Docker,
mobile TLS/device setup where applicable, and the required UAT are proven on that host.
