# SAD local API v1

The core API binds to loopback only and returns JSON. Protected endpoints require
`Authorization: Bearer <session token>`. Start the complete browser product with
`python alpha.py`, or start the API alone with `python api.py`.

The optional mobile surface does **not** change that core binding. `mobile.py` starts
a separate TLS-only paired gateway on one explicit private/overlay IPv4 address while
the normal SAD API remains on loopback.

## Core endpoints

- `GET /health`
- `POST /v1/auth/login`
- `GET /v1/auth/me`
- `POST /v1/auth/logout`
- `POST /v1/auth/password`
- `GET /v1/chat/sessions` — list the signed-in account's active conversations
- `POST /v1/chat/sessions` — start a new conversation
- `GET /v1/chat/sessions/{session_id}` — load one owned conversation
- `POST /v1/chat/sessions/{session_id}/messages` — send one message and persist the SAD reply
- `POST /v1/chat/sessions/{session_id}/archive` — archive an owned conversation
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
- `POST /v1/jobs/{work_item_id}/execute` (host-controlled draft + isolated verification)
- `POST /v1/jobs/{work_item_id}/result`
- `POST /v1/jobs/{work_item_id}/decision`
- `POST /v1/jobs/{work_item_id}/close`

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
- Conversation text does not grant tool, repair, approval, or Git authority. Those
  actions remain behind their existing explicit governed endpoints.

## Mobile gateway endpoints

These exist only on the paired TLS mobile gateway:

- `POST /mobile/pair` — consumes a valid one-time pairing code and sets the paired-device credential as a `Secure`, `HttpOnly`, `SameSite=Strict` cookie
- `GET /mobile/status` — verifies the paired-device cookie and returns public device metadata
- `POST /mobile/forget` — revokes the current paired device and clears the device cookie

A phone must pass the device gate **and** the normal account-login gate. Pairing never
creates a user session and never substitutes for SAD role authorization.

### Mobile device modes

- `learning`: admits SAD Chat, account-self, Personal Study, Forge play, and own-progress routes only. Chat routes are matched explicitly rather than by a broad prefix.
- `full_role`: the gateway admits the normal API surface, then SAD's existing RBAC
  decides what the signed-in role may actually do.

The device credential is hashed at rest and is never available to browser JavaScript.
The service worker excludes `/v1/*` and `/mobile/*` traffic, including conversation
requests and replies, from caching.

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
work and return correlated artifacts, diagnostics, and tests; it has no API action
for approval, Git commit, push, or merge authority.
