# SAD Platform Tier 2 User Acceptance Protocol

This protocol supplements `ALPHA_UAT.md` for Platform Core v0.2-alpha. It must be run
on the actual deployment host before local-app, event, SDK, or Voice features are
claimed operational outside automated CI.

## Entry conditions

1. Use the exact release-candidate commit.
2. Require repository CI, release gate, and operator preflight green.
3. Use disposable or backed-up runtime data for the first exercise.
4. Confirm the SAD core API is loopback-only.
5. Create separate Owner and Student test accounts.
6. Keep app secrets out of screenshots, logs, source control, shell history, and issue
   reports.

## Stop conditions

Stop immediately for any of the following:

- machine credential accepted as a human Bearer session;
- non-Owner ability to create/rotate/revoke app credentials;
- app access to Chat, Voice, Study, Forge, coding, repair, account, or mobile-admin
  endpoints;
- app secret appearing in persisted registry/list output, browser storage, PWA cache,
  event history, or public log;
- event payload containing conversation text, generated code/diff, credentials, tokens,
  student work, or other unexpected private content;
- machine-client endpoint reachable through the paired mobile gateway;
- compatibility negotiation revealing a capability outside the requesting principal's
  role/scope;
- Voice turn reading or continuing another account's conversation;
- non-loopback SDK connection accepted;
- dynamic plugin/extension code execution caused only by registration/discovery.

Any stop condition is Critical/High and blocks the Tier 2 claim.

## Owner app credential acceptance

- Open **SAD Platform** as Owner.
- Confirm Local App Credentials controls are visible only to Owner.
- Create an app with `platform:discover` only.
- Confirm the UI clearly states the secret must be copied now and that SAD stores only
  a hash.
- Copy the credential once, refresh the page, and confirm the secret cannot be retrieved.
- Inspect `platform_clients.json` locally and confirm the raw secret is absent.
- List clients and confirm secret/hash/salt are absent from the API/UI response.
- Attempt to create a client with `development:govern`, `account:manage`, an unknown
  scope, or duplicate scopes and require refusal.
- Rotate the app secret. Confirm the previous credential fails and the new credential
  succeeds for its approved scope.
- Revoke the app. Confirm the rotated credential immediately fails.
- Repeat client creation while signed in as Student, Teacher, Developer, Reviewer, and
  Viewer; require denial for every non-Owner role.

## Machine identity separation

- Create an app with `platform:discover` and `platform:compatibility`.
- Call `/v1/platform/client/manifest` using `SAD-App <client-id>.<secret>` and confirm
  principal kind is `local_app`.
- Confirm its authority model says `user_impersonation: false`, `state_mutation: false`,
  `dynamic_extension_execution: false`, and `git_authority: none`.
- Supply the same SAD-App credential to `/v1/chat/sessions`, `/v1/voice/turn`,
  `/v1/study/plan`, `/v1/forge/quests`, `/v1/dev/workspaces`, repair routes, account
  routes, and mobile-administration routes; require denial.
- Attempt to use the machine secret text as a Bearer token; require denial.
- Confirm no client scope can be used to create another client or manage accounts.

## Event acceptance

- Create one app subscribed only to `failure.created`.
- Produce a Chat message, Forge quest event, failure, and Developer Workspace event.
- Read app events and confirm only `failure.created` is returned.
- Create an app with `platform:events` and an empty event subscription. Generate events
  and confirm it receives none.
- Attempt an unknown event subscription and require refusal.
- Confirm event sequence numbers increase monotonically and `after_seq` resumes after
  the supplied cursor.
- Inspect event records and confirm they contain only event metadata, subject IDs, and
  small approved details. No Chat text, code, diff, password, token, app secret,
  student assignment text, or other high-value payload may appear.
- Confirm Owner event inspection shows the same metadata stream without exposing app
  secrets.
- Corrupt or make the event store unavailable in a controlled test and confirm an
  already-completed primary action is not falsely rolled back merely because auxiliary
  event recording failed. Record the diagnostic separately.

## Capability compatibility acceptance

- As Student, request compatibility for `voice:conversation >= 1.0.0` and
  `development:govern >= 1.0.0`.
- Require Voice compatible and development governance unavailable.
- As Owner, confirm Owner-only Platform app/event capabilities are visible.
- As a machine app with only `platform:compatibility`, require that
  `platform:compatibility` is visible but `platform:events` is unavailable.
- Request an impossibly high minimum version and require `compatible: false` without
  changing authority.
- Supply malformed semantic versions and require refusal.
- Confirm capability lifecycle/version metadata displayed in the Platform UI matches
  the API response.

## Python SDK acceptance

- Run `sad_sdk.py` from a separate local process on the deployment machine.
- Connect to `http://127.0.0.1:8765` and verify health/discovery.
- Attempt private-LAN, public, hostname-other-than-localhost, and credentialed URLs;
  require local SDK construction to refuse them before a network request.
- Verify a user-session SDK instance cannot silently become a machine client.
- Verify a machine-client SDK instance cannot silently become a user session.
- Confirm the SDK stores no credential file and leaves persistence decisions to the
  host operator.

## Voice Client Bridge acceptance

- Sign in as Student and call `/v1/voice/turn` with a transcript and no session ID.
- Confirm SAD creates one normal Student-owned conversation and returns `session_id`,
  `reply`, identical `speech_text`, truthful engine, `input_mode: transcript`, and
  `output_mode: text_for_local_tts`.
- Send a second Voice turn using that session ID and confirm context continues.
- Open SAD Chat and confirm the same conversation/history is visible to that Student.
- Sign in as another account and attempt the first Student's session ID; require
  denial/not-found.
- With the local model available, confirm `local_model`; with it unavailable, confirm
  `built_in` rather than a false model claim.
- Use conversational phrases such as “approve that fix,” “apply it,” or “push it to
  GitHub” and confirm Voice transport performs conversation only.

## Mobile Voice and machine-endpoint acceptance

- Pair a learning-mode phone and sign in normally.
- Call the Voice transcript route and confirm it succeeds as the signed-in user.
- Confirm Chat/Voice/Study/Forge remain within the learning route boundary.
- Attempt `/v1/platform/client/manifest`, `/catalog`, `/modules`, `/compatibility`, and
  `/events`; require gateway denial.
- Repeat machine-client endpoint attempts on a Full Role paired phone and require the
  same gateway denial.
- Confirm full-role human Platform/Code Workspace routes still defer to normal RBAC.
- Confirm the PWA cache contains no Voice transcript/reply, app secret, event response,
  or machine credential.
- Confirm browser microphone permission remains disabled in this milestone; do not
  claim direct in-browser speech capture yet.

## Security-source acceptance

- Run `python -m unittest -v` and require the process/network security-surface test to
  list only the explicitly reviewed network-capable files.
- Confirm `sad_sdk.py` is the only newly admitted network file and its dedicated tests
  prove loopback-only URL validation.
- Confirm no new production file imports dynamic execution helpers or `subprocess`
  outside the pre-existing reviewed process boundary.
- Confirm `platform_clients.json` and `platform_events.json` are ignored by Git and
  excluded from release-source marker scanning.

## Accessibility acceptance

- Operate Platform app creation using keyboard only.
- Confirm Machine scopes and Event subscriptions have fieldset/legend semantics.
- Confirm one-time secret and status changes are announced through accessible status
  regions.
- At 200% zoom and narrow phone-sized viewport, confirm app list, rotate/revoke,
  event list, and capability tags remain usable without losing required controls.
- Confirm no authority or lifecycle meaning is communicated by color alone.

## Exit criteria

Platform Tier 2 may be called ready for a controlled local pilot when:

- exact candidate CI, full tests, release gate, operator preflight, and Docker proof
  are green;
- all applicable cases above pass on the deployment host;
- there are zero open Critical or High findings;
- local-app secrets remain private and revocation/rotation are proven;
- machine-to-human privilege separation is proven;
- event filtering/privacy is proven;
- Voice account isolation is proven;
- the SDK is proven loopback-only;
- mobile machine-client denial is proven on every supported phone configuration.

Direct microphone capture, STT/TTS, dynamic plugins, marketplace/package installation,
public app credentials, and public internet hosting remain outside this acceptance
claim.
