# SAD + Forge Alpha 1

## Preflight

Run `python alpha_doctor.py` before the first launch or after changing local model or
sandbox configuration. The doctor reports Alpha core readiness separately from
repair-isolation readiness.

- `ALPHA CORE: READY` means the local browser product can be started.
- An unconfigured local model is optional for normal Alpha use, but automatic Forge
  repair drafting requires a configured loopback-only local model.
- `REPAIR ISOLATION: BLOCKED` means Forge repair execution remains disabled until
  Docker and a preloaded digest-pinned `SAD_SANDBOX_IMAGE` are available. It does
  not silently fall back to same-user execution.

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
- Owner YES applies only the exact passing sandbox proposal to the corresponding
  local live file, using a stale-source check, atomic replacement, verified hash,
  and a preserved proposal-local backup
- Shared role-filtered Failure Inbox and Forge job dashboard with advanced review,
  push, isolation approval, execution, decision, and close controls
- Optional Mobile Preview with installable PWA shell, one-time Owner pairing,
  revocable paired-device trust, learning-only/full-role modes, and TLS-only private
  gateway while the core API stays on loopback
- Password change and session revocation

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
file. Developer and Forge roles still cannot approve or apply their own work.

## Mobile authority boundary

Pairing a phone does not create a user session. The phone must first prove a valid
paired-device credential and then the person must sign in through the normal SAD
authentication system.

`learning` mode allows only account-self, Personal Study, Forge play, and own progress.
`full_role` mode allows the normal route surface, but the signed-in account still has
exactly its existing SAD permissions. Device credentials are revocable and kept from
browser JavaScript in a Secure/HttpOnly/SameSite=Strict cookie.

The mobile service worker never caches API, pairing, student, account, repair, session,
or device-credential traffic.

## Acceptance

Before widening a local pilot, run the scenarios in `ALPHA_UAT.md`. They cover every
role, security boundaries, keyboard and screen-reader use, zoom/mobile layout, stop
conditions, and the evidence required before calling a candidate Alpha-ready.

Automated accessibility checks run with the normal unit suite, but they are a
regression net rather than a substitute for the manual accessibility pass.

Mobile Preview also requires host/phone validation of TLS trust, pairing, revocation,
learning-mode route isolation, full-role RBAC, install/home-screen behavior, and
narrow-screen use before it should be treated as operational on that device.

## Private data and backups

`accounts.json`, `dashboard_state.json`, `student_progress.json`, `failures.json`,
`.env`, `local_data/`, and `.sad_sandbox/` are local runtime data and are ignored by
Git. Stop the app before copying those files into an encrypted backup. Never put
that backup in the public repository.

The `.sad_sandbox/<proposal-id>/` directory also retains the approved patch and local
pre-application backup used for repair evidence/rollback. Treat it as private runtime
data, not repository content.

## Isolation

Forge verification requires Docker plus a preloaded digest-pinned image in
`SAD_SANDBOX_IMAGE`. Without it, execution stops as `isolation_unavailable`; there
is no local-process fallback. Forge produces repair drafts and evidence only. Human
roles retain approval and Git authority.

## Alpha boundary

The core Alpha remains a local-first product. The normal SAD API deliberately refuses
non-loopback binding. The optional Mobile Preview is a separate paired TLS gateway
restricted to an explicit private/approved overlay address; it must not be
port-forwarded to the public internet.

Public internet hosting, hosted TLS termination, email recovery, federation/external
identity, and hosted secret management remain outside Alpha.
