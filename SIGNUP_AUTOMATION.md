# SAD / Forge automated signup plan

## Goal
Allow remote Forge alpha learners to complete signup without an Owner manually creating every account, while preserving the existing SAD authority model.

## Default enrollment mode
Invite-only self-service enrollment.

1. Owner generates a one-time or limited-use invite.
2. Learner opens the HTTPS Forge endpoint.
3. Learner submits invite code, username, password, display name, and age-band/guardian fields when required.
4. SAD validates the invite, applies server-owned role/mode defaults, creates the account, records consent metadata, and consumes the invite atomically.
5. Learner receives a normal session and is routed into Forge.

Public open registration remains disabled by default.

## Security requirements
- Client cannot choose privileged roles. Automated signup creates `student` only.
- Invite records are stored outside Git in protected runtime state.
- Invite codes are high-entropy secrets and stored only as salted/derived verifier material where practical.
- Invites have expiry, maximum-use count, creator identity, and revocation state.
- Signup and invite redemption are rate-limited and fail closed.
- Username uniqueness and password policy are enforced server-side.
- No account is created until required consent fields are present.
- Child/teen enrollment must not silently infer guardian consent.
- Signup events record metadata only and do not store plaintext passwords or invite secrets.

## Pilot UX
Mobile-first signup should be a short flow:
1. Invite code
2. Account setup
3. Guardian/consent step when applicable
4. Success -> Forge learning home

## Future commercial modes
After private-alpha evidence and legal/privacy review, the same service can support:
- parent-created family invites
- teacher/classroom cohort invites
- organization seat invites
- paid plan invitation issuance

Do not enable anonymous public signup until abuse controls, privacy/consent language, account recovery, email/guardian verification, deletion/export, and production monitoring are complete.
