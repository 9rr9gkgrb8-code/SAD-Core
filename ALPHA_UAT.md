# SAD + Forge Alpha User Acceptance Protocol

## Purpose

This protocol is the human acceptance gate for a controlled local Alpha pilot. It
supplements automated unit, security, contract, release-integrity, and accessibility
structure checks. Passing automation alone does not complete UAT.

## Entry conditions

Before a pilot session:

1. Run `python alpha_doctor.py` and require `ALPHA CORE: READY`.
2. Run the repository CI/release gate on the exact candidate commit.
3. Use a disposable or backed-up local data set for the first pilot.
4. Confirm the server binds only to loopback.
5. If repair execution will be tested, require `REPAIR ISOLATION: READY` first.
6. Create separate test accounts for each role. Do not share credentials between
   testers.

## Severity and stop rules

- **Critical:** privilege escape, credential exposure, remote binding, unapproved
  repair execution, local-data loss, or cross-account private-data exposure. Stop
  the pilot immediately.
- **High:** a core role cannot complete its primary workflow, security controls fail
  closed incorrectly, or accessibility prevents keyboard/screen-reader completion.
  Alpha release is blocked.
- **Medium:** workflow is usable but confusing, inconsistent, or requires an
  undocumented workaround. Fix or explicitly accept before widening the pilot.
- **Low:** cosmetic or wording issue with no material workflow impact.

Alpha acceptance requires zero open Critical or High findings and documented owners
for every accepted Medium finding.

## Owner acceptance

- Complete first-time owner setup and sign in again after restart.
- Create student, teacher, developer, reviewer, and viewer accounts.
- Confirm the owner account cannot be accidentally disabled through normal account
  controls.
- Open the shared Failure Inbox and verify detection alone does not start development.
- Review a failure, explicitly push it, approve isolated work, inspect evidence,
  approve or reject the result, and close the workflow.
- Confirm every authority-changing action requires the expected human role and
  explicit action.
- Change the owner password and confirm other sessions are revoked.

## Student acceptance

- Sign in with a student credential and confirm owner/development controls are absent.
- Use Personal Study for explanation, method teaching, walkthrough, work checking,
  hints, proofreading, essay editing, rubric review, an example, and word-count
  expansion.
- Confirm graded-work handling follows the selected request rather than forcing a
  quiz loop.
- Create a Forge quest from homework, request progressive hints, complete a boss
  check, and verify XP is awarded only after mastery conditions are met.
- Reload/restart and verify durable student progress is preserved.
- Confirm replaying completed work does not farm duplicate XP.

## Teacher acceptance

- Sign in with a teacher credential and confirm development/owner controls are absent.
- View the student roster and each available progress summary.
- Confirm a teacher can create an allowed student account but cannot create a
  privileged development account.
- Verify one student's progress cannot be mistaken for another student's record.

## Developer acceptance

- Confirm the developer sees the shared development dashboard but not owner account
  administration.
- Confirm the developer cannot perform owner-only push, final governance, or account
  authority actions.
- Where permitted, execute only work that already has the required owner isolation
  approval.
- Confirm Forge evidence does not grant merge, credential, or approval authority.

## Reviewer acceptance

- Confirm the reviewer can inspect/review the appropriate failure and result states.
- Confirm the reviewer cannot create privileged accounts or bypass owner push and
  isolation-approval boundaries.
- Verify approve/reject decisions are recorded and visible after restart.

## Viewer acceptance

- Confirm the viewer receives read-only development visibility.
- Attempt each available mutation path and require denial.
- Confirm no student-private or account-secret material appears in the viewer surface.

## Security acceptance

- Attempt a non-loopback bind and require refusal.
- Attempt local-model configuration with a non-loopback or credentialed URL and
  require refusal.
- Verify repeated incorrect passwords trigger temporary lockout.
- Verify logout invalidates the active session.
- Verify password change revokes other sessions.
- Attempt repair execution without ready isolation and require a fail-closed result
  with no same-user fallback.
- Confirm repair containers, when enabled, have no network and use the exact reviewed
  digest-pinned image.
- Confirm release-integrity checks reject retired private-mode implementation residue
  in the current release tree.

## Accessibility acceptance

Perform the following on login and every role-visible view:

- Complete the primary workflow using keyboard only. Focus must always be visible and
  navigation order must remain logical.
- Confirm view changes move focus to the new view heading and expose the selected
  navigation item as current.
- With a screen reader, confirm login errors are announced immediately and normal
  status updates/generated outputs are announced without stealing control.
- Confirm every input, select, and textarea has an understandable accessible label.
- Confirm data tables announce a meaningful caption and column headers.
- Test at 200% browser zoom and at a narrow mobile-sized viewport without losing a
  required control or forcing two-dimensional scrolling for ordinary forms.
- Confirm meaning is not communicated by color alone.
- Confirm error text identifies what needs correction rather than relying only on a
  red visual state.

## Pilot record

For each scenario record:

- candidate commit SHA
- tester role
- operating system and browser
- pass/fail
- finding severity
- reproduction steps
- screenshot or log reference when useful
- disposition and responsible owner

## Alpha exit decision

A candidate may be called **Alpha-ready for a controlled local pilot** when:

- CI, full tests, release integrity, and operator preflight are green;
- every role boundary above passes;
- the accessibility acceptance pass has no blocking finding;
- no Critical or High UAT finding remains open; and
- any repair workflow being claimed as ready has been demonstrated with the real
  reviewed Docker image on the target machine.

Internet deployment remains outside the Alpha boundary.
