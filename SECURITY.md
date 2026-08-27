# Security model

## Trust boundaries

- Account records, settings, failure reports, and sandbox artifacts are local data
  and are excluded from Git.
- Student and teacher sessions cannot enter owner repair-governance commands.
- Developer sessions can inspect or perform assigned work but cannot exercise owner
  governance.
- Local-model traffic is restricted to an HTTP loopback endpoint.
- Repair workers receive a minimal environment without common credential variables.
- A patch may target exactly one allow-listed root file and must match the source
  hash recorded when its proposal was created.

## Important limitation

The Python proposal directory is an integrity-monitored workspace, not an OS-level
security sandbox. The code detects changes to the live project and Git topology,
but Python alone cannot reliably prevent a hostile child process from accessing the
network, other processes, or files permitted to the current operating-system user.
Run untrusted repair workers in a separate OS/container sandbox with no network,
Git metadata, or credentials. Human approval remains mandatory before applying any
patch.

## Reporting

Do not include passwords, tokens, private conversation data, student records, or
live failure evidence in a public issue. Report suspected vulnerabilities privately
to the repository owner.
