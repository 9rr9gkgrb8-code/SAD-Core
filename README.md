# SAD — Sandbox Adaptive Dialogue

SAD is a local-first AI platform with human-controlled authority boundaries.

Current Alpha surfaces include SAD Chat, Voice, explicit Personal Memory, governed Tool
Actions, Personal Study, Forge Learning, multi-file Developer Workspace coding,
controlled repair, accounts/RBAC, paired Mobile access, scoped local app credentials,
platform events, capability/version discovery, transactional Tier 2/3 persistence,
Windows Encryption Tier 1, and verified encrypted operator backup/recovery.

## Platform Core v0.3-alpha

`platform_registry.py` defines the declarative platform catalog. Platform schema is `3`;
the HTTP API remains `v1`. Platform metadata never grants authority. Concrete endpoints
still enforce authentication, RBAC, workflow state, source hashes, Docker evidence, and
Owner approval where required.

Built-in modules include SAD Platform Core, Chat, Voice, Personal Memory, governed Tools,
Personal Study, Forge, Developer Workspace, Accounts/Roles, and Mobile.

## Runtime data, SQLite, and Windows at-rest protection

Private application data belongs outside source/control surfaces. Tier 2/3 state uses the
versioned transactional database:

```text
local_data/sad_runtime.sqlite3
```

The SQLite database currently holds default runtime documents for:

- Personal Memory;
- governed Tool Actions;
- Platform local-app registrations;
- privacy-minimized Platform events.

On the intended Windows deployment path, these document payloads are protected with the
current Windows user's DPAPI context before they are persisted. Existing plaintext rows
are transactionally migrated on first protected startup. Once protection is declared,
plaintext/downgraded rows fail closed.

Validated legacy JSON copies for those stores are imported only when SQLite has no
corresponding namespace, verified after import, then moved into
`local_data/legacy_imported/`. If both live SQLite and legacy JSON appear authoritative,
startup fails closed instead of guessing.

Accounts, Chat history, progress, failures/dashboard state, settings, and mobile pairing
state remain compatible private stores during this milestone. Until they migrate into the
protected data layer, use BitLocker/full-disk or deliberate host file encryption for their
at-rest confidentiality.

## Backup and recovery

Create an encrypted Windows backup outside the SAD tree:

```powershell
python backup.py create D:\SAD-Backups\sad-state.sadbak
python backup.py verify D:\SAD-Backups\sad-state.sadbak
```

Restore only while SAD is stopped and only with explicit approval:

```powershell
python backup.py restore D:\SAD-Backups\sad-state.sadbak --confirm
```

The verified ZIP/manifest exists inside a current-user DPAPI-protected container. Backups
retain per-file SHA-256, use SQLite's online backup API for a consistent database
snapshot, reject traversal/undeclared/tampered files, verify SQLite integrity, stage
restore files before replacement, and roll back already-replaced files if restore fails.

Legacy plaintext backup ZIPs are rejected by the normal verify/restore path. Convert a
verified old backup explicitly:

```powershell
python backup.py encrypt-legacy D:\OldBackups\sad-state.zip D:\SAD-Backups\sad-state.sadbak
```

Tier 1 DPAPI backups are tied to their Windows protection context and are not yet a
portable cross-machine disaster-recovery format. See `BACKUP.md` and `ENCRYPTION.md`.

## Conversation and Voice

SAD Chat persists account-owned sessions and recent conversation context. When the
configured loopback local model is healthy, replies are labeled `Local AI`; otherwise SAD
visibly falls back to `Built-in dialogue` where fallback is supported.

`POST /v1/voice/turn` provides authenticated transcript-to-conversation transport.
`voice_runtime.py` and `voice_client.py` add a provider-neutral local audio path:

```text
WAV -> loopback STT -> SAD Voice -> loopback TTS -> WAV
```

Speech services are restricted to explicitly configured loopback HTTP endpoints and gain
no SAD account/tool/coding/Git authority. Physical microphone capture and speaker playback
still require real host/client UAT. See `VOICE.md`.

## Personal Memory and governed Tools

SAD does not automatically copy ordinary conversation into long-term Memory. A signed-in
account explicitly creates/searches/edits/enables/expires/deletes its own memories, and a
turn can set `use_memory: false`.

The reviewed internal tool catalog remains deliberately small:

- `platform.status`
- `memory.search`
- `memory.remember`
- `memory.forget`

State-changing tools require explicit approval tied to the exact argument hash. There is
no generic shell, arbitrary URL/network tool, dynamic plugin/Python loader, package
installer, unrestricted filesystem tool, or Git tool.

## Coding and controlled repair

General coding:

```text
task -> human-approved file scope -> private workspace -> local AI edits
     -> Docker tests -> exact diff -> Owner apply/rollback
```

Failure-driven repair:

```text
failure -> human triage -> scoped repair draft -> isolated Docker tests
        -> exact diff -> Owner YES/NO -> verified local apply/rollback
```

Coding and repair agents receive no Git commit/push/fetch/rebase/merge/credential
authority.

## Local app integration

Owner can create scoped loopback `SAD-App` credentials for companion software. Machine
credentials remain read-only/control-plane scoped to Platform discovery, compatibility,
and approved metadata events. They cannot impersonate users or enter Chat, Memory, Tools,
Study, Forge, coding, repair, account, mobile-admin, or Git flows. See `PLATFORM_SDK.md`.

## Mobile

`mobile.py` keeps Core loopback-only and starts a separate paired TLS gateway on one
explicit private/approved-overlay IPv4 address. Learning-mode phones can use their own
Chat, Voice, Memory, governed Tools, Study, Forge, and progress. Machine-client endpoints
stay blocked through Mobile. Static PWA shell assets may cache; `/v1/*` and `/mobile/*`
private traffic never does. See `MOBILE.md`.

## Windows readiness

CI runs the full suite, Protocol Black, release gate, and Alpha preflight on:

- Ubuntu 24.04 / Python 3.11;
- Windows Server 2025 runner / Python 3.11;
- Windows Server 2025 runner / Python 3.12.

Windows CI additionally exercises real DPAPI protection/decryption, tamper/purpose
rejection, runtime payload confidentiality/migration/downgrade behavior, and encrypted
backup/restore.

On the actual Windows deployment host run:

```powershell
python windows_doctor.py
.\start_sad_windows.ps1
```

The Windows doctor requires a successful DPAPI probe and active runtime payload
protection. CI Windows coverage does not substitute for Windows 11/BitLocker/Docker/model/
TLS/phone/audio human UAT on the real machine. See `WINDOWS.md`.

## Private runtime data

Treat `local_data/`, legacy private JSON names, `.sad_sandbox/`, `.sad_dev/`, `.env`,
accounts/chat/progress/settings/failure state, app/device credentials, Memory, Tool
Actions, Platform events, the SQLite runtime database, and backup artifacts as private
host data. They remain Git-ignored and excluded from coding/release-source surfaces even
when a subset is application-encrypted.

## Run and verify

Desktop Alpha:

```powershell
python alpha.py
```

Guarded Windows startup:

```powershell
.\start_sad_windows.ps1
```

Core verification:

```powershell
python -m compileall -q .
python -m unittest -v
python protocol_black.py
python release_gate.py
python alpha_doctor.py
```

Automatic repair/coding readiness additionally requires the reviewed digest-pinned
Docker sandbox image and `python docker_proof.py`. Mobile readiness requires
`mobile_doctor.py` and real host/phone UAT.

See `PLATFORM.md`, `API.md`, `SECURITY.md`, `ALPHA1.md`, `BACKUP.md`, `ENCRYPTION.md`,
`VOICE.md`, `WINDOWS.md`, `PLATFORM_TIER2_UAT.md`, and `PLATFORM_TIER3_UAT.md` for the
current contracts.
