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
4. Confirm the core SAD server binds only to loopback.
5. If automatic repair or Developer Workspace execution will be tested, require `REPAIR ISOLATION: READY` first.
6. Create separate test accounts for each role. Do not share credentials between testers.
7. If Mobile Preview will be claimed, run `python mobile_doctor.py` on the actual host
   configuration and require `MOBILE GATEWAY: READY` before phone testing.

## Severity and stop rules

- **Critical:** privilege escape, credential exposure, unintended public/wildcard
  binding, unapproved live code application, local-data loss, or cross-account
  private-data exposure. Stop the pilot immediately.
- **High:** a core role cannot complete its primary workflow, security controls fail
  closed incorrectly, a tested-code integrity boundary is bypassed, or accessibility
  prevents keyboard/screen-reader completion. Alpha release is blocked.
- **Medium:** workflow is usable but confusing, inconsistent, or requires an
  undocumented workaround. Fix or explicitly accept before widening the pilot.
- **Low:** cosmetic or wording issue with no material workflow impact.

Alpha acceptance requires zero open Critical or High findings and documented owners
for every accepted Medium finding.

## Owner acceptance

- Complete first-time owner setup and sign in again after restart.
- Create student, teacher, developer, reviewer, and viewer accounts.
- Confirm the owner account cannot be accidentally disabled through normal account controls.
- Open the shared Failure Inbox and verify detection alone does not start development.
- Review a failure, explicitly push it, approve isolated work, inspect evidence,
  approve or reject the result, and close the workflow.
- Complete the Developer Workspace Owner scenarios below, including exact-diff review,
  multi-file application, and rollback.
- Confirm every authority-changing action requires the expected human role and explicit action.
- Change the owner password and confirm other sessions are revoked.

## SAD Chat acceptance

Run these scenarios with at least Owner and Student accounts.

- Sign in and confirm **SAD Chat** is available as the normal free-form conversation lane.
- Start a new conversation, send at least three related turns, and verify follow-up context is sensible.
- With the configured local model running, confirm the assistant reports **Local AI** for the reply engine.
- Stop or disable the local model and confirm SAD reports **Built-in dialogue** rather than pretending a model response occurred.
- Start a second conversation and confirm its context does not leak into the first conversation.
- Restart SAD, sign back in, and confirm active conversations and their messages are still available.
- Archive a conversation and confirm it disappears from the active list without deleting unrelated conversations.
- Sign in as a different account and attempt to fetch the first account's known conversation ID; require denial/not-found.
- Confirm ordinary conversation text such as “fix it,” “approve it,” “write the code,” or “merge it” does not invoke repair, Developer Workspace, approval, file, or Git actions.
- Confirm `chat_history.json` is local-only, excluded from Git, and not available from the service-worker cache.
- Confirm a full conversation can be operated using keyboard only and that the message log/status updates are announced sensibly by a screen reader.

## Developer Workspace acceptance

Use a disposable/backed-up project state for the first live-application exercise.

### Scope planning and creation

- Sign in as Owner and enter a real multi-file coding task in **Code Workspace**.
- Select **Plan file scope** and confirm SAD returns file names only; no source changes occur.
- Review the suggested paths, remove one, add one valid new source path, and create the workspace.
- Confirm `.sad_dev/<workspace-id>/worktree` exists locally and is excluded from Git.
- Confirm `.git`, `.github`, `.env`, account/session/progress/failure runtime files, and other protected paths are absent from the coding worktree.
- Attempt to approve `../outside.py`, `.github/workflows/ci.yml`, `.git/config`, `accounts.json`, and `.env`; require refusal.
- Confirm the workspace records the human-approved path list and source hashes before code generation.

### Isolated coding and tests

- As Owner or Developer, select **Generate code + run Docker tests**.
- Confirm the local model edits only approved paths and the live project stays unchanged while generation/testing runs.
- Confirm the workspace shows every changed path and the exact unified diff.
- Confirm the test run uses the reviewed digest-pinned Docker image with network disabled and no same-user local-process fallback.
- Confirm a successful run reaches `tests_passed` only when the full unittest suite exits successfully and host live/Git integrity is unchanged.
- Force a test failure and confirm the workspace reaches `tests_failed`, exposes evidence/output, and has no apply action.
- Stop Docker or invalidate the pinned image and require an isolation-unavailable/fail-closed state with live files unchanged.
- Modify an approved live source after tests but before application; require stale-source refusal.
- Modify the tested worktree after tests but before application; require tested-hash/tamper refusal.

### Owner application and rollback

- Use a passing workspace that updates at least two existing files and, where practical, creates one new file.
- Review the entire exact diff before selecting **YES: Apply tested workspace**.
- Confirm a Developer account cannot call the apply endpoint even with the workspace ID.
- Confirm Reviewer/Viewer cannot apply or execute the workspace.
- As Owner, apply the workspace and verify every live target exactly matches the post-test manifest.
- Confirm a backup exists for every pre-existing changed file and the application receipt reports `git_authority_used: false`.
- Confirm no Git branch, commit, remote, index, or credential operation occurred.
- Select **Rollback applied workspace** and verify every existing file returns to its captured base hash and every newly created file is removed.
- Repeat with a synthetic/controlled second-file write failure and confirm the whole file set is restored rather than leaving a partial application.
- After successful application, alter one live target manually and confirm rollback refuses rather than overwriting newer human work.

### Role separation

- **Developer:** can plan scope, create workspace, execute isolated coding/tests, and inspect evidence; cannot apply/rollback.
- **Reviewer:** can inspect workspace/diff/test evidence; cannot create, execute, apply, or rollback.
- **Viewer:** read-only inspection only.
- **Student/Teacher:** no Developer Workspace visibility or API access.
- Confirm SAD Chat cannot trigger any of these authority-changing operations through conversational wording alone.

## Student acceptance

- Sign in with a student credential and confirm owner/development/Code Workspace controls are absent.
- Use SAD Chat for a normal multi-turn conversation and confirm the Student cannot gain admin/repair/coding authority through chat.
- Use Personal Study for explanation, method teaching, walkthrough, work checking,
  hints, proofreading, essay editing, rubric review, an example, and word-count expansion.
- Confirm graded-work handling follows the selected request rather than forcing a quiz loop.
- Create a Forge quest from homework, request progressive hints, complete a boss
  check, and verify XP is awarded only after mastery conditions are met.
- Reload/restart and verify durable student progress is preserved.
- Confirm replaying completed work does not farm duplicate XP.

## Teacher acceptance

- Sign in with a teacher credential and confirm development/owner/Code Workspace controls are absent.
- View the student roster and each available progress summary.
- Confirm a teacher can create an allowed student account but cannot create a privileged development account.
- Verify one student's progress cannot be mistaken for another student's record.

## Developer acceptance

- Confirm the developer sees the shared development dashboard and Code Workspace but not owner account administration.
- Confirm the developer cannot perform owner-only push, final repair governance, Code Workspace apply/rollback, or account authority actions.
- Prepare and execute an approved Code Workspace and inspect its exact diff/test evidence.
- Where permitted, execute repair work only after required owner isolation approval.
- Confirm Forge/coding evidence does not grant merge, credential, or approval authority.

## Reviewer acceptance

- Confirm the reviewer can inspect/review the appropriate failure/result states and inspect Code Workspace evidence.
- Confirm the reviewer cannot create/execute Code Workspaces, create privileged accounts, or bypass owner push/isolation/application boundaries.
- Verify repair approve/reject decisions are recorded and visible after restart.

## Viewer acceptance

- Confirm the viewer receives read-only development and Code Workspace visibility.
- Attempt each available mutation path and require denial.
- Confirm no student-private, account-secret, chat-history, or workspace-private absolute-path material appears in the viewer surface.

## Mobile Preview acceptance

Run this section on every phone/browser combination that will be claimed as supported.

### Host and TLS

- Run `python mobile_doctor.py` and require `MOBILE GATEWAY: READY`.
- Confirm the normal desktop/core endpoint remains on `127.0.0.1`.
- Confirm the mobile gateway binds only to the configured explicit private/approved
  overlay IPv4 address, never `0.0.0.0` or a public address.
- Confirm the phone trusts the HTTPS certificate and receives no certificate warning.
- Confirm the router is not forwarding the mobile gateway to the public internet.

### Pairing and device trust

- Open the phone URL before pairing and confirm account login is not available until
  the phone is paired.
- From the local Owner Mobile Access screen, create a `learning` pairing code.
- Confirm the 8-digit code expires after five minutes and cannot be reused.
- Enter repeated bad codes and confirm the gateway throttles excessive pairing attempts.
- Pair successfully and confirm the phone then requires a normal SAD account login.
- Revoke the phone from Owner Mobile Access and require the phone to return to the pairing gate.
- Use **Forget this paired phone** and verify local device trust is removed.

### Learning-mode phone

- Pair the phone in `learning` mode and sign in as Student.
- Open SAD Chat, continue a multi-turn conversation, start a second chat, switch between them, and archive one.
- Confirm the phone shows **Local AI** when the host model is available and **Built-in dialogue** when it is not.
- Complete Personal Study and Forge quest/hint/mastery/progress workflows.
- Attempt Code Workspace, dashboard, account, teacher-roster, mobile-admin, failure, and repair routes; require denial at the gateway even if a higher-authority account token is supplied.
- Attempt invented chat subroutes such as `/repair` and require denial, proving the gateway allow-list is exact rather than prefix-wide.

### Full-role phone

- Pair a trusted phone in `full_role` mode.
- Sign in separately as Student, Teacher, Reviewer, Developer, Viewer, and Owner where practical.
- Confirm every role has the same authority it has on desktop, no more and no less.
- Specifically confirm a Student on a full-role paired phone still cannot reach Owner/Code Workspace controls.
- As Developer, confirm Code Workspace planning/execution works but live apply is denied.
- As Owner, inspect a passing Code Workspace diff and verify Owner apply is available only after the same test/hash gates as desktop.
- Confirm Owner repair approval still requires the same Forge evidence and repair-state boundaries.

### PWA / install behavior

- On iPhone/iPad Safari, add SAD Forge to the home screen and launch it standalone.
- On Android, use the browser install/add-to-home-screen flow and launch standalone.
- Confirm SAD Chat and Code Workspace (for an authorized full-role account) open cleanly in standalone mode and controls are not hidden by the keyboard/home indicator.
- Confirm safe-area padding prevents controls from hiding under notches/home indicators.
- Confirm all primary touch controls have comfortable tap targets and forms do not trigger unwanted zoom.
- Toggle phone connectivity and confirm the UI reports offline status.
- Confirm an offline shell may open but private/API functionality fails safely until the host is reachable.
- Confirm no prior chat text, Developer Workspace diff/test data, study output, account data, student record, repair evidence, session token, pairing code, or device credential is available from the service-worker cache.

## Security acceptance

- Attempt a non-loopback bind on the **core API** and require refusal.
- Attempt wildcard/public binding on the **mobile gateway** and require refusal.
- Attempt mobile startup without TLS certificate/key material and require refusal.
- Attempt local-model configuration with a non-loopback or credentialed URL and require refusal.
- Verify repeated incorrect passwords trigger temporary lockout.
- Verify logout invalidates the active account session.
- Verify password change revokes other account sessions.
- Attempt cross-account chat access by known session ID and require refusal/not-found.
- Attempt Developer Workspace scope traversal/protected paths and require refusal.
- Attempt Developer Workspace apply as Developer/Reviewer/Viewer and require refusal.
- Attempt repair or Developer Workspace execution without ready isolation and require a fail-closed result with no same-user fallback.
- Confirm repair/coding containers have no network and use the exact reviewed digest-pinned image.
- Confirm release-integrity checks ignore private `.sad_dev` runtime artifacts while still scanning current release source.
- Confirm release-integrity checks reject retired private-mode implementation residue in the current release tree.

## Accessibility acceptance

Perform the following on login and every role-visible view:

- Complete the primary workflow using keyboard only. Focus must always be visible and navigation order must remain logical.
- Confirm view changes move focus to the new view heading and expose the selected navigation item as current.
- With a screen reader, confirm login errors are announced immediately and normal status updates/generated outputs are announced without stealing control.
- In SAD Chat, confirm the conversation log, New conversation, Archive, history list, composer label, and Send control are understandable.
- In Code Workspace, confirm task/scope fields, workspace list, state, exact diff, test output, and action buttons have understandable labels/status announcements.
- Confirm every input, select, and textarea has an understandable accessible label.
- Confirm data tables announce a meaningful caption and column headers.
- Test at 200% browser zoom and at a narrow mobile-sized viewport without losing a required control or forcing two-dimensional scrolling for ordinary forms.
- Confirm meaning is not communicated by color alone.
- Confirm error text identifies what needs correction rather than relying only on a red visual state.

## Pilot record

For each scenario record:

- candidate commit SHA
- tester role
- operating system and browser
- phone model when Mobile Preview is tested
- paired-device mode when Mobile Preview is tested
- pass/fail
- finding severity
- reproduction steps
- screenshot or log reference when useful
- disposition and responsible owner

## Alpha exit decision

A candidate may be called **Alpha-ready for a controlled local pilot** when:

- CI, full tests, release integrity, and operator preflight are green;
- every required desktop role boundary above passes;
- SAD Chat account isolation and authority-boundary scenarios pass;
- Developer Workspace scope/test/application/rollback boundaries pass if general coding is claimed;
- the accessibility acceptance pass has no blocking finding;
- no Critical or High UAT finding remains open; and
- any automatic-code workflow being claimed as ready has been demonstrated with the real reviewed Docker image on the target machine.

The **Mobile Preview** may be called ready on a particular host/phone combination only
when its mobile preflight and Mobile Preview acceptance section also pass. A blocked or
disabled mobile preview does not make the base loopback Alpha remotely accessible.

Public internet deployment remains outside the Alpha boundary.
