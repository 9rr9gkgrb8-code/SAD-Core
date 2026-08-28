# SAD Windows Deployment Gate

Windows is the intended first host environment, so Windows compatibility and Encryption
Tier 2 are tested in CI rather than inferred from Linux results.

## CI coverage

Every change must pass the normal full suite, Protocol Black, release gate, and Alpha
preflight on:

- Ubuntu 24.04 / Python 3.11;
- Windows Server 2025 runner / Python 3.11;
- Windows Server 2025 runner / Python 3.12.

CI installs the exact dependency manifest in `requirements.txt`. Windows tests exercise
real current-user DPAPI, runtime payload confidentiality, legacy migration/downgrade
rejection, native encrypted backup/restore, portable AES-GCM backup authentication, and
destination-user re-protection during portable restore.

The Windows runner is not a substitute for the actual Windows 11 deployment computer,
but it catches path, file-locking, permissions, `os.replace`, SQLite, DPAPI, crypto-package,
PowerShell-adjacent, and Python-version regressions before host UAT.

Docker isolation proof remains on the reviewed Ubuntu runner and must be repeated on the
actual Windows host with Docker Desktop before coding/repair is claimed operational.

## Encryption layers

SAD uses layered protection:

1. **Windows DPAPI application layer** protects live/default runtime document payloads and
   native `.sadbak` containers for the current Windows user.
2. **Portable AES-256-GCM backup layer** provides passphrase-based cross-profile disaster
   recovery. The live DB is exported host-neutral only in memory and re-protected with
   destination-user DPAPI before restore writes live SQLite bytes.
3. **BitLocker/full-disk encryption** should protect the physical Windows volume and
   backup media against offline disk theft/access.
4. **Mobile TLS** protects supported phone traffic in transit.
5. Passwords and machine/device secrets remain one-way hashed where recovery of the
   original value is unnecessary.

SAD does not silently enable Windows EFS. EFS recovery/certificate handling must be
planned before enabling it because losing the EFS key can make data unrecoverable.

## Host setup and preflight

On the real Windows machine, from the SAD-Core folder:

```powershell
python -m pip install --disable-pip-version-check --no-input -r requirements.txt
python windows_doctor.py
```

The Windows doctor requires:

- Windows operating system;
- Alpha core preflight not blocked;
- writable `local_data/`;
- a successful real current-user DPAPI confidentiality/round-trip probe;
- versioned SQLite runtime database creation/open and `quick_check` success;
- live runtime payload protection using `windows-dpapi-user-v1`;
- the exact reviewed portable-backup `cryptography` dependency.

Local model, Docker repair isolation, and STT/TTS may report warnings when optional
components are not configured. Those warnings become feature-specific blockers before
claiming that feature operational.

## Guarded startup

After the Windows doctor passes:

```powershell
.\start_sad_windows.ps1
```

The script refuses to launch `alpha.py` if Windows preflight blocks.

## Before declaring Encryption Tier 2 operational

1. Pull the exact green `main` release.
2. Install `requirements.txt` exactly as reviewed.
3. Run `python -m unittest -v` locally.
4. Run `python protocol_black.py` locally.
5. Run `python windows_doctor.py` and require DPAPI/runtime/portable-crypto checks to pass.
6. Verify BitLocker/full-disk encryption status and recovery-key custody on the real host.
7. Configure and validate the intended loopback local model.
8. Configure Docker Desktop and the reviewed digest-pinned sandbox image.
9. Run `python docker_proof.py` and require success.
10. Create and verify a native DPAPI backup with `backup.py`.
11. Create and verify a portable backup with `backup.py portable-create`.
12. Complete `ENCRYPTION_TIER2_UAT.md`, preferably restoring the portable archive under a
    second disposable Windows profile or replacement test machine.
13. Confirm the restored DB is re-protected for the destination Windows user and SAD starts
    without the original source profile.
14. Run the documented Alpha/Tier 2/Tier 3 human UAT.
15. Configure private TLS and run mobile UAT before claiming phone operation.
16. If audio Voice is desired, configure reviewed loopback STT/TTS services and test real
    microphone/speaker behavior separately.

## Remaining host boundary

DPAPI protects copied live application data from offline reading outside its Windows
protection context. It does not protect SAD from malware or an attacker already running
as the logged-in Windows user. Portable recovery is only as strong as its passphrase, and
losing that passphrase means SAD cannot recover that archive.

Host patch state, Windows account security, BitLocker recovery, Docker daemon privileges,
router/LAN configuration, certificate key permissions, GPU/model runtime provenance,
portable-backup custody/passphrase handling, phone trust, and physical compromise remain
deployment responsibilities outside application CI.
