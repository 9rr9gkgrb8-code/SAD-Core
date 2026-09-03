# Temporary Cloud Deployment

SAD remains provider-neutral and local-first even while temporarily hosted in the cloud.

## Boundary

- SAD Core binds only to `127.0.0.1:8765`.
- Remote users connect through an HTTPS reverse proxy or private overlay gateway.
- Do not expose port 8765 directly to the public Internet.
- Do not add home-router port forwarding.
- Secrets, TLS private keys, cloud credentials, and runtime databases stay outside Git.

## Linux VPS flow

1. Provision a small Linux VPS with a non-root admin user and firewall.
2. Install Python 3.11+, Git, and an HTTPS reverse proxy such as Caddy or an approved private overlay.
3. Clone SAD-Core and install `requirements.txt`.
4. Run repository gates before deployment.
5. Complete Owner bootstrap interactively once with `python alpha.py`, then stop it.
6. Install `deploy/sad.service.example` as a system service after replacing placeholders.
7. Configure the gateway using `deploy/Caddyfile.example` or an equivalent private tunnel.
8. Verify `/health` only through the HTTPS/private endpoint.

## Migration back to private server

Clients store the backend as a validated endpoint profile. Change the profile from the temporary cloud URL to the future private-server HTTPS URL. The API contract, account model, Forge skill trees, and client code do not change.

## Client plan

- Web/PWA: same-origin shell, installable where supported.
- Windows: thin native wrapper around the same web client/API.
- Android/iOS: shared mobile client using the same versioned API and endpoint profile.
- Offline caches must never contain credentials or unrestricted sensitive memory.
