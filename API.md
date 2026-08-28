# SAD local API v1

SAD Core is a loopback-only JSON API. Human protected endpoints require
`Authorization: Bearer <session-token>`. Local machine integrations use the distinct
`Authorization: SAD-App <client-id>.<secret>` scheme only on the narrow Platform client
routes.

Platform version is `0.3-alpha`; manifest schema is `3`; HTTP API remains `v1`.

## Health and authentication

- `GET /health`
- `POST /v1/auth/login`
- `GET /v1/auth/me`
- `POST /v1/auth/logout`
- `POST /v1/auth/password`

`/health` intentionally remains the minimal `{status, api_version}` contract.

## Platform discovery and Owner control plane

- `GET /v1/platform`
- `GET /v1/platform/modules`
- `GET /v1/platform/capabilities`
- `POST /v1/platform/compatibility`
- `GET /v1/platform/clients` — Owner
- `POST /v1/platform/clients` — Owner
- `POST /v1/platform/clients/{client_id}/rotate` — Owner
- `POST /v1/platform/clients/{client_id}/revoke` — Owner
- `POST /v1/platform/events/read` — Owner

Machine-client routes are POST-only under `/v1/platform/client/*` and are documented in
`PLATFORM_SDK.md`. Machine credentials cannot substitute for a Bearer human session.

## SAD Chat

- `GET /v1/chat/sessions`
- `POST /v1/chat/sessions`
- `GET /v1/chat/sessions/{session_id}`
- `POST /v1/chat/sessions/{session_id}/messages`
- `POST /v1/chat/sessions/{session_id}/archive`

Message request:

```json
{
  "message": "What were we working on?",
  "use_memory": true
}
```

`use_memory` defaults to true. When enabled, SAD may provide enabled/non-expired saved
Personal Memory to the configured Local AI. The response includes `memory_used`, which
is true only when saved memory existed and the `local_model` engine actually handled the
turn. Built-in dialogue does not claim memory use.

## Voice Client Bridge

- `POST /v1/voice/turn`

Request:

```json
{
  "transcript": "Continue our discussion",
  "session_id": "optional-owned-chat-session-id",
  "use_memory": true
}
```

Response includes `session_id`, `reply`, `speech_text`, `engine`, `memory_used`,
`input_mode: transcript`, and `output_mode: text_for_local_tts`.

## Personal Memory

All Memory routes operate only on the signed-in account.

- `GET /v1/memory` — list owned memories
- `POST /v1/memory` — explicitly create a memory
- `POST /v1/memory/search` — search owned memory
- `POST /v1/memory/{memory_id}` — edit category/title/content/enabled/expiry
- `POST /v1/memory/{memory_id}/delete` — delete owned memory

Create example:

```json
{
  "category": "project",
  "title": "SAD direction",
  "content": "SAD is the platform; Forge is the game-learning module.",
  "enabled": true,
  "expires_at": null
}
```

Categories: `fact`, `preference`, `goal`, `project`, `note`.

SAD does not automatically write ordinary Chat messages into `memory.json`.

## Governed Tool Actions

- `GET /v1/tools` — available registered internal tools
- `GET /v1/tools/actions` — list owned action records
- `POST /v1/tools/actions` — create an action
- `GET /v1/tools/actions/{action_id}` — inspect an owned action
- `POST /v1/tools/actions/{action_id}/decision` — approve/reject when required
- `POST /v1/tools/actions/{action_id}/execute` — execute only when state is `ready`

Tier 3 tool IDs:

- `platform.status`
- `memory.search`
- `memory.remember`
- `memory.forget`

Create example:

```json
{
  "tool_id": "memory.remember",
  "args": {
    "category": "goal",
    "title": "Pilot goal",
    "content": "Complete host UAT"
  }
}
```

A state-changing action starts `awaiting_approval`. Execution before approval returns a
permission error. An approval request is explicit:

```json
{"decision":"approve"}
```

Rejected actions cannot execute. Action records are account-owned.

There is no generic shell/network/plugin/package/filesystem/Git action endpoint.

## Personal Study

- `POST /v1/study/plan`

`generate: true` requests configured loopback Local AI output. Normal Study permission
checks still apply.

## Forge Learning

- `POST /v1/forge/quests`
- `POST /v1/forge/hint`
- `POST /v1/forge/complete`
- `GET /v1/forge/progress`
- `GET /v1/forge/progress/{student_account_id}` — Teacher/Owner permission
- `GET /v1/students` — authorized roster/progress

## Developer Workspace

- `POST /v1/dev/workspaces/scope`
- `GET /v1/dev/workspaces`
- `POST /v1/dev/workspaces`
- `GET /v1/dev/workspaces/{workspace_id}`
- `POST /v1/dev/workspaces/{workspace_id}/execute`
- `POST /v1/dev/workspaces/{workspace_id}/apply` — Owner governance
- `POST /v1/dev/workspaces/{workspace_id}/rollback` — Owner governance

Generation is limited to the human-approved file scope in private `.sad_dev` worktrees.
Docker verification must pass before an applyable state exists. Exact tested hashes are
rechecked before live application. Git is not invoked by the coding/apply/rollback path.

## Failure and controlled repair

- `POST /v1/failures`
- `GET /v1/dashboard`
- `GET /v1/dashboard/failures`
- `GET /v1/dashboard/jobs`
- `POST /v1/jobs`
- `GET /v1/jobs/{work_item_id}`
- `POST /v1/failures/{failure_id}/review`
- `POST /v1/failures/{failure_id}/push`
- `POST /v1/jobs/{work_item_id}/approve-isolated`
- `POST /v1/jobs/{work_item_id}/start`
- `POST /v1/jobs/{work_item_id}/execute`
- `POST /v1/jobs/{work_item_id}/result`
- `POST /v1/jobs/{work_item_id}/decision`
- `POST /v1/jobs/{work_item_id}/close`

Forge/AI may draft and verify governed work but cannot grant its own approval or use Git.

## Accounts and paired devices

- `GET /v1/accounts`
- `POST /v1/accounts`
- `POST /v1/accounts/{account_id}/active`
- `POST /v1/mobile/pairings` — Owner/account management
- `GET /v1/mobile/devices`
- `POST /v1/mobile/devices/{device_id}/revoke`

## Mobile-only gateway routes

These exist on the separate TLS mobile gateway:

- `POST /mobile/pair`
- `GET /mobile/status`
- `POST /mobile/forget`

Learning-mode devices receive an explicit personal allow-list including Chat, Voice,
Memory, governed Tools, Study, Forge, and own progress. Development/admin routes remain
blocked. `/v1/platform/client/*` machine routes are blocked by Mobile even in full-role
mode.

## Privacy and event semantics

Runtime files such as accounts, conversations, Personal Memory, Tool Actions, student
progress, failures, platform clients/events, and coding/repair artifacts are private
host data and Git-ignored.

Memory/tool platform events are metadata-only. They may record event type, sequence,
subject ID, category/state/decision metadata, but not memory text/title, tool arguments
or output, conversation text, code/diffs, passwords, sessions, or secrets.

See `SECURITY.md`, `PLATFORM.md`, `MOBILE.md`, and `PLATFORM_TIER3_UAT.md`.
