# Security model

## Trust boundaries

- Account records, settings, conversation history, failure reports, mobile pairing state, and sandbox artifacts are local data and are excluded from Git.
- SAD Chat sessions are owned by exactly one authenticated account. Knowing another account's conversation UUID does not grant access.
- Conversation history is written atomically to local `chat_history.json`, uses restrictive file permissions where supported, and fails before save if the bounded history file would exceed its storage limit.
- Only recent conversation turns are supplied to the configured local model for context. The complete saved transcript is not automatically copied into every prompt.
- Chat text is untrusted conversational input and does not invoke repair, approval, file, shell, or Git authority. Those capabilities remain behind explicit governed APIs and role checks.
- Student and teacher sessions cannot enter owner repair-governance commands.
- Developer sessions can inspect or perform assigned work but cannot exercise owner governance.
- Reviewer sessions may approve/reject evidence but cannot apply a live file.
- Local-model traffic is restricted to an HTTP loopback endpoint.
- The normal SAD API remains loopback-only even when mobile mode is enabled.
- Mobile access uses a separate TLS-only gateway that refuses wildcard, loopback, hostname, and public IPv4 bindings. It must bind to one explicit private/approved overlay IPv4 address.
- A phone must pass two independent gates: a paired-device credential and normal SAD account authentication.
- One-time mobile pairing codes expire after five minutes, are single-use, and are rate-limited at the gateway.
- Pairing codes and paired-device tokens are hashed at rest. The live paired-device token is delivered only as a `Secure`, `HttpOnly`, `SameSite=Strict` cookie and is not exposed to browser JavaScript.
- `learning` paired devices are restricted at the gateway to explicitly matched SAD Chat, account-self, Personal Study, Forge play, and own-progress routes. A broad chat-prefix rule is not used.
- `full_role` devices still rely on normal SAD RBAC after the device gate.
- Revoking a paired device invalidates its device token server-side.
- The service worker caches only static shell assets and explicitly excludes `/v1/*` and `/mobile/*` traffic, including chat messages and replies.
- Automatic repair planning accepts only one JSON-described exact replacement in one allow-listed root file. Ambiguous, oversized, unchanged, or malformed plans fail closed before testing.
- Repair verification fails closed unless Docker and a digest-pinned, preloaded `SAD_SANDBOX_IMAGE` are available.
- Containers run without network, capabilities, privilege escalation, Git metadata, or a writable root filesystem. The proposal is mounted read-only; process, memory, CPU, time, and temporary-storage limits apply.
- A patch may target exactly one allow-listed root file and must match the source hash recorded when its proposal was created.
- Owner live application is permitted only for a successful correlated Forge proposal. SAD revalidates the source hash, copies the exact tested target through an atomic replacement, verifies the resulting hash, and preserves the original under the private proposal directory.
- If live application or dashboard persistence fails, SAD attempts an immediate verified rollback. A mismatch or unverifiable rollback is surfaced as an error; it is never silently treated as success.
- Live repair application does not invoke Git commit, push, fetch, rebase, merge, credentials, or repository-control metadata. Git authority remains host/human.

## Runtime requirement

Docker must be installed and the configured image must already exist locally under the exact digest in `SAD_SANDBOX_IMAGE`. SAD never pulls an image during repair verification and never falls back to same-user Python execution. Host-side live project and Git-topology verification still runs before and after the container. Human Owner approval remains mandatory before a tested repair is copied into the local live project.

The full SAD Chat experience requires the explicitly configured loopback local model. If that model is unavailable, the chat UI labels the response as `Built-in dialogue` and uses the limited built-in conversation layer instead of pretending a model-generated response occurred.

Automatic repair drafting additionally requires the explicitly configured local model. If the model is unavailable or cannot return a valid single-edit plan, Forge returns a failed repair result rather than testing or applying guessed code.

Mobile mode additionally requires a certificate/private-key pair that loads under TLS 1.2 or newer and is trusted by the phone. SAD intentionally does not auto-install a trust root. Do not port-forward the mobile gateway to the public internet. Public hosting, internet TLS termination, hosted identity, recovery, and hosted secret management remain outside Alpha.

## Reporting

Do not include passwords, pairing codes, device tokens, session tokens, private conversation data, student records, or live failure evidence in a public issue. Report suspected vulnerabilities privately to the repository owner.
