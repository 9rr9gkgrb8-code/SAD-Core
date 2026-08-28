# Security model

## Trust boundaries

- Account records, settings, conversation history, failure reports, mobile pairing state, repair artifacts, Developer Workspace artifacts, platform client registrations, and platform event history are local data and are excluded from Git.
- Platform Core is a declarative discovery layer. Module/capability metadata never grants permission, invokes a module, loads extension code, or substitutes for concrete endpoint authorization.
- Detailed human Platform manifests require a valid SAD account session and are filtered server-side using the existing `ROLE_PERMISSIONS` map. The browser/client is not trusted to enforce permissions.
- Platform manifests contain static capability/route/version metadata only. They do not embed account records, conversation text, failure evidence, pairing secrets, workspace source, environment values, or other runtime private data.
- Platform modules are not dynamic plugins in Alpha. Registering/describing a module cannot execute Python, JavaScript, shell commands, package installation, or Git operations.
- The established public `/health` response remains minimal and backward-compatible; detailed role/capability discovery stays authenticated.
- Platform Tier 2 separates three principals: human account sessions, scoped local-app credentials, and AI components. AI output does not inherit either human or machine authority.
- Owner-only `platform:manage` controls local-app registration, secret rotation/revocation, and Owner event inspection. No lower role can mint a machine credential.
- Local-app secrets are high-entropy random tokens, returned only at creation/rotation, salted/hashed at rest, and omitted from list responses. Rotation invalidates the previous secret; revocation disables the credential server-side.
- Tier 2 machine scopes are restricted to `platform:discover`, `platform:catalog`, `platform:modules`, `platform:compatibility`, and `platform:events`. A client cannot request arbitrary human permissions such as `development:govern` or `account:manage`.
- Machine credentials use the distinct `SAD-App <client-id>.<secret>` authorization scheme. They cannot be supplied as Bearer user sessions to Chat, Study, Forge, Developer Workspace, repair, account, or mobile-administration endpoints.
- Machine-client endpoints exist only on the loopback core API. `/v1/platform/client/*` is explicitly rejected by the paired mobile gateway even for `full_role` devices.
- App event access is intersected with the exact event types approved on the client record. An empty subscription yields no events. Unknown/duplicate scopes or event types fail closed.
- Platform event records are bounded, metadata-only, and deliberately exclude conversation text, prompts, generated code, diffs, passwords, session tokens, app/device secrets, student work, and other high-value payloads.
- `platform_clients.json` and `platform_events.json` are private ignored runtime files written atomically with restrictive permissions where supported.
- Capability compatibility negotiation is principal-filtered. A capability hidden from a role or app scope is reported unavailable rather than exposed through negotiation metadata.
- `sad_sdk.py` is an explicitly reviewed network-capable production client. It uses only the standard library, accepts only loopback core API URLs, rejects credentialed/non-loopback URLs, and does not persist credentials.
- The Voice Client Bridge requires a normal signed-in human account session. A transcript enters the same account-owned conversation engine/history as SAD Chat; the endpoint returns reply text for future local speech synthesis but grants no tool, repair, code, app-management, account, or Git authority.
- Learning-mode phones may use `/v1/voice/turn` after device pairing and normal user login. Browser microphone capture remains disabled by the current `Permissions-Policy`; this milestone is a transcript transport contract, not bundled microphone/STT/TTS execution.
- SAD Chat sessions are owned by exactly one authenticated account. Knowing another account's conversation UUID does not grant access.
- Conversation history is written atomically to local `chat_history.json`, uses restrictive file permissions where supported, and fails before save if the bounded history file would exceed its storage limit.
- Only recent conversation turns are supplied to the configured local model for context. The complete saved transcript is not automatically copied into every prompt.
- Chat text is untrusted conversational input and does not invoke repair, approval, coding-workspace, file, shell, app-management, or Git authority. Those capabilities remain behind explicit governed APIs and role checks.
- Student and teacher sessions cannot enter owner repair-governance or Developer Workspace controls.
- Developer sessions can prepare and execute isolated coding work but cannot exercise Owner live-application governance.
- Reviewer sessions may inspect development evidence and approve/reject repair evidence but cannot apply a live file or coding workspace.
- Developer Workspace scope planning returns file suggestions only. No code is written until a human submits an explicit approved path list.
- Developer Workspace automatic coding may target only the exact approved source paths, with bounded path count, context, generated output, and file size.
- `.git`, `.github`, `.sad_sandbox`, `.sad_dev`, local runtime data, credentials/environment secrets, hidden paths, and unsupported/binary file types are excluded from automatic coding scope. Repository-control metadata is excluded from the coding worktree entirely.
- The general coding model receives source text only for the human-approved scope, not arbitrary private project/runtime data.
- Generated coding plans must be JSON-only full-file write/delete operations. Duplicate paths, unapproved paths, deletes of nonexistent snapshot files, no-op edits, malformed output, and oversized plans fail closed.
- Developer Workspace verification uses the same digest-pinned, networkless, non-root Docker boundary as repair verification. A failed test or unavailable container cannot become applyable.
- Before Developer Workspace live application, SAD verifies every live base hash and every post-test worktree hash. A stale live source or tampered tested copy blocks the whole apply.
- Existing changed files are backed up before multi-file application. Any failed write or verification triggers restoration and verification of the whole original set.
- Only Owner's `development:govern` permission can apply or roll back a tested Developer Workspace. Developer/Reviewer/Viewer and the coding model cannot cross that boundary.
- Developer Workspace apply/rollback never invokes Git commands, repository credentials, branch operations, commit, push, fetch, rebase, or merge.
- Local-model traffic is restricted to an HTTP loopback endpoint.
- The normal SAD API remains loopback-only even when mobile mode is enabled.
- Mobile access uses a separate TLS-only gateway that refuses wildcard, loopback, hostname, and public IPv4 bindings. It must bind to one explicit private/approved overlay IPv4 address.
- A phone must pass two independent gates: a paired-device credential and normal SAD account authentication.
- One-time mobile pairing codes expire after five minutes, are single-use, and are rate-limited at the gateway.
- Pairing codes and paired-device tokens are hashed at rest. The live paired-device token is delivered only as a `Secure`, `HttpOnly`, `SameSite=Strict` cookie and is not exposed to browser JavaScript.
- `learning` paired devices are restricted at the gateway to explicitly matched SAD Chat, Voice bridge, account-self, Personal Study, Forge play, and own-progress routes. Developer Workspace, Platform administration, and machine-client routes are not admitted.
- `full_role` devices still rely on normal SAD RBAC after the device gate, so a Developer phone still cannot perform Owner application. Machine-client routes remain blocked even in full-role mode.
- Revoking a paired device invalidates its device token server-side.
- The service worker caches only static shell assets and explicitly excludes `/v1/*` and `/mobile/*` traffic, including Platform manifests, app secrets, event responses, chat, Voice, and Developer Workspace API responses.
- Automatic repair planning accepts only one JSON-described exact replacement in one allow-listed root file. Ambiguous, oversized, unchanged, or malformed plans fail closed before testing.
- Repair verification fails closed unless Docker and a digest-pinned, preloaded `SAD_SANDBOX_IMAGE` are available.
- Containers run without network, capabilities, privilege escalation, Git metadata, or a writable root filesystem. The proposal/worktree is mounted read-only; process, memory, CPU, time, and temporary-storage limits apply.
- A repair patch may target exactly one allow-listed root file and must match the source hash recorded when its proposal was created.
- Owner repair live application is permitted only for a successful correlated Forge proposal. SAD revalidates the source hash, copies the exact tested target through an atomic replacement, verifies the resulting hash, and preserves the original under the private proposal directory.
- If repair live application or dashboard persistence fails, SAD attempts an immediate verified rollback. A mismatch or unverifiable rollback is surfaced as an error; it is never silently treated as success.
- Live repair application does not invoke Git commit, push, fetch, rebase, merge, credentials, or repository-control metadata. Git authority remains host/human.

## Runtime requirement

Docker must be installed and the configured image must already exist locally under the exact digest in `SAD_SANDBOX_IMAGE`. SAD never pulls an image during repair or Developer Workspace verification and never falls back to same-user Python execution. Host-side live/Git integrity checks remain part of verification. Human Owner approval remains mandatory before any tested automatic code is copied into the local live project.

The full SAD Chat and Voice conversation experience requires the explicitly configured loopback local model. If that model is unavailable, the response is labeled `Built-in dialogue` and uses the limited built-in conversation layer instead of pretending a model-generated answer occurred.

Automatic repair drafting and Developer Workspace scope/implementation generation additionally require the explicitly configured local model. If the model is unavailable or cannot return the required strict JSON plan, the operation fails closed rather than testing or applying guessed code.

Platform discovery, local-app authentication, capability negotiation, and metadata event reads do not require the local model. Dynamic extension/plugin execution remains disabled and requires a separate reviewed isolation contract before it can be introduced.

Mobile mode additionally requires a certificate/private-key pair that loads under TLS 1.2 or newer and is trusted by the phone. SAD intentionally does not auto-install a trust root. Do not port-forward the mobile gateway to the public internet. Public hosting, internet TLS termination, hosted identity, recovery, hosted secret management, and public app credentials remain outside Alpha.

## Reporting

Do not include passwords, pairing codes, device tokens, session tokens, app client secrets, private conversation data, Developer Workspace source/diffs, student records, or live failure evidence in a public issue. Report suspected vulnerabilities privately to the repository owner.
