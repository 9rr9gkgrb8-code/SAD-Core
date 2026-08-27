# SAD + Forge Alpha 1

## Start

Run `python alpha.py`, complete the one-time owner setup, then open the displayed
`http://127.0.0.1:8765/` address. The application accepts local connections only.

The owner can create student, teacher, developer, reviewer, and viewer accounts.
Each person receives a separate credential. Students never see developer controls.

## Included surfaces

- Personal Study with all request-directed actions and optional local-model output
- Forge Student quests, hints, boss checks, XP, ranks, and companion progression
- Teacher student-progress roster
- Owner account administration
- Shared role-filtered Failure Inbox and Forge job dashboard
- Explicit review, push, isolation approval, isolated execution, decision, and close controls
- Password change and session revocation

## Private data and backups

`accounts.json`, `dashboard_state.json`, `student_progress.json`, `failures.json`,
`.env`, `local_data/`, and `.sad_sandbox/` are local runtime data and are ignored by
Git. Stop the app before copying those files into an encrypted backup. Never put
that backup in the public repository.

## Isolation

Forge verification requires Docker plus a preloaded digest-pinned image in
`SAD_SANDBOX_IMAGE`. Without it, execution stops as `isolation_unavailable`; there
is no local-process fallback. Forge produces evidence only. Human roles retain all
approval, export, and Git authority.

## Alpha boundary

This release is for one trusted computer or a controlled local pilot. It is not an
internet deployment: the server deliberately refuses non-loopback binding and does
not provide TLS, email recovery, federation, or hosted secret management.
