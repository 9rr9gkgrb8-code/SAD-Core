# Protocol Black

Protocol Black is SAD's adversarial security validation protocol. It assumes the caller or surrounding environment may be hostile and attempts to cross trust boundaries before a release is accepted.

## Threat actors

Protocol Black tests SAD against these principals and failure modes:

1. unauthenticated browser/network caller
2. unpaired LAN caller
3. stolen paired learning device
4. low-privilege Student or Teacher
5. Developer attempting horizontal or vertical escalation
6. scoped `SAD-App` machine credential
7. malicious prompt or saved-memory content
8. malicious or compromised coding-model output
9. tampered local runtime metadata
10. hostile code running inside the Docker verification boundary

## Rules

- Fail closed when identity, scope, state, hash, origin, path, or evidence cannot be proven.
- A lower-trust principal must never gain higher-trust authority by knowing an ID or route.
- Private runtime data must never enter the coding workspace, release source, platform event payloads, or Git.
- State-changing tool actions require approval of the exact arguments later executed.
- Browser traffic to local/private services must be same-origin JSON traffic unless the endpoint is explicitly public and read-only.
- Machine credentials never become human sessions.
- AI output never becomes approval, Git authority, account authority, or live-code authority.
- Container verification never falls back to same-user local execution.
- A concrete Protocol Black failure blocks release until repaired or explicitly documented as an external deployment limitation.

## Gates

### Black 0 — Release truth
Verify the exact commit, release gate, security tests, and Docker proof being evaluated.

### Black 1 — Network and browser boundary
Attempt hostile Host, Origin, fetch-site, content-type, oversized-body, static-path, and non-loopback binding cases. Private/mobile state-changing routes must not accept cross-site browser requests.

### Black 2 — Authentication and availability
Attempt invalid sessions, role escalation, account-growth abuse, excessive session creation, password abuse, and disabled-account reuse. Storage limits must fail before replacing good state.

### Black 3 — Mobile pairing and device trust
Attempt pairing brute force, stolen/revoked device reuse, mode escalation, machine-client routing, invalid bind ranges, and raw-secret recovery from persisted state.

### Black 4 — Machine credential and event isolation
Attempt human-session impersonation, scope widening, event subscription widening, secret reuse after rotation/revocation, and sensitive event-payload publication.

### Black 5 — Memory and governed tools
Attempt cross-account memory access, expired/disabled-memory reuse, prompt injection through saved memory, action-ID guessing, argument tampering after approval, and execution before approval.

### Black 6 — Developer Workspace
Attempt path traversal, hidden/control-plane access, private-runtime access, symlink escape, unapproved-file edits, foreign-workspace execution, test-evidence tampering, stale-source apply, and Owner-boundary bypass.

### Black 7 — Repair and live apply
Attempt stale proposals, altered tested files, unexpected live changes, symlink targets, forged state, partial writes, and rollback corruption.

### Black 8 — Container boundary
Attempt network access, host write access, privilege/capability elevation, unpinned image execution, Docker-runtime substitution, excessive output, and timeout abuse.

### Black 9 — Browser/UI privacy
Attempt reflected/stored markup injection, cached private API data, token persistence outside session storage, frame embedding, unsafe MIME execution, and credential exposure.

### Black 10 — Runtime/source drift
Compare every private runtime filename/directory against coding-scope, release-scan, and Git-ignore protections so newly added platform stores cannot silently become source-code inputs.

### Black 11 — Residual risk review
Record deployment-only risks that cannot be proven in GitHub CI, including the actual Windows host, local model process, certificate trust, LAN topology, and real phone behavior.

## Current non-GitHub deployment checks

Protocol Black CI cannot prove the security of the physical Windows host, router/LAN, locally installed Docker daemon, local model binary, TLS private-key permissions, or real phone/browser certificate trust. Those require host UAT and must not be reported as passed until tested on the deployment machine.
