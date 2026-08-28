# SAD + Forge milestone status

Updated: August 27, 2026

## Architecture direction

**SAD is the platform.** Chat, Voice, Personal Study, Forge Learning, Personal Memory,
Governed Tool Actions, Developer Workspace, controlled repair, accounts/roles, Mobile,
scoped local-app credentials, and platform events are governed SAD modules/clients.

The historical Protocol White audit remains recorded as blocked at its old independent
`Forge-Core` Gate 2. That separate-service topology is paused under the current
SAD-as-platform architecture and was not retroactively marked as passing.

## Current platform milestone

- Platform Core: **`0.3-alpha`**
- Platform manifest schema: **`3`**
- HTTP API: **`v1`**
- Core network binding: **loopback only**
- Dynamic plugin execution: **disabled**
- AI Git authority: **none**

## Completed platform capabilities

### Core/discovery

- Role-filtered `/v1/platform`, `/modules`, `/capabilities`, and compatibility negotiation.
- Capability version/lifecycle metadata.
- Backward-compatible minimal `/health` contract.
- Read-only Platform dashboard.

### Conversation and Voice

- Private durable per-account Chat sessions with multi-turn context.
- Visible Local AI vs Built-in dialogue engine status.
- Transcript-based Voice bridge using the same account-owned Chat history.
- Voice returns text suitable for a future local TTS client.

### Personal Memory

- Explicit per-account durable `memory.json` store.
- Categories: fact, preference, goal, project, note.
- Create/list/search/edit/enable/disable/expiry/delete.
- Cross-account memory access fails closed.
- Only enabled, non-expired memory may enter Local AI Chat/Voice context.
- Per-turn `use_memory: false` excludes saved Memory.
- Built-in dialogue never reports saved Memory use.
- Memory is Git-ignored and excluded from release-source scanning.

### Governed Tool Actions

- Fixed reviewed Tier 3 tool catalog:
  - `platform.status`
  - `memory.search`
  - `memory.remember`
  - `memory.forget`
- Per-account durable action records in ignored `tool_actions.json`.
- Read-only tools can execute when ready.
- State-changing personal tools require explicit approve/reject before execution.
- Rejected or unapproved mutation cannot execute.
- No generic shell, arbitrary network, dynamic plugin/Python loader, package installer,
  unrestricted filesystem action, or Git tool.

### Personal Study and Forge

- Request-directed Study help, including explanation, work checking, writing/essay/rubric
  help and optional Local AI generation.
- Forge quests, hints, mastery/boss checks, durable progress, XP/ranks, and companion
  progression.

### Coding and controlled repair

- Developer Workspace multi-file coding with human-approved scope, private worktree,
  strict generated edit plan, Docker verification, exact diff/test evidence, Owner-only
  apply/rollback, stale/tamper checks, backup, and whole-set restoration on failure.
- Failure-driven repair with strict scoped proposal, isolated verification, exact tested
  diff, Owner YES/NO, stale-source check, atomic local apply, backup, and rollback.
- Coding/repair agents have no Git commit/push/fetch/rebase/merge/credential authority.

### Platform apps/events

- Owner-managed scoped loopback `SAD-App` credentials.
- One-time app secrets, hashed at rest, rotation/revocation.
- Machine scopes limited to Platform discovery/catalog/modules/compatibility/events.
- Machine credentials cannot impersonate human users.
- Privacy-minimized bounded platform events.
- Tier 3 memory/tool lifecycle events contain metadata only, not private Memory content,
  tool arguments/output, conversations, code/diffs, or secrets.
- Standard-library loopback Python SDK.

### Mobile/PWA

- Separate TLS-only paired mobile gateway while Core remains loopback-only.
- One-time pairing, expiry, throttling, device revocation, Secure/HttpOnly/SameSite=Strict
  paired-device cookie.
- Learning mode allows exact personal routes for Chat, Voice, Memory, governed Tools,
  Study, Forge, and own progress.
- Full-role mode still defers human routes to account RBAC.
- `SAD-App` machine endpoints are blocked through Mobile in all device modes.
- Memory & Tools phone-first PWA surface.
- Service worker caches static shell only and excludes all `/v1/*` and `/mobile/*` data.

## Automated verification

Tier 3 automated coverage includes:

- Memory account isolation/search/edit/delete.
- enabled/disabled/expired context behavior.
- Local AI Memory injection and per-turn opt-out.
- governed tool ownership and mutation approval.
- unknown tool rejection.
- event privacy.
- mobile exact-route admission and privileged denial.
- Memory & Tools responsive/accessibility/PWA-cache contract.
- Platform registry schema/version/authority metadata.
- existing Chat/Voice/Study/Forge/coding/repair/account/mobile security regressions.
- compile and browser JavaScript syntax checks.
- Alpha release integrity/preflight.
- real CI Docker isolation proof.

## Remaining operational work

The code milestone is not the same as deployment proof. Remaining host/device work:

1. Pull the final merged `main` commit to the deployment Windows computer.
2. Configure and validate the intended local model.
3. Repeat the reviewed Docker proof on that actual host.
4. Run base Alpha human UAT for all representative roles.
5. Run `PLATFORM_TIER2_UAT.md` local-app/event/Voice transport checks.
6. Run `PLATFORM_TIER3_UAT.md` Memory/Tool ownership, context, approval, event privacy,
   mobile, PWA, keyboard, screen-reader, zoom, and narrow-screen checks.
7. Configure phone-trusted TLS/private bind address and require
   `python mobile_doctor.py` → `MOBILE GATEWAY: READY` before claiming mobile operation.
8. Pair/test real iPhone/Android devices for any platform support that will be claimed.
9. Add real local STT + TTS if full microphone-to-speaker Voice is desired.
10. Add Windows packaging/installer/service only after host-level Alpha behavior is
    accepted and migration/backup rules are defined.

## Current release gate

For the SAD-as-platform Alpha candidate, require:

```text
python -m compileall -q .
python -m unittest -v
python release_gate.py
python alpha_doctor.py
```

Automatic coding/repair readiness also requires `python docker_proof.py` using the
reviewed digest-pinned sandbox image. Mobile operation additionally requires
`mobile_doctor.py` and device-specific UAT.

A release is blocked by any failing core test, release-integrity failure, authority
leak, Memory/tool cross-account access, unapproved mutating tool execution, private-data
cache/source leakage, unavailable required coding isolation, stale/tampered tested code,
or failed live/Git integrity evidence.
