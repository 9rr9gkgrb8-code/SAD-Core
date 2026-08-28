# SAD — Sandbox Adaptive Dialogue

SAD is a local-first AI platform with human-controlled authority boundaries.

Current Alpha surfaces include SAD Chat, Voice transcript transport, explicit Personal
Memory, governed Tool Actions, Personal Study, Forge Learning, multi-file Developer
Workspace coding, controlled repair, accounts/RBAC, paired Mobile access, scoped local
app credentials, platform events, and capability/version discovery.

## Platform Core v0.3-alpha

`platform_registry.py` defines the declarative platform catalog. Platform schema is `3`;
the HTTP API remains `v1`.

Signed-in human clients can discover their role-filtered capabilities through:

- `GET /v1/platform`
- `GET /v1/platform/modules`
- `GET /v1/platform/capabilities`
- `POST /v1/platform/compatibility`

Current built-in modules:

- **SAD Platform Core** — discovery, versions, app/event control plane
- **SAD Chat** — private multi-turn conversation
- **Voice Client Bridge** — authenticated transcript-to-conversation transport
- **Personal Memory** — explicit per-account long-term memory controls
- **Governed Tool Actions** — reviewed internal tools with approval before mutation
- **Personal Study** — request-directed learning/writing assistance
- **Forge Learning** — quests, hints, mastery, XP/ranks, companion progress
- **Developer Workspace** — scoped multi-file coding + Docker verification
- **Accounts & Roles** — local identity/RBAC and device administration
- **Mobile Gateway** — paired private TLS phone access while Core stays loopback-only

Platform metadata never grants authority. Concrete endpoints still enforce authentication,
RBAC, workflow state, source hashes, Docker evidence, and Owner approval where required.

## Personal Memory

SAD does **not** automatically copy ordinary conversation into long-term memory.

A signed-in account may explicitly save memories in these categories:

- fact
- preference
- goal
- project
- note

Memory can be searched, edited, enabled/disabled, given an expiry, or deleted. Every
memory is account-owned. Only enabled, non-expired entries may be supplied to the
configured Local AI during Chat/Voice, and a request can set `use_memory: false` for a
memory-free turn. Built-in dialogue does not claim memory use.

Runtime memory is stored locally in ignored `memory.json`.

## Governed Tool Actions

Tier 3 exposes only a fixed reviewed internal tool catalog:

- `platform.status`
- `memory.search`
- `memory.remember`
- `memory.forget`

Read-only actions can be executed when ready. State-changing personal tools begin in
`awaiting_approval` and require explicit approve/reject before execution.

There is no generic shell, arbitrary URL/network tool, dynamic plugin/Python loader,
package installer, unrestricted filesystem tool, or Git tool.

Runtime tool state is stored locally in ignored `tool_actions.json`.

## Conversation and Voice

SAD Chat persists account-owned sessions and recent conversation context. When the
configured loopback local model is healthy, replies are labeled `Local AI`; otherwise
SAD visibly falls back to `Built-in dialogue`.

`POST /v1/voice/turn` reuses the same conversation identity/history and returns
`speech_text` for a later local TTS client. Direct microphone/STT/TTS integration is
still a deployment/client milestone.

## Coding and controlled repair

General coding:

`task → scope suggestion → human-approved files → private workspace → local AI edits → Docker tests → exact diff → Owner apply/rollback`

Failure-driven repair:

`failure → human triage → scoped repair draft → isolated Docker tests → exact diff → Owner YES/NO → verified local apply/rollback`

Coding and repair agents receive no Git commit/push/fetch/rebase/merge/credential
authority.

## Local app integration

Owner can create scoped loopback `SAD-App` credentials for companion software. Tier 2/3
machine credentials remain read-only/control-plane scoped to platform discovery,
compatibility, and approved metadata events. They cannot impersonate users or enter
Chat, Memory, Tools, Study, Forge, coding, repair, account, mobile-admin, or Git flows.

See `PLATFORM_SDK.md`.

## Mobile

`mobile.py` starts the loopback desktop/core service plus a separate paired TLS phone
gateway on an explicit private/approved-overlay IPv4 address.

Learning-mode phones can use their own Chat, Voice, Memory, governed personal Tools,
Study, Forge, and own progress. Development/admin routes remain blocked. `SAD-App`
machine endpoints stay blocked through Mobile even for full-role devices.

See `MOBILE.md` and `PLATFORM_TIER3_UAT.md`.

## Local private data

The following are ignored by Git and must be treated as private host data:

- `settings.json`
- `failures.json`
- `accounts.json`
- `dashboard_state.json`
- `student_progress.json`
- `chat_history.json`
- `memory.json`
- `tool_actions.json`
- `platform_clients.json`
- `platform_events.json`
- `.sad_sandbox/`
- `.sad_dev/`
- `local_data/`
- `.env`

## Run

Desktop Alpha:

```powershell
python alpha.py
```

Then open `http://127.0.0.1:8765/`.

Paired mobile mode, after TLS/private-address preflight:

```powershell
python mobile.py
```

API only:

```powershell
python api.py
```

## Verify

```powershell
python -m compileall -q .
python -m unittest -v
python release_gate.py
python alpha_doctor.py
```

Automatic repair/coding readiness additionally requires the reviewed digest-pinned
Docker sandbox image and `python docker_proof.py`. Mobile readiness additionally
requires `python mobile_doctor.py` and real host/phone UAT.

See `PLATFORM.md`, `API.md`, `SECURITY.md`, `ALPHA1.md`, `PLATFORM_TIER2_UAT.md`, and
`PLATFORM_TIER3_UAT.md` for the current contracts.
