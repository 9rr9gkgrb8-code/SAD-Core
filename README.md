# SAD — Sandbox Adaptive Dialogue

SAD is a local Python dialogue assistant with a human-controlled repair engine.

## Public SAD Core

The GitHub project can contain:

- Application code and automated tests
- Generic dialogue and safety rules
- Sandbox-only repair workflow
- Public documentation and example configuration

The repair engine follows this sequence:

`failure report → human approval → repeated evidence → repair plan → sandbox draft → tests → human approval → manual patch export → validation`

SAD does not apply changes to its live files automatically.

## Private Local Data

The following stay on the computer and are ignored by Git:

- `settings.json` — saved name and dialogue level
- `failures.json` — local failure reports
- `.sad_sandbox/` — isolated drafts and exported patches
- `private/` — optional personal preferences, memory notes, and private add-ons
- `.env` — local environment values, such as a model configuration

To create a private profile, make a `private` folder, copy
`private_profile.example.json` into it as `profile.json`, and edit your local
copy. Do not commit the `private` folder.

## Visible dialogue levels

- `0` — Business
- `1` — Warm
- `2` — Playful

Adult Mode is a separate session-only local add-on. It stays in `private/` and
is not part of SAD's public core or a visible dialogue level.

## Useful commands

- `help` — show all commands
- `repair status` — group saved failure patterns
- `repair candidates` — show patterns with two human-approved reports
- `repair plans` — show sandbox-only plans for those candidates
- `draft correction` — make a reviewable change only in a sandbox
- `validate proposal` — check an approved patch without applying it

## Run SAD

```powershell
python app.py
```

## Run tests

```powershell
python -m unittest -v
```
