# SAD Mobile Preview

SAD Mobile is the paired phone client for the local-first platform. It does **not** make
the normal SAD Core API internet-facing. Core remains loopback-only; phones enter
through a separate TLS-only gateway and must pass both device pairing and normal account
sign-in.

## Implemented phone surfaces

- SAD Chat with private durable conversations
- Voice transcript bridge
- Personal Memory
- Governed personal Tool Actions
- Personal Study
- Forge learning and own progress
- Code Workspace for authorized `full_role` development accounts
- SAD Platform/Owner controls where normal account RBAC permits them
- Installable PWA shell for iPhone/iPad and supported Android browsers

The phone is a client. Local AI generation, coding generation, repair generation, and
Docker verification run on the host computer.

## Device trust

Owner creates a one-time 8-digit pairing code. Codes expire after five minutes, are
single-use, and pairing attempts are throttled. Paired-device credentials expire after
30 days, are revocable by Owner, are hashed at rest, and are delivered to the browser
as a `Secure`, `HttpOnly`, `SameSite=Strict` cookie.

Pairing trusts the device. It does not create a SAD account session or grant a role.

## Learning mode

Use `learning` for student/family phones by default. The gateway admits only explicitly
matched personal routes:

- account sign-in/sign-out/own password change
- SAD Chat and owned conversation history
- Voice transcript turns
- own Personal Memory create/list/search/update/delete
- own governed Tool Action catalog/actions/decisions/execution
- Personal Study
- Forge quests/hints/completion
- own Forge progress

Memory and Tool IDs remain account-owned after the device gate. Knowing another
account's UUID does not grant access.

Learning mode blocks:

- development dashboard
- Developer Workspace
- repair governance
- account administration
- teacher/admin rosters
- mobile-device administration
- Owner Platform administration
- `SAD-App` machine-client endpoints

The gateway uses exact route patterns rather than broad `/v1/memory*` or `/v1/tools*`
prefix admission.

## Full role mode

`full_role` admits normal human API routes after pairing, then SAD's existing account
RBAC remains authoritative. A Developer still cannot perform Owner application. A
Student remains a Student.

`/v1/platform/client/*` machine-client endpoints are blocked by the mobile gateway even
in `full_role`. Scoped `SAD-App` credentials are intended for loopback machine-to-machine
integrations on the host, not phone distribution.

## Memory on a phone

The **Memory & Tools** surface lets the signed-in person explicitly save, search,
enable/disable, and delete personal memories. The API also supports category/content
edits and optional expiry.

SAD does not automatically turn normal conversation into long-term Memory. Enabled,
non-expired entries may be supplied to the configured Local AI for Chat or Voice unless
the request specifies `use_memory: false`.

If the full Local AI is unavailable and SAD falls back to Built-in dialogue, the
response does not claim that saved Memory was used.

## Governed Tools on a phone

Tier 3 tools are a fixed reviewed catalog:

- `platform.status`
- `memory.search`
- `memory.remember`
- `memory.forget`

Read-only tools can enter `ready`. A state-changing tool starts
`awaiting_approval`; the signed-in person must explicitly approve or reject it before
execution. Rejected actions cannot execute.

There is no generic shell, arbitrary URL/network request, dynamic plugin/Python loader,
package installer, unrestricted filesystem action, or Git tool in Tier 3.

## Voice

`POST /v1/voice/turn` accepts transcript text and returns SAD reply text plus
`speech_text` for a later local TTS client. It shares account-owned Chat history and the
same optional Personal Memory context.

Direct browser microphone capture/STT/TTS is not bundled yet. The mobile security
policy still disables browser microphone access until that client trust boundary is
implemented and tested.

## Network and TLS boundary

The mobile gateway requires TLS 1.2+ and one explicit private/approved-overlay IPv4
binding. It refuses wildcard, loopback, hostname-as-bind-target, and public IPv4
bindings.

Do **not** router-port-forward the mobile gateway to the public internet. Public hosting,
hosted identity/recovery, public TLS termination, and hosted secrets remain outside the
Alpha boundary.

Before phone use, configure the host address/certificate/key and require:

```text
python mobile_doctor.py
MOBILE GATEWAY: READY
```

Then start:

```text
python mobile.py
```

The desktop/core UI remains on `http://127.0.0.1:8765/`; the phone uses the configured
private HTTPS gateway.

## PWA privacy

The service worker may cache static shell assets including the Memory & Tools JS/CSS.
It explicitly skips all `/v1/*` and `/mobile/*` traffic. Conversation text, Memory,
Tool Actions, Study output, Forge data, coding diffs/tests, account records, repair
evidence, sessions, pairing data, and credentials are therefore not stored in the PWA
API cache.

## Acceptance

Mobile Preview remains a host/device claim, not only a code claim. Run the base mobile
UAT plus `PLATFORM_TIER3_UAT.md` on the deployment computer and phone before calling
Memory/Tools operational on that device. The key Tier 3 checks are account isolation,
Memory disable/expiry, per-turn memory opt-out, mutating-tool approval, privileged-route
denial, machine-route denial, and PWA cache privacy.
