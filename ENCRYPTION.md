# SAD Encryption Tier 2

SAD's Windows at-rest protection now has two complementary recovery modes: host-bound DPAPI protection for normal local operation and portable passphrase encryption for disaster recovery.

## Live runtime protection

On the intended Windows host, sensitive runtime documents are stored in `local_data/sad_runtime.sqlite3` and their JSON payloads are protected with current-user Windows DPAPI before SQLite writes them.

The encrypted runtime namespaces now include:

- accounts and profiles (passwords remain one-way PBKDF2 hashes inside the protected account document)
- Chat history
- Forge/student progress
- mobile pairing/device trust state
- failure records
- Owner/Developer dashboard evidence
- dialogue settings
- Personal Memory
- governed Tool Actions
- Platform client registrations
- Platform events

Legacy JSON state is validated, imported transactionally, read back for verification, then moved to a private import archive. On a protected Windows runtime, new import archives are DPAPI-protected. Existing plaintext import archives are upgraded on protected startup.

Once a runtime database declares the `windows-dpapi-user-v1` scheme, plaintext document rows are treated as a downgrade/tamper condition and startup fails closed.

## Native backup

`python backup.py create <path>` creates the existing current-user DPAPI backup. It is appropriate for routine recovery under the same Windows protection context.

The native backup preserves the verified manifest, SHA-256 file hashes, path checks, SQLite integrity checks, explicit restore approval, staged writes, and rollback behavior.

## Portable disaster-recovery backup

`python backup.py portable-create <path>` creates a host-neutral passphrase-encrypted backup.

Properties:

- AES-256-GCM authenticated encryption through the pinned PyCA `cryptography` package.
- PBKDF2-HMAC-SHA256 passphrase key derivation with a random per-backup salt.
- Random GCM nonce and authenticated container header.
- The passphrase is prompted interactively and is never accepted as a command-line argument or stored by SAD.
- The entire package is encrypted, including `.env` and any compatibility files included in the backup.
- Source-profile DPAPI legacy-import archives are excluded from portable backups.
- The live SQLite database is exported to a host-neutral representation only in memory before the outer portable container is encrypted.
- Portable restore is Windows-only and re-protects every runtime document with destination-user DPAPI before writing the restored live SQLite file.
- Wrong passphrases and modified ciphertext fail authentication without revealing which condition occurred.

This solves the Tier 1 limitation where copying a DPAPI backup to another Windows profile could leave the inner runtime data bound to the original profile.

## Cryptography supply chain

Portable backup encryption depends on exactly the reviewed version in `requirements.txt`. CI installs that pinned manifest on Linux and Windows, and Protocol Black rejects a floating or changed dependency specification.

SAD does not implement its own block cipher or AEAD construction. Windows live protection delegates to DPAPI; portable container encryption delegates to PyCA AESGCM.

## Remaining boundaries

- BitLocker remains the recommended outer stolen-drive defense for the Windows host.
- DPAPI cannot protect data from malware already executing as the authorized logged-in Windows user.
- A portable backup is only as strong as its passphrase. Losing the passphrase means SAD cannot recover that portable archive.
- SAD does not silently enable EFS because EFS certificate loss can itself cause permanent data loss.
- `.env` may exist as a live host configuration file outside the encrypted SQLite data layer. BitLocker/Windows ACLs protect it at rest; portable/native backup containers encrypt it while archived.
- SQLite pages rewritten during migrations are vacuumed where appropriate, but SAD does not claim forensic secure deletion from SSD media. BitLocker/full-disk encryption is the defense for remanence.
- CI validates Windows APIs and formats but does not prove the physical deployment PC has BitLocker enabled, strong Windows sign-in security, safe backup custody, or completed a cross-profile restore drill.

## Release rule

Encryption changes travel through a dedicated PR and must pass the complete Linux + Windows 3.11/3.12 suite, Protocol Black, release gate, Windows preflight, and digest-pinned Docker proof before merge. The merged `main` commit must pass the same release pipeline again.
