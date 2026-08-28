# SAD Windows Deployment Gate

Windows is the intended first host environment, so Windows compatibility and Encryption
Tier 1 are tested in CI rather than inferred from Linux results.

## CI coverage

Every change must pass the normal full suite, Protocol Black, release gate, and Alpha
preflight on:

- Ubuntu 24.04 / Python 3.11;
- Windows Server 2025 runner / Python 3.11;
- Windows Server 2025 runner / Python 3.12.

Windows tests include real current-user DPAPI round-trip, tamper/purpose rejection,
runtime payload confidentiality, plaintext-to-protected migration, downgrade rejection,
and encrypted backup/restore behavior.

The Windows runner is not a substitute for the actual Windows 11 deployment computer,
but it catches path, file-locking, permissions, `os.replace`, SQLite, DPAPI,
PowerShell-adjacent, and Python-version compatibility regressions before host UAT.

Docker isolation proof remains on the reviewed Ubuntu runner and must be repeated on the
actual Windows host with Docker Desktop before coding/repair is claimed operational.

## Encryption layers

SAD uses layered protection rather than treating one mechanism as magic armor:

1. **Windows DPAPI application layer** protects Tier 2/3 SQLite document payloads and
   `.sadbak` backup containers for the current Windows user.
2. **BitLocker/full-disk encryption** should protect the physical Windows volume and
   backup media against offline disk theft/access.
3. **Mobile TLS** protects supported phone traffic in transit.
4. Passwords and machine/device secrets remain one-way hashed where recovery of the
   original secret is unnecessary.

SAD does not silently enable Windows EFS. EFS recovery/certificate handling must be
planned before enabling it because losing the EFS key can make data unrecoverable.

## Host preflight

On the real Windows machine, from the SAD-Core folder:

```powershell
python windows_doctor.py
```

The Windows doctor requires:

- Windows operating system;
- Alpha core preflight not blocked;
- writable `local_data/`;
- a successful real current-user DPAPI confidentiality/round-trip probe;
- versioned SQLite runtime database creation/open and `quick_check` success;
- live runtime payload protection using `windows-dpapi-user-v1`.

Local model, Docker repair isolation, and STT/TTS may report warnings when optional
components are not configured. Those warnings become feature-specific blockers before
claiming that feature operational.

## Guarded startup

After the Windows doctor passes:

```powershell
.\start_sad_windows.ps1
```

The script refuses to launch `alpha.py` if Windows preflight blocks.

## Before declaring Windows Alpha operational

1. Pull the exact green `main` release.
2. Run `python -m unittest -v` locally.
3. Run `python protocol_black.py` locally.
4. Run `python windows_doctor.py` and require the DPAPI/runtime encryption checks to pass.
5. Verify BitLocker/full-disk encryption status on the real host and intended backup
   media. This is a host check, not something SAD silently enables.
6. Configure the intended loopback local model and validate a real Chat turn.
7. Configure Docker Desktop and the reviewed digest-pinned sandbox image.
8. Run `python docker_proof.py` and require success.
9. Create and verify a real encrypted `.sadbak` with `backup.py`.
10. Exercise encrypted backup restore on disposable/test state before relying on it.
11. Run the documented Alpha/Tier 2/Tier 3 human UAT.
12. Configure private TLS and run mobile UAT before claiming phone operation.
13. If audio Voice is desired, configure reviewed loopback STT/TTS services and test real
    microphone/speaker behavior separately.

## Remaining host boundary

DPAPI protects copied application data from casual/offline reading outside its Windows
protection context. It does not protect SAD from malware or an attacker already running
as the logged-in Windows user. Host patch state, Windows account security, BitLocker
recovery, Docker daemon privileges, router/LAN configuration, certificate key
permissions, GPU/model runtime provenance, backup custody, and physical compromise remain
deployment responsibilities outside application CI.
