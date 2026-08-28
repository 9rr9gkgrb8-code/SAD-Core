# SAD + Forge Alpha 1

## Preflight

Run `python alpha_doctor.py` before the first launch or after changing local model or
sandbox configuration. The doctor reports Alpha core readiness separately from
repair-isolation readiness.

- `ALPHA CORE: READY` means the local browser product can be started.
- An unconfigured local model is optional for normal Alpha use. SAD Chat falls back
  visibly to the built-in dialogue layer, while automatic repair drafting and
  Developer Workspace planning/coding require a configured loopback-only local model.
- `REPAIR ISOLATION: BLOCKED` means automatic code verification remains disabled
  until Docker and a preloaded digest-pinned `SAD_SANDBOX_IMAGE` are available. It
  does not silently fall back to same-user execution.

The optional paired mobile preview has its own `python mobile_doctor.py` preflight
and is not considered ready until it reports `MOBILE GATEWAY: READY` on the actual
host configuration.

Use `.env.example` as the configuration reference. Never commit a real `.env` file.

## Start

For desktop-only Alpha, run `python alpha.py`, complete the one-time owner setup, then
open `http://127.0.0.1:8765/`. The core API remains loopback-only.

For the optional paired mobile preview, configure the private bind address and trusted
TLS certificate/key described in `MOBILE.md`, then run `python mobile.py`. This starts
the same loopback desktop service plus a separate paired TLS phone gateway.

The owner can create student, teacher, developer, reviewer, and viewer accounts.
Each person receives a separate credential. Students never see developer controls.

## Included surfaces

- **SAD Platform Core** with a versioned, role-filtered module/capability registry and
  read-only Platform dashboard. Clients can discover what the signed-in role may use
  without Platform metadata granting any authority.
- **SAD Chat** as the default free-form conversation lane, with durable per-account
  conversations, new/archive/history controls, recent-turn context, and visible
  `Local AI` versus `Built-in dialogue` response status
- **SAD Developer Workspace** for governed general-purpose coding: task → scope plan →
  human-approved paths → multi-file isolated generation → Docker full-suite test →
  exact diff → Owner apply/rollback
- Personal Study with all request-directed actions and optional local-model output
- Forge Student game-first learning surface with a quest board, active quest view,
  progressive hint ladder, boss gate, real XP/rank progress, mastery path, and
  companion evolution driven by durable Forge progress
- Teacher student-progress roster
- Owner account administration
- Owner Repair Inbox that presents each failure, suggested correction, affected
  targets, Forge sandbox evidence, and the exact tested code diff before YES/NO
- One-click Owner repair preparation that explicitly authorizes review, push,
  isolation approval, local-model repair drafting, and isolated Forge verification
- Owner YES applies only the exact passing repair proposal to the corresponding local
  live file, using a stale-source check, atomic replacement, verified hash, and a
  preserved proposal-local backup
- Shared role-filtered Failure Inbox and Forge job dashboard with advanced review,
  push, isolation approval, execution, decision, and close controls
- Optional Mobile Preview with installable PWA shell, one-time Owner pairing,
  revocable paired-device trust, learning-only/full-role modes, SAD Chat, and a
  TLS-only private gateway while the core API stays on loopback
- Password change and session revocation

## Platform Core boundary

Platform Core is the common contract joining SAD's existing capabilities into one
platform. It does not create a second authority system.

- `/v1/platform`, `/v1/platform/modules`, and `/v1/platform/capabilities` require a
  valid SAD account session.
- The registry filters modules/capabilities through the same `ROLE_PERMISSIONS` map
  used by the live API.
- A client may use the catalog to decide what to render, but concrete endpoint
  authorization remains authoritative.
- Platform metadata cannot create accounts, invoke code, approve repairs, apply files,
  bypass Docker, or exercise Git authority.
- Platform modules are declarative in Alpha. Registering/describing a module does not
  dynamically execute extension code.
- The established public `/health` response remains backward-compatible; the separate
  platform version is exposed in the signed-in Platform manifest.
- Future voice, desktop, mobile, and local-app clients should consume this common
  discovery contract rather than inventing independent feature/permission maps.

See `PLATFORM.md` for the detailed module and client contract.

## SAD Chat boundary

SAD Chat is conversation, not an authority bypass.

- Every chat session belongs to one authenticated account.
- Another account receives not-found/denial even if it knows the session ID.
- `chat_history.json` stays on the host, is excluded from Git, uses atomic writes,
  and is bounded so an oversized history fails before replacing the saved file.
- The configured local model receives only recent turns needed for conversational
  context rather than the entire saved transcript on every request.
- If the local model is not available, SAD explicitly labels the answer as built-in
  dialogue rather than pretending a full model generated it.
- Conversation text cannot approve repairs, create Developer Workspace authority,
  apply files, commit, push, merge, or otherwise exercise governed authority.

## Developer Workspace authority boundary

Developer Workspace is the broad coding lane; the failure-driven repair flow remains
the narrow self-correction lane.

- Scope planning may suggest file names but cannot write code.
- A human must submit the explicit approved file list before a workspace exists.
- The coding model sees source context only for approved paths and may edit only those
  paths inside `.sad_dev/<workspace-id>/worktree`.
- `.git`, `.github`, environment secrets, private runtime data, local data, hidden
  paths, other workspace/sandbox directories, and unsupported/binary file types are
  excluded from the coding worktree/scope.
- At most 20 paths/edits are admitted per Alpha workspace, with bounded context and
  generated file sizes.
- The complete repository unittest suite runs through the digest-pinned, networkless,
  non-root Docker boundary. Failed or unavailable isolation cannot be applied.
- Developer may plan, create, execute, and inspect. Reviewer/Viewer may inspect.
  Student/Teacher have no Code Workspace access.
- Only Owner may select **YES: Apply tested workspace** or rollback an application.
- Before application SAD rechecks every live base hash and every exact post-test
  worktree hash. Stale or tampered content blocks the entire transaction.
- Existing changed files are backed up before the first write. A failed multi-file
  operation restores and verifies the entire original set.
- Developer Workspace never invokes Git. Commit/push/fetch/rebase/merge and repository
  publication remain a separate host/human workflow.

See `DEVELOPER_WORKSPACE.md` for the detailed contract.

## Repair authority boundary

Forge may draft one tightly scoped edit in one approved root Python file and test it
inside the configured Docker boundary. The Owner must review the actual diff before
approving it. A failed Forge result disables the simple YES path.

For an Owner approval, SAD marks the passing sandbox draft human-approved and applies
that exact tested file locally. If the live file no longer matches the source hash,
application is refused. If the atomic write or dashboard persistence fails, SAD
restores the preserved original and verifies the rollback.

This does **not** grant Forge Git authority. The live-application code never commits,
pushes, rebases, or merges. Repository publication remains a separate host/human
workflow.

Reviewer approval remains evidence/governance approval only and does not apply a live
file. Developer and Forge roles still cannot approve or apply their own repair work.

## Mobile authority boundary

Pairing a phone does not create a user session. The phone must first prove a valid
paired-device credential and then the person must sign in through the normal SAD
authentication system.

`learning` mode allows SAD Chat plus account-self, Personal Study, Forge play, and own
progress through an explicit route allow-list. Developer Workspace and development
Platform administration surfaces are blocked. `full_role` mode allows the normal
route surface, but the signed-in account still has exactly its existing SAD
permissions. A Developer on a full-role phone can prepare and test code but cannot
apply it; Owner authority is still required. Device credentials are revocable and
kept from browser JavaScript in a Secure/HttpOnly/SameSite=Strict cookie.

The mobile service worker may cache Platform UI shell assets but never caches API,
pairing, platform manifests, chat, coding-workspace, student, account, repair,
session, or device-credential traffic.

## Acceptance

Before widening a local pilot, run the scenarios in `ALPHA_UAT.md`. They cover every
role, Platform role-filtering/authority separation, SAD Chat account isolation,
Developer Workspace scope/test/apply separation, security boundaries, keyboard and
screen-reader use, zoom/mobile layout, stop conditions, and the evidence required
before calling a candidate Alpha-ready.

Automated accessibility checks run with the normal unit suite, but they are a
regression net rather than a substitute for the manual accessibility pass.

Mobile Preview also requires host/phone validation of TLS trust, pairing, revocation,
SAD Chat, learning-mode route isolation, full-role RBAC, Code Workspace behavior for
full-role development accounts, install/home-screen behavior, and narrow-screen use
before it should be treated as operational on that device.

## Private data and backups

`accounts.json`, `dashboard_state.json`, `student_progress.json`, `chat_history.json`,
`failures.json`, `.env`, `local_data/`, `.sad_sandbox/`, and `.sad_dev/` are local
runtime data and are ignored by Git. Stop the app before copying those files into an
encrypted backup. Never put that backup in the public repository.

The `.sad_sandbox/<proposal-id>/` directory retains repair evidence/backups. The
`.sad_dev/<workspace-id>/` directory retains coding scope, isolated worktree, exact
diff/test evidence, application receipt, and any pre-application backups. Treat both
as private runtime data, not repository content.

## Isolation

Automatic repair and Developer Workspace verification require Docker plus a preloaded
digest-pinned image in `SAD_SANDBOX_IMAGE`. Without it, execution stops fail-closed;
there is no local-process fallback. AI components produce drafts/evidence only.
Human roles retain approval and Git authority.

## Alpha boundary

The core Alpha remains a local-first product. The normal SAD API deliberately refuses
non-loopback binding. The optional Mobile Preview is a separate paired TLS gateway
restricted to an explicit private/approved overlay address; it must not be
port-forwarded to the public internet.

Platform Core does not add public hosting, dynamic plugin execution, unattended
machine credentials, hosted identity, or an internet marketplace. Those remain future
platform work behind separate security contracts.

Public internet hosting, hosted TLS termination, email recovery, federation/external
identity, and hosted secret management remain outside Alpha.
