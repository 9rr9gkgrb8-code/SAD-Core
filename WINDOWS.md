# SAD Windows Deployment Gate

Windows is the intended first host environment, so Windows compatibility is now tested
in CI rather than inferred from Linux results.

## CI coverage

Every change must pass the normal full suite, Protocol Black, release gate, and Alpha
preflight on:

- Ubuntu 24.04 / Python 3.11;
- Windows Server 2025 runner / Python 3.11;
- Windows Server 2025 runner / Python 3.12.

The Windows runner is not a substitute for the actual Windows 11 deployment computer,
but it catches path, file-locking, permissions, `os.replace`, SQLite, PowerShell-adjacent,
and Python-version compatibility regressions before host UAT.

Docker isolation proof remains on the reviewed Ubuntu runner and must be repeated on the
actual Windows host with Docker Desktop before coding/repair is claimed operational.

## Host preflight

On the real Windows machine, from the SAD-Core folder:

```powershell
python windows_doctor.py
```

The Windows doctor requires:

- Windows operating system;
- Alpha core preflight not blocked;
- writable `local_data/`;
- versioned SQLite runtime database creation/open and `quick_check` success.

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
4. Run `python windows_doctor.py`.
5. Configure the intended loopback local model and validate a real Chat turn.
6. Configure Docker Desktop and the reviewed digest-pinned sandbox image.
7. Run `python docker_proof.py` and require success.
8. Create and verify a real backup with `backup.py`.
9. Exercise backup restore on disposable/test state before relying on it.
10. Run the documented Alpha/Tier 2/Tier 3 human UAT.
11. Configure private TLS and run mobile UAT before claiming phone operation.
12. If audio Voice is desired, configure reviewed loopback STT/TTS services and test real
    microphone/speaker behavior separately.

Host firewall, Windows account security, full-disk encryption, Docker daemon privileges,
router/LAN configuration, certificate key permissions, GPU/model runtime provenance,
and physical compromise remain deployment responsibilities outside application CI.
