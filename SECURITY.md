# Security model

## Trust boundaries

- Account records, settings, failure reports, and sandbox artifacts are local data
  and are excluded from Git.
- Student and teacher sessions cannot enter owner repair-governance commands.
- Developer sessions can inspect or perform assigned work but cannot exercise owner
  governance.
- Local-model traffic is restricted to an HTTP loopback endpoint.
- Repair verification fails closed unless Docker and a digest-pinned, preloaded
  `SAD_SANDBOX_IMAGE` are available.
- Containers run without network, capabilities, privilege escalation, Git
  metadata, or a writable root filesystem. The proposal is mounted read-only;
  process, memory, CPU, time, and temporary-storage limits apply.
- A patch may target exactly one allow-listed root file and must match the source
  hash recorded when its proposal was created.

## Runtime requirement

Docker must be installed and the configured image must already exist locally under
the exact digest in `SAD_SANDBOX_IMAGE`. SAD never pulls an image during repair
verification and never falls back to same-user Python execution. Host-side live
project and Git-topology verification still runs before and after the container.
Human approval remains mandatory before applying any patch.

## Reporting

Do not include passwords, tokens, private conversation data, student records, or
live failure evidence in a public issue. Report suspected vulnerabilities privately
to the repository owner.
