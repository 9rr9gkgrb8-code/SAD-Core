# SAD + Forge Beta Evaluator Quickstart

This is the shortest supported evaluator path. Beta is currently a release candidate until `BETA_ACCEPTANCE.md` is completed on real hardware.

## 1. Prepare the Windows host

Install Python and Docker according to `WINDOWS.md`, then from a clean repository checkout:

```powershell
python -m pip install -r requirements.txt
python windows_doctor.py
```

Do not continue past a failed readiness check by weakening the check.

## 2. Verify the repository contract

```powershell
python -m compileall -q .
python -m unittest -v
python protocol_black.py
python release_gate.py
python alpha_stable.py
python beta_gate.py
python alpha_doctor.py
python docker_proof.py
```

`beta_gate.py` proves repository evidence only. It does not certify your microphone, phone, network, BitLocker state, accessibility, or recovery drill.

## 3. Start SAD

```powershell
.\start_sad_windows.ps1
```

Follow the startup output and documented local URL. Keep Core within its documented loopback/network boundary.

## 4. Exercise SAD

Use the running UI to:

1. sign in with an appropriate test account;
2. open Chat and confirm the response source is visible;
3. explicitly create a test Personal Memory and retrieve it;
4. exercise a state-changing governed Tool Action and confirm approval is tied to the exact arguments;
5. inspect Owner/Developer failure evidence with the appropriate role.

## 5. Exercise Forge

Start a Forge learning flow from a learning objective or homework request. Verify progressive hints, a mastery/check-work step, and persisted XP/progress. Restart before considering persistence verified.

## 6. Exercise controlled repair

Use safe test evidence rather than damaging the live host. Confirm the workflow produces an isolated proposal, independent test evidence, an exact diff, and an explicit Owner approve/reject decision. Confirm rejection does not alter live code.

## 7. Complete human acceptance

Work through `BETA_ACCEPTANCE.md` on the intended hardware. Do not mark the candidate public-ready until required device, mobile, voice, recovery, security, accessibility, and evaluator checks are evidenced.

## 8. Report problems safely

Include expected behavior, actual behavior, reproduction steps, environment, and privacy-safe evidence. Never publish `.env`, credentials, runtime databases, student PII, backup passphrases, private keys, recovery keys, or other secrets.
