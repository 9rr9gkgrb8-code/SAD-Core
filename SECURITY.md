# SAD security model

SAD is local-first and fail-closed around authority. Platform discovery, AI output, saved
Memory, Tool Actions, mobile pairing, coding evidence, and app metadata do not create
permission by themselves.

## Principal separation

SAD distinguishes:

1. **Human account sessions** — Bearer sessions authorized by the existing role map.
2. **Local app credentials** — scoped `SAD-App` secrets for loopback Platform metadata
   integrations only.
3. **AI components** — text/code generators that receive no human or machine identity
   merely because they produced output.

No principal may be silently converted into another.

## Platform discovery

- `/health` remains minimal and public on the loopback service.
- Detailed Platform manifests require a valid human session or an explicitly scoped
  machine credential on the machine-client endpoints.
- Capability metadata is descriptive and never grants endpoint authority.
- Compatibility negotiation is filtered to the requesting principal.
- Dynamic extension/plugin execution remains disabled.

## Personal Memory

Tier 3 Memory is explicit user-controlled data.

- Ordinary Chat/Voice text is **not automatically written** into long-term Memory.
- Every memory record has one `account_id`; cross-account list/search/update/delete is
  denied/not-found.
- Categories are allow-listed: fact, preference, goal, project, note.
- Title/content, file size, item count, search count, and expiry format are bounded.
- Memory writes use a temporary file + replace and restrictive file permissions where
  supported.
- `memory.json` is Git-ignored and excluded from release-source scanning.
- Only enabled, non-expired memories may be returned by the Memory context selector.
- Chat/Voice may set `use_memory: false` to exclude Memory for that request.
- `memory_used` is true only when memory context existed and the configured Local AI
  engine actually handled the response.
- Built-in dialogue does not claim that saved Memory was used.

Memory contents/titles are not placed in Platform event metadata.

## Governed Tool Actions

Tier 3 Tool Actions use a fixed reviewed catalog. A tool identifier alone cannot load or
execute arbitrary code.

Current tools:

- `platform.status`
- `memory.search`
- `memory.remember`
- `memory.forget`

Security rules:

- Tool definitions are explicit Python call paths inside `tool_actions.py`.
- There is no generic shell/subprocess, arbitrary URL/network request, dynamic
  `eval`/`exec`/plugin loader, package installation, unrestricted filesystem tool, or
  Git tool.
- Tool arguments/output are JSON bounded.
- Tool records are owned by one account and cannot be read/decided/executed by another.
- Read-only tools may enter `ready` immediately.
- State-changing tools enter `awaiting_approval`.
- State-changing execution before explicit approval fails.
- Rejecting a tool leaves it non-executable.
- The exact approved action arguments are the arguments executed.
- `tool_actions.json` is Git-ignored and excluded from release-source scanning.

Platform tool events contain lifecycle/status metadata only, not arguments or outputs.

## SAD Chat and Voice

- Conversations belong to exactly one account.
- Guessing another conversation UUID does not grant access.
- Conversation history is bounded, atomically written, Git-ignored, and uses restrictive
  permissions where supported.
- Only recent turns are sent to Local AI rather than blindly injecting the full history.
- Chat/Voice text itself has no repair, coding, account, app-management, tool-approval,
  filesystem, shell, or Git authority.
- The Voice route uses the same account ownership and optional Memory rules as Chat.
- Browser microphone access remains disabled until the STT/TTS client boundary is
  implemented and reviewed.

## Local model

- Conversation/model data may be sent only to an explicitly configured loopback HTTP
  model endpoint.
- Credentialed or non-loopback model URLs are rejected.
- If the model is unavailable, SAD fails honestly to Built-in dialogue where that
  fallback exists; coding/automatic repair generation fails closed rather than guessing.

## Accounts

- Passwords are salted PBKDF2 hashes, never stored plaintext.
- Sessions expire and can be revoked.
- Repeated failed logins trigger temporary lockout.
- Owner controls privileged account lifecycle; Teacher/Student/Developer/Reviewer/Viewer
  authority remains role-limited.

## Local app credentials and events

- Owner alone manages local app registration/rotation/revocation.
- App secrets are high entropy, returned only at create/rotate, salted/hashed at rest,
  and omitted from list responses.
- Machine scopes remain limited to Platform discovery/catalog/modules/compatibility and
  approved event metadata.
- `SAD-App` credentials cannot be used as Bearer human sessions.
- Event subscriptions are exact and cannot widen themselves; an empty subscription
  returns no events.
- `platform_clients.json` and `platform_events.json` are private ignored runtime files.
- Events must not contain conversations, prompts, memory content/title, tool args/output,
  code/diffs, passwords, user/app/device tokens, student work, or other high-value
  payloads.
- `sad_sdk.py` accepts loopback Core URLs only and does not persist credentials.

## Mobile

- Normal SAD Core remains loopback-only.
- Mobile is a separate TLS 1.2+ gateway bound to one explicit private/approved-overlay
  IPv4 address.
- Wildcard, loopback, hostname-as-bind-target, and public IPv4 bindings are refused.
- A phone must pass both paired-device trust and normal account authentication.
- Pairing codes are one-time, five-minute, rate-limited, and hashed at rest.
- Device tokens are hashed at rest and delivered as Secure/HttpOnly/SameSite=Strict
  cookies.
- Learning-mode admission uses exact routes for personal Chat, Voice, Memory, governed
  Tools, Study, Forge, and own progress. Privileged development/admin routes stay
  blocked.
- `/v1/platform/client/*` machine endpoints are blocked through Mobile even in full-role
  mode.
- Revocation invalidates paired device access server-side.
- Do not router-port-forward the mobile gateway to the public internet.

## PWA privacy

The service worker may cache static shell assets only. It explicitly skips all `/v1/*`
and `/mobile/*` traffic, including Chat, Voice, Memory, Tool Actions, Study, Forge,
accounts, Platform manifests, coding evidence, repair evidence, sessions, pairing, and
credentials.

## Coding and repair isolation

- Developer Workspace is restricted to an explicit human-approved file scope.
- `.git`, `.github`, credentials, runtime private data, hidden/control-plane paths, and
  unsupported/binary files are excluded from automatic coding scope/worktrees.
- Repair planning is narrower still and accepts only a strict approved single-file
  replacement contract.
- Automatic verification requires a preloaded digest-pinned Docker image.
- Containers run networkless, non-root, with a read-only root/workspace, dropped
  capabilities, no-new-privileges, stripped Git credentials, and resource/time limits.
- Missing Docker/isolation fails closed. There is no same-user execution fallback.
- Failed tests cannot become applyable.
- Before live application SAD rechecks live source hashes and exact post-test hashes.
- Developer Workspace multi-file application backs up originals and restores the whole
  set if any operation/verification fails.
- Repair application is exact-test-proposal/hash controlled and preserves a backup.
- Only Owner governance crosses the live-code application/rollback boundary.
- Repair/coding/apply paths do not run Git commit/push/fetch/rebase/merge or use Git
  credentials.

## Private runtime data

Treat these as private host data and never commit them:

- accounts/settings/failures/dashboard/progress data
- `chat_history.json`
- `memory.json`
- `tool_actions.json`
- `platform_clients.json`
- `platform_events.json`
- mobile pairing state under local data
- `.sad_sandbox/`
- `.sad_dev/`
- `.env`

## Acceptance

Automated tests are a regression net, not a substitute for deployment validation. Run
`ALPHA_UAT.md`, `PLATFORM_TIER2_UAT.md`, and `PLATFORM_TIER3_UAT.md` on the actual host,
and the mobile UAT on any phone/device for which operational support will be claimed.
