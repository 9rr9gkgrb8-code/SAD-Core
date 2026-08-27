# SAD + Forge milestone status

Updated: August 27, 2026

## Completed

- Sandbox paths resolve under the proposal root; symlink and traversal targets are
  rejected. Live files and expanded Git topology are fingerprinted before/after.
- Production repair tests require a networkless, non-root, resource-limited Docker
  container using a preloaded digest-pinned image. Missing isolation fails closed.
- Approval and export reject failed or unavailable isolation states. Git and human
  authority remain outside Forge.
- SAD↔Forge schema v1.0 includes request, correlation, job and artifact IDs;
  deterministic test plans; terminal states; hashed durable diff/test/diagnostic/
  receipt artifacts; and no Forge approval or merge authority.
- Loopback HTTP/JSON API v1 provides health, login, failure, job, result, dashboard,
  Personal Study and Forge Student endpoints.
- One durable dashboard store supports Failure Inbox, review, suggested correction,
  explicit push, isolated-work approval, Forge status/results, evidence,
  approve/reject and close.
- Owner, developer, reviewer and viewer share the dashboard under distinct
  permissions. Student and teacher roles remain separate from admin controls.
- Failure and job state survives restart, deduplicates repeated failures, preserves
  ordered evidence and prevents duplicate work items under concurrent pushes.
- Personal Study exposes all requested help modes without a forced quiz loop.
- Forge Student exposes quests, homework conversion, hints, mastery, XP/ranks,
  companion state, boss checks and durable progress for student/teacher dashboards.
- Forge Student now presents those mechanics through a game-first Alpha interface:
  companion evolution, real XP-to-rank progress, a mastery path, quest board, active
  quest view, progressive hint ladder, and boss gate. Frontend rank thresholds are
  regression-tested against the backend progression contract.
- Local per-user authentication uses salted PBKDF2 hashes, expiring sessions,
  lockout, owner-controlled privileged account creation and no shared credential.
- GitHub CI compiles the project and runs the full test/contract/security suite.
- The Alpha release gate is tested and enforced by CI; it verifies required release
  surfaces and blocks retired private-mode implementation markers from returning to
  the current release tree, including Python, docs, browser JavaScript, HTML, and CSS.
- PR-triggered GitHub Actions verification has completed successfully with compile,
  full unit suite, Alpha release gate, and operator preflight all green.
- Alpha operator preflight reports core readiness separately from optional local-model
  configuration and Docker-backed repair-isolation readiness.
- GitHub Actions now performs a real Docker isolation proof after the core gate. The
  workflow explicitly preloads a Python image, resolves its immutable repository
  digest, requires `REPAIR ISOLATION: READY`, and executes a disposable test workspace
  through `DockerSandboxRunner` with the production boundary. The proof verifies
  non-root execution, a read-only workspace, writable tmpfs, stripped GitHub
  credentials, and unavailable external networking.
- Alpha 1 browser UI provides separate role-filtered Personal Study, Forge Student,
  teacher roster, Owner/Dev dashboard, account control, and security surfaces.
- Browser accessibility structure now has automated regression checks for form
  labels, keyboard order, visible focus, live announcements, navigation semantics,
  and data-table captions/column scopes.
- A role-by-role `ALPHA_UAT.md` protocol defines owner, student, teacher, developer,
  reviewer, viewer, security, accessibility, severity, stop, and Alpha-exit criteria.
- Personal Study can generate full output through the explicitly configured
  loopback-only local model and reports honestly when the model is unavailable.
- The host-controlled Forge worker turns approved jobs into isolated test evidence
  without receiving approval, export, merge, credential, or Git authority.
- Account lifecycle now includes owner listing/disable controls, self-service
  password changes, logout, and revocation of other sessions after password change.

## Remaining operational work

- Repeat the Docker proof on the actual deployment computer using the reviewed image
  approved for that machine. The Linux CI runner now proves the container code path,
  but it does not substitute for host-specific Docker Desktop/Windows verification.
- Execute the controlled human UAT protocol with representative student, teacher,
  owner, developer, reviewer, and viewer accounts. The protocol is defined; human
  pilot evidence is not yet claimed as complete.
- Perform the manual keyboard, screen-reader, 200% zoom, and narrow-viewport checks
  in `ALPHA_UAT.md`; automated structural accessibility checks do not replace them.
- Sessions are intentionally memory-only and require login again after API restart.
- Internet hosting remains deliberately unsupported for Alpha 1: TLS, hosted
  secrets, email recovery, and external identity are future-beta work.

## Verification gate

Run `python -m unittest -v`, `python -m compileall -q .`, `python release_gate.py`,
`python alpha_doctor.py`, and Protocol White. When Docker-backed repair readiness is
claimed, also run `python docker_proof.py` with the reviewed digest-pinned sandbox
image. A release is blocked if any core test fails, the worktree is dirty
unexpectedly, the release-integrity gate fails, container isolation is unavailable
for an actual repair, or live/Git integrity evidence fails.
