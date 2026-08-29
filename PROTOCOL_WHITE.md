# Protocol White

Protocol White is SAD Platform's cooperative verification gate.

Its purpose is to prove that the intended product and governance paths work correctly under authorized, ordinary use **before** Protocol Black attacks the same build.

## Core question

> Can SAD do the right thing when the user, client, extension, verifier, and owner stay inside their intended authority boundaries?

Protocol Black answers the complementary question:

> Does SAD fail safely when inputs, identities, boundaries, or dependencies are hostile, malformed, stale, or compromised?

A release candidate should pass **White first, then Black**. Passing either one alone is insufficient.

## What White verifies

The executable gate runs deterministic existing tests covering:

- platform startup and ordinary authenticated API use;
- private chat and conversation persistence;
- request-directed Personal Study;
- Forge Student quests, hints, mastery, XP, and game UI contracts;
- failure intake, dashboard routing, developer workspace, controlled live repair, and human decision boundaries;
- platform discovery and capability contracts;
- declarative external extensions;
- evidence-bound skill candidates, independent verification, human promotion, versioning, and revocation;
- Tier 2/Tier 3 platform services;
- shared protected runtime persistence;
- SAD/Forge request-result contracts;
- governed tool actions;
- local voice and paired mobile product surfaces.

## What White does not do

Protocol White does not:

- dynamically load extension code into SAD Core;
- grant extension credentials or permissions;
- grant AI or workers Git authority;
- bypass human approval;
- replace Protocol Black;
- replace the complete test suite;
- claim physical Windows, audio, mobile, firewall, backup-media, or local-model UAT.

## Required execution order

```text
python protocol_white.py
python protocol_black.py
```

If Protocol White fails, the build is functionally blocked. Protocol Black may still be run for diagnosis, but the release candidate remains blocked.

If Protocol Black fails, the build is security-blocked even if Protocol White passed.

Only a build that passes both gates, the full suite, release/stability gates, platform preflights, and required Docker/Windows checks may proceed toward human review.
