# Forge Private Alpha: Cloud + Mobile

Forge is intended to be tested remotely as an invite-only learning product while SAD Core remains the governed infrastructure underneath it.

## Alpha goal

Start with 10-20 invited learners, not an open public launch. The purpose is to validate repeat use, learning progression, reliability, and parent/teacher trust before scaling.

## Deployment shape

```text
Phone / tablet / laptop
        |
      HTTPS
        |
Caddy or approved private gateway
        |
127.0.0.1:8765
        |
SAD Core + Forge
        |
Encrypted / protected runtime state
```

SAD Core must never bind directly to a public interface. The reverse proxy is the Internet-facing trust boundary and forwards only to loopback.

## Cloud host checklist

1. Provision a small Linux VPS with a non-root administrator and firewall.
2. Install Python 3.11+, Git, Caddy, and required system packages.
3. Clone this repository into an application-owned directory.
4. Install pinned Python dependencies from `requirements.txt`.
5. Run the complete repository gates before deployment.
6. Bootstrap the Owner account interactively once.
7. Install the reviewed systemd service example.
8. Configure a real HTTPS hostname from `deploy/Caddyfile.example`.
9. Keep 8765 closed at the provider firewall and host firewall.
10. Verify `/health`, sign-in, Forge quest creation, hints, completion, progress persistence, logout, and restart recovery through the HTTPS hostname.
11. Test on iPhone Safari, Android Chrome, and a desktop browser before inviting learners.
12. Back up runtime state and perform at least one restore drill before expanding the pilot.

## Mobile experience

The web client is an installable PWA-style shell and now includes a mobile-first layer with:

- safe-area support for notches and home indicators;
- 48px minimum primary navigation targets;
- bottom thumb navigation on phones;
- responsive Forge quest, mastery, companion, hint, and boss-gate views;
- full-width mobile actions and 16px form controls to avoid iOS zoom;
- horizontally bounded tables and progress paths;
- no credential caching in the offline shell.

## Invite-only learner model

For the first remote test:

- Owner creates accounts; there is no open self-registration.
- Student accounts receive only learner permissions.
- Use unique temporary passwords and require password changes when practical.
- Revoke accounts/devices immediately when a pilot ends.
- Keep Owner/Developer credentials off shared learner devices.
- Do not expose developer, repair, Git, or administrative authority to student accounts.

## Testing with minors

Before inviting children outside the household, define and document the parent/guardian consent flow, what learner data is collected, retention/deletion behavior, incident contact path, and who can inspect student activity. Avoid collecting data that is not required for the learning experience. A private alpha is not a substitute for legal/privacy review before a broader commercial launch.

## Alpha success metrics

Track product evidence rather than raw account count:

- weekly active learners;
- voluntary sessions per learner;
- quests started and completed;
- hint depth used;
- mastery/boss-check completion;
- return rate after week 1;
- parent/learner reported friction;
- whether learners can perform a comparable task without assistance afterward.

## Not yet claimed

This repository is cloud-ready scaffolding, not evidence of a live production deployment. A real provider account, DNS name, TLS certificate, runtime backup, external-device UAT, monitoring, privacy/consent process, and production operations must be completed before calling the service live.
