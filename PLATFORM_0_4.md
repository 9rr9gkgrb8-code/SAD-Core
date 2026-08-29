# SAD Platform 0.4 Alpha

This milestone moves SAD from a feature-complete Platform Alpha toward an extensible,
auditable platform without weakening the authority boundaries that made Alpha stable.

"Adolescence" is a project metaphor. The product version is `0.4-alpha`.

## What changes in 0.4

### 1. Declarative external extensions

SAD now has a reviewed extension manifest contract for out-of-process local software.
An extension registration describes what a program needs. It does **not** install code,
load Python into SAD Core, launch a process, create credentials, impersonate a user,
grant permissions, grant network access, or grant Git authority.

Platform Alpha extension rules:

- execution model: external process only
- transport: reviewed `SAD-App` HTTP contract
- network scope: loopback only
- dynamic code loading into SAD Core: disabled
- silent fallback to host execution: forbidden
- Git authority: none
- manifest fields: strict allowlist
- compatibility: recorded against the platform capability registry
- registration: Owner-governed and revocable
- credentials: created separately through existing scoped local-app management

Registration and authorization remain separate state transitions.

### 2. Evidence-bound governed skills

A working repair is not automatically a learned rule.

The governed skill lifecycle is:

`candidate -> validated -> promoted`

with terminal governance paths:

`validated/promoted -> revoked`

and versioned replacement:

`promoted vN -> superseded by promoted vN+1`

Each candidate retains:

- task signature
- active configuration fingerprint
- producer identity
- source failure IDs and/or work-item IDs
- repair summary
- execution evidence references
- optional source snapshot and diff hash

Validation additionally requires:

- explicit passing verification
- independent verifier identity
- verification evidence references
- review identity and timestamp

Promotion additionally requires:

- explicit human approval
- approving account identity
- promotion timestamp

Producer and verifier cannot be the same identity. A candidate never promotes itself.
There is no delete operation that erases provenance.

### 3. Existing role model, no RBAC sprawl

0.4 reuses SAD's current development permissions instead of adding parallel roles:

- Viewer: inspect skill state through `development:view`
- Developer: inspect and propose through `development:view` + `development:work`
- Reviewer: inspect and independently validate through `development:view` + `development:review`
- Owner: full review plus promotion/revocation through `development:govern`

Students and teachers do not receive the governed development skill surface.

### 4. Metadata-only lifecycle events

The platform event stream gains:

- `platform.extension.registered`
- `platform.extension.revoked`
- `skill.candidate.created`
- `skill.validated`
- `skill.promoted`
- `skill.revoked`

Events expose bounded lifecycle metadata, not repair text, source code, diffs, prompts,
secrets, or private conversation content.

## New API surface

Owner extension management:

- `GET /v1/platform/extensions`
- `POST /v1/platform/extensions`
- `POST /v1/platform/extensions/{extension_id}/revoke`

Governed skill workflow:

- `GET /v1/skills`
- `POST /v1/skills`
- `POST /v1/skills/{skill_id}/validate`
- `POST /v1/skills/{skill_id}/promote`
- `POST /v1/skills/{skill_id}/revoke`

The 0.4 routes are provided by `SadPlatform04Service`, a thin additive wrapper over the
existing `SadApiService`. The stable 0.3 API implementation remains underneath rather
than being rewritten for this milestone.

## Authority invariants

0.4 must always preserve all of these:

1. Platform metadata grants no authority.
2. Extension registration grants no authority.
3. Extension failure never silently falls back to unrestricted host execution.
4. Dynamic extension execution inside SAD Core remains disabled.
5. Repair success does not equal skill promotion.
6. Skill producer does not certify its own work.
7. Promotion requires explicit human approval.
8. Revoked and superseded learning remains traceable.
9. AI and extensions receive no Git publication authority.
10. Human/host remains the final Git authority.

## Not in this milestone

The following remain intentionally out of scope:

- arbitrary plugin code loading
- plugin package installation
- internet-facing extension execution
- automatic extension process launch
- automatic credential creation from a manifest
- automatic skill promotion
- automatic injection of promoted skills into every prompt
- autonomous Git commit, push, pull request, or merge authority
- replacing SAD's existing governed tool layer with a plugin marketplace

## Acceptance gate

Platform 0.4 is a merge candidate only when:

- the full existing test suite is green on Ubuntu and Windows CI
- new extension manifest tests pass
- new governed skill lifecycle tests pass
- API role/approval tests pass
- Protocol Black passes
- Alpha release gate passes
- Alpha Stable completion gate remains green
- Alpha operator preflight remains green
- Windows deployment preflight remains green
- Docker isolation proof remains green

Even after repository acceptance, physical host/device UAT is still required before
calling a particular deployment operational.
