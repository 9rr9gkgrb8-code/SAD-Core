# SAD Platform Core

SAD Platform Core turns the existing SAD product surfaces into one discoverable,
role-governed local platform. Chat, Personal Study, Forge, repair governance,
Developer Workspace, accounts, and Mobile are modules of the same SAD API rather
than separate authority systems.

## Platform objective

A SAD client should not need a hard-coded assumption about every feature. After
normal SAD sign-in, a client can ask the platform what the signed-in account may see
and which stable routes implement those capabilities.

Current discovery endpoints:

- `GET /health` — existing public minimal health/API version contract
- `GET /v1/platform` — signed-in role-filtered platform manifest including platform version
- `GET /v1/platform/modules` — signed-in visible modules and their capabilities
- `GET /v1/platform/capabilities` — signed-in flattened capability catalog

The platform metadata is **descriptive only**. Returning a capability in the catalog
does not bypass the existing endpoint authorization check. Every concrete endpoint
continues to enforce SAD authentication and RBAC independently.

## Platform version

Current Platform Core version: `0.1-alpha`

Platform manifest schema version: `1`

The API remains `v1`. Platform and API versions are intentionally separate so SAD can
evolve module discovery without silently changing an existing route contract. The
legacy `/health` response is intentionally unchanged for backward compatibility.

## Built-in modules

### `sad.platform`

Platform discovery, module catalog, capability catalog, version and authority metadata.

### `sad.chat`

General free-form multi-turn SAD conversation with durable per-account history.

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

## Capability shape

Each capability includes:

```json
{
  "capability_id": "development:govern",
  "title": "Govern live code",
  "description": "Apply/rollback tested code and close governed work.",
  "permission": "development:govern",
  "routes": [
    {"method": "POST", "path": "/v1/dev/workspaces/{workspace_id}/apply"}
  ],
  "mutates_state": true,
  "human_approval_boundary": true
}
```

`permission: null` means the capability is available to any authenticated SAD account,
not to an anonymous caller.

`human_approval_boundary: true` is documentation for clients and reviewers. It does
not replace server-side authorization or workflow-state checks.

## Role-filtered discovery

The registry filters capabilities against the same role-permission map used by SAD's
live API.

Examples:

- Student: platform discovery, SAD Chat, Personal Study, Forge play, own progress.
- Teacher: Student capabilities plus student progress and allowed student-account work.
- Viewer: platform discovery plus read-only development visibility.
- Reviewer: platform discovery plus development review/decision visibility authorized
  by the existing role map.
- Developer: platform discovery plus development work, but no Owner governance.
- Owner: all role-permitted Alpha modules, including account administration and live
  development governance.

The platform catalog intentionally does not invent a second permission system.

## Client model

The web UI, PWA/mobile UI, future voice client, and future local applications should
consume Platform Core as SAD clients.

Current client rule:

1. establish the required device trust if entering through Mobile;
2. sign in through SAD's normal account authentication;
3. fetch `/v1/platform`;
4. render only the capabilities returned for that signed-in role;
5. call the documented concrete endpoints;
6. handle a server-side permission denial as authoritative even if cached/client
   metadata suggested a capability was available.

The web **SAD Platform** dashboard is a read-only visualization of this contract.

## Extension boundary

Platform Core is intentionally **declarative, not a dynamic plugin loader** in Alpha.
A module manifest can describe capabilities, but it cannot cause Python, JavaScript,
shell commands, or arbitrary packages to execute.

This prevents a future extension from gaining authority merely by registering itself.
A later plugin/extension milestone must define, test, and approve a separate execution
boundary before dynamic modules are permitted.

For the same reason, Platform Core currently has no third-party API-key issuance,
OAuth, remote package installation, or internet marketplace.

## Authority model

Platform manifests report the authority boundary explicitly:

```json
{
  "authentication": "local_account_session",
  "authorization": "role_permissions",
  "platform_metadata_grants_authority": false,
  "git_authority": "human_host_only"
}
```

Platform discovery cannot:

- create or elevate an account;
- approve a repair;
- apply a tested file;
- run Developer Workspace code;
- bypass Docker isolation;
- commit, push, merge, fetch, rebase, or alter Git;
- expose secrets or private runtime data;
- load arbitrary extension code.

## Mobile

The Platform dashboard is intended for trusted `full_role` Owner/development phones.
Learning-only paired devices keep their smaller gateway allow-list and do not gain
administrative/development routes merely because Platform Core exists.

The service worker may cache the static Platform UI shell but never caches `/v1/*`
responses, including the live capability catalog.

## Security and privacy

- `/health` keeps the established minimal `{status, api_version}` response.
- Detailed modules/capabilities require a valid account session.
- Role filtering happens on the server.
- The client is not trusted to enforce permissions.
- No runtime account, conversation, failure, progress, pairing, or workspace data is
  embedded in the platform registry.
- No platform route widens the core API beyond loopback.

## What this milestone changes

Before Platform Core, SAD had multiple working surfaces behind one API, but clients had
to know those surfaces independently.

After Platform Core, SAD has a common discovery contract and module/capability model.
That is the foundation for treating SAD as the platform and Chat, Forge, Study, Mobile,
repair, coding, voice, and future clients as governed parts of that platform.

## Not yet implemented

Platform Core is a foundation, not the final ecosystem. Remaining later-platform work
includes:

- a governed extension/plugin execution contract;
- scoped machine-to-machine client credentials if local external apps need unattended
  access;
- stable event/subscription contracts for platform notifications;
- formal capability version/deprecation negotiation;
- voice as a SAD client surface;
- deployment-host UAT and eventual Beta packaging.

Those additions must preserve SAD's local-first and human-approval boundaries.
