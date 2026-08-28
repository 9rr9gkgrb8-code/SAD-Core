# SAD + Forge milestone status

Updated: August 27, 2026

## Architecture direction

**SAD is the platform.** Chat, Voice, Personal Study, Forge Learning, Personal Memory,
Governed Tool Actions, Developer Workspace, controlled repair, accounts/roles, Mobile,
scoped local-app credentials, platform events, runtime persistence, and backup/recovery
are governed SAD modules or platform infrastructure.

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
- Backup/recovery: **hash-manifested verified operator workflow**
- CI OS coverage: **Ubuntu 24.04 + Windows 2025 runners**

## Foundation Stabilization

This milestone directly addresses the lowest senior-engineering readiness scores without
pretending host/device work can be completed from GitHub.

### Runtime database

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

Default SQLite namespaces now cover:

- Personal Memory;
- governed Tool Actions;
- Platform local-app registrations;
- Platform event history.

Explicit custom JSON paths remain supported for compatibility/test fixtures. Accounts,
Chat/progress/settings/failure/mobile state remain compatible private stores for now and
are included in backup/recovery.

### Backup/recovery

`backup.py` + `backup_manager.py` support:

```text
create -> verify -> explicit offline restore
```

The archive has per-file SHA-256, size/path manifesting, SQLite backup-API snapshots,
SQLite integrity verification, traversal/undeclared/tamper rejection, external-destination
enforcement, staged restore, explicit `--confirm`, and rollback of already-replaced files
on restore failure.

### Voice runtime

The existing authenticated `/v1/voice/turn` transcript bridge now has a provider-neutral
local audio layer:

```text
WAV -> loopback STT -> SAD Voice -> loopback TTS -> WAV
```

`voice_runtime.py` restricts STT/TTS to reviewed fixed contracts on loopback HTTP and
bounds payloads/timeouts. `voice_client.py` orchestrates one authenticated audio turn.
Speech services gain no SAD user/app/tool/coding/Git authority. Microphone capture and
speaker playback remain real-client UAT.

### Windows readiness

CI now executes compile, browser syntax, full suite, Protocol Black, release gate, and
Alpha preflight on:

- Ubuntu 24.04 / Python 3.11;
- Windows Server 2025 runner / Python 3.11;
- Windows Server 2025 runner / Python 3.12.

`windows_doctor.py` checks the Windows platform gate, Alpha core readiness, writable
private data, and SQLite runtime integrity. `start_sad_windows.ps1` refuses startup when
that host preflight blocks.

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
repair additionally require the digest-pinned Docker proof.

## Remaining real-world blockers

The code milestone is not deployment proof. Remaining work requiring actual devices or
host administration:

1. Pull the exact final green `main` commit onto the intended Windows 11 host.
2. Run the full local suite, Protocol Black, and `windows_doctor.py` there.
3. Configure and validate the intended local model/runtime on that host.
4. Validate Docker Desktop permissions and repeat the reviewed digest-pinned Docker proof.
5. Create/verify a backup on real backup media and perform a disposable restore drill.
6. Run full human role/accessibility Alpha UAT.
7. Configure private TLS and complete real iPhone/Android pairing/mobile UAT.
8. Install/configure reviewed loopback STT/TTS providers and test real microphone/speaker
   behavior if audio Voice will be claimed.
9. Validate Windows firewall/account/full-disk-encryption expectations and LAN/router/no-
   public-port-forwarding policy.
10. Configure GitHub branch protection/rulesets administratively so green CI is enforced,
    not merely followed by convention.
11. Continue later migration of remaining compatible JSON state only after backup/restore
    and migration behavior is accepted on the real host.

## Release language

SAD may be described as a **Protocol-Black-hardened local-first Platform Alpha** when the
code gates are green. Do not call Windows deployment, mobile operation, full audio Voice,
or production readiness complete until their real host/device acceptance gates pass.
