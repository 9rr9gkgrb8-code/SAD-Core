# Protocol Black — Initial Adversarial Audit Report

Date: 2026-08-27 (America/New_York)

Target: `SAD-Core` Platform `0.3-alpha`

Protocol Black assumes hostile unauthenticated callers, compromised paired devices, low-privilege users, scoped machine credentials, malicious prompts/model output, and tampered runtime artifacts. This report records the concrete findings discovered during the first run and the remediation included in the same security release.

## Fixed findings

### PB-001 — HIGH — Tier 2/3 private runtime data could drift into Developer Workspace scope

**Finding:** Developer Workspace already excluded `local_data/`, but newer runtime stores were introduced at repository root after the original denylist was written. `memory.json`, `tool_actions.json`, `platform_clients.json`, and `platform_events.json` were text/JSON files that could be mistaken for approved coding source.

**Impact:** A Developer could potentially place private runtime data in isolated coding context and expose it to the coding model/workspace/evidence surface.

**Fix:** All four stores now default below protected `local_data/`. Legacy root files are migrated before the service becomes available. If both legacy and protected copies exist, startup fails closed rather than guessing which contains authoritative private data. A shared `runtime_privacy.py` registry and Protocol Black drift tests keep private-store policy centralized.

### PB-002 — MEDIUM — Developer could execute another Developer's workspace

**Finding:** `development:work` was checked before execution, but workspace creator identity was not.

**Impact:** A Developer could execute a peer's already-scoped workspace and replace the generated diff/test evidence. Live application still required Owner, but review integrity could be disturbed.

**Fix:** A non-Owner Developer may execute only a workspace whose `created_by` account matches the signed-in account. Owner may execute any governed workspace. Regression tests cover peer denial and Owner override.

### PB-003 — MEDIUM — Browser-to-local/private request boundary was too permissive

**Finding:** The loopback API and private mobile gateway relied primarily on authentication/SameSite behavior and did not explicitly reject hostile Host/Origin/fetch-site or simple non-JSON POST traffic.

**Impact:** This left unnecessary DNS-rebinding/cross-site request surface against local/private listeners.

**Fix:** API requests now validate approved listener Host names, same-origin browser metadata when supplied, and `application/json` for POST. Mobile additionally requires Host to match the configured private listener address. JSON/static responses carry no-store/nosniff/referrer/cross-origin-resource protections.

### PB-004 — MEDIUM — Eight-digit pairing hashes were cheap to attack offline

**Finding:** One-time pairing codes were rate-limited online but persisted as unsalted SHA-256. The code space is only 100,000,000 values.

**Impact:** Theft of the mobile pairing-state file during the five-minute pairing window made offline recovery cheaper than intended.

**Fix:** New pairings use salted PBKDF2-HMAC-SHA256 with 200,000 iterations. Existing high-entropy device tokens retain constant-time SHA-256 comparison. Outstanding pairings and active devices are bounded. Pre-Black pairings receive transitional verification only for their already-short lifetime.

### PB-005 — MEDIUM — Account/session growth could create availability pressure

**Finding:** The accounts file had a read-time size ceiling but no write-time preflight size check or account-count ceiling, and in-memory sessions were unbounded.

**Impact:** An authorized or stolen credential with account-creation access could grow persistent state until a later load failed; repeated successful logins could grow process memory.

**Fix:** SAD now checks serialized account size before replacement, caps Alpha installations at 500 accounts, caps active sessions per account and globally, prunes expired sessions, and evicts the oldest session when bounded capacity is reached.

### PB-006 — MEDIUM — Tool approval was not cryptographically bound to exact arguments

**Finding:** Tool actions stored arguments and approval state together, but execution did not verify that the arguments were unchanged after approval.

**Impact:** Current tools are intentionally narrow, but future stronger tools would make runtime metadata tampering after approval more consequential.

**Fix:** Each action stores a canonical SHA-256 argument fingerprint. Approval records the exact fingerprint. Execution revalidates tool identity, mutation/approval metadata, current arguments, and approved fingerprint. Mismatch moves the action to `tampered` and refuses execution.

### PB-007 — MEDIUM — Event privacy depended only on correct callers

**Finding:** Platform event callers intentionally emitted metadata, but the event store itself accepted arbitrary detail keys.

**Impact:** A future feature could accidentally publish conversation text, prompts, tokens, diffs, or other sensitive values into machine-readable events.

**Fix:** The event-store boundary recursively rejects high-risk payload keys such as content, message, prompt, password, secret, token, transcript, material, diff, source code, args, and output.

### PB-008 — MEDIUM — Saved Memory could resemble model instructions

**Finding:** Saved Memory entered the Local AI prompt as conversational-looking text.

**Impact:** Copied or malicious memory text could attempt prompt injection, even though the model itself has no direct authority to execute tools or approvals.

**Fix:** The system prompt explicitly labels saved memory/conversation history as untrusted data. Context is serialized as JSON under an `UNTRUSTED CONTEXT DATA` boundary and separated from the current user request. This is defense-in-depth; model prompt-injection resistance is never treated as an authorization boundary.

### PB-009 — LOW/MEDIUM — Mobile bind classification was broader than the documented intent

**Finding:** Python's generic `is_private` classification can include non-global ranges beyond the intended LAN/overlay policy.

**Fix:** The gateway now accepts only RFC1918 `10/8`, `172.16/12`, `192.168/16`, and approved CGNAT/overlay `100.64/10` IPv4 addresses. Wildcard, loopback, link-local, documentation, multicast, public, hostname, and IPv6 binds remain rejected for this Alpha gateway.

### PB-010 — MEDIUM — CI supply-chain references were movable

**Finding:** Runtime sandbox execution required a digest-pinned image, but CI first resolved that digest from mutable `python:3.11-slim`; official GitHub Actions were referenced by movable major tags.

**Fix:** CI now pins the reviewed Python image digest and pins `actions/checkout` and `actions/setup-python` to exact commit SHAs. Protocol Black tests reject reintroduction of mutable action tags or the mutable Docker tag pull.

## Security controls that resisted the Black pass

The audit revalidated existing boundaries rather than changing them where they already failed closed:

- SAD Core refuses non-loopback bind addresses.
- Mobile machine-client routes remain blocked even in Full Role mode.
- `SAD-App` secrets cannot authenticate as human Bearer sessions.
- Memory and Tool Actions are account-owned.
- Student/Teacher roles cannot enter development governance.
- Developer cannot apply live code.
- Reviewer cannot apply live code.
- Owner approval remains required for live coding/repair application.
- Developer Workspace rejects traversal, hidden/control-plane paths, symlinks, unapproved edits, stale live source, and post-test workspace tampering.
- Repair/live-apply uses source/test hashes, atomic replacement, verified backups, and rollback.
- Docker verification remains digest-pinned, `--pull never`, networkless, read-only, capability-dropped, non-root, resource-limited, and without Docker-socket/Git authority.
- PWA service-worker policy excludes `/v1/*` and `/mobile/*` private traffic from caching.
- Browser CSP and frame-ancestor policy remain restrictive.

## Residual risks requiring deployment UAT

These are not marked as passed by GitHub CI:

1. Security and patch level of the actual Windows host.
2. Security of the locally installed Docker daemon and its host permissions.
3. Authenticity/trustworthiness of the installed local model runtime and model files.
4. TLS private-key permissions and phone certificate trust on the real deployment.
5. Router/LAN segmentation, hostile-device exposure, and assurance that no public port forwarding exists.
6. Connection-flood/slow-client resilience of the simple Alpha HTTP servers under a hostile LAN. Private-network binding and pairing reduce exposure, but production-grade connection admission/rate limiting should be added before broader network deployment.
7. Prompt injection remains a model-quality risk. Prompt text is never relied upon as the authorization boundary; server-side RBAC/approval remains authoritative.
8. Physical/local-OS compromise can bypass application-layer guarantees and is outside SAD's current Alpha threat boundary.

## Release rule

A Protocol Black regression is release-blocking. `python protocol_black.py` must print `PROTOCOL BLACK: PASS`, the normal full suite/release gate/preflight must pass, and the Docker isolation proof must remain green before a Black-hardened release may merge.
