# SAD + Forge Beta Gap Tracker

This is a launch tracker, not a completion claim.

## Blocking before public Beta

- [ ] Integrate and verify the observable context-ladder change after its PR passes review/CI.
- [ ] Finish an automated review/policy gate without weakening human review/approval boundaries.
- [ ] Capture real SAD Chat screenshot from a running build.
- [ ] Capture real Owner/Developer dashboard screenshot from a running build.
- [ ] Capture real Forge learning/quest screenshot from a running build.
- [ ] Capture real governed approval or controlled-repair screenshot from a running build.
- [ ] Complete `BETA_ACCEPTANCE.md` on intended Windows/phone/audio/network hardware.
- [ ] Run all automated gates on the exact release-candidate commit.
- [ ] Confirm first-time evaluator can follow `BETA_QUICKSTART.md` without owner intervention.
- [ ] Publish `v0.5.0-beta.1` only as a GitHub pre-release after the blockers above are cleared.

## Beta hardening / high priority

- [ ] Add Beta-specific end-to-end regression coverage for the evaluator journey where it can be safely automated.
- [ ] Ensure dashboard presentation makes failure → suggestion → isolated repair → Owner decision easy to understand.
- [ ] Verify Forge homework, progressive hints, mastery/check-work, XP/ranks/companion progression, and persistent progress as one coherent user journey.
- [ ] Verify uncertainty/verification messaging for advanced tutoring paths.
- [ ] Verify child-facing privacy/injection protections through realistic learning inputs.
- [ ] Tighten troubleshooting for local model, Docker, Windows protection, TLS/mobile pairing, Voice services, and recovery.

## Public launch/discoverability

- [ ] Add real screenshots/demo to README.
- [ ] Set repository description and searchable topics in GitHub's About panel.
- [ ] Add a custom social preview image using real product visuals/branding.
- [ ] Publish concise Beta release notes with known limitations.
- [ ] Open a clear feedback path for bugs and evaluator reports without inviting secrets/PII into public issues.

## Explicitly not Beta blockers

- Multi-agent manager/worker orchestration beyond the current governed architecture.
- Broad autonomous machine authority.
- Generic shell/Git/network/package-install tools for agents.
- Production/commercial readiness claims.

Those can be evaluated later without holding the first controlled public Beta hostage.
