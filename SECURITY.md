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

## At-rest encryption

Encryption Tier 2 uses two reviewed cryptographic boundaries rather than a home-grown cipher:

1. Windows Data Protection API (DPAPI) for live/default runtime state and routine native backups.
2. AES-256-GCM through the exact PyCA `cryptography` version pinned in `requirements.txt` for portable disaster-recovery backups.

On the intended Windows deployment path:

- runtime SQLite document payloads use current-user DPAPI protection;
- DPAPI purpose/entropy is bound to the exact SAD data namespace;
- existing plaintext runtime documents are converted transactionally before the database declares the protection scheme active;
- after protection is declared, a plaintext/downgraded document row blocks startup;
- native `.sadbak` containers protect the complete verified archive with DPAPI;
- portable `.sadbak` containers encrypt the complete verified archive with passphrase-derived AES-256-GCM;
- portable runtime SQLite is exported host-neutral only in memory and is re-protected for the destination Windows user before live restore;
- plaintext legacy backup ZIPs are rejected by normal verify/restore and require an explicit compatibility/migration path;
- passwords remain one-way PBKDF2 hashes rather than reversible encrypted values;
- app/device secrets remain one-way hashed where the original value need not be recovered.

Portable key derivation uses PBKDF2-HMAC-SHA256 with a random per-backup salt. The portable
passphrase is prompted interactively, is never accepted as a command-line argument, and is
not stored by SAD. Wrong passphrases and modified AES-GCM ciphertext fail authenticated
decryption through the same caller-visible error class.

DPAPI is user-context protection, not a substitute for full-disk encryption. BitLocker or
equivalent full-disk encryption remains the outer protection against offline disk theft.
DPAPI also does not defend against malware or an attacker already controlling the logged-
in Windows account.

SAD does not silently enable Windows EFS because loss of EFS recovery material can make
data permanently inaccessible. EFS is an optional host hardening decision only after its
certificate/recovery process is established.

## Runtime persistence

Default live state uses `local_data/sad_runtime.sqlite3`, a versioned SQLite runtime
database. Protected namespaces now cover:

- accounts and profiles;
- Chat history;
- Forge/student progress;
- mobile pairing/device trust state;
- failure records;
- Owner/Developer dashboard evidence;
- dialogue settings;
- Personal Memory;
- governed Tool Actions;
- Platform client registrations;
- Platform events.

Security rules:

- the database path is private runtime data and never coding source;
- existing database paths must be regular files, not symlinks;
- SQLite uses full synchronous writes and explicit transactions;
- database/document sizes are bounded;
- database schema/document schema versions are checked;
- `PRAGMA quick_check` is used by preflight/backup verification;
- Windows live document payloads are DPAPI-protected before persistence;
- protected envelopes and at-rest metadata are versioned and downgrade-checked;
- validated legacy JSON/record state is imported only if the SQLite namespace does not already exist;
- imported content is read back before the legacy live file is archived;
- on protected Windows, new legacy-import archives are themselves DPAPI-protected and old plaintext import archives are upgraded;
- simultaneous live SQLite + legacy state fails closed instead of being merged implicitly.

Explicit custom file paths remain available to isolated tests and compatibility/recovery
tools. They are not the live/default production persistence path and must not be confused
with the protected Windows runtime claim.

## Backup and restore

Backups contain sensitive local data. `backup_manager.py` therefore:

- requires the destination to be outside the SAD project/runtime tree;
- rejects symlink and path-escape sources;
- creates consistent SQLite snapshots/exports;
- emits an inner manifest with every path, size, and SHA-256;
- rejects duplicate, undeclared, traversal, size-mismatched, or hash-mismatched archive data;
- verifies SQLite integrity inside the archive;
- DPAPI-protects native Windows backup containers;
- AES-GCM-protects portable backup containers;
- excludes source-profile DPAPI import archives from portable disaster-recovery exports;
- rejects normal plaintext backup verify/restore unless compatibility is explicitly requested;
- requires explicit approval before restore;
- stages and verifies files before replacement;
- restores already-replaced original bytes if a later replacement fails.

Portable restore is Windows-only because the final live database must be re-bound to the
destination Windows user's DPAPI context before it is written as live state. SAD should be
stopped during all restore operations.

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
Owner, Developer, Reviewer, Viewer, Teacher, and Student. The account document is now
inside the protected runtime database, but the password verifier remains intentionally
one-way rather than decryptable.

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
SameSite=Strict cookies. Mobile trust metadata now also resides inside the encrypted live
runtime document layer.

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

The full suite, Protocol Black, release gate, and Alpha preflight run in CI on Ubuntu
Python 3.11 plus Windows Python 3.11 and 3.12. `windows_doctor.py` additionally requires
the Windows OS gate, private-data writability, a real current-user DPAPI round-trip,
SQLite runtime integrity, active runtime payload protection, and the exact reviewed
portable-backup crypto dependency.

CI Windows runners do not prove the actual Windows deployment machine. Real host patch
state, Windows account permissions, firewall, BitLocker/full-disk encryption, Docker
Desktop permissions, model/runtime provenance, TLS key permissions, LAN/router
configuration, portable-backup passphrase custody, cross-profile restore evidence, phone
trust, microphone/speaker behavior, and physical compromise remain deployment UAT or
host-security responsibilities.

## Private runtime data

Treat `local_data/` (including `sad_runtime.sqlite3` and legacy import archives), app/device
credentials, Memory, Tool Actions, `.sad_sandbox/`, `.sad_dev/`, `.env`, and all backup
artifacts as private. Never commit them, even when a subset is application-encrypted.

`.env` remains a live host configuration file rather than a runtime SQLite document. It is
encrypted when inside a native/portable backup container, but its live at-rest protection
depends on Windows ACLs plus BitLocker/full-disk encryption.

## Acceptance

Automated tests are a regression net, not a substitute for deployment validation. Run
`ALPHA_UAT.md`, `PLATFORM_TIER2_UAT.md`, `PLATFORM_TIER3_UAT.md`,
`ENCRYPTION_TIER2_UAT.md`, `WINDOWS.md`, and the mobile/Voice/backup procedures on the
actual devices for which operational support will be claimed.
