# SAD — Sandbox Adaptive Dialogue

SAD is a local-first AI platform with human-controlled authority boundaries.

Its current Alpha combines one authenticated API, browser/mobile clients, general AI
conversation, Personal Study, Forge learning, failure/repair governance, and a
multi-file Developer Workspace. Platform Core gives those surfaces one discoverable
module/capability contract instead of treating them as unrelated features.

## Platform Core

`platform_registry.py` defines the declarative SAD platform catalog.

After normal sign-in, clients can discover the capabilities available to the current
role through:

- `GET /v1/platform`
- `GET /v1/platform/modules`
- `GET /v1/platform/capabilities`

Current built-in platform modules are:

- **SAD Platform Core** — discovery/version/capability contract
- **SAD Chat** — free-form multi-turn local AI conversation
- **Personal Study** — request-directed learning and writing assistance
- **Forge Learning** — quests, hints, mastery, XP, ranks, companion progression
- **Developer Workspace** — scoped multi-file coding and Docker verification
- **Accounts & Roles** — local identity, RBAC, account/device administration
- **Mobile Gateway** — paired TLS phone access while core API stays loopback-only

Platform metadata is descriptive only. A manifest cannot grant permissions, execute a
plugin, approve a repair, apply code, or gain Git authority. Concrete endpoints still
enforce the existing SAD authentication/RBAC/workflow checks.

See `PLATFORM.md` for the Platform Core contract.

## Controlled repair and coding

Failure-driven repair follows:

`failure → human triage → scoped repair draft → isolated Docker tests → exact diff → Owner YES/NO → verified local apply/rollback`

General coding follows:

`task → scope suggestion → human-approved files → private multi-file workspace → local AI edits → Docker tests → exact diff → Owner apply/rollback`

Forge/coding agents do not receive Git commit, push, fetch, rebase, merge, branch, or
credential authority. Repository publication remains host/human controlled.

## Learning package

SAD includes two separate learning experiences:

- `personal_study.py` follows the learner's request directly: problem breakdowns,
  method teaching, walkthroughs, work checking, hints, direct answers when asked,
  proofreading, essay editing, rubric review, examples, and substantive word-count
  expansion. It does not force a three-question tutoring loop.
- `forge_student.py` provides game-first homework quests, a four-step hint ladder,
  mastery-gated XP and ranks, companion progression, and boss checks. Homework is
  preserved as a challenge rather than silently replaced with an answer.

## SAD Chat

SAD Chat is the platform's general conversation lane. Chats are private to the signed-in
account, persist locally across restarts, and use recent conversational context. When
the configured loopback local model is available the UI reports **Local AI**; otherwise
it reports the limited **Built-in dialogue** fallback rather than pretending the full
model answered.

Conversation text itself carries no repair, file, shell, approval, or Git authority.

## Failure and development control

`failure_dashboard.py` provides the shared owner/developer workflow. SAD, Forge, tests,
and users may submit normalized evidence to the Failure Inbox. Duplicate signatures
merge evidence. Detection does not start development by itself; governed actions remain
role-checked and explicit.

`developer_workspace.py` adds general-purpose multi-file coding in a private `.sad_dev`
copy. Developer can prepare/test; only Owner governance can apply or roll back the
exact tested file set.

## Local accounts and login

`auth.py` provides local student, teacher, owner, developer, reviewer, and viewer roles.
Passwords are salted and hashed with PBKDF2, repeated failures temporarily lock an
account, sessions expire and can be revoked, and role permissions protect governance.
The first owner requires explicit local bootstrap approval.

Runtime account data is stored in ignored `accounts.json` and must never be committed.

## Isolation hardening

Repair and Developer Workspace verification require Docker plus a preloaded,
digest-pinned image configured through `SAD_SANDBOX_IMAGE`. Execution is networkless,
non-root, resource-limited, stripped of Git credentials, and denied Git control
metadata. Missing isolation fails closed; SAD does not fall back to same-user repair
execution.

Live apply rechecks source/test hashes, preserves backups, and performs verified
rollback when a transaction fails.

## Mobile

`mobile.py` provides an optional paired TLS phone gateway. The normal SAD API stays
loopback-only. Phones require both device pairing and normal SAD login. Learning-only
devices receive a narrow Study/Forge/Chat route set; full-role devices still receive
only the signed-in user's normal RBAC authority.

See `MOBILE.md` for host/TLS setup and phone UAT.

## Local data

The following stay on the computer and are ignored by Git:

- `settings.json`
- `failures.json`
- `accounts.json`
- `dashboard_state.json`
- `student_progress.json`
- `chat_history.json`
- `.sad_sandbox/`
- `.sad_dev/`
- `local_data/`
- `.env`

Do not commit runtime data or private backups.

## Run SAD

For the Alpha browser product, including first-time Owner setup:

```powershell
python alpha.py
```

Then open `http://127.0.0.1:8765/`.

For paired mobile mode after the required private-address/TLS setup:

```powershell
python mobile.py
```

For the loopback-only JSON API:

```powershell
python api.py
```

See `ALPHA1.md`, `API.md`, `PLATFORM.md`, `SECURITY.md`, and `ALPHA_UAT.md` for the
current release contract.

## Run tests

```powershell
python -m unittest -v
```
