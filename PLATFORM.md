# SAD Platform Core

SAD is a local-first, role-governed AI platform. Chat, Voice, Personal Study, Forge,
Memory, governed Tools, Developer Workspace, repair governance, accounts, Mobile, and
local app integrations share one API and authority model.

## Current contract

- Platform version: `0.3-alpha`
- Platform manifest schema: `3`
- API contract: `v1`
- Core API binding: loopback only
- Dynamic extension execution: disabled
- AI Git authority: none
- Git publication authority: human/host only

The established public `GET /health` response remains the minimal
`{status, api_version}` contract. Detailed discovery requires a signed-in account.

Human platform discovery:

- `GET /v1/platform`
- `GET /v1/platform/modules`
- `GET /v1/platform/capabilities`
- `POST /v1/platform/compatibility`

Owner local-app/event management:

- `GET /v1/platform/clients`
- `POST /v1/platform/clients`
- `POST /v1/platform/clients/{client_id}/rotate`
- `POST /v1/platform/clients/{client_id}/revoke`
- `POST /v1/platform/events/read`

Machine-client usage is documented in `PLATFORM_SDK.md`. `SAD-App` credentials remain
read-only/control-plane credentials and cannot impersonate a person or enter Chat,
Memory, Tools, Study, Forge, coding, repair, account, mobile-admin, or Git workflows.

## Built-in modules

### `sad.platform`

Versioned discovery, compatibility negotiation, Owner-governed loopback app
credentials, and metadata-only platform events.

### `sad.chat`

Private per-account multi-turn conversation. Chat can optionally use enabled,
non-expired Personal Memory when the configured Local AI model is active. A request can
set `use_memory: false` to exclude saved memory for that turn.

### `sad.voice`

Authenticated transcript-to-conversation bridge. It shares SAD Chat history and the
same optional Personal Memory context. The response contains text suitable for a local
TTS layer. Microphone capture, STT, and TTS engines are deployment/client work rather
than hidden server authority.

### `sad.memory`

Explicit user-controlled long-term memory. SAD does not automatically promote ordinary
chat text into this store.

Supported memory categories:

- `fact`
- `preference`
- `goal`
- `project`
- `note`

Memory controls:

- create
- list/search
- edit
- enable/disable for Local AI context
- optional expiry
- delete

Every memory belongs to exactly one account. Disabled or expired memories are not
provided to Local AI context. The built-in dialogue fallback never reports memory use.
Runtime memory lives in ignored `memory.json`.

Memory endpoints:

- `GET /v1/memory`
- `POST /v1/memory`
- `POST /v1/memory/search`
- `POST /v1/memory/{memory_id}`
- `POST /v1/memory/{memory_id}/delete`

### `sad.tools`

Governed internal Tool Actions. Tool definitions are fixed reviewed Python call paths,
not dynamically loaded plugins.

Tier 3 built-in tools:

- `platform.status` — read platform status
- `memory.search` — search the signed-in account's memories
- `memory.remember` — save an explicit personal memory
- `memory.forget` — delete an owned memory

Read-only actions can enter `ready`. State-changing tools enter `awaiting_approval` and
cannot execute until the same signed-in account explicitly approves them. Rejected
actions cannot execute.

There is no generic shell, arbitrary URL/network request, dynamic Python/plugin
execution, package install, unrestricted filesystem action, or Git tool in this tier.
Tool-action runtime state lives in ignored `tool_actions.json`.

Tool endpoints:

- `GET /v1/tools`
- `GET /v1/tools/actions`
- `POST /v1/tools/actions`
- `GET /v1/tools/actions/{action_id}`
- `POST /v1/tools/actions/{action_id}/decision`
- `POST /v1/tools/actions/{action_id}/execute`

### `sad.study`

Request-directed explanation, method teaching, work checking, proofreading, essay and
rubric help, examples, and expansion through the existing Personal Study contract.

### `sad.forge`

Game-first learning: quests, hints, mastery checks, XP, ranks, companion progress, and
student progress.

### `sad.developer`

Human-scoped multi-file coding and failure-driven repair. Generation occurs only in
private workspaces; Docker verification must pass; live application remains governed by
the existing Owner boundary. No coding or repair agent receives Git authority.

### `sad.accounts`

Local accounts, roles, passwords, lifecycle controls, and Owner-managed mobile device
trust.

### `sad.mobile`

Separate paired TLS gateway for phone access while the normal core API remains
loopback-only. Pairing trusts a device; normal login authorizes a person.

## Authority model

Platform metadata is descriptive only. A capability appearing in a manifest never
bypasses concrete route authorization.

Human accounts use the existing role-permission map. Local apps use separately scoped
`SAD-App` credentials. AI output receives neither identity automatically.

The Platform manifest explicitly reports:

- `platform_metadata_grants_authority: false`
- `dynamic_extension_execution: false`
- `tool_execution: registered_internal_tools_only`
- `memory_model: explicit_user_controlled`
- `git_authority: human_host_only`

## Platform events

Events are bounded metadata notifications. Tier 3 adds memory and tool lifecycle event
types, but event payloads must not contain memory content/title, tool arguments/output,
conversation text, generated code/diffs, passwords, sessions, or app secrets.

## Mobile Tier 3

A paired `learning` phone may use its signed-in account's Chat, Voice, Memory, governed
personal Tools, Personal Study, Forge play, and own progress through explicit route
matching. Development/admin routes remain blocked. `SAD-App` machine endpoints remain
blocked through the mobile gateway even on `full_role` phones so machine credentials
stay loopback-only.

The PWA may cache Memory & Tools static JS/CSS but never caches `/v1/*` or `/mobile/*`
responses.

## Acceptance

Automated gates cover ownership, expiry/disable behavior, per-turn memory exclusion,
mutating-tool approval, unknown-tool rejection, mobile route isolation, event privacy,
PWA cache privacy, browser syntax, release integrity, and Docker isolation.

Deployment acceptance is defined in `PLATFORM_TIER3_UAT.md`. Host/device UAT remains
required before calling Tier 3 operational on a particular deployment computer or
phone.
