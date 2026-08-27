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

## Learning package

SAD Core now includes two separate learning experiences:

- `personal_study.py` follows the learner's request directly: problem breakdowns,
  method teaching, walkthroughs, work checking, hints, direct answers when asked,
  proofreading, essay editing, rubric review, examples, and substantive word-count
  expansion. It does not force a three-question tutoring loop.
- `forge_student.py` provides game-first homework quests, a four-step hint ladder,
  mastery-gated XP and ranks, companion progression, and boss checks. Homework is
  preserved as a challenge rather than silently replaced with an answer.

## Failure and development control

`failure_dashboard.py` provides one shared owner/developer workflow. SAD, Forge,
tests, and users may automatically submit normalized evidence to the Failure Inbox.
Duplicate signatures merge their evidence. Detection never starts development:
only an explicit owner action can create one development work item or approve
isolated work. Future developers use the same workflow without owner governance.

## Isolation hardening

Sandbox execution validates the resolved proposal path, fingerprints the live
project and protected Git topology before and after execution, removes Git
credentials from the worker environment, checks context root against execution
root, and records ordered evidence. Any integrity or authority failure blocks
approval with `isolation_failed`. Git operations remain host/human controlled.

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
