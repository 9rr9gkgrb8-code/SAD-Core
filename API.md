# SAD local API v1

The core API binds to loopback only and returns JSON. Human protected endpoints require
`Authorization: Bearer <session token>`. Scoped local-app endpoints use a separate
`Authorization: SAD-App <client-id>.<secret>` credential and are intentionally limited
to Platform control-plane reads.

Start the browser product with `python alpha.py`, or the API alone with `python api.py`.
The optional mobile surface does **not** change the core binding. `mobile.py` starts a
separate TLS-only paired gateway on one explicit private/overlay IPv4 address while the
normal SAD API remains on loopback.

## Human/session endpoints

### Health and authentication

- `GET /health` — established minimal `{status, api_version}` contract
- `POST /v1/auth/login`
- `GET /v1/auth/me`
- `POST /v1/auth/logout`
- `POST /v1/auth/password`

### Platform Core

- `GET /v1/platform` — signed-in role-filtered manifest
- `GET /v1/platform/modules` — visible modules/capabilities
- `GET /v1/platform/capabilities` — flattened visible capability catalog
- `POST /v1/platform/compatibility` — role-filtered capability-version negotiation
- `GET /v1/platform/clients` — Owner-only local-app list
- `POST /v1/platform/clients` — Owner-only local-app creation
- `POST /v1/platform/clients/{client_id}/rotate` — Owner-only secret rotation
- `POST /v1/platform/clients/{client_id}/revoke` — Owner-only revocation
- `POST /v1/platform/events/read` — Owner-only metadata event inspection

### SAD Chat and Voice

- `GET /v1/chat/sessions`
- `POST /v1/chat/sessions`
- `GET /v1/chat/sessions/{session_id}`
- `POST /v1/chat/sessions/{session_id}/messages`
- `POST /v1/chat/sessions/{session_id}/archive`
- `POST /v1/voice/turn` — signed-in transcript bridge into the same account-owned SAD conversation engine

### Developer Workspace

- `POST /v1/dev/workspaces/scope`
- `GET /v1/dev/workspaces`
- `POST /v1/dev/workspaces`
- `GET /v1/dev/workspaces/{workspace_id}`
- `POST /v1/dev/workspaces/{workspace_id}/execute`
- `POST /v1/dev/workspaces/{workspace_id}/apply`
- `POST /v1/dev/workspaces/{workspace_id}/rollback`

### Accounts and mobile trust

- `GET /v1/accounts`
- `POST /v1/accounts`
- `POST /v1/accounts/{account_id}/active`
- `GET /v1/students`
- `POST /v1/mobile/pairings`
- `GET /v1/mobile/devices`
- `POST /v1/mobile/devices/{device_id}/revoke`

### Failure/repair governance

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
- `POST /v1/jobs/{work_item_id}/execute`
- `POST /v1/jobs/{work_item_id}/result`
- `POST /v1/jobs/{work_item_id}/decision`
- `POST /v1/jobs/{work_item_id}/close`

### Learning

- `POST /v1/study/plan`
- `POST /v1/forge/quests`
- `POST /v1/forge/hint`
- `POST /v1/forge/complete`
- `GET /v1/forge/progress`
- `GET /v1/forge/progress/{student_account_id}`

## Platform Core v0.2 semantics

Platform Core gives clients one discovery and compatibility surface for the whole SAD
platform. The API contract stays `v1`; Platform Core is separately versioned as
`0.2-alpha`, manifest schema `2`.

Each capability now reports:

- `capability_version` (`major.minor.patch`)
- `lifecycle` (`alpha`, `stable`, or `deprecated`)
- optional `replacement`
- routes
- permission requirement
- whether it mutates state
- whether it crosses a human-approval boundary

Platform metadata is descriptive only. A returned capability does not authorize its
route. The concrete route performs its normal authentication, permission, workflow,
source-hash, isolation, and approval checks independently.

### Compatibility request

`POST /v1/platform/compatibility` accepts:

```json
{
  "requirements": [
    {"capability_id": "voice:conversation", "min_version": "1.0.0"}
  ]
}
```

The result reports whether each capability is visible to the signed-in role and whether
the available version meets the minimum. A capability hidden from that role is reported
unavailable, not leaked through negotiation metadata.

## Local app credentials

Owner can create a local app credential through the Platform screen or
`POST /v1/platform/clients`:

```json
{
  "name": "Workshop status panel",
  "capability_ids": ["platform:discover", "platform:events"],
  "event_types": ["failure.created"]
}
```

Allowed machine scopes are deliberately narrow:

- `platform:discover`
- `platform:catalog`
- `platform:modules`
- `platform:compatibility`
- `platform:events`

The creation/rotation response includes `client_secret` once. `platform_clients.json`
stores only a salted hash. Listing never returns the secret/hash/salt. Rotation
invalidates the previous secret. Revocation disables the app.

A machine credential is not a user session. Supplying `SAD-App ...` to a normal Chat,
Study, Forge, coding, repair, account, or admin route fails the Bearer-session gate.

## Machine-client endpoints

These endpoints are available only on the loopback core API. The mobile gateway blocks
the entire `/v1/platform/client/*` path family even for a `full_role` paired device.

All are `POST`:

- `/v1/platform/client/manifest` — requires `platform:discover`
- `/v1/platform/client/catalog` — requires `platform:catalog`
- `/v1/platform/client/modules` — requires `platform:modules`
- `/v1/platform/client/compatibility` — requires `platform:compatibility`
- `/v1/platform/client/events` — requires `platform:events`

Machine manifests explicitly report:

- principal kind `local_app`
- `user_impersonation: false`
- `state_mutation: false`
- `dynamic_extension_execution: false`
- `git_authority: none`

See `PLATFORM_SDK.md` for the Python helper and examples.

## Platform event semantics

`platform_events.py` maintains a bounded metadata-only event log in private
`platform_events.json`.

An event contains:

- monotonic `seq`
- UUID `event_id`
- `event_type`
- timestamp
- optional `subject_id`
- small bounded `details` object

The event layer deliberately excludes conversation text, generated code, diffs,
passwords, session/app/device secrets, student work, and other high-value payloads.

A local app sees only event types explicitly approved on its stored client record. An
empty subscription returns no events. Unsupported event types fail closed.

## Voice Client Bridge

`POST /v1/voice/turn` requires a normal signed-in SAD user session. It accepts:

```json
{
  "session_id": "optional-existing-chat-session-id",
  "transcript": "What should I check first?"
}
```

If `session_id` is absent, SAD creates a normal account-owned chat session. The
transcript goes through the same conversation history/model path as SAD Chat.

Response:

```json
{
  "session_id": "...",
  "reply": "...",
  "speech_text": "...",
  "engine": "local_model",
  "input_mode": "transcript",
  "output_mode": "text_for_local_tts"
}
```

This milestone does not bundle browser microphone capture, STT, or TTS. The endpoint
is the stable transport contract those future local voice clients can call. It grants
no repair, coding, app-management, account, or Git authority.

Learning-mode phones may call `/v1/voice/turn` after the normal paired-device gate and
user login.

## SAD Chat semantics

SAD Chat is the general free-form conversation surface, separate from Personal Study,
Forge quests, Developer Workspace, and repair governance.

- Sessions belong to exactly one account.
- Active history persists in ignored `chat_history.json`.
- Only recent turns are supplied to the configured local model for context.
- Model replies report `engine: local_model`; unavailable model uses and reports
  `engine: built_in`.
- Conversation wording cannot itself approve repairs, create coding authority, apply
  files, manage apps, commit, push, or merge.

## Developer Workspace semantics

Developer Workspace is the broad multi-file coding lane; the failure-driven repair flow
remains the narrow self-correction lane.

`development:work` may plan/create/execute an explicitly scoped private workspace.
Generation sees only approved paths. `.git`, `.github`, environment secrets, private
runtime data, hidden paths, and unsupported/binary files are excluded.

The full repository unittest suite runs through the digest-pinned, networkless,
non-root Docker boundary. Failed/unavailable isolation cannot become applyable.

Only Owner `development:govern` can apply or rollback the exact tested file set. Before
application SAD rechecks live base hashes and post-test worktree hashes. Existing files
are backed up and a failed multi-file operation restores/verifies the whole original
set. Developer Workspace never invokes Git.

See `DEVELOPER_WORKSPACE.md` for the full contract.

## Mobile gateway endpoints

These exist only on the paired TLS mobile gateway:

- `POST /mobile/pair`
- `GET /mobile/status`
- `POST /mobile/forget`

A phone must pass device trust **and** normal SAD account login. Pairing never creates a
user session.

### Mobile modes

- `learning`: account-self, SAD Chat, Voice bridge, Personal Study, Forge play, and own
  progress through explicit route matching. Developer/admin/machine-client routes are
  denied.
- `full_role`: normal user routes are admitted and SAD RBAC remains authoritative, but
  machine-client `/v1/platform/client/*` routes are still blocked at the gateway.

The paired-device credential remains a `Secure`, `HttpOnly`, `SameSite=Strict` cookie.
The PWA service worker excludes all `/v1/*` and `/mobile/*` traffic from caching.

## Repair decision semantics

Repair execution creates one scoped local-model draft and verifies the changed sandbox
through the configured Docker boundary. Successful results contain exact diff/test
artifacts and a correlated execution receipt.

For `decision: approve`:

- **Owner:** may apply the exact tested proposal after stale-source validation, atomic
  replacement, hash verification, and backup creation.
- **Reviewer:** records review evidence only; no live application.
- **Developer/Forge:** cannot approve.

Reject never applies. Close remains Owner governance. No repair path invokes Git
commit/push/merge authority.

## Learning semantics

Personal Study follows the requested help mode. Forge supplies quests, hints, mastery,
XP/rank/companion progression, and durable student progress. Neither learning surface
inherits repair, app-management, code-application, or Git authority.
