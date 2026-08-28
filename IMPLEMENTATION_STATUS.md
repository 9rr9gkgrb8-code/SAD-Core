# SAD + Forge milestone status

Updated: August 27, 2026

## Architecture direction

**SAD is the platform.** Chat, Voice, Personal Study, Forge Learning, Personal Memory,
Governed Tool Actions, Developer Workspace, controlled repair, accounts/roles, Mobile,
scoped local-app credentials, platform events, runtime persistence, backup/recovery, and
at-rest protection are governed SAD modules or platform infrastructure.

The historical Protocol White independent `Forge-Core` Gate 2 remains paused under the
current SAD-as-platform architecture. Protocol Black remains the active adversarial
security gate.

## Current platform milestone

- Platform Core: **`0.3-alpha`**
- Platform manifest schema: **`3`**
- HTTP API: **`v1`**
- Core network binding: **loopback only**
- Dynamic plugin execution: **disabled**
- AI Git authority: **none**
- Tier 2/3 default persistence: **versioned SQLite runtime database**
- Windows Tier 2/3 payload protection: **current-user DPAPI**
- Windows backup/recovery: **DPAPI-protected, hash-manifested verified workflow**
- CI OS coverage: **Ubuntu 24.04 + Windows 2025 runners**

## Foundation Stabilization

This milestone directly addresses the lowest senior-engineering readiness scores without
pretending host/device work can be completed from GitHub.

### Runtime database and Encryption Tier 1

`runtime_database.py` introduces `local_data/sad_runtime.sqlite3` with:

- explicit database schema version;
- named document namespaces and document schema versions;
- bounded document/database size;
- SQLite transactions, full synchronous writes, and busy timeout;
- `quick_check` integrity validation;
- consistent SQLite snapshot support;
- validated one-time legacy JSON import;
- verified import before protected legacy archival;
- fail-closed conflict when both SQLite and legacy JSON look authoritative.

On Windows, default live Tier 2/3 document payloads add:

- current-user Windows DPAPI protection through `windows_crypto.py`;
- no repository/runtime application master key;
- purpose/namespace binding;
- transactional plaintext-to-protected migration;
- versioned protected envelopes and at-rest scheme metadata;
- fail-closed rejection if plaintext appears after protection is declared;
- a post-migration SQLite `VACUUM` to reduce ordinary plaintext remnants, without
  claiming forensic secure erase.

Default SQLite namespaces cover:

- Personal Memory;
- governed Tool Actions;
- Platform local-app registrations;
- Platform event history.

Explicit custom JSON/SQLite paths remain supported for compatibility/test fixtures.
Accounts, Chat/progress/settings/failure/mobile state remain compatible private stores for
now and rely on host/full-disk/file encryption until their later persistence migration.

### Backup/recovery

`backup.py` + `backup_manager.py` support:

```text
create encrypted -> decrypt/verify -> explicit offline restore
```

The inner archive has per-file SHA-256, size/path manifesting, SQLite backup-API
snapshots, SQLite integrity verification, traversal/undeclared/tamper rejection,
external-destination enforcement, staged restore, explicit `--confirm`, and rollback of
already-replaced files on restore failure.

On Windows, the complete verified inner archive is DPAPI-protected before the final
`.sadbak` is written. Normal verify/restore rejects plaintext legacy archives. A dedicated
`encrypt-legacy` command verifies an old ZIP and writes a new protected artifact without
destroying the source.

Tier 1 DPAPI backups are intentionally tied to the Windows protection context and are not
yet a portable cross-machine encrypted archival format.

### Voice runtime

The existing authenticated `/v1/voice/turn` transcript bridge has a provider-neutral
local audio layer:

```text
WAV -> loopback STT -> SAD Voice -> loopback TTS -> WAV
```

`voice_runtime.py` restricts STT/TTS to reviewed fixed contracts on loopback HTTP and
bounds payloads/timeouts. `voice_client.py` orchestrates one authenticated audio turn.
Speech services gain no SAD user/app/tool/coding/Git authority. Microphone capture and
speaker playback remain real-client UAT.

### Windows readiness

CI executes compile, browser syntax, full suite, Protocol Black, release gate, and Alpha
preflight on:

- Ubuntu 24.04 / Python 3.11;
- Windows Server 2025 runner / Python 3.11;
- Windows Server 2025 runner / Python 3.12.

Windows security tests now exercise real DPAPI round-trip/tamper behavior, raw SQLite
ciphertext absence, protected migration/downgrade rejection, and encrypted backup/restore.
`windows_doctor.py` requires Windows, Alpha core readiness, writable private data, DPAPI
round-trip, SQLite integrity, and active runtime payload protection.

## Existing completed capabilities

- role-filtered Platform discovery and compatibility negotiation;
- durable private SAD Chat and transcript Voice bridge;
- explicit account-owned Memory;
- governed Tool Actions with exact-argument approval integrity;
- request-directed Personal Study;
- game-first Forge quests/hints/mastery/XP/progress;
- governed multi-file Developer Workspace;
- failure-driven isolated repair and exact tested live apply/rollback;
- local accounts/RBAC;
- scoped loopback `SAD-App` credentials and privacy-minimized events;
- paired TLS Mobile/PWA with learning/full-role admission;
- Protocol Black security hardening including bounded HTTP admission and supply-chain pinning.

## Automated release gate

A release candidate must pass:

```text
python -m compileall -q .
python -m unittest -v
python protocol_black.py
python release_gate.py
python alpha_doctor.py
```

The CI matrix must pass on all declared Ubuntu/Windows Python legs. Automatic coding and
repair additionally require the digest-pinned Docker proof. Encryption Tier 1 adds
`ENCRYPTION.md`, `windows_crypto.py`, and Windows encryption tests to the release-required
surface.

## Remaining real-world blockers

The code milestone is not deployment proof. Remaining work requiring actual devices or
host administration:

1. Pull the exact final green `main` commit onto the intended Windows 11 host.
2. Run the full local suite, Protocol Black, and `windows_doctor.py` there.
3. Verify BitLocker/full-disk encryption and recovery-key custody on the actual host and
   intended backup media.
4. Configure and validate the intended local model/runtime on that host.
5. Validate Docker Desktop permissions and repeat the reviewed digest-pinned Docker proof.
6. Create/verify a real encrypted `.sadbak` and perform a disposable restore drill under
   the intended Windows account/profile.
7. Run full human role/accessibility Alpha UAT.
8. Configure private TLS and complete real iPhone/Android pairing/mobile UAT.
9. Install/configure reviewed loopback STT/TTS providers and test real microphone/speaker
   behavior if audio Voice will be claimed.
10. Validate Windows firewall/account permissions, LAN/router/no-public-port-forwarding,
    certificate-key custody, and physical host security.
11. Configure GitHub branch protection/rulesets administratively so green CI is enforced,
    not merely followed by convention.
12. Continue later migration of remaining compatible JSON state into the protected data
    layer only after backup/restore and encryption migration are accepted on the real host.
13. Design a portable encrypted export/backup format with separately recoverable key
    management before relying on DPAPI backups for cross-machine disaster recovery.

## Release language

SAD may be described as a **Protocol-Black-hardened local-first Platform Alpha with
Windows Encryption Tier 1** when the code gates are green. Do not call Windows deployment,
BitLocker posture, cross-machine encrypted recovery, mobile operation, full audio Voice,
or production readiness complete until their real host/device acceptance gates pass.
