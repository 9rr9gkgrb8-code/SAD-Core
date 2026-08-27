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

## Mobile gateway endpoints

These exist only on the paired TLS mobile gateway:

- `POST /mobile/pair` — consumes a valid one-time pairing code and sets the paired-device credential as a `Secure`, `HttpOnly`, `SameSite=Strict` cookie
- `GET /mobile/status` — verifies the paired-device cookie and returns public device metadata
- `POST /mobile/forget` — revokes the current paired device and clears the device cookie

A phone must pass the device gate **and** the normal account-login gate. Pairing never
creates a user session and never substitutes for SAD role authorization.

### Mobile device modes

- `learning`: only account-self, Personal Study, Forge play, and own-progress routes
  are admitted by the gateway.
- `full_role`: the gateway admits the normal API surface, then SAD's existing RBAC
  decides what the signed-in role may actually do.

The device credential is hashed at rest and is never available to browser JavaScript.
The service worker excludes `/v1/*` and `/mobile/*` traffic from caching.

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
