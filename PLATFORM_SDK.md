# SAD Platform SDK and Local App Contract

SAD Platform Tier 2 adds a controlled integration surface for local applications.
It does **not** add arbitrary plugin execution, remote user impersonation, or AI-owned
credentials.

## Trust model

SAD now distinguishes three principals:

1. **People** use normal SAD account sessions (`Bearer <session-token>`).
2. **Local apps** use scoped machine credentials (`SAD-App <client-id>.<secret>`).
3. **AI modules** receive no principal automatically and cannot inherit either person's
   or app's authority merely by generating text or code.

Machine credentials are deliberately weaker than user credentials in this Alpha tier.
They can discover the platform, negotiate compatibility, and read only explicitly
subscribed metadata events. They cannot access Chat, Study, Forge, Developer Workspace,
repair approval/application, account administration, mobile trust, or Git operations.

## Owner app registration

Owner can use the SAD Platform screen or API to create a local app credential.

Supported machine scopes:

- `platform:discover`
- `platform:catalog`
- `platform:modules`
- `platform:compatibility`
- `platform:events`

The Owner also chooses exact event types when granting `platform:events`.
An empty subscription means no events, not every event.

Creation returns the app secret **once**. SAD stores a salted hash, never the live
secret. Rotation immediately invalidates the old secret. Revocation disables the
client server-side.

Runtime app records live in ignored `platform_clients.json` and must never be
committed.

## Machine endpoints

Machine endpoints exist only on the loopback SAD core API. The mobile gateway rejects
`/v1/platform/client/*` even for a `full_role` paired device.

All machine calls are `POST` and require:

`Authorization: SAD-App <client-id>.<secret>`

Endpoints:

- `/v1/platform/client/manifest`
- `/v1/platform/client/catalog`
- `/v1/platform/client/modules`
- `/v1/platform/client/compatibility`
- `/v1/platform/client/events`

A scope must be present on the stored client record for the matching endpoint.
A machine credential cannot be supplied as a Bearer token to user endpoints.

## Event stream

`platform_events.py` stores a bounded, monotonic, metadata-only local event stream in
ignored `platform_events.json`.

Events intentionally exclude conversation text, generated code, diffs, passwords,
secrets, tokens, student work, and other high-value payloads. Events contain only a
sequence number, event ID, type, timestamp, optional subject ID, and small bounded
metadata object.

Current event types:

- `chat.session.created`
- `chat.message.created`
- `chat.session.archived`
- `development.workspace.created`
- `development.workspace.executed`
- `development.workspace.applied`
- `development.workspace.rolled_back`
- `failure.created`
- `forge.quest.created`
- `forge.quest.completed`
- `platform.client.created`
- `platform.client.rotated`
- `platform.client.revoked`
- `voice.turn.completed`

App event reads are intersected with the exact subscriptions stored on that app.
Owner may also inspect recent event metadata through the Platform screen.

## Capability version negotiation

Platform Core is now `0.2-alpha` with manifest schema version `2`.

Every capability reports:

- `capability_version`
- `lifecycle` (`alpha`, `stable`, or `deprecated`)
- optional `replacement`

A client may call the compatibility endpoint with requirements such as:

```json
{
  "requirements": [
    {"capability_id": "voice:conversation", "min_version": "1.0.0"}
  ]
}
```

SAD answers whether each required capability is visible to that principal and whether
its current version meets the minimum. Hidden capabilities are reported as unavailable,
not leaked through compatibility metadata.

## Python SDK

`sad_sdk.py` is a standard-library-only synchronous helper for local integrations.
It intentionally accepts only loopback core URLs and does not persist credentials.

Example user session:

```python
from sad_sdk import SadLocalClient

sad = SadLocalClient()
sad.login("my-user", "my-password")
print(sad.platform())
reply = sad.voice_turn("What should I check first?")
print(reply["speech_text"])
```

Example machine client:

```python
from sad_sdk import SadLocalClient

app = SadLocalClient(client_id="...", client_secret="...")
manifest = app.app_manifest()
events = app.app_events(after_seq=0)
```

Do not hard-code app secrets in source control. Supply them through a local secret
store or process environment controlled by the host operator.

## Voice client bridge

`POST /v1/voice/turn` is the first voice-client contract. It is intentionally a
**transcript bridge**, not a bundled speech-recognition or speech-synthesis engine.

Input:

```json
{
  "session_id": "optional-existing-chat-session-id",
  "transcript": "spoken words converted to text by the local voice client"
}
```

If `session_id` is omitted, SAD creates a normal account-owned conversation. The
transcript enters the same SAD conversation engine and durable account isolation as
SAD Chat.

Output includes:

- `session_id`
- `reply`
- `speech_text` (text suitable for a future local TTS engine)
- `engine` (`local_model` or `built_in`)
- `input_mode: transcript`
- `output_mode: text_for_local_tts`

The voice bridge never grants tool, code, repair, approval, app-management, or Git
authority. It is conversation transport only.

Learning-mode phones may use `/v1/voice/turn` after normal pairing and user login.
The current gateway still sets `Permissions-Policy: microphone=()` because the PWA has
not yet been given direct browser microphone capture in this milestone. A future
speech-input client can use the same contract without changing SAD's authority model.

## Not implemented yet

This tier does not include:

- arbitrary third-party Python/JavaScript plugin loading;
- an extension marketplace or remote package installation;
- app access to user-private Chat/Study/Forge content;
- app impersonation of a SAD account;
- browser microphone capture;
- bundled speech-to-text or text-to-speech models;
- public-internet app credentials;
- app Git credentials or repository publication authority.

Those require separate reviewed trust boundaries rather than an automatic widening of
this SDK.
