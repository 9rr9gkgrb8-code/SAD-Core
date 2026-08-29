# SAD Platform Core

SAD is a local-first, role-governed AI platform. Chat, Voice, Personal Study, Forge,
Memory, governed Tools, Developer Workspace, repair governance, governed Skills,
accounts, Mobile, and local app integrations share one API and authority model.

## Current contract

- Platform version: `0.4-alpha`
- Platform manifest schema: `4`
- API contract: `v1`
- Core API binding: loopback only
- Dynamic extension execution: disabled
- Extension registration authority: descriptive only
- Extension host fallback: forbidden
- AI Git authority: none
- Git publication authority: human/host only
- Skill promotion: independent verification plus explicit human approval

The established public `GET /health` response remains the minimal
`{status, api_version}` contract. Detailed discovery requires a signed-in account.

Human platform discovery:

- `GET /v1/platform`
- `GET /v1/platform/modules`
- `GET /v1/platform/capabilities`
- `POST /v1/platform/compatibility`

Owner local-app/event/extension management:

- `GET /v1/platform/clients`
- `POST /v1/platform/clients`
- `POST /v1/platform/clients/{client_id}/rotate`
- `POST /v1/platform/clients/{client_id}/revoke`
- `POST /v1/platform/events/read`
- `GET /v1/platform/extensions`
- `POST /v1/platform/extensions`
- `POST /v1/platform/extensions/{extension_id}/revoke`

Machine-client usage is documented in `PLATFORM_SDK.md`. `SAD-App` credentials remain
read-only/control-plane credentials and cannot impersonate a person or enter Chat,
Memory, Tools, Study, Forge, coding, repair, governed Skill, account, mobile-admin, or
Git workflows.

The 0.4 extension manifest is also not a credential. Registering an extension creates
no `SAD-App` secret and grants no machine or human permission. Credentials, when
appropriate, are issued separately through the existing Owner-governed client store.

## Built-in modules

### `sad.platform`

Versioned discovery, compatibility negotiation, Owner-governed loopback app
credentials, declarative out-of-process extension contracts, and metadata-only
platform events.

External extension contracts in 0.4 are deliberately narrow:

- external process only
- reviewed `SAD-App` HTTP transport only
- loopback network scope only
- no dynamic code loading into SAD Core
- no silent host fallback
- no Git authority
- strict manifest field allowlist
- compatibility snapshot recorded at registration
- Owner-governed revocation

See `PLATFORM_0_4.md` for the milestone acceptance contract.

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
Runtime memory is stored through the protected runtime persistence layer.

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
Tool-action runtime state uses the protected runtime persistence layer.

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

### `sad.skills`

Evidence-bound reusable procedures. A successful repair may create a candidate, but a
candidate is not a learned rule and is never auto-promoted.

Lifecycle:

`candidate -> validated -> promoted`

Governance paths:

- validated or promoted skills can be revoked
- a promoted skill can be superseded by a verified next version
- superseded/revoked records remain traceable

A candidate binds task/configuration provenance to repair and execution evidence.
Validation adds an independent verifier and deterministic verification evidence.
Promotion requires explicit human approval. The producer identity cannot also be the
independent verifier identity.

Skill endpoints:

- `GET /v1/skills`
- `POST /v1/skills`
- `POST /v1/skills/{skill_id}/validate`
- `POST /v1/skills/{skill_id}/promote`
- `POST /v1/skills/{skill_id}/revoke`

The role mapping deliberately reuses current development permissions:

- Viewer: inspect
- Developer: inspect and propose
- Reviewer: inspect and validate
- Owner: inspect, propose/review, promote, revoke

Students and teachers do not receive this development/governance surface.

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
- `extension_model: declarative_external_sad_app_contract_only`
- `extension_registration_grants_authority: false`
- `host_fallback_on_extension_failure: false`
- `tool_execution: registered_internal_tools_only`
- `memory_model: explicit_user_controlled`
- `skill_promotion: independent_verification_plus_human_approval`
- `repair_success_equals_skill_promotion: false`
- `git_authority: human_host_only`

## Platform events

Events are bounded metadata notifications. 0.4 adds extension and governed-skill
lifecycle event types, but event payloads must not contain memory content/title, tool
arguments/output, conversation text, repair text, generated code/diffs, passwords,
sessions, or app secrets.

0.4 lifecycle events:

- `platform.extension.registered`
- `platform.extension.revoked`
- `skill.candidate.created`
- `skill.validated`
- `skill.promoted`
- `skill.revoked`

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
extension authority rejection, skill provenance, independent verification, human skill
promotion, versioned skill lineage, PWA cache privacy, browser syntax, release
integrity, and Docker isolation.

Repository acceptance for 0.4 is defined in `PLATFORM_0_4.md`. Existing deployment
acceptance remains in `PLATFORM_TIER3_UAT.md`. Host/device UAT remains required before
calling a particular deployment operational.
