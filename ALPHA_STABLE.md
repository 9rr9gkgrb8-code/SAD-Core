# SAD + Forge Alpha Stable

Alpha Stable freezes the existing Alpha product scope. It does not add Beta features or
widen any authority boundary. A product surface is 100% code-complete only when every
declared module, capability, contract, implementation, regression test, security control,
and operator document required by `alpha_stable.py` is present and all CI gates pass.

## SAD completion contract — 100%

- Platform discovery, compatibility, scoped local apps, and privacy-minimized events.
- Durable Chat and transcript Voice with explicit local-provider boundaries.
- Account-owned Memory and exact-argument governed Tool Actions.
- Request-directed Personal Study without an arbitrary question-count ceiling.
- Owner/Developer shared dashboard evidence and role-specific authority.
- Docker-isolated development and repair with independent verification, exact diff,
  Owner apply, and rollback.
- Accounts/RBAC, paired private-TLS Mobile, protected SQLite persistence, native backup,
  portable recovery, and destination-user DPAPI re-protection.
- Protocol Black, supply-chain pinning, bounded HTTP admission, release integrity, Windows
  readiness, accessibility regression checks, and digest-pinned Docker proof.

## Forge completion contract — 100%

- Versioned SAD–Forge HTTP/JSON contract with fail-closed validation.
- Game-first quests, progressive hints, mastery checks, XP, ranks, companion evolution,
  and durable per-student progress.
- Homework, study, examples, essay/rubric review, and check-work support through the
  request-directed Study/Forge boundary without a fixed three-question sequence.
- Child-facing injection/PII screening and privacy-minimized failure/result reporting.
- Isolated Forge work evidence, independent verification, human disposition, and no
  worker authority to merge, publish, access credentials, or alter live SAD code.
- Owner/teacher progress visibility constrained by account relationships and RBAC.
- Desktop and paired-mobile UI/accessibility regression coverage.

## Required automated gates

```text
python -m compileall -q .
python -m unittest -v
python protocol_black.py
python release_gate.py
python alpha_stable.py
python alpha_doctor.py
python windows_doctor.py
python docker_proof.py
```

`alpha_stable.py` reports SAD and Forge separately and fails closed below full completion.
The percentage describes the frozen repository-backed Alpha contract, not production
readiness or unperformed physical-device acceptance.

## Operational acceptance remains human

Physical microphone/speaker testing, real phone certificate trust/pairing, multi-role
human accessibility UAT, BitLocker and recovery-key custody, backup-passphrase custody,
LAN/router review, and GitHub branch-protection administration cannot be converted into
code assertions. They remain deployment acceptance gates and must not be reported as
passed until a human performs them.
