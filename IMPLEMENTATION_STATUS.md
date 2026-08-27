# SAD + Forge milestone status

Updated: August 27, 2026

## Completed

- Sandbox paths resolve under the proposal root; symlink and traversal targets are
  rejected. Live files and expanded Git topology are fingerprinted before/after.
- Production automatic-code tests require a networkless, non-root, resource-limited
  Docker container using a preloaded digest-pinned image. Missing isolation fails closed.
- Approval and application reject failed or unavailable isolation states. Git authority
  remains outside Forge and the general coding agent.
- SAD↔Forge schema v1.0 includes request, correlation, job and artifact IDs;
  deterministic test plans; terminal states; hashed durable diff/test/diagnostic/
  receipt artifacts; and no Forge approval or merge authority.
- Loopback HTTP/JSON API v1 provides health, login, SAD Chat, Developer Workspace,
  failure, job, result, dashboard, Personal Study and Forge Student endpoints.
- SAD Chat provides a dedicated general-conversation lane separate from Forge and
  repair governance. It supports durable per-account sessions, new/history/archive,
  multi-turn recent context, and visible Local AI vs Built-in dialogue status.
- Conversation ownership is enforced by account ID. A different signed-in account
  cannot read a conversation by guessing or learning its UUID.
- Chat history is local-only in Git-ignored `chat_history.json`, written atomically
  with restrictive permissions where supported, bounded before save, and excluded
  from the service-worker cache.
- SAD Chat sends recent turns to the configured loopback local model. When the model
  is unavailable, SAD explicitly uses and labels the limited built-in dialogue layer.
- Conversation text has no repair, coding-workspace, file, shell, approval, or Git
  authority. Governed actions remain behind their explicit role and approval endpoints.
- SAD Developer Workspace provides the general-purpose coding lane: task → scope
  suggestion → human-approved file list → multi-file isolated generation → Docker
  verification → exact diff/test evidence → Owner-only application or rollback.
- Developer Workspace scope planning writes no code. It returns only validated file
  suggestions and accepts at most 20 explicitly approved text-source paths per Alpha
  workspace.
- Developer Workspace rejects traversal, absolute/symlink paths, hidden/control-plane
  paths, `.git`, `.github`, other SAD workspaces/sandboxes, local runtime data,
  account/chat/progress/failure state, environment secrets, and unsupported/binary
  file types.
- `.sad_dev/<workspace-id>/worktree` is a private stripped source/test copy. Git and
  repository-control metadata are absent; private runtime data is not copied; the
  directory is excluded from Git and release-source scanning.
- The general coding model sees source content only for the human-approved scope and
  must return strict JSON full-file write/delete operations. Unapproved/duplicate
  paths, nonexistent deletes, no-op edits, malformed JSON, and oversized output fail
  closed before testing.
- Developer Workspace supports multi-file updates, new files, and deletions. The live
  project remains unchanged while the model works and while Docker verification runs.
- Developer Workspace runs the repository unittest suite through the same preloaded,
  digest-pinned, networkless, non-root Docker boundary used for repair verification.
  Failed tests or unavailable isolation cannot become applyable.
- Every tested Developer Workspace records changed paths, exact unified diff, bounded
  test output, post-test file hashes, scope evidence, live/Git integrity evidence,
  and `git_authority_used: false`.
- Before Owner application, SAD verifies every changed live path still matches its
  captured base hash and every isolated file still matches the exact post-test hash.
  Stale live source or a tampered tested worktree blocks the whole transaction.
- Owner-only Developer Workspace application backs up all existing changed files and
  applies the exact tested file set. A failed write/verification or persistence error
  restores and verifies the entire original set rather than leaving a partial update.
- Owner rollback is receipt/hash controlled and refuses to overwrite newer human work
  if any live target changed after application.
- Developer may plan, create, execute and inspect Developer Workspaces but cannot
  apply/rollback them. Reviewer/Viewer are inspection-only. Student/Teacher have no
  Developer Workspace access. Only Owner `development:govern` crosses live-code authority.
- Developer Workspace application/rollback never invokes Git commit, push, fetch,
  rebase, merge, branches, remotes, index operations, or repository credentials.
- Code Workspace is a dedicated desktop/mobile browser surface showing task/scope,
  workspace state, changed paths, exact diff, test output, and role-filtered actions.
- Full-role mobile devices preserve the same Developer Workspace RBAC: Developer can
  prepare/test but only Owner can apply. Learning-mode phones deny all coding-workspace
  routes at the gateway.
- Code Workspace static JS/CSS may be installed with the PWA shell, but all `/v1/*`
  workspace API data, including diffs and test evidence, remains excluded from the
  service-worker cache.
- Developer Workspace regression tests cover protected path handling, scope planning,
  stripped worktree, multi-file generation, failed-test blocking, stale/tamper checks,
  update/create/delete application, role separation, mobile denial, exact-diff UI,
  whole-set automatic rollback, explicit rollback, and release-private-data exclusion.
- One durable dashboard store supports Failure Inbox, review, suggested correction,
  explicit push, isolated-work approval, Forge status/results, evidence,
  approve/reject and close.
- Owner, developer, reviewer and viewer share the dashboard under distinct
  permissions. Student and teacher roles remain separate from admin controls.
- Failure and job state survives restart, deduplicates repeated failures, preserves
  ordered evidence and prevents duplicate work items under concurrent pushes.
- Owner Repair Inbox provides the normal failure → generate/test → review exact
  diff → YES/NO path while preserving the advanced workflow underneath.
- Forge repair execution creates a real single-file draft through the configured
  loopback local model. Planner output must be JSON-only, match one exact source
  location, stay within an approved root target, and make an actual change.
- Forge tests the changed sandbox copy and returns the exact diff, test evidence, and
  correlated proposal receipt. A failed result cannot use the simple Owner YES path.
- Owner YES marks the passing repair proposal human-approved and applies only that exact
  tested file to the local live project after a stale-source hash check. Application
  is atomic, verifies the resulting hash, retains the original under the proposal,
  and automatically restores it if the write or dashboard persistence fails.
- Reviewer repair approval remains evidence/governance approval only. Developer and
  Forge roles cannot approve or apply live repair changes.
- Live repair application never invokes Git commit, push, rebase, or merge authority.
  Repository publication remains a separate host/human action.
- Live-application regression tests cover strict repair-plan parsing, exact patch
  application, stale-target refusal, Owner-vs-Reviewer authority, preserved backup,
  and verified rollback.
- Personal Study exposes all requested help modes without a forced quiz loop.
- Forge Student exposes quests, homework conversion, hints, mastery, XP/ranks,
  companion state, boss checks and durable progress for student/teacher dashboards.
- Forge Student presents those mechanics through a game-first Alpha interface:
  companion evolution, real XP-to-rank progress, a mastery path, quest board, active
  quest view, progressive hint ladder, and boss gate. Frontend rank thresholds are
  regression-tested against the backend progression contract.
- Local per-user authentication uses salted PBKDF2 hashes, expiring sessions,
  lockout, owner-controlled privileged account creation and no shared credential.
- Mobile Preview includes a phone-first installable PWA shell, safe-area/touch
  layout, install hooks, online/offline status, and static-shell-only service-worker
  caching. API, pairing, chat, coding-workspace and private data traffic are excluded.
- Mobile device trust uses Owner-generated one-time 8-digit codes, five-minute expiry,
  single-use consumption, pairing-attempt throttling, 30-day device expiry, and
  Owner revocation. Pairing codes/device tokens are hashed at rest.
- Paired-device secrets are delivered to phones only through Secure, HttpOnly,
  SameSite=Strict cookies, so browser JavaScript and the service worker cannot read
  the credential.
- The mobile gateway is a separate TLS 1.2+ network surface; the normal SAD API stays
  loopback-only. The gateway rejects wildcard, loopback, hostname, and public IPv4
  bindings and accepts one explicit private/approved overlay IPv4 address.
- Mobile `learning` mode admits explicitly matched SAD Chat, account-self, Personal
  Study, Forge play and own progress routes. Invented chat subroutes and Developer
  Workspace routes do not pass the gateway. `full_role` mode defers to signed-in RBAC.
- Owner Mobile Access UI can create temporary pairing codes, list paired phones, and
  revoke device access. Phones still require a normal SAD account login after pairing.
- Mobile preflight (`mobile_doctor.py`), combined desktop/mobile launcher (`mobile.py`),
  and Windows wrapper (`start_mobile.ps1`) are included. Provider/certificate-specific
  host setup remains an operational step, not an implicit trust change by SAD.
- Chat regression tests cover durable ownership, local-model history, built-in fallback,
  authenticated API access, cross-account denial, archive behavior, learning-phone
  route scoping, PWA cache privacy, accessible chat controls, and phone layout.
- Mobile regression tests cover pairing secrecy/expiry/revocation, owner authority,
  route isolation, bind-address refusal, rate limiting, PWA install contract, API
  cache exclusion, and phone touch/safe-area requirements.
- GitHub CI compiles the project, syntax-checks all browser JavaScript including SAD
  Chat and Code Workspace, and runs the full test/contract/security suite.
- The Alpha release gate is tested and enforced by CI; it verifies required release
  surfaces and blocks retired private-mode implementation markers from returning to
  the current release tree while excluding private `.sad_dev` runtime artifacts.
- Alpha operator preflight reports core readiness separately from optional local-model
  configuration and Docker-backed automatic-code isolation readiness.
- GitHub Actions performs a real Docker isolation proof after the core gate. The
  workflow explicitly preloads a Python image, resolves its immutable repository
  digest, requires `REPAIR ISOLATION: READY`, and executes a disposable test workspace
  through `DockerSandboxRunner` with the production boundary. The proof verifies
  non-root execution, a read-only workspace, writable tmpfs, stripped GitHub
  credentials, and unavailable external networking.
- Alpha browser UI provides SAD Chat and Code Workspace plus role-filtered Personal
  Study, Forge Student, teacher roster, Owner/Dev dashboard, account control, mobile
  control, and security surfaces.
- Browser accessibility structure has automated regression checks for form labels,
  keyboard order, visible focus, live announcements, navigation semantics, data-table
  captions/column scopes, SAD Chat controls, and Code Workspace status/actions.
- A role-by-role `ALPHA_UAT.md` protocol defines owner, student, teacher, developer,
  reviewer, viewer, SAD Chat, Developer Workspace, mobile, security, accessibility,
  severity, stop, and Alpha-exit criteria.
- Personal Study can generate full output through the explicitly configured
  loopback-only local model and reports honestly when the model is unavailable.
- Account lifecycle includes owner listing/disable controls, self-service password
  changes, logout, and revocation of other sessions after password change.

## Remaining operational work

- Repeat the Docker proof on the actual deployment computer using the reviewed image
  approved for that machine. The Linux CI runner proves the container code path, but
  it does not substitute for host-specific Docker Desktop/Windows verification.
- Configure and validate the intended local model on the deployment computer. SAD
  Chat can fall back to built-in dialogue without it, but full AI conversation,
  automatic repair drafting, Developer Workspace scope planning, and multi-file coding
  require the intended local model to be healthy and capable of the strict JSON contract.
- Execute Developer Workspace human UAT on the actual host with a disposable/backed-up
  project state: scope review, real multi-file generation, Docker tests, exact diff,
  Owner apply, stale/tamper denial, automatic rollback, explicit rollback, and Git
  topology unchanged.
- Execute the broader controlled human UAT protocol with representative student,
  teacher, owner, developer, reviewer, and viewer accounts, including SAD Chat and
  Developer Workspace authority-boundary scenarios. Human pilot evidence is not yet
  claimed complete.
- Perform the manual keyboard, screen-reader, 200% zoom, and narrow-viewport checks
  in `ALPHA_UAT.md`; automated structural accessibility checks do not replace them.
- For Mobile Preview, provision a phone-trusted TLS certificate/key on the Windows
  deployment host, choose the explicit private bind address, and require
  `python mobile_doctor.py` → `MOBILE GATEWAY: READY`.
- Run mobile host/phone UAT: pairing, repeated invalid-code throttling, revocation,
  SAD Chat continuity, learning-mode denial of coding/admin/development routes,
  full-role Code Workspace RBAC, iPhone/Android install/home-screen behavior,
  reconnect behavior, and narrow-screen usability.
- Account sessions are intentionally memory-only and require login again after API
  restart. Conversation and Developer Workspace state are durable on the host.
- Public internet hosting remains deliberately unsupported for Alpha 1. The mobile
  preview must not be router-port-forwarded; public TLS termination, hosted secrets,
  email recovery, and external identity remain future work.

## Verification gate

Run `python -m unittest -v`, `python -m compileall -q .`, `python release_gate.py`,
`python alpha_doctor.py`, and Protocol White. Automatic repair and Developer Workspace
readiness also require `python docker_proof.py` with the reviewed digest-pinned sandbox
image on the deployment host. Mobile Preview readiness also requires
`python mobile_doctor.py` with the deployment host's actual private address/trusted TLS
material, then the phone-specific UAT in `MOBILE.md`.

A release is blocked if any core test fails, the worktree is dirty unexpectedly, the
release-integrity gate fails, container isolation is unavailable for automatic code,
a tested-code source/hash boundary fails, or live/Git integrity evidence fails. Mobile
Preview must remain disabled when its own preflight is blocked; that does not weaken
or expose the base loopback Alpha surface.
