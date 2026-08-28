# SAD Encryption Tier 1

SAD's first application-level at-rest encryption milestone targets the intended Windows host without inventing cryptography or weakening the networkless Docker sandbox.

## Goals

1. Protect Tier 2/3 runtime document payloads on Windows with Windows Data Protection API (DPAPI), scoped to the current Windows user.
2. Protect SAD backup archives on Windows with DPAPI by default so copied backup files are not plaintext ZIP archives.
3. Preserve explicit integrity checks, restore approval, path validation, SQLite verification, and rollback.
4. Keep passwords one-way hashed. Encryption is not a replacement for password hashing.
5. Add native Windows regression tests and Protocol Black checks for encryption/downgrade behavior.
6. Keep full-disk encryption such as BitLocker as the outer stolen-disk defense.

## Non-goals / boundaries

- DPAPI does not protect SAD from malware or an attacker already controlling the logged-in Windows account.
- DPAPI-protected backups are recovery artifacts for the same Windows protection context. They are not yet a portable cross-machine archival format.
- SAD will not silently enable Windows EFS because EFS certificate loss can cause permanent data loss. EFS may be exposed as an explicit operator hardening action only after recovery material is handled.
- Legacy root JSON stores that have not yet moved into the shared SQLite runtime database are not magically encrypted by this milestone. BitLocker/EFS remains the at-rest boundary for those files until their persistence migration is completed.
- CI proves DPAPI behavior on Windows runners; it does not prove BitLocker/EFS state on the physical deployment computer.

## Release rule

Encryption changes must travel through a dedicated PR and pass Linux + Windows 3.11/3.12 full suite, Protocol Black, release gate, Windows preflight, and digest-pinned Docker proof before merge.
