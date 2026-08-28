# SAD Backup and Recovery

SAD has two encrypted recovery formats on Windows: a current-user DPAPI backup for routine recovery and a passphrase-encrypted portable backup for disaster recovery across Windows profiles or replacement machines.

## Native Windows backup

Stop high-write activity when practical, then run:

```powershell
python backup.py create D:\SAD-Backups\sad-native.sadbak
python backup.py verify D:\SAD-Backups\sad-native.sadbak
```

The native backup manager:

- discovers known private runtime files plus `local_data/` and `.env`;
- creates a transactionally consistent SQLite snapshot;
- writes an inner manifest with file count, byte count, and SHA-256 for every file;
- validates paths and SQLite integrity;
- wraps the complete verified archive with current-user Windows DPAPI;
- refuses symlink/private-path escapes and destinations inside the SAD runtime tree;
- verifies the encrypted result before reporting success.

Native DPAPI backups are intended for the same Windows protection context. They are not the disaster-recovery format for a lost Windows profile.

## Portable disaster-recovery backup

Create a portable archive with:

```powershell
python backup.py portable-create D:\SAD-Backups\sad-portable.sadbak
python backup.py portable-verify D:\SAD-Backups\sad-portable.sadbak
```

The passphrase is requested interactively. SAD never accepts it as a command-line argument and does not store it.

Portable backup properties:

- AES-256-GCM authenticated encryption via the exact PyCA `cryptography` version pinned in `requirements.txt`;
- PBKDF2-HMAC-SHA256 passphrase key derivation with a random per-backup salt;
- random nonce and authenticated container header;
- the whole archive is encrypted, including `.env` and compatibility files;
- the runtime SQLite database is exported to a host-neutral representation only in memory;
- source-profile DPAPI legacy-import archives are excluded because they cannot be useful on another profile;
- the usual manifest, SHA-256, path, size, and SQLite integrity checks still run inside the encrypted container;
- wrong passphrases or modified ciphertext fail authentication.

The host-neutral SQLite representation is never deliberately written as a live restored database. During portable restore, SAD re-protects every runtime document for the destination Windows user before writing staged/live SQLite bytes.

## Restore native backup

**Stop SAD before restoring.** Then run:

```powershell
python backup.py restore D:\SAD-Backups\sad-native.sadbak --confirm
```

## Restore portable backup

On the destination Windows account or replacement Windows machine:

```powershell
python backup.py portable-restore D:\SAD-Backups\sad-portable.sadbak --confirm
```

Portable restore:

1. authenticates/decrypts the outer AES-GCM container;
2. verifies the complete inner manifest and every hash/path;
3. verifies the host-neutral SQLite database in memory;
4. re-encrypts each runtime document with destination-user DPAPI;
5. verifies the new destination-protected database;
6. stages all files;
7. replaces live files only after the preceding checks;
8. rolls back already-replaced targets if a later replacement fails.

A portable restore intentionally requires Windows because SAD's live at-rest runtime contract is Windows DPAPI.

## Legacy plaintext backup migration

Older verified ZIP backups can still be converted to a host-bound DPAPI artifact:

```powershell
python backup.py encrypt-legacy D:\OldBackups\sad-state.zip D:\SAD-Backups\sad-native.sadbak
```

Plaintext legacy backup verification/restoration remains explicit compatibility behavior. Normal backup operations do not silently downgrade encrypted archives to plaintext.

## What is included

The backup manager includes registered private-runtime files, `.env` when present, and normal private files beneath `local_data/`. Ephemeral `.sad_sandbox/` and `.sad_dev/` workspaces are intentionally excluded from account/conversation/platform recovery.

Portable backups exclude `local_data/legacy_imported/` because those are migration rollback artifacts that may contain source-profile DPAPI material. The current live runtime database contains the authoritative imported state.

## Runtime persistence

The protected runtime database now carries the live/default document state for:

- accounts/profiles;
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

Passwords remain one-way PBKDF2 verifier material. They are not made decryptable merely because the account document itself receives at-rest encryption.

## Recovery rules

1. Keep BitLocker or equivalent full-disk encryption enabled on the live host.
2. Keep at least one portable backup physically/logically separate from the SAD host.
3. Do not store the portable passphrase beside the archive.
4. Do not delete the last known-good backup while testing a new format or migration.
5. Complete `ENCRYPTION_TIER2_UAT.md`, preferably including a restore under a second disposable Windows profile, before relying on portable disaster recovery.
6. Loss of the portable passphrase means SAD cannot recover that portable archive.
7. Automated CI proves format and API behavior, not the custody of your real passphrase or physical backup media.
