# SAD + Forge Mobile Preview

SAD Mobile is an optional paired phone surface for the local-first Alpha. It does **not** make the core SAD API internet-facing. The normal API remains loopback-only; phones enter through a separate TLS-only gateway with an additional device-trust layer.

## What is implemented

- Responsive phone-first SAD + Forge browser UI
- Installable Progressive Web App metadata and service worker
- iPhone/iPad standalone/home-screen support through Safari
- Android install prompt support where the browser exposes it
- One-time 8-digit pairing codes generated only by an Owner
- Pairing codes expire after 5 minutes and are single-use
- Pair-attempt rate limiting
- 30-day paired-device credentials with Owner revocation
- Device credential stored as a `Secure`, `HttpOnly`, `SameSite=Strict` cookie
- Device credentials and pairing codes are hashed at rest
- Two mobile device modes: `learning` and `full_role`
- TLS 1.2+ required before the mobile gateway starts
- Explicit private/overlay IPv4 binding only; wildcard and public IP bindings are refused
- Mobile preflight doctor
- Combined desktop + mobile launcher
- Service worker caches only static shell files; API, pairing, student, account, and repair traffic is never cached

## Authority model

Pairing trusts a **device**. Signing in authorizes a **person**. Both gates are required.

### Learning mode

Use this for student/family phones by default. The gateway permits only:

- sign in / sign out / own password change
- Personal Study
- Forge quests
- Forge hints
- Forge completion
- own Forge progress

It blocks dashboard, account administration, teacher roster, repair, and mobile-device administration routes before normal SAD role authorization is reached.

### Full role mode

The paired phone may reach the normal API surface, but SAD's existing account permissions still apply. A Student account remains a Student account. An Owner account can use Owner controls only after signing in as Owner.

Use `full_role` only for a device you intend to trust with the signed-in role's full authority.

## Network boundary

The mobile gateway refuses:

- `0.0.0.0`
- loopback addresses
- public IPv4 addresses
- hostnames in place of an explicit bind address

It accepts explicit private RFC1918-style addresses and the `100.64.0.0/10` shared-address range used by some private overlay networks. Provider-specific remote-access setup is not part of this Alpha milestone.

**Do not port-forward the SAD mobile gateway from a home router to the public internet.** Internet hosting, public TLS termination, hosted identity, recovery, and hosted secret management are still outside Alpha.

## TLS requirement

A phone must connect over HTTPS. The certificate must be valid/trusted by the phone and must match the address/name used by the phone.

SAD does not silently generate or trust a certificate for you. Certificate provisioning is deliberately a host-administration step because installing a trust root changes the security posture of the computer and phone.

Configure:

```text
SAD_MOBILE_HOST=192.168.1.20
SAD_MOBILE_PORT=8766
SAD_MOBILE_CERT=C:\path\to\trusted-mobile-cert.pem
SAD_MOBILE_KEY=C:\path\to\trusted-mobile-key.pem
```

Then run:

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

This launches:

- desktop/core UI on `http://127.0.0.1:8765/`
- paired mobile gateway on `https://<SAD_MOBILE_HOST>:8766/`

The desktop/core endpoint remains loopback-only.

## Pair a phone

1. On the host computer, sign in as Owner.
2. Open **Mobile Access**.
3. Enter a phone label.
4. Choose **Learning only** or **Full signed-in role**.
5. Select **Create 5-minute pairing code**.
6. On the phone, open the HTTPS mobile address.
7. Enter the 8-digit code and phone name.
8. After pairing succeeds, sign in using the person's normal SAD account.
9. The Owner can revoke the phone at any time from **Mobile Access**.

Revoking a device invalidates its device credential even if the browser still has the cookie.

## Install on iPhone / iPad

After the HTTPS page is trusted and paired:

1. Open the mobile SAD address in Safari.
2. Use Safari's Share menu.
3. Choose **Add to Home Screen**.
4. Launch **SAD Forge** from the new home-screen icon.

Account sessions remain intentionally memory-based. A person may need to sign in again after a SAD server restart even though the phone itself remains paired.

## Install on Android

After opening the trusted HTTPS page, supported Chromium-based browsers can surface the **Install app** control. The same PWA can also be added from the browser's install/add-to-home-screen menu.

## Offline behavior

The app shell may open while offline, but private functions require a live connection to the host. SAD does not cache API responses, study output, account data, repair evidence, student records, bearer sessions, or mobile device credentials in the service worker.

## Mobile security checks

The automated suite verifies:

- public/wildcard binding refusal
- learning-mode route isolation
- full-role mode continuing to rely on SAD RBAC
- pairing attempt rate limiting
- TLS material required before startup
- owner-only pairing administration
- single-use/expiring pairing codes
- hashed-at-rest pairing/device secrets
- device revocation
- API/pairing exclusion from service-worker caching
- phone pairing UI and touch/safe-area rules

## Current mobile designation

**Mobile Preview / Alpha companion surface.**

This mobile layer is usable only after host-specific TLS and network setup are proven on the deployment computer and phone. The implementation does not change the base Alpha rule that the core SAD service itself is local-only.
