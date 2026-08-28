# SAD local API v1

The core API binds to loopback only and returns JSON. Protected endpoints require
`Authorization: Bearer <session token>`. Start the complete browser product with
`python alpha.py`, or start the API alone with `python api.py`.

The optional mobile surface does **not** change that core binding. `mobile.py` starts
a separate TLS-only paired gateway on one explicit private/overlay IPv4 address while
the normal SAD API remains on loopback.

## Core endpoints

- `GET /health` — minimal service health plus API/platform versions
- `POST /v1/auth/login`
- `GET /v1/auth/me`
- `POST /v1/auth/logout`
- `POST /v1/auth/password`
- `GET /v1/platform` — signed-in role-filtered SAD platform manifest
- `GET /v1/platform/modules` — modules visible to the signed-in role
- `GET /v1/platform/capabilities` — flattened capability catalog visible to the signed-in role
- `GET /v1/chat/sessions` — list the signed-in account's active conversations
- `POST /v1/chat/sessions` — start a new conversation
- `GET /v1/chat/sessions/{session_id}` — load one owned conversation
- `POST /v1/chat/sessions/{session_id}/messages` — send one message and persist the SAD reply
- `POST /v1/chat/sessions/{session_id}/archive` — archive an owned conversation
- `POST /v1/dev/workspaces/scope` — Owner/Developer asks the local model for file-scope suggestions only
- `GET /v1/dev/workspaces` — development roles list coding workspaces
- `POST /v1/dev/workspaces` — Owner/Developer creates an isolated workspace from an explicitly approved scope
- `GET /v1/dev/workspaces/{workspace_id}` — development roles inspect task, scope, diff, tests, and evidence
- `POST /v1/dev/workspaces/{workspace_id}/execute` — Owner/Developer generates scoped code and runs Docker verification
- `POST /v1/dev/workspaces/{workspace_id}/apply` — Owner-only live application of the exact tested file set
- `POST /v1/dev/workspaces/{workspace_id}/rollback` — Owner-only verified rollback of an applied workspace
- `GET /v1/accounts` (owner)
- `POST /v1/accounts` (role-permitted account creation)
- `POST /v1/accounts/{account_id}/active` (owner)
- `GET /v1/students` (teacher/owner roster and progress)
- `POST /v1/mobile/pairings` (owner; creates a one-time 5-minute device code)
- `GET /v1/mobile/devices` (owner)
- `POST /v1/mobile/devices/{device_id}/revoke` (owner)
- `POST /v1/failures`
- `POST /v1/jobs`
- `GET /v1/jobs/{work_item_id}`
- `GET /v1/dashboard`
- `GET /v1/dashboard/failures`
- `GET /v1/dashboard/jobs`
- `POST /v1/failures/{failure_id}/review`
- `POST /v1/failures/{failure_id}/push`
- `POST /v1/jobs/{work_item_id}/approve-isolated`
- `POST /v1/jobs/{work_item_id}/start`
- `POST /v1/jobs/{work_item_id}/execute` (host-controlled repair draft + isolated verification)
- `POST /v1/jobs/{work_item_id}/result`
- `POST /v1/jobs/{work_item_id}/decision`
- `POST /v1/jobs/{work_item_id}/close`

## Platform Core semantics

Platform Core gives SAD clients one stable discovery surface for Chat, Study, Forge,
Developer Workspace, repair governance, accounts, Mobile, and future modules.

The detailed platform endpoints require a valid SAD login. Their output is filtered by
the signed-in role's existing permission set. A Student does not receive Owner coding
or account-management capabilities; a Viewer receives development visibility but not
work/govern authority; an Owner receives the full Alpha role-permitted catalog.

Platform metadata is descriptive only. A returned capability does not authorize its
route. The concrete route performs its normal authentication, permission, workflow,
source-hash, isolation, and human-approval checks independently.

The platform manifest reports this boundary explicitly through
`platform_metadata_grants_authority: false` and `git_authority: human_host_only`.

See `PLATFORM.md` for module/capability shapes and client integration rules.

## SAD Chat semantics

SAD Chat is the general free-form conversation surface. It is distinct from Personal
Study, Forge quests, and the governed repair workflow.

- Chat sessions belong to exactly one account and cannot be read by another account.
- Active history is persisted in local `chat_history.json`, which is excluded from Git
  and written with owner-only file permissions where the operating system supports it.
- Only recent turns are supplied to the local model for conversational context; the
  full saved transcript is not blindly inserted into every prompt.
- When the configured loopback local model is available, chat replies use that model
  and report `engine: local_model`.
- If the local model is unavailable, SAD falls back to its built-in dialogue layer and
  reports `engine: built_in` rather than pretending a model-generated answer occurred.
- Conversation text does not grant tool, repair, approval, coding-workspace, or Git
  authority. Those actions remain behind their existing explicit governed endpoints.

## Developer Workspace semantics

Developer Workspace is SAD's general multi-file coding lane. It does not replace the
narrow failure-driven repair workflow.

### Scope planning

`POST /v1/dev/workspaces/scope` requires `development:work`. The local model receives
the task plus eligible project file names and may suggest up to 20 source paths. It
writes no code and persists no workspace. The returned paths are recommendations for
human review only.

### Workspace creation

`POST /v1/dev/workspaces` requires `development:work` and accepts:

```json
{
  "task": "Build the feature",
  "allowed_paths": ["api.py", "web/app.js", "test_feature.py"]
}
```

Creation captures source hashes and makes a private `.sad_dev/<uuid>/worktree` copy.
Git control metadata, `.github`, private runtime JSON, credentials, environment
secrets, local data, and other protected paths are excluded from the coding copy.

### Execution

`POST /v1/dev/workspaces/{id}/execute` requires `development:work`.

The configured local model receives source context only for the explicitly approved
paths. It returns a strict JSON full-file edit plan. SAD rejects unapproved paths,
duplicate edits, malformed JSON, no-op edits, unsupported/binary file types, and
oversized context/output.

Edits occur only inside the private worktree. SAD then runs the repository unittest
suite through the same digest-pinned, networkless, non-root Docker boundary used by
repair verification. The response includes the exact unified diff, changed path list,
test output, and integrity evidence. Failed or unavailable isolation never becomes an
applyable state.

### Application and rollback

`POST /v1/dev/workspaces/{id}/apply` requires Owner-only `development:govern`.
Developer, Reviewer, Viewer, Student, Teacher, and the coding model cannot call the
live application boundary successfully.

Before the first write SAD verifies every changed live path still matches its captured
base hash and every worktree path still matches the exact post-test hash. Existing
files are backed up. The exact tested file set is then applied. If any file operation
or verification fails, SAD restores and verifies the whole original set.

`POST /v1/dev/workspaces/{id}/rollback` is also Owner-only and refuses rollback if a
live target changed after application. Git commands are never invoked by either
operation.

See `DEVELOPER_WORKSPACE.md` for the complete contract.

## Mobile gateway endpoints

These exist only on the paired TLS mobile gateway:

- `POST /mobile/pair` — consumes a valid one-time pairing code and sets the paired-device credential as a `Secure`, `HttpOnly`, `SameSite=Strict` cookie
- `GET /mobile/status` — verifies the paired-device cookie and returns public device metadata
- `POST /mobile/forget` — revokes the current paired device and clears the device cookie

A phone must pass the device gate **and** the normal account-login gate. Pairing never
creates a user session and never substitutes for SAD role authorization.

### Mobile device modes

- `learning`: admits SAD Chat, account-self, Personal Study, Forge play, and own-progress routes only. Chat routes are matched explicitly rather than by a broad prefix. Developer Workspace and Platform administration surfaces are denied.
- `full_role`: the gateway admits the normal API surface, then SAD's existing RBAC
  decides what the signed-in role may actually do. An Owner can use Code Workspace
  and the read-only Platform dashboard; a Developer can prepare/test but still cannot
  apply; lower roles retain their limits.

The device credential is hashed at rest and is never available to browser JavaScript.
The service worker excludes `/v1/*` and `/mobile/*` traffic, including conversation,
platform discovery, and Developer Workspace API data, from caching.

### Repair decision semantics

`execute` asks Forge to create one scoped repair draft for an approved target and
runs the resulting sandbox copy through the configured Docker verification boundary.
A successful result contains the exact diff plus an execution receipt that correlates
the tested proposal.

For `decision: approve`:

- **Owner:** SAD requires a successful Forge result and applyable proposal receipt,
  marks that sandbox draft human-approved, verifies the live target still matches
  the proposal source hash, then atomically applies the exact tested file. A backup
  is retained under the proposal directory. Git commit/push/merge is never invoked.
- **Reviewer:** records the human review decision only. Reviewer approval does not
  apply a live file.
- **Developer/Forge:** cannot approve.

`decision: reject` never applies a file. `close` remains an Owner governance action.

## Learning endpoints

- `POST /v1/study/plan` (`generate: true` requests configured local-model output)
- `POST /v1/forge/quests`
- `POST /v1/forge/hint`
- `POST /v1/forge/complete`
- `GET /v1/forge/progress`
- `GET /v1/forge/progress/{student_account_id}` (teacher/owner)

SAD owns approval, live application, and closure. Forge may draft and test approved
repair work; the general coding agent may draft and test approved Developer Workspace
scope. Neither has API authority for Owner approval, Git commit, push, or merge.
