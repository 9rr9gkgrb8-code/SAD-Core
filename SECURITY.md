# SAD security model

SAD is local-first and fail-closed around authority. Platform discovery, AI output, saved
Memory, Tool Actions, mobile pairing, coding evidence, app metadata, backup artifacts,
and Voice transport do not create permission by themselves.

## Principal separation

SAD distinguishes:

1. **Human account sessions** authorized by the local role map.
2. **Local app credentials** scoped to loopback Platform metadata integrations.
3. **AI components** that receive no human/machine identity merely because they produced output.
4. **Speech services** that receive only turn audio/text and gain no SAD identity or authority.

No principal may be silently converted into another.

## Runtime persistence

Tier 2/3 default state now uses `local_data/sad_runtime.sqlite3`, a versioned SQLite
runtime database. Current namespaces cover Personal Memory, Tool Actions, Platform client
registrations, and Platform events.

Security rules:

- the database path is private runtime data and never coding source;
- existing database paths must be regular files, not symlinks;
- SQLite uses full synchronous writes and explicit transactions;
- database/document sizes are bounded;
- database schema/document schema versions are checked;
- `PRAGMA quick_check` is exposed for preflight/backup verification;
- validated legacy JSON is imported only if the SQLite namespace does not already exist;
- import is verified before the legacy JSON is moved to a protected archive;
- simultaneous live SQLite + legacy JSON state fails closed instead of being merged implicitly.

Accounts, Chat/progress/settings/failure/mobile state remain compatible private stores in
this stabilization milestone and remain inside the backup/security boundary.

## Backup and restore

Backups contain sensitive local data. `backup_manager.py` therefore:

- requires the destination to be outside the SAD project/runtime tree;
- rejects symlink and path-escape sources;
- uses SQLite's backup API for a consistent runtime-database snapshot;
- emits a manifest with every path, size, and SHA-256;
- rejects duplicate, undeclared, traversal, size-mismatched, or hash-mismatched archive data;
- verifies SQLite integrity inside the archive;
- requires explicit approval before restore;
- stages and verifies files before replacement;
- restores already-replaced original bytes if a later replacement fails.

SAD should be stopped during restore. Backups are not encrypted by SAD in this milestone;
the operator must store them on trusted encrypted media/location when confidentiality at
rest is required.

## Personal Memory

Ordinary Chat/Voice text is not automatically promoted into long-term Memory. Memories
are account-owned, bounded, user-controlled, and only enabled/non-expired entries may be
supplied to Local AI. Chat/Voice may disable Memory per turn. Context is labeled untrusted
model data and is never treated as authorization.

## Governed Tool Actions

The current reviewed catalog is `platform.status`, `memory.search`, `memory.remember`, and
`memory.forget`. There is no generic shell/subprocess, arbitrary URL/network request,
dynamic `eval`/`exec`/plugin loader, package installer, unrestricted filesystem tool, or
Git tool.

Tool records are account-owned. State-changing actions require explicit approve/reject,
and approval is bound to the exact canonical argument SHA-256. Argument/tool metadata
mismatch moves the action to `tampered` and execution is refused.

## Chat, local model, and Voice

Conversations belong to one account, are bounded, and do not grant repair/coding/tool/Git
authority. Model traffic may be sent only to an explicitly configured loopback HTTP
endpoint. Credentialed/non-loopback model URLs are rejected.

`voice_runtime.py` applies the same network principle to optional STT/TTS services:

- only HTTP on `127.0.0.1`, `localhost`, or `::1`;
- no credentials/path/query/fragment in configured base URLs;
- fixed `/health`, `/v1/stt`, and `/v1/tts` contracts;
- bounded audio/text/response sizes and timeouts;
- speech services receive no SAD Bearer token, app secret, tool approval, filesystem,
  Docker, or Git authority.

Browser microphone permission remains disabled. Physical microphone capture/speaker
playback are deployment/client UAT, not an authority capability silently enabled here.

## Accounts

Passwords use salted PBKDF2 hashes, sessions expire/revoke, repeated failed logins lock
accounts temporarily, and account/session growth is bounded. Roles remain explicit:
Owner, Developer, Reviewer, Viewer, Teacher, and Student.

## Local app credentials and events

Owner alone manages local app registration/rotation/revocation. App secrets are high
entropy, returned only at creation/rotation, hashed at rest, and omitted from list
responses. Machine scopes remain limited to Platform discovery/catalog/modules/
compatibility and approved metadata events. `SAD-App` credentials cannot become human
Bearer sessions.

Platform events are metadata-only and recursively reject high-risk keys such as content,
messages, prompts, transcripts, passwords, tokens, secrets, code, diffs, tool args, and
outputs.

## Mobile

Core remains loopback-only. Mobile is a separate TLS 1.2+ paired gateway bound only to an
explicit RFC1918/approved CGNAT IPv4 address. Pairing codes are one-time, five-minute,
rate-limited, and persisted with slow salted hashing; device tokens are high entropy,
hashed at rest, revocable, and delivered to browsers through Secure/HttpOnly/
SameSite=Strict cookies.

Learning-mode route admission is narrow and machine-client endpoints are blocked through
Mobile even for full-role devices. Core and Mobile HTTP servers have bounded concurrent
admission, bounded queues, and slow-client socket timeouts.

## Browser/PWA boundary

Local/private browser API requests validate Host and same-origin browser metadata and
require JSON for POST. CSP/frame restrictions remain active. Service workers cache static
shell assets only and skip all `/v1/*` and `/mobile/*` private traffic.

## Coding and repair isolation

Developer Workspace requires human-approved file scope, private worktrees, strict edit
plans, Docker verification, exact tested diffs, stale/tamper checks, and Owner-only live
apply/rollback. Repair is narrower still. `.git`, `.github`, private runtime data,
credentials, hidden/control-plane paths, unsupported/binary files, and SAD private
workspaces are outside automatic coding scope.

Containers remain digest-pinned, `--pull never`, networkless, non-root, read-only,
capability-dropped, no-new-privileges, resource/time limited, and without Docker-socket or
Git credential authority.

## Windows deployment boundary

The full suite, Protocol Black, release gate, and Alpha preflight now run in CI on Ubuntu
Python 3.11 plus Windows Python 3.11 and 3.12. `windows_doctor.py` additionally checks the
Windows OS gate, private-data writability, and SQLite runtime integrity.

CI Windows runners do not prove the actual Windows 11 deployment machine. Real host
patch state, Windows account permissions, firewall, full-disk encryption, Docker Desktop
permissions, model/runtime provenance, TLS key permissions, LAN/router configuration,
phone trust, microphone/speaker behavior, and physical compromise remain deployment UAT
or host-security responsibilities.

## Private runtime data

Treat `local_data/` (including `sad_runtime.sqlite3` and legacy import archives), account/
conversation/progress/settings/failure/mobile state, app/device credentials, Memory,
Tool Actions, `.sad_sandbox/`, `.sad_dev/`, `.env`, and backup archives as private. Never
commit them.

## Acceptance

Automated tests are a regression net, not a substitute for deployment validation. Run
`ALPHA_UAT.md`, `PLATFORM_TIER2_UAT.md`, `PLATFORM_TIER3_UAT.md`, `WINDOWS.md`, and the
mobile/Voice/backup procedures on the actual devices for which operational support will
be claimed.
