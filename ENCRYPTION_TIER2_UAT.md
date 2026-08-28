# SAD Encryption Tier 2 UAT

Run this on the actual Windows deployment host before claiming Encryption Tier 2 operational. Use disposable data and a disposable portable backup first.

## Evidence to record

- tested Git commit SHA
- Windows edition/build and signed-in Windows account
- Python version
- `cryptography` installed version
- BitLocker status for the volume containing SAD
- disposable backup destination
- whether a second Windows profile or replacement host was used for the portable restore drill

## 1. Preflight

1. Stop SAD and make a normal filesystem copy of any existing private data before the first migration test.
2. Pull the exact tested commit.
3. Install the pinned runtime dependencies from `requirements.txt`.
4. Run `python windows_doctor.py`.
5. Require `WINDOWS HOST: READY`.
6. Confirm the doctor reports both current-user DPAPI runtime protection and portable backup cryptography ready.

**Stop** if DPAPI, SQLite integrity, or the portable crypto dependency is blocked.

## 2. Legacy live-store migration

Using disposable copies where possible, place valid pre-Tier-2 state in the legacy locations for accounts, Chat, progress, mobile trust, failures, dashboard, and settings. Start the corresponding SAD surfaces.

Require:

- data remains readable through the same public API/UI behavior;
- the matching namespace exists in `local_data/sad_runtime.sqlite3`;
- the legacy live file no longer remains authoritative;
- an import archive is created only after read-back verification;
- on Windows, import archive bytes are not readable as their original JSON/plaintext;
- if both encrypted DB state and a live legacy copy exist, SAD fails closed instead of merging them.

## 3. Password boundary

Create a disposable account and inspect application-visible account output.

Require:

- the original password never appears in account data, API output, logs, or backup manifests;
- password verification remains salted PBKDF2 and is not converted to reversible encryption;
- changing a password still invalidates other sessions as designed.

## 4. Runtime confidentiality smoke test

Create disposable markers in:

- Chat
- Memory
- account profile
- Forge progress context where applicable
- mobile device label
- failure/dashboard evidence

Stop SAD and search the raw SQLite file for those markers.

Require the sensitive markers are not present as plaintext on a protected Windows runtime. Then restart SAD and verify each value still round-trips through its authorized product surface.

## 5. Native DPAPI backup

Create and verify a normal backup:

```powershell
python backup.py create D:\SAD-Backups\sad-native.sadbak
python backup.py verify D:\SAD-Backups\sad-native.sadbak
```

Require:

- the artifact is not a plaintext ZIP;
- known private markers are not visible in raw backup bytes;
- verification succeeds under the same Windows user;
- restore still requires `--confirm`.

## 6. Portable backup

Create a portable archive:

```powershell
python backup.py portable-create D:\SAD-Backups\sad-portable.sadbak
python backup.py portable-verify D:\SAD-Backups\sad-portable.sadbak
```

Enter a strong unique passphrase at the interactive prompt. Do not put it in the command line, notes committed to Git, or shell scripts.

Require:

- known Chat/Memory/`.env` markers are not visible in raw archive bytes;
- the archive is not readable as a ZIP;
- the correct passphrase verifies;
- a wrong passphrase fails;
- modifying one byte in a disposable copy causes verification to fail;
- the original archive remains unchanged.

## 7. Cross-profile disaster-recovery drill

Preferred proof: use a second disposable Windows account or a clean replacement Windows test machine.

1. Stop SAD on the destination.
2. Copy only the portable encrypted backup and the reviewed SAD release/source needed to run restore.
3. Install the exact pinned runtime dependency.
4. Run:

```powershell
python backup.py portable-restore D:\SAD-Backups\sad-portable.sadbak --confirm
```

5. Enter the portable passphrase.
6. Run `python windows_doctor.py`.
7. Start SAD and validate disposable accounts, Chat, Memory, Forge progress, mobile administration state, failure/dashboard evidence, Tools, Platform clients/events, and settings.

Require:

- restore succeeds under the destination Windows user;
- restored SQLite is protected by destination-user DPAPI;
- the original source Windows profile is not required to start/use the restored data;
- wrong-passphrase restore changes no live files;
- failed restore rolls back files already replaced.

## 8. Backup custody

Confirm at least one portable recovery copy is stored separately from the SAD host. Record who knows the passphrase and how recovery access is controlled. Do not store the passphrase beside the backup.

BitLocker or equivalent full-disk encryption should remain enabled on the live Windows volume even though application-level DPAPI is active.

## 9. Stop conditions

Do not claim Encryption Tier 2 operational if any of these occur:

- a sensitive runtime marker remains plaintext in the protected SQLite database;
- a portable backup exposes plaintext payloads;
- wrong passphrase or ciphertext tampering is accepted;
- legacy and encrypted state are silently merged;
- portable restore writes a host-neutral/plaintext runtime DB to disk;
- restored runtime data cannot be opened under the destination Windows user;
- Windows doctor reports a block;
- a restore failure leaves partially replaced live state.

Automated CI is a regression net. This UAT is the evidence for the real host, real Windows profile, real storage, and real recovery path.
