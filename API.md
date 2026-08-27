# SAD local API v1

The API binds to loopback only and returns JSON. Protected endpoints require
`Authorization: Bearer <session token>`. Start the complete browser product with
`python alpha.py`, or start the API alone with `python api.py`.

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
