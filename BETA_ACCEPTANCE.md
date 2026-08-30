# SAD + Forge Beta Human Acceptance Record

Candidate: `v0.5.0-beta.1`

Status: **NOT YET ACCEPTED**

This file is deliberately conservative. Check an item only after it has been performed on the intended hardware/environment. CI must never edit these boxes or infer a pass.

## Host and security

- [ ] Windows 11 clean install/startup/shutdown verified.
- [ ] BitLocker/recovery-key custody reviewed where applicable.
- [ ] LAN/router exposure reviewed; Core remains within documented network boundaries.
- [ ] TLS configuration and certificate handling reviewed.
- [ ] Owner and Developer authority boundaries exercised with real accounts.

## SAD

- [ ] Chat local-model path exercised.
- [ ] Visible built-in fallback behavior exercised.
- [ ] Personal Memory create/search/disable/expire/delete exercised.
- [ ] Governed mutating Tool Action exact-argument approval exercised.
- [ ] Owner/Developer dashboard failure evidence reviewed for usability.
- [ ] Controlled repair proposal, isolated verification, exact diff, reject, approve, and rollback exercised.
- [ ] Restart confirms protected state persistence.

## Voice and Mobile

- [ ] Physical microphone capture exercised.
- [ ] Physical speaker playback exercised.
- [ ] Real phone certificate trust and pairing exercised.
- [ ] Phone reconnect exercised.
- [ ] Phone logout/revocation exercised.

## Forge

- [ ] Start a quest from a learning objective.
- [ ] Start a quest from a homework request.
- [ ] Progressive hint flow teaches method before answer where appropriate.
- [ ] Mastery/check-work flow exercised.
- [ ] XP/rank/companion progress persists across restart.
- [ ] Student progress visibility obeys account relationships/RBAC.
- [ ] Forge failure/result evidence reaches the shared dashboard without live-code authority.
- [ ] Paired-mobile Forge flow exercised.

## Recovery

- [ ] Native backup create/verify/restore drill completed.
- [ ] Portable backup create/verify completed.
- [ ] Cross-profile or replacement-profile portable restore drill completed.
- [ ] Destination-user DPAPI re-protection verified by the documented recovery checks.

## Accessibility and evaluator experience

- [ ] Keyboard navigation smoke test completed.
- [ ] Focus/state cues readable.
- [ ] A clean evaluator can follow README/BETA instructions without owner intervention.
- [ ] Known limitations are accurate enough for public prerelease notes.

## Release decision

- [ ] All blocking automated gates are green on the exact release candidate commit.
- [ ] All required human acceptance items above are complete.
- [ ] Screenshots/demo in public materials were captured from the real running product.
- [ ] Release notes clearly mark the build as Beta/pre-release and non-production.

Final Owner decision: **HOLD** until every required blocking item is evidenced.
