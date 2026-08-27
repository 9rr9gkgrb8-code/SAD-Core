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
- Local per-user authentication uses salted PBKDF2 hashes, expiring sessions,
  lockout, owner-controlled privileged account creation and no shared credential.
- GitHub CI compiles the project and runs the full test/contract/security suite.

## Remaining operational work

- Install Docker on the deployment machine, preload a reviewed Python image and set
  `SAD_SANDBOX_IMAGE` to its exact `name@sha256:<digest>`. This environment has no
  Docker/Podman, so real container execution cannot be demonstrated here; the
  production path records `isolation_unavailable` and does not fall back.
- Build a graphical dashboard if desired. The complete dashboard workflow is
  currently exposed as stable JSON endpoints, not a browser UI.
- Connect Personal Study plans to the configured local-model generation adapter for
  generated explanations/edits. The current module produces authoritative request
  plans and boundaries; it does not fabricate subject answers without a model.
- Sessions are intentionally memory-only and require login again after API restart.
- Run and inspect the first GitHub Actions CI result after this commit is pushed.

## Verification gate

Run `python -m unittest -v`, `python -m compileall -q .`, and Protocol White. A
release is blocked if any test fails, the worktree is dirty unexpectedly, container
isolation is unavailable for an actual repair, or live/Git integrity evidence fails.
