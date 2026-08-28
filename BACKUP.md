# SAD Backup and Recovery

SAD private state must be recoverable before Beta. Backups are explicit operator artifacts
and contain sensitive local data. Encryption Tier 1 makes Windows backup creation use
current-user Windows DPAPI by default.

## Create an encrypted backup

Stop high-write activity when practical, then run:

```powershell
python backup.py create D:\SAD-Backups\sad-state.sadbak
```

On Windows the backup manager:

- discovers known private runtime files plus `local_data/`;
- creates a transactionally consistent SQLite snapshot with SQLite's backup API;
- writes an inner manifest with file count, byte count, and SHA-256 for every file;
- verifies paths and SQLite integrity;
- wraps the complete verified backup container with current-user Windows DPAPI;
- refuses symlink/private-path escapes;
- refuses backup destinations inside the SAD project/runtime tree;
- verifies the encrypted result before reporting success.

A normal `.sadbak` artifact is not a plaintext ZIP and should not expose account/chat/
Memory/runtime contents if merely copied from storage. DPAPI protection is purpose-bound
to SAD's backup contract.

## Verify

```powershell
python backup.py verify D:\SAD-Backups\sad-state.sadbak
```

SAD first decrypts the DPAPI container and then verifies the inner archive. Verification
rejects:

- backup ciphertext that cannot be decrypted in the current Windows protection context;
- missing/duplicate manifests;
- undeclared archive files;
- absolute or traversal paths;
- size/hash mismatches;
- unsupported backup versions;
- corrupt SQLite runtime snapshots.

Verification performs no restore.

## Restore

**Stop SAD before restoring.** Then run:

```powershell
python backup.py restore D:\SAD-Backups\sad-state.sadbak --confirm
```

Restore requires the explicit `--confirm` flag. The container must decrypt and the
complete inner archive must verify before any live file is touched. Files are staged
first, SQLite is integrity-checked again, and already-replaced targets are rolled back if
a later replacement fails.

Restore does not delete unrelated private files that are absent from an older backup.
That conservative behavior prevents an old archive from silently erasing newer local
state outside its manifest.

## Legacy plaintext backup migration

Older verified ZIP backups can be converted on the Windows account that will own the new
DPAPI artifact:

```powershell
python backup.py encrypt-legacy D:\OldBackups\sad-state.zip D:\SAD-Backups\sad-state.sadbak
```

SAD verifies the legacy ZIP before encrypting it. The source is left untouched so the
operator can verify the new encrypted copy before deciding how to securely dispose of the
old plaintext artifact. Normal `verify` and `restore` commands reject plaintext legacy
archives instead of silently downgrading confidentiality.

## DPAPI portability boundary

Tier 1 backup encryption is intentionally tied to the Windows DPAPI protection context.
It is excellent for preventing a copied backup from being readable as plaintext, but it
is **not yet a portable cross-machine archival format**. A backup may become unavailable
if the required Windows user/profile protection material is lost.

Therefore:

1. Keep Windows account/profile recovery material healthy.
2. Keep BitLocker or equivalent full-disk encryption enabled on the host and backup media
   where possible.
3. Perform a real restore drill before relying on backups.
4. Do not delete the last known-good backup during migration.
5. A later Beta milestone should add a separately recoverable portable encrypted export
   format with explicit key/recovery handling.

## What is currently included

The manager includes existing files named in SAD's private-runtime registry, `.env` when
present, and regular files under `local_data/`. Ephemeral `.sad_sandbox/` and `.sad_dev/`
workspaces are intentionally not required for account/conversation/platform recovery.

## SQLite persistence and at-rest protection

Tier 2/3 platform state uses `local_data/sad_runtime.sqlite3` by default for:

- Personal Memory;
- governed Tool Actions;
- local Platform app registrations;
- Platform event history.

On the Windows deployment path, those document payloads are DPAPI-protected before being
written to SQLite. Existing validated plaintext document rows are transactionally
converted on first protected startup. After the database declares the DPAPI scheme,
plaintext rows are treated as downgrade/tamper evidence and startup fails closed.

Validated legacy JSON can still be imported when SQLite does not already contain that
namespace. Accounts, conversations, progress, dashboard/failure state, settings, and
mobile state remain compatible private stores in this milestone and still depend on the
host's full-disk/file encryption until their later persistence migration.
