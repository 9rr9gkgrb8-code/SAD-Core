# SAD Backup and Recovery

SAD private state must be recoverable before Beta. Backups are explicit operator artifacts
and contain sensitive local data. Store them only in a trusted location outside the SAD
project/runtime tree.

## Create

Stop high-write activity when practical, then run:

```powershell
python backup.py create D:\SAD-Backups\sad-state.zip
```

The backup manager:

- discovers known private runtime files plus `local_data/`;
- creates a transactionally consistent SQLite snapshot with SQLite's backup API;
- refuses symlink/private-path escapes;
- writes a manifest with file count, byte count, and SHA-256 for every file;
- refuses backup destinations inside the SAD project/runtime tree;
- verifies the resulting archive before reporting success.

## Verify

```powershell
python backup.py verify D:\SAD-Backups\sad-state.zip
```

Verification rejects:

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
python backup.py restore D:\SAD-Backups\sad-state.zip --confirm
```

Restore requires the explicit `--confirm` flag. The complete archive is verified before
any live file is touched. Files are staged first, SQLite is integrity-checked again, and
already-replaced targets are rolled back if a later replacement fails.

Restore does not delete unrelated private files that are absent from an older backup.
That conservative behavior prevents an old archive from silently erasing newer local
state outside its manifest.

## What is currently included

The manager includes existing files named in SAD's private-runtime registry, `.env` when
present, and regular files under `local_data/`. Ephemeral `.sad_sandbox/` and `.sad_dev/`
workspaces are intentionally not required for account/conversation/platform recovery.

## SQLite migration

Tier 2/3 platform state now uses `local_data/sad_runtime.sqlite3` by default for:

- Personal Memory;
- governed Tool Actions;
- local Platform app registrations;
- Platform event history.

When a validated protected legacy JSON copy exists and SQLite does not yet contain that
namespace, SAD imports it, verifies the stored document, and moves the old JSON into
`local_data/legacy_imported/`. If both authoritative-looking copies exist, startup fails
closed so the operator can reconcile them instead of SAD guessing.

Accounts, conversations, progress, dashboard/failure state, settings, and mobile state
remain compatible private stores in this stabilization milestone and are included in
backups. Their later migration can use the same versioned database/migration machinery.
