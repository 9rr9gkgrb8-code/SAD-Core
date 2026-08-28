# SAD + Forge milestone status

Updated: August 28, 2026

## Architecture direction

**SAD is the platform.** Chat, Voice, Personal Study, Forge Learning, Personal Memory,
Governed Tool Actions, Developer Workspace, controlled repair, accounts/roles, Mobile,
scoped local-app credentials, platform events, protected runtime persistence, and
backup/recovery are governed SAD modules or platform infrastructure.

The historical Protocol White independent `Forge-Core` Gate 2 remains paused under the
current SAD-as-platform architecture. Protocol Black remains the active adversarial
security gate.

## Current platform milestone

- Platform Core: **`0.3-alpha`**
- Repository-backed SAD completion: **Alpha Stable — 100%**
- Repository-backed Forge completion: **Alpha Stable — 100%**
- Platform manifest schema: **`3`**
- HTTP API: **`v1`**
- Core network binding: **loopback only**
- Dynamic plugin execution: **disabled**
- AI Git authority: **none**
- Default live persistence: **versioned SQLite runtime database**
- Windows live payload protection: **current-user DPAPI**
- Native Windows backup: **current-user DPAPI protected**
- Portable disaster recovery: **passphrase AES-256-GCM + destination-user DPAPI re-key**
- CI OS coverage: **Ubuntu 24.04 + Windows Server 2025 / Python 3.11 and 3.12**

## Encryption Tier 2

### Protected runtime database

`local_data/sad_runtime.sqlite3` is the live/default document store for:

- accounts and profiles;
- Chat history;
- Forge/student progress;
- mobile pairing/device trust state;
- failure records;
- Owner/Developer dashboard evidence;
- dialogue settings;
- Personal Memory;
- governed Tool Actions;
- Platform local-app registrations;
- Platform events.

On Windows, document payloads are DPAPI-protected before SQLite persistence. Passwords
remain salted one-way PBKDF2 verifier data and are not made decryptable.

Legacy JSON/record state is validated, imported, read back, and only then archived.
Protected Windows startup DPAPI-protects new import archives and upgrades prior plaintext
import archives. If both live encrypted state and a legacy live copy appear authoritative,
startup fails closed.

Explicit custom file paths remain supported for isolated tests and compatibility/recovery
tools. They are not the live/default protected persistence claim.

### Portable encrypted disaster recovery

Tier 2 adds a second recovery format in addition to native DPAPI backups:

```text
live DPAPI DB -> host-neutral SQLite in memory -> verified archive
              -> AES-256-GCM portable .sadbak
              -> destination Windows restore
              -> destination-user DPAPI DB -> staged live replacement
```

Portable backup uses the exact reviewed PyCA `cryptography` version pinned in
`requirements.txt`, PBKDF2-HMAC-SHA256 passphrase derivation, a random per-backup salt,
a random GCM nonce, and authenticated headers. The passphrase is prompted interactively,
never accepted as a command-line argument, and never stored by SAD.

Wrong passphrases and modified ciphertext fail authenticated decryption. Portable restore
is Windows-only because the final live database is re-protected with destination-user
DPAPI before staged/live bytes are written.

Source-profile DPAPI legacy-import archives are excluded from portable recovery because
they are rollback artifacts, not portable authoritative state.

### Native backup/recovery

Native Windows backups remain current-user DPAPI protected and retain:

- per-file SHA-256 manifesting;
- path/size/undeclared-file rejection;
- consistent SQLite snapshots;
- SQLite integrity verification;
- explicit `--confirm` before restore;
- staged replacement;
- rollback if a later replacement fails.

Legacy plaintext backup migration remains explicit and fail-closed.

## Voice runtime

The authenticated `/v1/voice/turn` transcript bridge has a provider-neutral local audio
layer:

```text
WAV -> loopback STT -> SAD Voice -> loopback TTS -> WAV
```

Speech services gain no SAD user/app/tool/coding/Git authority. Real microphone capture,
speaker playback, and installed STT/TTS providers remain host/client UAT.

## Windows readiness

CI executes dependency installation, compile, browser syntax, full suite, Protocol Black,
release gate, and Alpha preflight on:

- Ubuntu 24.04 / Python 3.11;
- Windows Server 2025 / Python 3.11;
- Windows Server 2025 / Python 3.12.

Windows doctor requires real current-user DPAPI, SQLite integrity, active runtime payload
protection, and the exact reviewed portable-backup crypto dependency. Docker isolation
proof remains digest-pinned and separately gated.

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
python alpha_stable.py
python alpha_doctor.py
```

All declared Ubuntu/Windows Python legs must pass. Windows additionally runs
`windows_doctor.py`. Automatic coding and repair additionally require the digest-pinned
Docker proof. Encryption Tier 2 adds portable-crypto dependency pinning, migration tests,
portable backup/tamper tests, and cross-profile DB re-protection tests to the required
security surface.

## Remaining real-world blockers

The code milestone is not deployment proof. Remaining work requiring actual devices or
host administration:

1. Pull the exact final green `main` commit onto the intended Windows 11 host.
2. Install the exact pinned `requirements.txt` dependency set.
3. Run the full local suite, Protocol Black, and `windows_doctor.py` there.
4. Verify BitLocker/full-disk encryption and recovery-key custody on the actual host.
5. Configure and validate the intended local model/runtime.
6. Validate Docker Desktop permissions and repeat the digest-pinned Docker proof.
7. Create/verify a real native encrypted `.sadbak` and perform a disposable restore drill.
8. Create/verify a portable encrypted `.sadbak` and complete a cross-profile or replacement
   Windows restore drill under `ENCRYPTION_TIER2_UAT.md`.
9. Confirm restored runtime data is re-protected for the destination Windows user.
10. Run full human role/accessibility Alpha UAT.
11. Configure private TLS and complete real iPhone/Android pairing/mobile UAT.
12. Install/configure reviewed loopback STT/TTS providers and test real microphone/speaker
    behavior if audio Voice will be claimed.
13. Validate Windows firewall/account permissions, LAN/router/no-public-port-forwarding,
    certificate-key custody, portable-backup passphrase custody, and physical host security.
14. Configure GitHub branch protection/rulesets administratively so green CI is enforced,
    not merely followed by convention.

## Explicit encryption boundaries

- BitLocker remains the outer stolen-drive defense.
- DPAPI does not protect against malware already running as the authorized Windows user.
- Portable recovery is only as strong as its passphrase; SAD cannot recover a lost
  passphrase.
- SAD does not silently enable EFS.
- `.env` remains live host configuration protected by Windows ACLs/BitLocker, though it is
  encrypted inside backup containers.
- SAD does not claim forensic secure deletion of historical SSD pages/remnants.

## Release language

When the code gates are green, SAD may be described as a **Protocol-Black-hardened
local-first Platform Alpha with Encryption Tier 2 code complete**. Do not claim the real
Windows host, BitLocker posture, cross-profile recovery, mobile operation, full audio
Voice, or production readiness until their physical host/device UAT gates pass.
