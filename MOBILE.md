# SAD + Forge Mobile Preview

SAD Mobile is an optional paired phone surface for the local-first Alpha. It does **not**
make the core SAD API internet-facing. The normal API remains loopback-only; phones
enter through a separate TLS-only gateway with an additional device-trust layer.

## What is implemented

- Responsive phone-first SAD + Forge browser UI
- Free-form **SAD Chat** with durable per-account conversation history and follow-up context
- **Voice Client Bridge** transcript route for signed-in phone conversations
- **Code Workspace** shell for authorized Full Role development accounts
- **SAD Platform** surface for authorized Full Role development accounts
- Installable PWA metadata/service worker
- iPhone/iPad home-screen and Android install support where browser/platform allows
- Owner-created one-time 8-digit pairing codes, 5-minute expiry, single use
- Pair-attempt rate limiting
- 30-day paired-device credentials with Owner revocation
- Device credential stored as a Secure, HttpOnly, SameSite=Strict cookie and hashed at rest
- `learning` and `full_role` device modes
- TLS 1.2+ requirement
- Explicit private/approved-overlay IPv4 binding only
- Mobile preflight doctor, combined desktop/mobile launcher, and Windows wrapper
- Static-shell-only PWA caching; private `/v1/*` and `/mobile/*` traffic is never cached

## SAD Chat and Voice on a phone

SAD Chat is the normal conversation lane. Forge remains the game/tutoring lane.

The phone is a secure client. The host PC runs SAD and the configured local model.
When the model is unavailable, SAD visibly uses the limited Built-in dialogue fallback.

`POST /v1/voice/turn` adds the first Voice transport contract. It accepts transcript
text from a signed-in person, optionally continues an existing owned Chat session,
and returns reply text plus `speech_text` for future local TTS.

This milestone does **not** turn on direct browser microphone capture. The mobile
security headers still set `microphone=()` because no browser STT/TTS trust boundary has
been approved yet. A future native/browser speech client can convert speech to text and
call the same Voice endpoint without changing SAD's conversation ownership model.

Chat/Voice text does not grant repair, coding, app-management, approval, or Git authority.

## Code Workspace on a phone

Code Workspace is available only through a `full_role` paired phone whose signed-in
account already has development permissions.

- **Owner:** plan/create/execute, inspect exact diff/tests, apply, rollback.
- **Developer:** plan/create/execute/inspect, but no live apply/rollback.
- **Reviewer / Viewer:** inspection only according to normal permissions.
- **Student / Teacher:** no Code Workspace authority.

Generation and Docker testing happen on the host, never on the phone.

## Platform and local-app boundary on mobile

Full Role Owner/development accounts may use the normal human **SAD Platform** UI and
its normal RBAC-protected routes.

However, Tier 2 `SAD-App` machine-client endpoints under `/v1/platform/client/*` are
explicitly rejected by the mobile gateway in **both** device modes. Machine credentials
are a loopback core API feature for local host integrations, not network credentials to
be carried through the phone gateway.

Owner app secrets and Platform event API responses are also excluded from PWA caching.

## Authority model

Pairing trusts a **device**. Signing in authorizes a **person**. Both gates are required.

### Learning mode

Default for student/family phones. The gateway permits only explicitly matched routes:

- sign in / sign out / own password change
- SAD Chat
- Voice transcript turn
- Personal Study
- Forge quests/hints/completion
- own Forge progress

It blocks Code Workspace, dashboard, account administration, teacher roster, repair,
Platform app administration, mobile-device administration, and all machine-client
routes before normal SAD account RBAC is reached.

### Full role mode

The paired phone may reach the normal **human** API surface, but SAD account permissions
remain authoritative. Student remains Student; Developer cannot apply code; Owner gets
Owner controls only after Owner login.

Machine-client `/v1/platform/client/*` routes remain blocked even in Full Role mode.

## Network boundary

The mobile gateway refuses wildcard, loopback, public IPv4, and hostname bind values.
It accepts explicit private RFC1918-style addresses and the `100.64.0.0/10` shared
address range used by some private overlay networks.

**Do not port-forward the SAD mobile gateway to the public internet.**

## TLS requirement

A phone must connect over HTTPS with a certificate trusted by the phone and matching
the address/name used to connect. SAD does not silently install a trust root.

Example configuration:

```text
SAD_MOBILE_HOST=192.168.1.20
SAD_MOBILE_PORT=8766
SAD_MOBILE_CERT=C:\path\to\trusted-mobile-cert.pem
SAD_MOBILE_KEY=C:\path\to\trusted-mobile-key.pem
```

Run:

```text
python mobile_doctor.py
```

Required result:

```text
MOBILE GATEWAY: READY
```

## Start desktop + mobile together

```text
python mobile.py
```

This launches desktop/core UI at `http://127.0.0.1:8765/` and the paired gateway at
`https://<SAD_MOBILE_HOST>:8766/`.

## Pair a phone

1. Sign in as Owner on the host.
2. Open **Mobile Access**.
3. Enter a phone label.
4. Choose Learning only or Full signed-in role.
5. Create the 5-minute pairing code.
6. Open the trusted HTTPS mobile address on the phone.
7. Enter the code and device name.
8. Sign in with the person's normal SAD account.
9. SAD Chat opens as the primary conversation view.
10. Learning mode may use Chat, Voice transcript transport, Study, and Forge.
11. Authorized Full Role development accounts can also use Platform/Code Workspace.
12. Owner can revoke the phone at any time.

Revocation invalidates server-side device trust even if the browser still holds its
cookie.

## Install

On iPhone/iPad Safari, use Share → Add to Home Screen. On supported Android Chromium
browsers, use Install app/Add to Home Screen. Account sessions remain memory-only, so a
server restart can require login again while device pairing remains valid.

## Offline behavior

The static app shell may open offline, but private functions require a live connection
to the host. The service worker does not cache API responses, Chat/Voice text,
Developer Workspace evidence, Platform manifests/events/app secrets, Study output,
account/student data, repair evidence, Bearer sessions, pairing codes, or device
credentials.

## Automated mobile checks

The suite verifies:

- public/wildcard/loopback/hostname bind refusal
- Learning exact-route isolation
- Voice allowed for signed-in Learning phones
- machine-client endpoint denial in Learning and Full Role modes
- Full Role continuing to rely on human SAD RBAC
- Developer-vs-Owner Code Workspace authority
- pairing rate limiting, expiry, single use, hashing, and revocation
- TLS material requirement
- Owner-only pairing administration
- PWA private-traffic cache exclusion
- account-owned conversation isolation
- phone touch/safe-area/narrow-screen rules

## Current designation

**Mobile Preview / Alpha companion surface.**

Operational readiness still requires host-specific TLS/network proof and real phone UAT.
Direct microphone capture, bundled speech-to-text/text-to-speech, and public-internet
mobile hosting are not current Alpha claims.
