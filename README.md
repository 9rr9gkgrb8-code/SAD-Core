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

## Local Data

The following stay on the computer and are ignored by Git:

- `settings.json` — saved name and dialogue level
- `failures.json` — local failure reports
- `.sad_sandbox/` — isolated drafts and exported patches
- `local_data/` — optional preferences and memory notes
- `.env` — local environment values, such as a model configuration

To create local preferences, make a `local_data` folder, copy
`local_preferences.example.json` into it as `preferences.json`, and edit your
local copy. Do not commit the `local_data` folder.

## Visible dialogue levels

- `0` — Business
- `1` — Warm
- `2` — Playful

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
