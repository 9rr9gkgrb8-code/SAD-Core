# Security model

## Trust boundaries

- Account records, settings, failure reports, and sandbox artifacts are local data
  and are excluded from Git.
- Student and teacher sessions cannot enter owner repair-governance commands.
- Developer sessions can inspect or perform assigned work but cannot exercise owner
  governance.
- Reviewer sessions may approve/reject evidence but cannot apply a live file.
- Local-model traffic is restricted to an HTTP loopback endpoint.
- Automatic repair planning accepts only one JSON-described exact replacement in
  one allow-listed root file. Ambiguous, oversized, unchanged, or malformed plans
  fail closed before testing.
- Repair verification fails closed unless Docker and a digest-pinned, preloaded
  `SAD_SANDBOX_IMAGE` are available.
- Containers run without network, capabilities, privilege escalation, Git
  metadata, or a writable root filesystem. The proposal is mounted read-only;
  process, memory, CPU, time, and temporary-storage limits apply.
- A patch may target exactly one allow-listed root file and must match the source
  hash recorded when its proposal was created.
- Owner live application is permitted only for a successful correlated Forge
  proposal. SAD revalidates the source hash, copies the exact tested target through
  an atomic replacement, verifies the resulting hash, and preserves the original
  under the private proposal directory.
- If live application or dashboard persistence fails, SAD attempts an immediate
  verified rollback. A mismatch or unverifiable rollback is surfaced as an error;
  it is never silently treated as success.
- Live repair application does not invoke Git commit, push, fetch, rebase, merge,
  credentials, or repository-control metadata. Git authority remains host/human.

## Runtime requirement

Docker must be installed and the configured image must already exist locally under
the exact digest in `SAD_SANDBOX_IMAGE`. SAD never pulls an image during repair
verification and never falls back to same-user Python execution. Host-side live
project and Git-topology verification still runs before and after the container.
Human Owner approval remains mandatory before a tested repair is copied into the
local live project.

Automatic repair drafting additionally requires the explicitly configured local
model. If the model is unavailable or cannot return a valid single-edit plan, Forge
returns a failed repair result rather than testing or applying guessed code.

## Reporting

Do not include passwords, tokens, private conversation data, student records, or
live failure evidence in a public issue. Report suspected vulnerabilities privately
to the repository owner.
